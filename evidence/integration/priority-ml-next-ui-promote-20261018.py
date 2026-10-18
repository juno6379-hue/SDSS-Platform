"""Promote completed159 read-only candidate pointer; preserve153 receipt and no model approval."""
from pathlib import Path
import json,hashlib,datetime,os
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
read=lambda p:json.loads(p.read_text('utf-8'))
f=read(E/'priority-ml-next-20261018-final-verification.json')
assert f['status']=='FINAL_CANDIDATE_ROW_AND_FILE_PINS_MATCH' and f['file_sha_mismatches']==[]
assert f['candidate_source_identity_cross_split_conflicts']==0 and f['retained_rows_exact'] and f['partition_complete']
paths=['priority-ml-next-snapshot-20261018/annual-window-report.json','priority-ml-next-stage-20261018/candidate.json','priority-ml-next-readiness-20261018/readiness.json']
pins=[f['source_sha256'],f['candidate_sha256'],f['qa_report_sha256']]
for n,h in zip(paths,pins):assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h,n
qa=read(D/paths[2]);assert qa['ready_for_training'] is False and qa['patch_counts_by_split']=={'train':658,'val':217,'test':250} and len(qa['blockers'])==4
folder=D/'first-group-training-priority';pointer=folder/'latest-candidate.json';previous=pointer.read_bytes();prevsha=hashlib.sha256(previous).hexdigest()
assert read(pointer)['source_manifest_sha256']=='9211524656d92f0fcfcdf11f2ec382965e3aeacbc7f80da5b02f4f59784df1e7'
receipt={'schema_version':1,'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'path':n,'sha256':h} for n,h in zip(paths,pins)],'source_manifest_sha256':pins[0],'by_split':qa['patch_counts_by_split'],'blocker_count':4,'scene_split_conflicts':[],'ready_for_training':False,'scientific_accuracy_validated':False,'scope':'FROZEN_1432_ROW_SOURCE_NOT_LATER_COLLECTION','limitations':['Connectivity ancillary witness NOT_CAPTURED_BUDGET; no cap bypass','Later1464 aggregate additions excluded'],'previous_pointer_sha256':prevsha}
raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
for p,b in [(folder/'candidate-receipt-next-20261018.json',raw),(folder/'candidate-pointer-before159-20261018.json',previous),(E/'priority-ml-next-ui-receipt-20261018.json',raw)]:
 with p.open('xb') as s:s.write(b)
temp=folder/'latest-candidate159.tmp'
with temp.open('xb') as s:s.write(raw);s.flush();os.fsync(s.fileno())
assert pointer.read_bytes()==previous,'Concurrent pointer changed; preserve it'
os.replace(temp,pointer)
print(json.dumps({'promoted':True,'eligible':1125,'blockers':4,'ready':False,'previous_pointer_sha256':prevsha,'pointer_sha256':hashlib.sha256(raw).hexdigest()}))
