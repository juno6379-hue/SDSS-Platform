"""One explicitly bounded SE target, after round188 QA; preserve crash outcome."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
qa=read(E/'priority188-native-root-20261018.json')
assert qa['native_validation_complete'] and not any(qa['external_metadata_changed_during_audit'].values())
assert not (E/'target189-launch-root-20261018.json').exists()
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mraw=mp.read_bytes();lraw=lp.read_bytes();l=json.loads(lraw)
pending={k:v for k,v in l['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert l['additional_maximum_bytes']==4*1024**3 and not l['rate_limit_active']
assert l['additional_maximum_bytes']-l['new_charged_bytes']>=68157440
folder=D/'target189-recovery-20261018';folder.mkdir(exist_ok=False)
snapshot=folder/'source.json';snapshot.write_bytes(mraw)
request=read(E/'target187-request-20261018.json')
request['plan']['current_manifest_ref']={'path':snapshot.relative_to(R).as_posix(),'sha256':sha(snapshot)}
request['ledger_ref']={'path':lp.relative_to(R).as_posix(),'sha256':hashlib.sha256(lraw).hexdigest()}
assert len(request['plan']['targets'])==1 and request['plan']['targets'][0]['province']=='southeast_sulawesi'
request_path=E/'target189-request-root-20261018.json'
with request_path.open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
assert mp.read_bytes()==mraw and lp.read_bytes()==lraw
command=[sys.executable,'-X','faulthandler',str(R/'scripts/collect_targeted_bare.py'),'--request',str(request_path),'--expected-request-sha256',pin,'--execute']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_PREFLIGHT_NOT_COMPLETED','manifest_before_sha256':sha(mp),'ledger_before_sha256':sha(lp),'source_rows_before':len(json.loads(mraw)['scenes']),'pending_before':pending,'request_sha256':pin,'command':command,'new_budget_added':False,'training_started':False,'source_pins':{p:sha(R/p) for p in ['scripts/collect_targeted_bare.py','backend/app/data/targeted_live_guards.py','backend/app/data/targeted_bare_plan.py','backend/app/data/parallel.py']}}
started=time.monotonic()
with (E/'target189-live-root-20261018-stdout.log').open('xb') as out,(E/'target189-live-root-20261018-stderr.log').open('xb') as err:
    p=subprocess.Popen(command,cwd=R,env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    record['pid']=p.pid
    with (E/'target189-launch-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pid':p.pid,'status':record['status']}),flush=True)
    code=p.wait()
record.update(status='PROCESS_TERMINATED_OUTCOME_REQUIRES_STDOUT_AND_LEDGER_REVIEW',exit_code=code,seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),lock_present=(D/'first-group-training-budget/global-ledger.execution.lock').exists())
with (E/'target189-process-terminal-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'exit_code':code,'seconds':record['seconds'],'lock_present':record['lock_present']}),flush=True)
