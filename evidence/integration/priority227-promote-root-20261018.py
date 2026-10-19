"""Publish only completed pinned QA; preserve prior pointer and source bytes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
sys.path.insert(0,str(R/'backend'))
from app.collection_priority_status import candidate_quality
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=D/'priority164-guarded227-20261018';eb=E/'priority164-guarded227-20261018'
summary=read(eb/'summary.json')
assert sha(eb/'summary.json')=='99927a8a0e7559feda77191308fe7f51221e1d39796fc4f8685384752d26eb85'
assert sha(eb/'handoff-verification.json')=='9c7327cc09b4e26688966f0a7bfea1440fe63b0ad1deda9d99e7af6afb9874f6'
ledger=D/'first-group-training-budget/global-ledger.json';ledger_before=sha(ledger)
assert ledger_before=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
assert summary['source_row_count']==1715 and summary['candidate_row_count']==1699
assert summary['candidate_eligible']=={'train':816,'val':276,'test':250}
assert summary['status']=='PINNED_CANDIDATE_QA_COMPLETED' and summary['file_sha_mismatches']==0
assert summary['remaining_source_identity_conflicts']==0 and summary['training_executed'] is False
assert summary['ready_for_training'] is False and summary['observed_gate_ready_for_training'] is False
for name,value in summary['outputs'].items():assert sha(Path(name))==value['sha256'],name
source=read(base/'source.json');candidate=read(base/'stage/candidate.json');plan=read(eb/'split-plan.json');qa=read(base/'qa/readiness.json')
retained=plan['retained_row_indexes'];excluded=plan['excluded_row_indexes']
assert sorted(retained+excluded)==list(range(len(source['scenes']))) and len(set(retained+excluded))==len(source['scenes'])
assert candidate['scenes']==[source['scenes'][i] for i in retained]
assert qa['patch_counts_by_split']==summary['candidate_eligible'] and qa['blockers']==summary['candidate_blockers'] and qa['ready_for_training'] is False
current=D/'first-group-training-esri-v1/annual-window-report.json';current_pin=sha(current)
assert current_pin==summary['source_sha256']==sha(base/'source.json')
folder=D/'first-group-training-priority';pointer=folder/'latest-candidate.json';prior=pointer.read_bytes();old=json.loads(prior)
assert old['by_split']=={'train':813,'val':276,'test':250} and old['source_manifest_sha256']=='80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a'
assert hashlib.sha256(prior).hexdigest()=='ac6827a1841fd657c430c2a4953aae6089dc4322041dfad87b20fbd1e751c12a'
paths=[base/'source.json',base/'stage/candidate.json',base/'qa/readiness.json']
receipt={'schema_version':1,'recorded_at':datetime.now(timezone.utc).isoformat(),'files':[{'path':p.relative_to(D).as_posix(),'sha256':sha(p)} for p in paths],'source_manifest_sha256':current_pin,'by_split':qa['patch_counts_by_split'],'blocker_count':len(qa['blockers']),'scene_split_conflicts':[],'ready_for_training':False,'scientific_accuracy_validated':False,'scope':'FROZEN_1715_ROW_SOURCE_NOT_LATER_COLLECTION','limitations':['Connectivity witness '+summary['connectivity_capture_status']+'; no gate bypass','Weak labels are not independent ground truth; no training or registry approval'],'previous_pointer_sha256':hashlib.sha256(prior).hexdigest()}
raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
for path,payload in [(folder/'candidate-pointer-before227-20261018.json',prior),(folder/'candidate-receipt227-20261018.json',raw)]:
    with path.open('xb') as f:f.write(payload)
tmp=folder/'latest-candidate227.tmp'
with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert pointer.read_bytes()==prior and sha(current)==current_pin
os.replace(tmp,pointer)
view=candidate_quality(D,current_pin,lambda p,h:sha(p)==h)
assert view['available'] and view['source_matches_current_manifest'] and view['eligible_total']==sum(summary['candidate_eligible'].values()) and view['ready_for_training'] is False
assert sha(ledger)==ledger_before and sha(current)==current_pin
result={'status':'COMPLETED_QA_PUBLISHED_AND_READER_VERIFIED','recorded_at':datetime.now(timezone.utc).isoformat(),'pointer_sha256':sha(pointer),'previous_pointer_preserved':True,'exact_retained_rows':True,'partition_complete':True,'file_sha_mismatches':0,'source_snapshot_sha256':current_pin,'candidate_view':view,'training_started':False,'registry_written':False,'source_or_ledger_written':False}
with (E/'priority227-publication-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=True),flush=True)
