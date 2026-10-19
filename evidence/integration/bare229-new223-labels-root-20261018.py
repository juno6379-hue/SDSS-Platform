"""One bounded local search of one newly acquired expanded weak-label crops."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
sys.path[:0]=[str(R),str(R/'.runtime'),str(R/'backend'),str(R/'scripts')]
from scripts.find_bare_targets173 import discover
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
approval=read(E/'bare229-reviewed-code-pins-root-20261018.json')
assert approval['status']=='REVIEWED_TESTED_LOCAL_LABEL_SEARCH_ONLY'
assert sha(R/'scripts/find_bare_targets173.py')==approval['discovery_source_sha256']
manifest=D/'priority164-guarded227-20261018/source.json';boundary=D/'first-group-boundaries/selected-six.geojson'
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
sp='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert sha(manifest)==sp and sha(mp)==sp
ledger_pin=sha(lp);assert ledger_pin=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
rows=read(manifest)['scenes'];assert len(rows)==1715
launch=read(E/'deficit223-launch-root-20261018.json');keys={j['key'] for j in launch['selected_jobs']}
refs={}
for row in rows[1699:]:
    assert row['province']=='southeast_sulawesi' and any(k in row['image_path'] for k in keys)
    crop=row['source_window']['raw_source_crops']['raw-esri_io.tif']
    path=Path(crop['path']);path=path if path.is_absolute() else R/path
    value={'path':path.relative_to(R).as_posix(),'sha256':crop['sha256']}
    if value['path'] in refs:assert refs[value['path']]==value
    refs[value['path']]=value
assert len(refs)==1
folder=D/'bare229-new223-20261018';folder.mkdir(exist_ok=False)
started=time.monotonic()
result=discover(R,manifest,sp,boundary,sha(boundary),limits={'max_files':1,'max_total_bytes':8*1024**2,'max_windows':256,'max_candidates':50},window_stride=128,provinces=['southeast_sulawesi'],label_refs=list(refs.values()))
assert sha(mp)==sp and sha(lp)==ledger_pin
assert result['local_label_crops_read']==1 and result['execution_supported'] is False and result['network_requests']==0
proposal=folder/'proposal.json'
with proposal.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
record={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'LOCAL_NEW_LABEL_SEARCH_COMPLETE_UNAPPROVED','seconds':time.monotonic()-started,'source_manifest_sha256':sp,'ledger_sha256':ledger_pin,'selected_refs':list(refs.values()),'proposal_sha256':sha(proposal),'label_crops_read':result['local_label_crops_read'],'label_bytes_read':result['label_bytes_read'],'windows_scanned':result['windows_scanned'],'qualified_dense_inside_windows':result['qualified_dense_inside_windows'],'ranked_candidates':len(result['ranked_windows']),'operating_source_and_ledger_unchanged':True,'remote_requests':0,'collection_executed':False,'training_executed':False}
with (E/'bare229-new223-result-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=True),flush=True)
