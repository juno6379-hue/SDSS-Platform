"""One fresh199 inventory review; no collection, reservation or source writes."""
from pathlib import Path
import sys,json,hashlib,time,subprocess
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R),str(R/'.runtime'),str(R/'backend'),str(R/'scripts')]
from backend.app.data.deficit_candidate_guard import prepare_deficit_candidate_jobs
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
E=R/'evidence/integration';req=json.loads((E/'centers205-review-request-root-20261018.json').read_text('utf-8'))
assert sha(R/'backend/app/data/deficit_candidate_guard.py')=='c8eece7cbb0d3fed77f704b65eda9e51fe2e300ea56fdfd4aa020d9c9653204f'
assert not (R/'data/first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
inputs=[R/'data/first-group-training-esri-v1/annual-window-report.json',R/'data/first-group-training-budget/global-ledger.json']
before=[sha(p) for p in inputs];assert before==[req['current_manifest_ref']['sha256'],req['ledger_ref']['sha256']]
started=time.monotonic();result=prepare_deficit_candidate_jobs(R,req)
stable=before==[sha(p) for p in inputs]
record={'at_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-started,'operating_inputs_unchanged':stable,'review':result,'collection_started':False,'training_started':False}
with (E/'centers205-review-result-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2,allow_nan=False)
assert stable
print(json.dumps({'local_checks_passed':result['local_checks_passed'],'issue':result['issue'],'seconds':record['seconds'],'inventory_scan_count':result['inventory_scan_count'],'jobs':len(result['job_proposals']),'execution_supported':result['execution_supported']}),flush=True)
