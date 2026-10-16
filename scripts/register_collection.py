"""실수집 파일의 해시를 확인한 뒤 출처 데이터셋으로 로컬 카탈로그에 등록한다."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.store import Store


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,nargs='+',required=True)
    parser.add_argument('--id',required=True)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    args=parser.parse_args()
    root=args.data_root.resolve()
    store=Store(root,recover_jobs=False)
    if any(row['id']==args.id for row in store.list('datasets')):
        raise ValueError('기존 데이터셋을 덮어쓸 수 없습니다. 새 id를 지정하십시오.')
    items=[]; verified=0
    for manifest in args.manifest:
        report=json.loads(manifest.read_text(encoding='utf-8'))
        state_path=manifest.parent/'window-state.json'
        state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        for row in report['scenes']:
            if row['status']!='rgb_window_downloaded':
                continue
            key=f"{row['aoi']}-{row['year']}"
            cell=state.get('cells',{}).get(key)
            if cell is None:
                # 격자 수집의 집계 보고서는 각 256 패치에 원본 경로와 실제 해시를 남긴다.
                hashes=row.get('patch_sha256') or {}
                if not hashes.get('image') or not hashes.get('label'):
                    raise ValueError('집계 패치의 영상/라벨 해시 근거가 없습니다.')
                cell={name:{'path':row[field],'sha256':hashes[name]} for name,field in
                      (('image','image_path'),('label','label_path'),('quality','quality_mask_path'))
                      if hashes.get(name) and row.get(field)}
            evidence={}
            for field in ('image','label','quality'):
                if field not in cell:
                    continue
                record=cell[field]
                path=Path(record['path']).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError('등록할 원본이 데이터 루트 내부에 없습니다.')
                digest=hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):
                        digest.update(block)
                if digest.hexdigest()!=record['sha256']:
                    raise ValueError(f'수집 파일 해시 불일치: {key}/{field}')
                evidence[field]={'path':str(path.relative_to(root)),'sha256':record['sha256'],'bytes':path.stat().st_size}
                verified+=1
            items.append({**row,'verified_files':evidence})
    if not items:
        raise ValueError('실제 다운로드와 해시 검증을 통과한 영상이 없습니다.')
    result=store.put('datasets',{'id':args.id,'kind':'source-crop-collection','status':'registered-source-data',
        'training_ready':False,'full_scene_downloaded':False,'items':items,'downloaded_windows':len(items),
        'verified_file_count':verified,'source_manifests':[str(p.resolve().relative_to(root)) for p in args.manifest],
        'readiness_note':'원본 창 수집 기록입니다. 품질·연도별 라벨·패치 수·정규화·독립평가는 별도 검토해야 합니다.'})
    print(json.dumps({'id':result['id'],'downloaded_windows':len(items),'verified_files':verified,'training_ready':False},ensure_ascii=False))


if __name__=='__main__':
    main()
