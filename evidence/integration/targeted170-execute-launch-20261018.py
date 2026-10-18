from pathlib import Path
import json,hashlib,subprocess,sys,os,datetime
r=Path.cwd();e=r/'evidence/integration';d=r/'data';record_path=e/'targeted170-execute-launch-20261018.json'
assert not record_path.exists(),'Do not repeat an existing dispatch'
assert not (d/'first-group-training-budget/global-ledger.execution.lock').exists(),'Existing global execution lock'
check=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python.*\\.exe$' -and ($_.CommandLine -like '*scripts*collect_training_*' -or $_.CommandLine -like '*scripts*collect_targeted_bare.py*') } | Select-Object ProcessId | ConvertTo-Json"],encoding='utf-8',errors='replace');assert not check.strip(),'Existing collector'
pin=json.loads((e/'targeted170-live-request-pin-20261018.json').read_text('utf-8'))['request_sha256'];request=json.loads((e/'targeted170-live-request-20261018.json').read_text('utf-8'))
ledger_path=d/'first-group-training-budget/global-ledger.json';aggregate=d/'first-group-training-esri-v1/annual-window-report.json';ledger=json.loads(ledger_path.read_text('utf-8'));source=json.loads(aggregate.read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ledger_path)==request['ledger_ref']['sha256'] and sha(aggregate)==request['plan']['current_manifest_ref']['sha256']
pending={k:v for k,v in ledger['batches'].items() if v['status']=='pending'};assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert ledger['additional_maximum_bytes']==4294967296 and not ledger['rate_limit_active']
files=['scripts/collect_targeted_bare.py','scripts/collect_samples.py','backend/app/data/service.py','backend/app/data/targeted_live_guards.py','backend/app/data/targeted_inventory.py','backend/app/data/targeted_bare_plan.py','backend/app/data/targeted_scene_claims.py','backend/app/data/targeted_execution.py']
command=[sys.executable,str(r/'scripts/collect_targeted_bare.py'),'--request',str(e/'targeted170-live-request-20261018.json'),'--expected-request-sha256',pin,'--execute']
env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONUNBUFFERED']='1'
with (e/'targeted170-execute-20261018-stdout.log').open('xb') as out,(e/'targeted170-execute-20261018-stderr.log').open('xb') as err:
 p=subprocess.Popen(command,cwd=r,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
record={'started_at':datetime.datetime.now().astimezone().isoformat(),'status':'STARTED_NOT_COMPLETED','pid':p.pid,'request_sha256':pin,'maximum_new_batches':1,'command':command,'source_pins':{f:sha(r/f) for f in files},'pending_before':pending,'source_rows_before':len(source['scenes']),'old_rows_canonical_sha256':hashlib.sha256(json.dumps(source['scenes'],sort_keys=True).encode()).hexdigest(),'source_before_sha256':sha(aggregate),'ledger_before_sha256':sha(ledger_path),'charged_before':ledger['new_charged_bytes'],'remaining_before':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],'new_budget_added':False,'training_started':False,'prior_local_validation':'1152 asset inventory; LOCAL_DISPATCH_INPUTS_VERIFIED, no HTTP'}
record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'pid':p.pid,'status':record['status'],'max_batches':1}))
