from pathlib import Path
import urllib.request,json,os,subprocess,sys,time,datetime
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration'
def get(path,origin=False):
 req=urllib.request.Request('http://127.0.0.1:8002'+path,headers={'Origin':'http://127.0.0.1:5174'} if origin else {})
 with urllib.request.urlopen(req,timeout=15) as response:return json.load(response),response.headers.get('Access-Control-Allow-Origin')
health,_=get('/api/health');before,_=get('/api/dashboard');_,origin=get('/api/health',True)
assert health['authentication'].startswith('localhost-only') and before['jobs']==0
pid=36400
actual=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',f'Get-CimInstance Win32_Process -Filter "ProcessId={pid}" | Select-Object ProcessId,CommandLine | ConvertTo-Json'],encoding='utf-8'))
assert 'uvicorn app.main:app' in actual['CommandLine'] and '--port 8002' in actual['CommandLine']
subprocess.run(['powershell','-NoProfile','-Command',f'Stop-Process -Id {pid} -ErrorAction Stop'],check=True)
env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['GEOAI_DATA_ROOT']=str(R/'data')
env['PYTHONPATH']=os.pathsep.join([str(R/'.runtime'),str(R/'backend')])
if origin=='http://127.0.0.1:5174':env['GEOAI_CORS_ORIGINS']='http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174'
with (E/'ui180-root-api-20261018-stdout.log').open('xb') as out,(E/'ui180-root-api-20261018-stderr.log').open('xb') as err:
 proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8002'],cwd=R/'backend',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
after=None
for i in range(30):
 try:after,_=get('/api/dashboard');break
 except Exception:
  if proc.poll() is not None:raise RuntimeError('API_START_FAILED')
  time.sleep(1)
assert after is not None
assert all(before[k]==after[k] for k in ['datasets','models','jobs','analyses'])
status,_=get('/api/data/collection-status');assert 'collection_policy' in status['collection_targets']
record={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_pid':pid,'new_pid':proc.pid,'before':before,'after':after,'authentication_before':health['authentication'],'status':'API_RELOADED_ADDONLY_CONTRACT_CONFIRMED','collection_policy':status['collection_targets']['collection_policy'],'bare_review':status['collection_targets'].get('bare_target_review'),'training_started':False,'registry_written':False}
(E/'ui180-root-api-restart-20261018.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'pid':proc.pid,'counts':after},ensure_ascii=True))
