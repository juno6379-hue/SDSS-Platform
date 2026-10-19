"""Explicit post-reboot continuation; original ledger/pending remain unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
R=Path(__file__).resolve().parents[2]; E=R/'evidence/integration'; D=R/'data'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=E/'priority188-recovery-launch-root-20261018.json'
assert not receipt.exists()
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
m=read(mp);l=read(lp); recovery=read(E/'target187-lock-recovery-root-20261018.json')
assert sha(mp)==recovery['manifest_sha256'] and sha(lp)==recovery['ledger_sha256']
pending={k:v for k,v in l['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert l['additional_maximum_bytes']==4*1024**3 and l['rate_limit_active'] is False
assert l['additional_maximum_bytes']-l['new_charged_bytes']>=2*68157440
base=[sys.executable,str(R/'scripts/collect_training_priority.py'),'--max-batches','2','--continue-unrelated-pending','--priority-province','southeast_sulawesi','--priority-province','gorontalo']
dry=subprocess.run(base,cwd=R,capture_output=True,text=True,encoding='utf-8',check=True)
value=json.loads(dry.stdout);plan=value['priority_plan']
(E/'priority188-recovery-dryrun-root-20261018.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
assert len(plan['selected_jobs'])==2 and all(j['province']=='southeast_sulawesi' and j['key'] not in l['batches'] for j in plan['selected_jobs'])
assert len(m['scenes'])+32<=3000 and sha(mp)==recovery['manifest_sha256'] and sha(lp)==recovery['ledger_sha256']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_NOT_COMPLETED','plan_sha256':plan['plan_sha256'],'selected_jobs':plan['selected_jobs'],'pending_before':pending,'manifest_before_rows':len(m['scenes']),'manifest_before_sha256':sha(mp),'old_rows_canonical_sha256':hashlib.sha256(json.dumps(m['scenes'],sort_keys=True).encode()).hexdigest(),'ledger_before_sha256':sha(lp),'new_charged_before':l['new_charged_bytes'],'budget_remaining_before':l['additional_maximum_bytes']-l['new_charged_bytes'],'new_budget_added':False,'training_started':False,'pending_refund':False,'source_pins':{p:sha(R/p) for p in ['scripts/collect_training_priority.py','scripts/collect_training_parallel.py','backend/app/data/parallel.py']}}
command=base+['--expected-plan-sha256',plan['plan_sha256'],'--execute']
with (E/'priority188-recovery-live-root-20261018-stdout.log').open('xb') as out,(E/'priority188-recovery-live-root-20261018-stderr.log').open('xb') as err:
    p=subprocess.Popen(command,cwd=R,env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
record.update(wrapper_pid=p.pid,command=command)
with receipt.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps({'wrapper_pid':p.pid,'selected_jobs':plan['selected_jobs'],'status':record['status']}),flush=True)
