from pathlib import Path
import os,sys,json,subprocess,time,datetime,hashlib,urllib.request
R=Path.cwd();E=R/'evidence/integration'
def get(path,timeout=15):
 req=urllib.request.Request('http://127.0.0.1:8002'+path,headers={'Origin':'http://127.0.0.1:5174'})
 started=time.perf_counter()
 with urllib.request.urlopen(req,timeout=timeout) as res:return json.load(res),res.headers.get('Access-Control-Allow-Origin'),time.perf_counter()-started
health,origin,_=get('/api/health');before,_,_=get('/api/dashboard');assert health['authentication'].startswith('localhost-only')
actual=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process -Filter "ProcessId=20676" | Select-Object ProcessId,CommandLine | ConvertTo-Json'],encoding='utf-8'));assert 'uvicorn app.main:app' in actual['CommandLine'] and '--port 8002' in actual['CommandLine']
names=['first-group-training-esri-v1/annual-window-report.json','first-group-training-budget/global-ledger.json','first-group-training-priority/latest-candidate.json','first-group-training-priority/latest-bare-review.json'];pins={n:hashlib.sha256((R/'data'/n).read_bytes()).hexdigest() for n in names}
subprocess.run(['powershell','-NoProfile','-Command','Stop-Process -Id 20676 -ErrorAction Stop'],check=True)
env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',GEOAI_DATA_ROOT=str(R/'data'),PYTHONPATH=os.pathsep.join([str(R/'.runtime'),str(R/'backend')]),GEOAI_CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174')
with (E/'service225-api-stdout-20261018.log').open('xb') as out,(E/'service225-api-stderr-20261018.log').open('xb') as err:
 proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8002'],cwd=R/'backend',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
for attempt in range(20):
 try:afterhealth,afterorigin,_=get('/api/health');break
 except Exception:
  if proc.poll() is not None:raise RuntimeError('API exited')
  time.sleep(.5)
after,_,_=get('/api/dashboard');assert all(before[k]==after[k] for k in ['datasets','models','jobs','analyses'])
budget,cors,seconds=get('/api/data/collection-budget-status',60)
assert budget['available'] and budget['additional_maximum_bytes']==4294967296 and budget['charged_including_pending_bytes']==2398022341 and budget['remaining_bytes']==1896944955 and budget['old_pending_bytes']==136314880
assert budget['source_manifest_sha256']==pins[names[0]] and budget['ledger_sha256']==pins[names[1]] and budget['process_verification']=='UNKNOWN'
assert all(hashlib.sha256((R/'data'/n).read_bytes()).hexdigest()==h for n,h in pins.items())
record={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_pid':20676,'new_pid':proc.pid,'before_dashboard':before,'after_dashboard':after,'health':afterhealth,'cors':cors,'budget_http200':budget,'budget_seconds':seconds,'operating_pins_preserved':pins,'only_development_api_restarted':True,'frontend_unchanged':True,'ledger_lock_pointer_mutation':False}
(E/'service225-api-application-20261018.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'pid':proc.pid,'budget_seconds':seconds,'budget':budget},ensure_ascii=True))
