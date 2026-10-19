"""Exactly one pinned local179 review after232 code approval; never dispatch."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
sys.path[:0]=[str(R),str(R/'.runtime'),str(R/'backend'),str(R/'scripts')]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
approval=read(E/'bare234-reviewed-code-pins-root-20261018.json')
assert approval['status']=='REVIEWED_TESTED_LOCAL_FULL_REVIEW_ONLY'
assert all(sha(R/k)==h for k,h in approval['source_pins'].items())
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
request_path=E/'bare234-prepared-request-root-20261018.json'
assert sha(request_path)==approval['request_file_sha256']
request=read(request_path)
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
pins={'source':sha(mp),'ledger':sha(lp),'request':sha(request_path)}
assert pins['source']==request['manifest_ref']['sha256'] and pins['ledger']==request['ledger_ref']['sha256']
assert request['schema_version']==2 and request['local_support_profile']==approval['local_support_profile']
assert not (E/'bare234-report-root-20261018.json').exists()
from scripts.review_bare_targets179 import review
started=time.monotonic();result=None;error=None
print(json.dumps({'status':'STARTED_ONE_LOCAL_FULL_REVIEW','at':datetime.now(timezone.utc).isoformat(),'network_requests':0}),flush=True)
try:
    result=review(R,request)
    assert result['inventory_scan_count']==1 and result['execution_supported'] is False
    assert result['network_requests']==0 and result['source_or_ledger_writes']==0
    payload=(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    assert len(payload)<=2*1024**2,'LOCAL_REVIEW_OUTPUT_LIMIT'
    assert sha(mp)==pins['source'] and sha(lp)==pins['ledger'] and sha(request_path)==pins['request']
    with (E/'bare234-report-root-20261018.json').open('xb') as f:f.write(payload)
except Exception as exc:
    code=str(exc);error=code if re.fullmatch('[A-Z_]{1,80}',code) else 'LOCAL_FULL_REVIEW_FAILED'
stable={'source':sha(mp)==pins['source'],'ledger':sha(lp)==pins['ledger'],'request':sha(request_path)==pins['request']}
record={'status':'LOCAL_FULL_REVIEW_COMPLETE_EXECUTION_UNAPPROVED' if result is not None and error is None and all(stable.values()) else 'LOCAL_FULL_REVIEW_BLOCKED',
 'at_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-started,'issue':error,
 'pins_before':pins,'pins_stable_after':stable,'network_requests':0,'collection_started':False,
 'inventory_scan_count':result['inventory_scan_count'] if result is not None else None,
 'report_sha256':sha(E/'bare234-report-root-20261018.json') if (E/'bare234-report-root-20261018.json').exists() else None,
 'targets':len(result['targets']) if result is not None else None,
 'historical_clear_count':result['historical_clear_count'] if result is not None else None}
with (E/'bare234-result-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record),flush=True)
if record['status']!='LOCAL_FULL_REVIEW_COMPLETE_EXECUTION_UNAPPROVED':raise SystemExit(2)
