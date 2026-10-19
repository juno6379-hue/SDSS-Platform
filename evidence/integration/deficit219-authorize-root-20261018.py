from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=read(E/'inventory218-freeze-20261018.json')
assert freeze['status']=='IMPLEMENTED_TESTED_SYNTHETIC_NOT_OPERATIONALLY_REEXECUTED'
assert freeze['related_tests']['passed']==108 and freeze['focused_tests']['passed']==38
for item in freeze['source_pins']+freeze['test_pins']+freeze['logs']+freeze['reconstructed_archives']+[freeze['documentation'],freeze['reconstruction_record']]:
 assert sha(R/item['path'])==item['sha256'] and (R/item['path']).stat().st_size==item['bytes']
prior=read(E/'deficit211-reviewed-code-pins-root-20261018.json')
new={x['path']:x['sha256'] for x in freeze['source_pins']}
pins={**prior['source_pins'],**new}
assert all(sha(R/p)==h for p,h in pins.items())
assert read(E/'deficit211-terminal-root-20261018.json')['exit_code']==2
assert not (R/'data/first-group-training-budget/global-ledger.execution.lock').exists()
assert sha(R/'data/first-group-training-esri-v1/annual-window-report.json')=='80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a'
assert sha(R/'data/first-group-training-budget/global-ledger.json')=='6e9e27b0ba9e4d222f9fde6b1e22f2adfd604701163d8e2c4653617c47af02fc'
record={**prior,'at_utc':datetime.now(timezone.utc).isoformat(),'separate_execution_run':'219',
 'source_pins':pins,'maximum_batches':1,'maximum_new_physical_patches':16,
 'selected_cells':[['southeast_sulawesi',2024]],'fresh_guard_required':True,
 'unit218_freeze_sha256':sha(E/'inventory218-freeze-20261018.json'),
 'unit218_focused_tests':freeze['focused_tests'],'unit218_related_tests':freeze['related_tests'],
 'resource_profile':'DEFICIT_LOCAL_SUPPORT_3G_V1','local_support_bytes':3*1024**3,
 'remote_download_budget_increased':False,'historical211_failure_preserved':True,
 'supervisor_sha256':sha(E/'deficit219-supervisor-root-20261018.py'),
 'request_file_sha256':sha(E/'deficit219-prepared-request-root-20261018.json'),
 'root_218_review':['14 freeze pins','minimal diff vs exact reconstructed original SHA',
 'unchanged success/fail execution predicate and pre-reservation cleanup',
 'fixed3GiB aggregate cap within existing4GiB function range,default2GiB unchanged',
 'safe optional CLI issue/count/byte contract and Temp actual CLI regressions',
 'source JSON/individual raster/COG/global budget/pending/overlap/quality constraints unchanged']}
with (E/'deficit219-reviewed-code-pins-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':record['status'],'new_run':'219','maximum_new_physical_patches':16}))
