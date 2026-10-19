from pathlib import Path
import os,sys,json,subprocess,time,datetime,hashlib,urllib.request
R=Path.cwd();E=R/'evidence/integration'
def get(path):
 req=urllib.request.Request('http://127.0.0.1:8002'+path,headers={'Origin':'http://127.0.0.1:5174'})
 with urllib.request.urlopen(req,timeout=10) as res:return json.load(res),res.headers.get('Access-Control-Allow-Origin')
health,origin=get('/api/health');before,_=get('/api/dashboard')
assert health['authentication'].startswith('localhost-only')
actual=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process -Filter "ProcessId=32576" | Select-Object ProcessId,CommandLine | ConvertTo-Json'],encoding='utf-8'))
assert 'uvicorn app.main:app' in actual['CommandLine'] and '--port 8002' in actual['CommandLine']
files=['data/sdss.sqlite','data/first-group-training-priority/latest-bare-review.json','data/first-group-training-priority/latest-candidate.json']
pins={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in files if (R/f).is_file()}
subprocess.run(['powershell','-NoProfile','-Command','Stop-Process -Id 32576 -ErrorAction Stop'],check=True)
env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',GEOAI_DATA_ROOT=str(R/'data'),PYTHONPATH=os.pathsep.join([str(R/'.runtime'),str(R/'backend')]),GEOAI_CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174')
with (E/'bare195-api-stdout-20261018.log').open('xb') as out,(E/'bare195-api-stderr-20261018.log').open('xb') as err:
 proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8002'],cwd=R/'backend',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
result=None
for attempt in range(20):
 try:
  afterhealth,afterorigin=get('/api/health');after,_=get('/api/dashboard');result=True;break
 except Exception:
  if proc.poll() is not None:raise RuntimeError('API exited')
  time.sleep(.5)
assert result
assert all(before[k]==after[k] for k in ['datasets','models','jobs','analyses'])
assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==h for f,h in pins.items())
sys.path[:0]=[str(R/'.runtime'),str(R/'backend')]
from app.collection_priority_status import bare_target_review,PROVINCES
review=bare_target_review(R/'data','ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f')
assert review['available'] and review['candidate_total']==50 and review['searched_provinces']==list(PROVINCES)
record={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_pid':32576,'new_pid':proc.pid,'health':afterhealth,'cors':afterorigin,'dashboard_before':before,'dashboard_after':after,'operating_pins_preserved':pins,'legacy179_reader':review,'loaded_source_sha256':hashlib.sha256((R/'backend/app/collection_priority_status.py').read_bytes()).hexdigest(),'scope':'development API only, no collector or pointer mutation, no collection-status HTTP requested'}
(E/'bare195-api-restart-20261018.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pid':proc.pid,'health':'ok','legacy_rows':len(review['rows']),'legacy_scope':review['searched_provinces']},ensure_ascii=True))
