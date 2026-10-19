"""One bounded local search of two newly acquired expanded weak-label crops."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
sys.path[:0]=[str(R),str(R/'.runtime'),str(R/'backend'),str(R/'scripts')]
from scripts.find_bare_targets173 import discover
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
approval=read(E/'bare215-reviewed-code-pins-root-20261018.json')
assert approval['status']=='REVIEWED_TESTED_LOCAL_LABEL_SEARCH_ONLY'
assert sha(R/'scripts/find_bare_targets173.py')==approval['discovery_source_sha256']
manifest=D/'centers210-fresh-20261018/source.json';boundary=D/'first-group-boundaries/selected-six.geojson'
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
sp='80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a'
assert sha(manifest)==sp and sha(mp)==sp
ledger_pin=sha(lp);assert ledger_pin=='6e9e27b0ba9e4d222f9fde6b1e22f2adfd604701163d8e2c4653617c47af02fc'
rows=read(manifest)['scenes'];assert len(rows)==1699
launch=read(E/'deficit209-launch-root-20261018.json');keys={j['key'] for j in launch['selected_jobs']}
refs={}
for row in rows[1667:]:
    assert row['province']=='southeast_sulawesi' and any(k in row['image_path'] for k in keys)
    crop=row['source_window']['raw_source_crops']['raw-esri_io.tif']
    path=Path(crop['path']);path=path if path.is_absolute() else R/path
    value={'path':path.relative_to(R).as_posix(),'sha256':crop['sha256']}
    if value['path'] in refs:assert refs[value['path']]==value
    refs[value['path']]=value
assert len(refs)==2
folder=D/'bare215-new209-20261018';folder.mkdir(exist_ok=False)
started=time.monotonic()
result=discover(R,manifest,sp,boundary,sha(boundary),limits={'max_files':2,'max_total_bytes':16*1024**2,'max_windows':512,'max_candidates':50},window_stride=128,provinces=['southeast_sulawesi'],label_refs=list(refs.values()))
assert sha(mp)==sp and sha(lp)==ledger_pin
assert result['local_label_crops_read']==2 and result['execution_supported'] is False and result['network_requests']==0
proposal=folder/'proposal.json'
with proposal.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
record={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'LOCAL_NEW_LABEL_SEARCH_COMPLETE_UNAPPROVED','seconds':time.monotonic()-started,'source_manifest_sha256':sp,'ledger_sha256':ledger_pin,'selected_refs':list(refs.values()),'proposal_sha256':sha(proposal),'label_crops_read':result['local_label_crops_read'],'label_bytes_read':result['label_bytes_read'],'windows_scanned':result['windows_scanned'],'qualified_dense_inside_windows':result['qualified_dense_inside_windows'],'ranked_candidates':len(result['ranked_windows']),'operating_source_and_ledger_unchanged':True,'remote_requests':0,'collection_executed':False,'training_executed':False}
with (E/'bare215-new209-result-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=True),flush=True)
