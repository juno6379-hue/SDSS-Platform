from pathlib import Path
import sys,json,hashlib,datetime
R=Path(__file__).resolve().parents[2]
for p in [R/'backend',R/'scripts']:sys.path.insert(0,str(p))
from collect_targeted_bare import physical_patch_inventory
from app.collection_priority_status import collection_targets
E=R/'evidence/integration';D=R/'data'
source=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json'
raw=source.read_bytes();lr=ledger.read_bytes();manifest=json.loads(raw);state=json.loads(lr)
qa=json.loads((E/'priority177-round9-native-20261018.json').read_text('utf-8-sig'))
assert qa['native_validation_complete'] and qa['native_patches_checked']==16 and qa['native_eligible_patches']==10
counts=collection_targets(manifest,hashlib.sha256(raw).hexdigest())
physical=physical_patch_inventory(R,manifest,state)
assert source.read_bytes()==raw and ledger.read_bytes()==lr
out={'status':'CURRENT_INVENTORY_AND_PHYSICAL_CAP_OBSERVED','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'raw_manifest_sha256':hashlib.sha256(raw).hexdigest(),'ledger_sha256':hashlib.sha256(lr).hexdigest(),
 'collection_targets':counts,'physical_inventory':physical,'new_charged_bytes':state['new_charged_bytes'],
 'remaining_additional_bytes':state['additional_maximum_bytes']-state['new_charged_bytes'],
 'pending':{k:v for k,v in state['batches'].items() if v['status']=='pending'},
 'execution_lock_present':(ledger.with_suffix('.execution.lock')).exists(),
 'training_started':False,'scientific_accuracy_validated':False}
with (E/'priority177-round9-observe-20261018.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({'physical':counts['physical_total'],'eligible':counts['eligible_total'],'gap':counts['cell_gap_total'],'cap_inventory':physical,'remaining':out['remaining_additional_bytes']},ensure_ascii=True))
