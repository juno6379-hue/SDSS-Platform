"""Bounded two-SE execution after200 source freeze and205 local proof review."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (E/'deficit206-launch-root-20261018.json').exists()
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded|prepare_priority_candidate164)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
review=read(E/'centers205-review-result-root-20261018.json')
assert review['operating_inputs_unchanged'] and review['review']['local_checks_passed']
assert review['review']['execution_supported'] is False
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();state=json.loads(lr)
assert hashlib.sha256(mr).hexdigest()=='39bb0245e586342bd116f5b052428fcf857fb26eae0ee1413c9c5f5275c40ba9'
assert hashlib.sha256(lr).hexdigest()=='024f5eabb2cadf88af4f34661fab6e6c209bf9aa8d105c2d1fbadf10f1c0dae3'
pending={k:v for k,v in state['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert state['additional_maximum_bytes']==4*1024**3 and not state['rate_limit_active']
assert state['additional_maximum_bytes']-state['new_charged_bytes']>=2*68157440
approval=read(E/'deficit206-reviewed-code-pins-root-20261018.json')
assert approval['status']=='REVIEWED_TESTED_BOUNDED_EXECUTION_APPROVED'
assert all(sha(R/p)==pin for p,pin in approval['source_pins'].items())
request=read(E/'centers205-review-request-root-20261018.json')
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
assert pin==review['review']['request_sha256']
jobs=review['review']['job_proposals']
assert [(j['province'],j['year'],j['nominal_patches']) for j in jobs]==[('southeast_sulawesi',2024,16),('southeast_sulawesi',2021,16)]
assert all(j['key'] not in state['batches'] for j in jobs)
rp=E/'deficit206-request-root-20261018.json'
with rp.open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
assert mp.read_bytes()==mr and lp.read_bytes()==lr
command=[sys.executable,'-X','faulthandler',str(R/'scripts/collect_deficit_guarded.py'),'--request',rp.relative_to(R).as_posix(),'--expected-request-sha256',pin,'--execute']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_PREFLIGHT_NOT_COMPLETED','manifest_before_sha256':sha(mp),'ledger_before_sha256':sha(lp),'source_rows_before':len(json.loads(mr)['scenes']),'pending_before':pending,'request_sha256':pin,'selected_jobs':[{k:j[k] for k in ('key','province','year','nominal_patches','spatial_window_id')} for j in jobs],'command':command,'new_budget_added':False,'training_started':False,'source_pins':approval['source_pins'],'maximum_new_physical_patches':32}
started=time.monotonic()
with (E/'deficit206-live-root-20261018-stdout.log').open('xb') as out,(E/'deficit206-live-root-20261018-stderr.log').open('xb') as err:
    p=subprocess.Popen(command,cwd=R,env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    record['pid']=p.pid
    with (E/'deficit206-launch-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pid':p.pid,'status':record['status']}),flush=True)
    code=p.wait()
record.update(status='PROCESS_TERMINATED_REVIEW_STDOUT_AND_LEDGER',exit_code=code,seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),lock_present=(D/'first-group-training-budget/global-ledger.execution.lock').exists())
with (E/'deficit206-terminal-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'exit_code':code,'seconds':record['seconds'],'lock_present':record['lock_present']}),flush=True)
