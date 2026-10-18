"""Read saved stage witnesses only; no replay, URL fetch or signed query output."""
import hashlib,json,sys
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from app.data.references import esri_annual_plan
E=ROOT/'evidence/integration';D=ROOT/'data'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
launch=read(E/'priority-collection-round2-launch-20261018.json')
proof=[]
for selected in launch['selected_jobs']:
    folder=D/'first-group-training-esri-v1/sources'/selected['key']
    report=read(folder/'annual-window-report.json');terminal=read(folder/'worker-result.json')
    for row in report['scenes']:
        scene=row.get('scene_id');tile=esri_annual_plan(int(row['year']),scene) if scene else None
        public=urlsplit(tile['url']) if tile else None
        proof.append({'key':selected['key'],'scene_id':scene,'year':row['year'],'status':row['status'],
            'candidate_selection_statuses':[r.get('status') for r in row.get('candidate_selection',[])],
            'stac_saved':bool(row.get('stac_item')),'calibration_saved':bool(row.get('calibration')),
            'source_crop_count':len(row.get('source_crops',{})),'label_first_preview_present':'label_first_preview' in row,
            'first_ref_source_host':public.hostname if public else None,'first_ref_source_path':public.path if public else None,
            'query_and_fragment_emitted':False,
            'error_category':row.get('error',{}).get('category') or terminal.get('error',{}).get('category'),
            'recorded_center_outside_COG':('AOI 중심점이 COG 범위 밖' in json.dumps(row,ensure_ascii=False)),
            'stage_inference':'SCL_CANDIDATE_SELECTED_AND_CALIBRATION_SAVED_THEN_EARLY_ESRI_LABEL_FETCH_BEFORE_FIRST_CROP',
            'stage_is_explicit_runtime_field':False,
            'inference_basis':'collector source ordering: label_first fetch precedes raw-esri crop and label_first_preview; no raw crops/preview survived',
            'terminal_charged_bytes':terminal['charged_bytes']})
result={'schema_version':1,'recorded_at':datetime.now().astimezone().isoformat(),'observations':proof,
    'collector_source_sha256':hashlib.sha256((ROOT/'scripts/collect_samples.py').read_bytes()).hexdigest(),
    'HTTP_requests':0,'collector_replayed':False,'source_or_ledger_writes':0,
    'limits':['Stage is a saved-witness/source-order inference, not a newly instrumented runtime stage or network reproduction.',
        'Public source hostname/path only; signed query/fragment not read out or written.',
        'No bbox/COG center guard is relaxed; no retry or candidate expansion is performed.']}
path=E/'priority-collection-independent-round2-stage-20261018.json'
with path.open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
print(json.dumps({'observations':len(proof),'HTTP_requests':0,'source_writes':0},ensure_ascii=True))
