"""192: one179 product CLI review of190 candidates after191 native-ready."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from app.ml.per_scene_normalization_files import _snapshot
SOURCE_SHA='ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f'
LEDGER_SHA='7839929111f3e70e8b9ba2bda3eb0972bc8c0055bb8c03b9273f4c0b381e353f'
PROPOSAL_SHA='1cda6dd428dfffcca9df4ac690d9f79ca2187fdc953de0dd3b67d0d1226dce92'
BOUNDARY_SHA='de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909'
source=ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
ledger=ROOT/'data/first-group-training-budget/global-ledger.json'
proposal=ROOT/'evidence/integration/bare190-gap-20261018/proposal.json'
boundary=ROOT/'data/first-group-boundaries/selected-six.geojson'
data=ROOT/'data/bare192-review-20261018'
out=ROOT/'evidence/integration/bare192-review-20261018'
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
    assert len(raw)<=2*1024**2
    with path.open('xb') as stream:stream.write(raw)
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def pin(path,sha,cap):
    actual,raw=_snapshot(ROOT,path,cap,'review192',True)
    assert actual==sha,'Root-ready pin changed'
    return raw
started=time.monotonic()
assert not data.exists() and not data.is_symlink()
assert set(p.name for p in out.iterdir())=={'run.py'}
native=json.loads((ROOT/'evidence/integration/priority191-native-root-20261018.json').read_text(encoding='utf-8'))
assert native['status']=='COMPLETED_NATIVE_CHECKED' and native['native_validation_complete'] is True
source_raw=pin(source,SOURCE_SHA,128*1024**2)
ledger_raw=pin(ledger,LEDGER_SHA,8*1024**2)
pin(proposal,PROPOSAL_SHA,2*1024**2);pin(boundary,BOUNDARY_SHA,2*1024**2)
assert digest(source)==SOURCE_SHA and digest(ledger)==LEDGER_SHA
protected=[ROOT/'evidence/integration/bare173-verified-20261018/proposal.json',ROOT/'evidence/integration/bare173-verified-20261018/receipt.json',ROOT/'evidence/integration/bare179-report-20261018.json',ROOT/'data/first-group-training-priority/latest-bare-review.json',ROOT/'data/first-group-training-priority/bare-review179-20261018.json',proposal]
before={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
data.mkdir(exist_ok=False)
for path,raw in [(data/'source.json',source_raw),(data/'ledger.json',ledger_raw)]:
    with path.open('xb') as stream:stream.write(raw)
request={'schema_version':1,'proposal_ref':{'path':proposal.relative_to(ROOT).as_posix(),'sha256':PROPOSAL_SHA},'manifest_ref':{'path':(data/'source.json').relative_to(ROOT).as_posix(),'sha256':SOURCE_SHA},'ledger_ref':{'path':(data/'ledger.json').relative_to(ROOT).as_posix(),'sha256':LEDGER_SHA},'boundary_ref':{'path':boundary.relative_to(ROOT).as_posix(),'sha256':BOUNDARY_SHA}}
request_ref=write(out/'request.json',request)
write(out/'preflight.json',{'status':'ROOT_READY_191_POST_NATIVE_FIXED_INPUTS','at_kst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'request':request_ref,'source_rows':len(json.loads(source_raw)['scenes']),'source_eligible':sum(r.get('quality_status')=='quality_eligible' for r in json.loads(source_raw)['scenes']),'protected_pins':before,'collector_held_by_root':True,'native191_repeated':False,'product_cli_invocations_authorized':1,'expected_internal_inventory_scans':1})
del source_raw,ledger_raw
command=[sys.executable,'scripts/review_bare_targets179.py','--request',str(out/'request.json'),'--request-sha256',request_ref['sha256'],'--output',str(out/'report.json')]
print('Starting one179 product CLI for37 fixed190 windows',flush=True)
cli_started=time.monotonic();completed=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=1800)
cli_seconds=round(time.monotonic()-cli_started,3)
for name,payload in [('stdout',completed.stdout),('stderr',completed.stderr)]:
    with (out/(name+'.log')).open('xb') as stream:stream.write(payload)
assert completed.returncode==0,('179 CLI blocked',completed.returncode,completed.stderr)
report_raw=(out/'report.json').read_bytes();report=json.loads(report_raw)
assert report['status']=='LOCAL_NATIVE_REVIEW_COMPLETE_EXECUTION_UNAPPROVED' and len(report['targets'])==37
assert report['inventory_scan_count']==1
assert all(report['inventory'][key] is True for key in ['inventory_verified','pending_footprints_verified','source_pins_verified'])
assert report['request']==request
for path,sha,cap in [(source,SOURCE_SHA,128*1024**2),(ledger,LEDGER_SHA,8*1024**2),(data/'source.json',SOURCE_SHA,128*1024**2),(data/'ledger.json',LEDGER_SHA,8*1024**2),(proposal,PROPOSAL_SHA,2*1024**2),(boundary,BOUNDARY_SHA,2*1024**2)]:pin(path,sha,cap)
after={p.relative_to(ROOT).as_posix():digest(p) for p in protected}
assert before==after
assert digest(out/'request.json')==request_ref['sha256']
assert sum(not o['historical_overlap'] for o in report['observations'])==report['historical_clear_count']
assert len(report['targets'])==len(report['observations'])==sum(r['candidates'] for r in report['ui_summary']['summary_by_province'])
clear=[{'index':i,'target_id':t['target_id'],'province':t['province'],'year':t['year'],'bare_pixels':o['native_bare_pixels']} for i,(t,o) in enumerate(zip(report['targets'],report['observations'])) if not o['historical_overlap']]
report_ref={'path':(out/'report.json').relative_to(ROOT).as_posix(),'bytes':len(report_raw),'sha256':hashlib.sha256(report_raw).hexdigest()}
summary={'status':'LOCAL37_NATIVE_SUPPORT_REVIEW_COMPLETE_UNAPPROVED','at_kst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'cli_seconds':cli_seconds,'total_seconds':round(time.monotonic()-started,3),'cli_exit_code':completed.returncode,'product_cli_invocations':1,'inventory_scan_count':report['inventory_scan_count'],'source_sha256':SOURCE_SHA,'ledger_sha256':LEDGER_SHA,'proposal_sha256':PROPOSAL_SHA,'boundary_sha256':BOUNDARY_SHA,'request':request_ref,'report':report_ref,'candidate_total':len(report['targets']),'historical_clear_count':report['historical_clear_count'],'summary_by_province':report['ui_summary']['summary_by_province'],'mutual_overlap_pairs':len(report['candidate_mutual_overlap_pairs']),'native_label_files_read':report['native_label_files_read'],'native_label_bytes_read':report['native_label_bytes_read'],'support_files_verified':report['inventory']['support_files_verified'],'inventory_asset_count':len(report['inventory']['assets']),'inventory_bytes_verified':report['inventory'].get('support_bytes_verified'),'pending':report['inventory']['pending'],'clear_targets_for_root_revalidation':clear,'protected_pins_after':after,'operational_source_and_ledger_stable':True,'snapshot_inputs_stable':True,'old50report_and_pointer_preserved':before==after,'UI_publication_performed':False,'collection_executed':False,'network_requests':0,'source_or_ledger_writes':0,'native191_repeated':False,'execution_supported':False,'actual_quality_eligible':False,'scientifically_verified_bare':False,'ready_for_training':False,'limitations':['Historical-clear is not mutual independence or collection authorization.','Native labels are weak reference; Sentinel/SCL/B02/scene/budget quality requires fresh175/176/170 checks.','Root must revalidate current input pins before any execution.','New source/ledger snapshots were created; operational original writes are0.']}
write(out/'receipt.json',summary)
write(out/'ui-handoff.json',{'status':'PREPARED_NOT_PUBLISHED','report':report_ref,'request':request,'ui_summary':report['ui_summary'],'mutual_overlap_pairs':len(report['candidate_mutual_overlap_pairs']),'existing_UI_pointer_preserved':True,'published_to_DATA':False,'API_or_browser_verified':False,'note':'Existing UI remains prior50 review. Root/UI owner decides explicit immutable report copy and pointer publication; do not silently replace50 with37.'})
print(json.dumps({k:summary[k] for k in ['status','cli_seconds','candidate_total','historical_clear_count','mutual_overlap_pairs','native_label_files_read','native_label_bytes_read','support_files_verified','report']},ensure_ascii=True),flush=True)
