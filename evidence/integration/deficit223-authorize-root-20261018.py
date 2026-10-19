from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prior=read(E/'deficit219-reviewed-code-pins-root-20261018.json')
assert all(sha(R/p)==h for p,h in prior['source_pins'].items())
assert read(E/'deficit219-terminal-root-20261018.json')['exit_code']==0
assert read(E/'deficit219-native-root-20261018.json')['checks']['old_pending_exact']
assert read(E/'centers222-fresh-result-20261018.json')['status']=='LOCAL_PROPOSAL_COMPLETE_UNAPPROVED'
assert all(read(E/'centers222-fresh-result-20261018.json')['metadata_pins_stable'].values())
assert sha(R/'data/first-group-training-esri-v1/annual-window-report.json')=='f85925ebf188675060598352ffaa658d82b6dc6f6a1fb4b9025ec01433c92efc'
assert sha(R/'data/first-group-training-budget/global-ledger.json')=='60ae5217d3c4b4cc59a5806ddda60010e3583122a4a9b64cc95efd297ec5ebf0'
assert not (R/'data/first-group-training-budget/global-ledger.execution.lock').exists()
ui=read(E/'service219-postcollection-ui-20261018.json')
assert ui['source_sha256']=='f85925ebf188675060598352ffaa658d82b6dc6f6a1fb4b9025ec01433c92efc'
record={**prior,'at_utc':datetime.now(timezone.utc).isoformat(),'separate_execution_run':'223',
 'selected_cells':[['southeast_sulawesi',2024]],'maximum_batches':1,'maximum_new_physical_patches':16,
 'supervisor_sha256':sha(E/'deficit223-supervisor-root-20261018.py'),
 'request_file_sha256':sha(E/'deficit223-prepared-request-root-20261018.json'),
 'proposal222_sha256':sha(R/'data/centers222-fresh-20261018/proposal.json'),
 'actual_ui219_sha256':sha(E/'service219-postcollection-ui-20261018.json'),
 'latest_source_sha256':ui['source_sha256'],'historical207_publication_is_current_source':False,
 'prior219_audit_sha256':sha(E/'deficit219-native-root-20261018.json'),
 'cohort_qa_repeated':False,'fresh_guard_required':True,'download_budget_increased':False}
with (E/'deficit223-reviewed-code-pins-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':record['status'],'new_run':'223','maximum_new_physical_patches':16}))
