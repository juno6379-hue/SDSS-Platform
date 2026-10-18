"""Promote verified164 cohort without registry, training or source mutation."""
from pathlib import Path
import json,hashlib,os,datetime
r=Path(__file__).resolve().parents[2];d=r/'data';e=r/'evidence/integration'
read=lambda p:json.loads(p.read_text('utf-8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=read(e/'priority164-final-verification-20261018.json')
assert f['status']=='FINAL_PRIORITY164_ROWS_AND_FILE_PINS_MATCH' and not f['file_mismatches'] and f['exact_retained_rows'] and f['partition_complete'] and f['cross_split_source_identity_conflicts']==0
paths=['priority164-cohort-20261018/source.json','priority164-cohort-20261018/stage/candidate.json','priority164-cohort-20261018/qa/readiness.json'];pins=[f['source_sha256'],f['candidate_sha256'],f['qa_report_sha256']]
for p,h in zip(paths,pins):assert sha(d/p)==h,p
qa=read(d/paths[2]);assert qa['ready_for_training'] is False and qa['patch_counts_by_split']=={'train':720,'val':249,'test':250} and len(qa['blockers'])==3
folder=d/'first-group-training-priority';pointer=folder/'latest-candidate.json';prior=pointer.read_bytes();old=read(pointer);assert old['source_manifest_sha256']=='7eac5a54cce152f1f3163e35e8565217b6cbef61b86068150209bb39fa3a9bbe'
receipt={'schema_version':1,'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'path':p,'sha256':h} for p,h in zip(paths,pins)],'source_manifest_sha256':pins[0],'by_split':qa['patch_counts_by_split'],'blocker_count':3,'scene_split_conflicts':[],'ready_for_training':False,'scientific_accuracy_validated':False,'scope':'FROZEN_1536_ROW_SOURCE_NOT_LATER_COLLECTION','limitations':['Connectivity witness NOT_CAPTURED_BUDGET; no gate bypass','Later general/targeted collection excluded'],'previous_pointer_sha256':hashlib.sha256(prior).hexdigest()}
raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
for p,b in [(folder/'candidate-receipt164-20261018.json',raw),(folder/'candidate-pointer-before164-20261018.json',prior),(e/'priority164-ui-receipt-20261018.json',raw)]:
 with p.open('xb') as s:s.write(b)
tmp=folder/'latest-candidate164.tmp'
with tmp.open('xb') as s:s.write(raw);s.flush();os.fsync(s.fileno())
assert pointer.read_bytes()==prior,'Concurrent pointer edit preserved';os.replace(tmp,pointer)
print(json.dumps({'candidate_eligible':1219,'bare_blockers':3,'ready':False,'prior_preserved':True,'pointer_sha256':sha(pointer)}))
