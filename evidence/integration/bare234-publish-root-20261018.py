"""Publish one completed local-only review, preserving the prior receipt bytes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
sys.path.insert(0,str(R/'backend'))
from app.collection_priority_status import bare_target_review
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
result=read(E/'bare234-result-root-20261018.json')
assert result['status']=='LOCAL_FULL_REVIEW_COMPLETE_EXECUTION_UNAPPROVED'
assert result['inventory_scan_count']==1 and all(result['pins_stable_after'].values())
assert result['network_requests']==0 and result['collection_started'] is False
source=D/'first-group-training-esri-v1/annual-window-report.json'
ledger=D/'first-group-training-budget/global-ledger.json'
assert sha(source)==result['pins_before']['source'] and sha(ledger)==result['pins_before']['ledger']
assert not (ledger.parent/'global-ledger.execution.lock').exists()
p=E/'bare234-report-root-20261018.json';raw=p.read_bytes();report=json.loads(raw)
assert len(raw)<=2*1024**2 and sha(p)==result['report_sha256']=='c936575e2937d5c8ec9f1e4675de89eed0f5dbabce26bbd26bea8661c4b18458'
assert report['inventory']['inventory_verified'] and report['inventory']['pending_footprints_verified'] and report['inventory']['source_pins_verified']
assert len(report['targets'])==50 and report['historical_clear_count']==15
assert sum(o['historical_overlap'] for o in report['observations'])==35
assert report['execution_supported'] is False and report['actual_quality_eligible'] is False
folder=D/'first-group-training-priority';pointer=folder/'latest-bare-review.json'
prior=pointer.read_bytes();old=json.loads(prior)
assert old['report']['sha256']=='6d72cfceb04589d59fe55674ca10d79764672dbd09bfb3e4345b69cd67f3009f'
target=folder/'bare-review234-20261018.json'
with target.open('xb') as f:f.write(raw)
receipt={'schema_version':1,'report':{'path':target.relative_to(D).as_posix(),'sha256':sha(target)}}
payload=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
for path,data in [(folder/'bare-review-pointer-before234-20261018.json',prior),(folder/'bare-review-receipt234-20261018.json',payload)]:
    with path.open('xb') as f:f.write(data)
tmp=folder/'latest-bare-review234.tmp'
with tmp.open('xb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
assert pointer.read_bytes()==prior and sha(source)==result['pins_before']['source'] and sha(ledger)==result['pins_before']['ledger']
os.replace(tmp,pointer)
view=bare_target_review(D,result['pins_before']['source'])
assert view['available'] and view['source_matches_current_manifest'] and view['candidate_total']==50
assert view['execution_supported'] is False and view['actual_quality_verified'] is False
assert sha(source)==result['pins_before']['source'] and sha(ledger)==result['pins_before']['ledger']
out={'status':'LOCAL_ONLY_REVIEW_PUBLISHED_READER_VERIFIED','at_utc':datetime.now(timezone.utc).isoformat(),
 'report_sha256':sha(target),'pointer_sha256':sha(pointer),'prior_pointer_sha256':hashlib.sha256(prior).hexdigest(),
 'previous_pointer_preserved':True,'view':view,'source_or_ledger_written':False,'collection_started':False,'training_started':False}
with (E/'bare234-publication-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=True),flush=True)
