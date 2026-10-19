"""Two SE targets after193 publication; full original guards remain mandatory."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
published=read(E/'priority193-publication-root-20261018.json')
assert published['status']=='COMPLETED_QA_PUBLISHED_AND_READER_VERIFIED'
assert not (E/'target196-launch-root-20261018.json').exists()
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|prepare_priority_candidate164)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();l=json.loads(lr)
assert hashlib.sha256(mr).hexdigest()==published['source_snapshot_sha256']
pending={k:v for k,v in l['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert l['additional_maximum_bytes']==4*1024**3 and not l['rate_limit_active']
assert l['additional_maximum_bytes']-l['new_charged_bytes']>=2*68157440
check=read(E/'bare194-southeast-refresh-20261018.json')
pair=check['mutual_followup']['priority_rank12_2024_and_rank1_2025']
assert pair['overlap'] is False and pair['old179_indices']==[1,12]
old=read(E/'bare179-report-20261018.json')
assert sha(E/'bare179-report-20261018.json')=='36aaf1107292eee74b0f6a2ce462d90e40a22de498ca31aaff1c1ded636775f0'
targets=[old['targets'][12],old['targets'][1]]
assert [(t['province'],t['year'],t['declared_bare_pixels']) for t in targets]==[('southeast_sulawesi',2024,266),('southeast_sulawesi',2025,840)]
folder=D/'target196-20261018';folder.mkdir(exist_ok=False);snapshot=folder/'source.json';snapshot.write_bytes(mr)
request=read(E/'target187-request-20261018.json')
request['plan']['targets']=targets;request['maximum_batches']=2;request['plan']['policy']['maximum_new_batches']=2
request['plan']['current_manifest_ref']={'path':snapshot.relative_to(R).as_posix(),'sha256':sha(snapshot)}
request['ledger_ref']={'path':lp.relative_to(R).as_posix(),'sha256':hashlib.sha256(lr).hexdigest()}
rp=E/'target196-request-root-20261018.json'
with rp.open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
assert mp.read_bytes()==mr and lp.read_bytes()==lr
command=[sys.executable,'-X','faulthandler',str(R/'scripts/collect_targeted_bare.py'),'--request',str(rp),'--expected-request-sha256',pin,'--execute']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_PREFLIGHT_NOT_COMPLETED','manifest_before_sha256':sha(mp),'ledger_before_sha256':sha(lp),'source_rows_before':len(json.loads(mr)['scenes']),'pending_before':pending,'request_sha256':pin,'selected_targets':[{'target_id':t['target_id'],'year':t['year'],'declared_bare_pixels':t['declared_bare_pixels']} for t in targets],'command':command,'new_budget_added':False,'training_started':False,'source_pins':{p:sha(R/p) for p in ['scripts/collect_targeted_bare.py','backend/app/data/targeted_live_guards.py','backend/app/data/targeted_bare_plan.py','backend/app/data/parallel.py']}}
started=time.monotonic()
with (E/'target196-live-root-20261018-stdout.log').open('xb') as out,(E/'target196-live-root-20261018-stderr.log').open('xb') as err:
    p=subprocess.Popen(command,cwd=R,env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    record['pid']=p.pid
    with (E/'target196-launch-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pid':p.pid,'status':record['status']}),flush=True)
    code=p.wait()
record.update(status='PROCESS_TERMINATED_REVIEW_STDOUT_AND_LEDGER',exit_code=code,seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),lock_present=(D/'first-group-training-budget/global-ledger.execution.lock').exists())
with (E/'target196-terminal-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'exit_code':code,'seconds':record['seconds'],'lock_present':record['lock_present']}),flush=True)
