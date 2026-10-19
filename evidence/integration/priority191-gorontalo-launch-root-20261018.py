"""One Gorontalo job after recovered SE collection/target QA, same budget."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (E/'priority191-gorontalo-launch-root-20261018.json').exists()
qa=read(E/'target189-native-root-20261018.json')
assert qa.get('native_validation_complete') is True, 'Need real189 QA before continuation'
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();m=json.loads(mr);l=json.loads(lr)
pending={k:v for k,v in l['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert l['additional_maximum_bytes']==4*1024**3 and not l['rate_limit_active']
assert l['additional_maximum_bytes']-l['new_charged_bytes']>=68157440
base=[sys.executable,str(R/'scripts/collect_training_priority.py'),'--max-batches','1','--continue-unrelated-pending','--priority-province','southeast_sulawesi','--priority-province','gorontalo']
dry=subprocess.run(base,cwd=R,capture_output=True,text=True,encoding='utf-8',check=True)
value=json.loads(dry.stdout);plan=value['priority_plan'];jobs=plan['selected_jobs']
assert len(jobs)==1 and jobs[0]['province']=='gorontalo' and jobs[0]['key'] not in l['batches']
assert len(m['scenes'])+16<=3000 and mp.read_bytes()==mr and lp.read_bytes()==lr
(E/'priority191-gorontalo-dryrun-root-20261018.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_NOT_COMPLETED','plan_sha256':plan['plan_sha256'],'selected_jobs':jobs,'pending_before':pending,'manifest_before_rows':len(m['scenes']),'manifest_before_sha256':sha(mp),'old_rows_canonical_sha256':hashlib.sha256(json.dumps(m['scenes'],sort_keys=True).encode()).hexdigest(),'ledger_before_sha256':sha(lp),'new_charged_before':l['new_charged_bytes'],'budget_remaining_before':l['additional_maximum_bytes']-l['new_charged_bytes'],'new_budget_added':False,'training_started':False,'pending_refund':False,'source_pins':{p:sha(R/p) for p in ['scripts/collect_training_priority.py','scripts/collect_training_parallel.py','backend/app/data/parallel.py']}}
command=base+['--expected-plan-sha256',plan['plan_sha256'],'--execute']
with (E/'priority191-gorontalo-live-root-20261018-stdout.log').open('xb') as out,(E/'priority191-gorontalo-live-root-20261018-stderr.log').open('xb') as err:
    p=subprocess.Popen(command,cwd=R,env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
record.update(wrapper_pid=p.pid,command=command)
with (E/'priority191-gorontalo-launch-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps({'pid':p.pid,'selected_jobs':jobs,'status':record['status']}),flush=True)
