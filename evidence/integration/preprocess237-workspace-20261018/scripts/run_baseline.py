"""로컬 수집 보고서로 실제 LCLUC CPU baseline을 실행한다. 외부 데이터 요청은 하지 않는다."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml.service import prepare_dataset, train_model, infer_raster
from backend.app.ml.raster import read, safe_path, assert_aligned
from backend.app.ml.dataset import file_digest
from backend.app.store import Store
import numpy as np


def register_report(report_path, root):
    """기존 실험 결과만 카탈로그에 등록한다. 모델은 반드시 Draft로 유지한다."""
    report_path = safe_path(root,report_path)
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report.get('status') != 'completed_functional_baseline':
        raise ValueError('완료된 baseline 보고서만 등록할 수 있습니다.')
    prepared, trained = report['dataset'], report['training']
    checkpoint = safe_path(root,trained['checkpoint_path'])
    checksum = file_digest(checkpoint)
    if report.get('checkpoint_sha256') and report['checkpoint_sha256'] != checksum:
        raise ValueError('checkpoint SHA256이 실행 보고서와 다릅니다.')
    manifest_path = safe_path(root,prepared['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['version'] != trained['dataset_version']:
        raise ValueError('데이터셋과 모델 버전 연결이 다릅니다.')
    prediction_checksums = [file_digest(safe_path(root,p['classification_path'])) for p in report['predictions']]
    store = Store(root,recover_jobs=False)
    registration = {'operation':'manual_import_existing_baseline','report_path':str(report_path.relative_to(root)),
                    'report_sha256':file_digest(report_path),'registered_at':datetime.now(timezone.utc).isoformat(),
                    'checkpoint_sha256':checksum,
                    'checksum_basis':'verified_against_run_report' if report.get('checkpoint_sha256') else 'computed_at_manual_registration; original report has no checkpoint checksum'}
    # 재실행이 기존 승인상태나 검토 이력을 초기화하지 않도록 등록 ID 충돌은 거부한다.
    ids = {'dataset':prepared['dataset_id'],'model':trained['model_id'],
           'analyses':[f"{report['run_id']}_prediction_{i}" for i in range(len(report['predictions']))]}
    for kind, identifier in [('datasets',ids['dataset']),('models',ids['model'])]+[('analyses',i) for i in ids['analyses']]:
        try:
            store.get(kind,identifier)
        except KeyError:
            continue
        raise ValueError(f'이미 등록된 ID입니다: {kind}/{identifier}')
    store.put('datasets',{**prepared,'id':ids['dataset'],'synthetic':report['synthetic'],'registration':registration})
    store.put('models',{**trained,'id':ids['model'],'status':'Draft','independent_evaluation':False,
                        'synthetic':report['synthetic'],
                        'training_history':trained['history'],
                        'history':[{'status':'Draft','reason':'실자료 기능실험의 수동 등록; 운영 승인 아님','at':registration['registered_at']}],
                        'checkpoint_sha256':checksum,'registration':registration})
    for index,prediction in enumerate(report['predictions']):
        path = safe_path(root,prediction['classification_path'])
        store.put('analyses',{**prediction,'id':ids['analyses'][index],'analysis_type':'classification',
                             'model_id':ids['model'],'synthetic':report['synthetic'],'independent_evaluation':False,
                             'classification_sha256':prediction_checksums[index],'source':'actual_2021_satellite_functional_baseline' if not report['synthetic'] else 'explicit_synthetic_baseline',
                             'quality_warning':'원본 RGB 추론은 SCL 품질 마스크 미적용; 라벨 유효범위와 다릅니다.',
                             'registration':registration})
    receipt={'status':'registered','ids':ids,'registration':registration}
    (report_path.parent/'registration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt


def source_scenes(document, data_root):
    """수집기의 연차 보고서 또는 명시적 prepare 입력 목록을 공통 계약으로 바꾼다."""
    scenes = []
    for row in document.get('scenes', []):
        if row.get('image_path') and row.get('label_path'):
            image = safe_path(data_root, row['image_path'])
            label = safe_path(data_root, row['label_path'])
            scenes.append({'image_path': str(image.relative_to(data_root)), 'label_path': str(label.relative_to(data_root)),
                           'group': str(row.get('group', row.get('aoi', 'unknown'))),
                           'scene_id': row.get('scene_id', row['image_path']),
                           'label_source': row.get('label_source', 'worldcover'),
                           'source': row.get('source', row.get('scene_id', 'unverified')),
                           'license': row.get('license', 'Sentinel-2: Copernicus open access; WorldCover: CC-BY-4.0'),
                           'acquisition_date': row.get('acquisition_date', row.get('datetime')),
                           **({'quality_mask_path':row['quality_mask_path']} if row.get('quality_mask_path') else {})})
    return scenes


def run(args):
    root = args.data_root.resolve()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.run_id):
        raise ValueError('run-id는 영문·숫자·밑줄·하이픈 1~80자여야 합니다.')
    destination = safe_path(root, f'results/{args.run_id}')
    if destination.exists():
        raise ValueError('동일 run-id 결과가 있습니다. 새 run-id를 사용하세요.')
    destination.mkdir(parents=True)
    report = {'run_id': args.run_id, 'status': 'preflight', 'started_at': datetime.now(timezone.utc).isoformat(),
              'input_manifest': str(args.manifest.resolve()), 'synthetic': None,
              'claim': '소규모 파이프라인 기능실증 및 의사라벨 일치도입니다. 독립 실정확도 검증이 아닙니다.'}
    try:
        source = json.loads(args.manifest.read_text(encoding='utf-8'))
        report['input_manifest_sha256'] = file_digest(args.manifest)
        report['synthetic'] = bool(source.get('synthetic', False))
        report['collection_learning_ready'] = source.get('learning_ready')
        report['readiness_scope'] = 'small functional baseline; does not assert 1000-3000 patches or independent scientific validation'
        scenes = source_scenes(source, root)
        report['available_labeled_scenes'] = len(scenes)
        groups = {scene['group'] for scene in scenes}
        if 'unknown' in groups or len(groups) < 3:
            raise ValueError('최소 3개 독립 지역의 영상과 정합 라벨이 필요합니다. 미확보 자료를 생성하지 않습니다.')
        quality = []
        for scene in scenes:
            image, imask, ip = read(safe_path(root,scene['image_path']))
            label, lmask, lp = read(safe_path(root,scene['label_path']))
            assert_aligned(ip,lp)
            valid = imask & lmask & np.isfinite(image).all(0)
            values, counts = np.unique(label[0][valid], return_counts=True)
            quality.append({'group':scene['group'],'image_path':scene['image_path'],'label_path':scene['label_path'],
                            'shape':list(image.shape),'valid_label_pixels':int(valid.sum()),'valid_ratio':float(valid.mean()),
                            'raw_label_counts':{str(int(v)):int(n) for v,n in zip(values,counts)},
                            'image_sha256':file_digest(safe_path(root,scene['image_path'])),
                            'label_sha256':file_digest(safe_path(root,scene['label_path']))})
        report['quality'] = quality
        report['normalization'] = {'scale':args.scale,'offset':args.offset,'basis':'explicit CLI parameters; verify product metadata before scientific validation'}
        if args.check_only:
            report['status'] = 'preflight_passed_no_training'
        else:
            if not report['synthetic']:
                raise ValueError('실자료 신규 학습은 run_experiment.py의 충분성·정규화·라벨 QA gate를 통과해야 합니다. 기존 소규모 baseline은 재학습하지 않습니다.')
            prepared = prepare_dataset({'dataset_id':args.run_id+'_dataset','scenes':scenes,'patch_size':256,
                                        'bands':[1,2,3],'scale':args.scale,'offset':args.offset,
                                        'synthetic':report['synthetic'],'reference_kind':'worldcover_weak_label','seed':args.seed},root)
            trained = train_model({'dataset_path':prepared['manifest_path'],'model_id':args.run_id+'_model',
                                   'epochs':args.epochs,'batch_size':1,'cpu_threads':2,'device':'cpu','seed':args.seed},root)
            predictions = []
            for index, scene in enumerate(scenes):
                predictions.append({'group':scene['group'],'input_image':scene['image_path'],**infer_raster({
                    'image_path':scene['image_path'],'checkpoint_path':trained['checkpoint_path'],
                    'output_id':f'{args.run_id}/predictions/{index}'},root)})
            report.update(status='completed_functional_baseline',dataset=prepared,training=trained,predictions=predictions,
                          checkpoint_sha256=file_digest(safe_path(root,trained['checkpoint_path'])),
                          independent_evaluation=False,target_1000_patches_met=len(prepared['patches'])>=1000,
                          limitations=['고작 3지역 수준의 소규모 표본','WorldCover 의사라벨은 독립 지상정답이 아님',
                                       'RGB 3밴드만 사용; DN 수치 스케일링은 제품 메타데이터 확인 전 물리 반사도로 검증되지 않음',
                                       '수집기 SCL 제외는 라벨 NoData에 반영됨; 원본 영상 추론은 별도 품질 마스크가 없으면 cloud nodata-only',
                                       '추론은 동일 수집 영상에 대한 기능 확인; 별도 일반화 검증 아님'])
    except Exception as exc:
        report.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    output = destination/'baseline-run.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if getattr(args,'register',False) and report['status']=='completed_functional_baseline':
        register_report(output,root)
    print(json.dumps({'status':report['status'],'report_path':str(output),'error':report.get('error')},ensure_ascii=False))
    return 0 if report['status'] in ('completed_functional_baseline','preflight_passed_no_training') else 2


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--manifest',type=Path)
    source.add_argument('--register-report',type=Path,help='이미 완료된 실행 보고서만 등록하며 재학습하지 않음')
    parser.add_argument('--data-root',type=Path,default=PROJECT_ROOT/'data')
    parser.add_argument('--run-id',default='baseline_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    parser.add_argument('--epochs',type=int,default=3)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--scale',type=float,default=.0001)
    parser.add_argument('--offset',type=float,default=0)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--register',action='store_true',help='새 실행이 성공한 경우 카탈로그에 Draft로 등록')
    args=parser.parse_args()
    if args.register_report:
        print(json.dumps(register_report(args.register_report.resolve(),args.data_root.resolve()),ensure_ascii=False))
        return 0
    return run(args)


if __name__=='__main__':
    raise SystemExit(main())
