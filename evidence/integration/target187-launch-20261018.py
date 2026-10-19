from pathlib import Path
import hashlib,json,os,subprocess,sys,datetime
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
launch=E/'target187-launch-20261018.json';assert not launch.exists()
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
running=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python.*\\.exe$' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare)\\.py' } | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not running.strip()
report=read(E/'bare179-report-20261018.json');assert sha(E/'bare179-report-20261018.json')=='36aaf1107292eee74b0f6a2ce462d90e40a22de498ca31aaff1c1ded636775f0'
target=report['targets'][2];observation=report['observations'][2]
assert target['province']=='southeast_sulawesi' and target['year']==2024 and target['declared_bare_pixels']==814 and observation['historical_overlap'] is False
refs=report['request'];manifest=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json'
assert sha(manifest)==refs['manifest_ref']['sha256'] and sha(ledger)==refs['ledger_ref']['sha256']
plan={'schema_version':1,'kind':'TARGETED_BARE_256_COLLECTION_PLAN','proposal_ref':refs['proposal_ref'],'current_manifest_ref':refs['manifest_ref'],'boundary_ref':refs['boundary_ref'],'policy':{'window_size':256,'source_taxonomy_code':8,'minimum_declared_bare_pixels':256,'minimum_valid_fraction':.8,'minimum_inside_fraction':.95,'maximum_new_batches':1},'targets':[target]}
request={'schema_version':1,'plan':plan,'ledger_ref':refs['ledger_ref'],'maximum_batches':1}
payload=(json.dumps(request,ensure_ascii=False,indent=2)+'\n').encode();path=E/'target187-request-20261018.json'
with path.open('xb') as f:f.write(payload)
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
state=read(ledger);pending={k:v for k,v in state['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'STARTED_PREFLIGHT_NOT_COMPLETED','source_rows_before':len(read(manifest)['scenes']),'manifest_before_sha256':sha(manifest),'ledger_before_sha256':sha(ledger),'old_rows_canonical_sha256':hashlib.sha256(json.dumps(read(manifest)['scenes'],sort_keys=True).encode()).hexdigest(),'pending_before':pending,'request_sha256':pin,'report_sha256':sha(E/'bare179-report-20261018.json'),'target_id':target['target_id'],'province':target['province'],'year':target['year'],'source_pins':{p:sha(R/p) for p in ['backend/app/data/targeted_bare_plan.py','backend/app/data/targeted_live_guards.py','scripts/collect_targeted_bare.py','backend/app/data/parallel.py','backend/app/data/service.py','scripts/collect_samples.py']},'new_budget_added':False,'training_started':False,'scientific_accuracy_validated':False}
command=[sys.executable,str(R/'scripts/collect_targeted_bare.py'),'--request',str(path),'--expected-request-sha256',pin,'--execute'];env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
with (E/'target187-live-20261018-stdout.log').open('xb') as out,(E/'target187-live-20261018-stderr.log').open('xb') as err:
 proc=subprocess.Popen(command,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
record.update(pid=proc.pid,command=command);launch.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pid':proc.pid,'status':record['status'],'target':target['target_id'],'province':target['province'],'year':target['year']},ensure_ascii=True))
