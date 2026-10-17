"""충분성 gate를 통과한 경우에만 새 의사라벨 실험을 실행한다. 기본 동작은 읽기 전용 QA이다."""
import argparse
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT))
from backend.app.ml.readiness import assess, verify_files, default_policy
from backend.app.ml.service import prepare_dataset, train_model, infer_raster
from backend.app.ml.raster import safe_path
from backend.app.ml.dataset import file_digest


def run(manifests,root,readiness_path,policy=None,execute=False,run_id=None,epochs=20,resume=False,max_seconds=1800,epochs_per_call=20):
    root=root.resolve()
    result=assess([Path(path).resolve() for path in manifests],root,policy)
    result['assessed_at']=datetime.now(timezone.utc).isoformat()
    readiness_path=safe_path(root,readiness_path)
    readiness_path.parent.mkdir(parents=True,exist_ok=True)
    readiness_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not execute or not result['ready_for_training']:
        return result
    if not run_id or not re.fullmatch('[A-Za-z0-9_-]{1,80}',run_id):
        raise ValueError('execute에는 고유한 영문/숫자 run-id가 필요합니다.')
    destination=safe_path(root,f'results/{run_id}')
    if destination.exists() and not resume:
        raise ValueError('기존 실험을 덮어쓰지 않습니다. 새 run-id를 지정하세요.')
    verify_files(result['verified_files'],root)
    if resume:
        previous=json.loads((destination/'experiment.json').read_text(encoding='utf-8'))
        if previous['status'] not in ('paused_training','training_started'):
            raise ValueError('중단된 동일 실험만 재개할 수 있습니다.')
        prepared=previous['dataset']
        # 재개 시 새 계획을 기존 가중치의 실험 범위로 잘못 표시하지 않는다.
        frozen=json.loads(safe_path(root,prepared['manifest_path']).read_text(encoding='utf-8'))['readiness_contract']
        current=result['prepared_payload']['readiness_contract']
        if frozen['policy']!=current['policy'] or {r['path']:r['sha256'] for r in frozen['verified_files']}!={r['path']:r['sha256'] for r in current['verified_files']}:
            raise ValueError('재개 시 이전 실험의 계획·입력 출처를 변경할 수 없습니다.')
    else:
        prepared=prepare_dataset({**result['prepared_payload'],'dataset_id':run_id+'_dataset'},root)
    destination.mkdir(parents=True,exist_ok=True)
    base={'schema_version':1,'run_id':run_id,'status':'training_started','dataset':prepared,
          'model_status':'Draft','independent_evaluation':False,'scientific_accuracy_validated':False,
          'user_full_period_target_met':result['coverage']['available_cells']==36 and result['policy']['required_years']==list(range(2020,2026)),
          'experiment_years':result['policy']['required_years'],'readiness_path':str(readiness_path.relative_to(root))}
    (destination/'experiment.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
    trained=train_model({'dataset_path':prepared['manifest_path'],'model_id':run_id+'_model',
                         'epochs':epochs,'device':'cpu','batch_size':1,'seed':result['policy']['seed'],
                         'resume':resume,'max_seconds':max_seconds,'epochs_per_call':epochs_per_call},root)
    if trained.get('training_state')=='paused':
        report={**base,'status':'paused_training','training':trained,'finished_at':datetime.now(timezone.utc).isoformat()}
        (destination/'experiment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return report
    predictions=[]
    for index,scene in enumerate(result['prepared_payload']['scenes']):
        predictions.append({'province':scene['province'],'year':scene['year'],'group':scene['group'],
                            **infer_raster({'image_path':scene['image_path'],'checkpoint_path':trained['checkpoint_path'],
                                             'normalization':scene['normalization'],'quality_mask_path':scene['quality_mask_path'],
                                             'source_scene':{'scene_id':scene['scene_id'],'image_sha256':scene['image_sha256'],'band_names':result['policy']['band_names']},
                                             'output_id':f'{run_id}/predictions/{index}'},root)})
    accepted=trained['weak_label_experiment_output_accepted']
    report={**base,'schema_version':1,'run_id':run_id,'status':'completed_weak_label_experiment' if accepted else 'completed_rejected_prediction_collapse',
            'model_status':'Draft','independent_evaluation':False,'scientific_accuracy_validated':False,
            'claim':'의사라벨 일치도 실험입니다. 독립 지상정답 정확도나 운영 승인이 아닙니다.',
            'readiness_path':str(readiness_path.relative_to(root)),'readiness_sha256':file_digest(readiness_path),
            'dataset':prepared,'training':trained,'predictions':predictions,'output_accepted':accepted,
            'finished_at':datetime.now(timezone.utc).isoformat()}
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'experiment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,nargs='+',required=True)
    parser.add_argument('--data-root',type=Path,default=PROJECT_ROOT/'data')
    parser.add_argument('--readiness-output',type=Path,default=PROJECT_ROOT/'data/first-group/training-readiness.json')
    parser.add_argument('--plan',type=Path,help='범위/밴드/클래스/패치 기준을 명시한 JSON. 실자료 1000개 하한은 낮출 수 없음')
    parser.add_argument('--write-default-plan',type=Path)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--run-id')
    parser.add_argument('--epochs',type=int,default=20)
    parser.add_argument('--resume',action='store_true',help='동일 dataset/config의 마지막 완료 epoch부터 재개')
    parser.add_argument('--max-seconds',type=float,default=1800,help='호출별 학습/평가 시간 예산; 미완료 epoch는 재개 때 다시 실행')
    parser.add_argument('--epochs-per-call',type=int,default=20)
    args=parser.parse_args()
    if args.write_default_plan:
        args.write_default_plan.write_text(json.dumps(default_policy(),ensure_ascii=False,indent=2),encoding='utf-8')
    policy=json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else None
    result=run(args.manifest,args.data_root,args.readiness_output,policy,args.execute,args.run_id,args.epochs,args.resume,args.max_seconds,args.epochs_per_call)
    print(json.dumps({'status':result['status'],'ready_for_training':result.get('ready_for_training',False),
                      'blocker_count':len(result.get('blockers',[])),'scientific_accuracy_validated':False},ensure_ascii=False))
    return 2 if args.execute and result.get('status')=='blocked' else 0


if __name__=='__main__':
    raise SystemExit(main())
