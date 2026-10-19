"""Root-reviewed runtime18 application; preserve baseline, registry and raw evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sqlite3,subprocess,sys,time,urllib.request
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
W=E/'preprocess237-workspace-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def get(route,timeout=20):
    request=urllib.request.Request('http://127.0.0.1:8002'+route,headers={'Origin':'http://127.0.0.1:5174'})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        raw=response.read(2*1024**2+1);assert len(raw)<=2*1024**2
        return json.loads(raw),response.headers.get('Access-Control-Allow-Origin')
def catalog():
    c=sqlite3.connect((D/'catalog.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:rows=c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
    finally:c.close()
    assert not any(json.loads(body).get('status') in ('queued','running') for kind,identifier,body in rows if kind=='jobs')
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert sha(W/'freeze237.json')=='56c9f57bf4929338835170e48d15495385e48cf58140f7ca396bdbbf4a07ceb6'
assert sha(W/'apply-preflight237.json')=='6236751af0da68ee128548b5878e522a9392a1f4c5cd401ceee3c87c6268b771'
review=R/'docs/implementation/240_profile237_independent_review.md'
assert sha(review)=='c617a634b50690eb3f83926be438b8747b430f2679da0007777db37f51b7b9f5'
items=[x for x in read(W/'apply-preflight237.json')['files'] if x['artifact_class']=='RUNTIME_PRODUCT_CODE']
assert len(items)==18 and len({x['path'] for x in items})==18
assert not any('targeted_' in x['path'] or 'deficit_candidate_guard' in x['path'] for x in items)
for item in items:
    rel=Path(item['path']);assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] in ('backend','scripts')
    target=R/rel;assert target.resolve().is_relative_to(R)
    before=item['baseline_before_any_profile_revision']
    assert sha(target)==before['sha256'] if before else not target.exists()
    assert sha(W/rel)==item['final237']['sha256']
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
query="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded|prepare_priority_candidate164)\\.py' -and $_.CommandLine -notmatch 'preprocess[0-9]+-'} | Select-Object ProcessId | ConvertTo-Json"
assert not subprocess.check_output(['powershell','-NoProfile','-Command',query],text=True).strip()
old=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process -Filter "ProcessId=40492" | Select-Object ProcessId,CommandLine | ConvertTo-Json'],encoding='utf-8'))
assert 'uvicorn app.main:app' in old['CommandLine'] and '--port 8002' in old['CommandLine']
health,cors=get('/api/health');dashboard,_=get('/api/dashboard')
assert health['authentication'].startswith('localhost-only') and not os.getenv('GEOAI_API_TOKEN')
assert cors=='http://127.0.0.1:5174'
names=['first-group-training-esri-v1/annual-window-report.json','first-group-training-budget/global-ledger.json','first-group-training-priority/latest-candidate.json','first-group-training-priority/latest-bare-review.json']
pins={name:sha(D/name) for name in names}
assert pins[names[0]]=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert pins[names[1]]=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
state=read(D/names[1]);pending=[v for v in state['batches'].values() if v['status']=='pending']
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending)==136314880
catalog_before=catalog()
backup=E/'profile243-runtime-baseline-root-20261018';backup.mkdir(exist_ok=False)
for item in items:
    if item['baseline_before_any_profile_revision']:
        destination=backup/item['path'];destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as stream:stream.write((R/item['path']).read_bytes())
        assert sha(destination)==item['baseline_before_any_profile_revision']['sha256']
approval={'status':'ROOT_APPROVED_RUNTIME18_ONLY_TEST3_DEFERRED_TO242','at_utc':datetime.now(timezone.utc).isoformat(),
 'review_sha256':sha(review),'freeze237_sha256':sha(W/'freeze237.json'),'runtime_files':items,'protected_pins':pins,
 'catalog_record_snapshot':catalog_before,'old_api_pid':40492,'collector_started':False,'external_deployment':False}
write(E/'profile243-runtime-approval-root-20261018.json',approval)
subprocess.run(['powershell','-NoProfile','-Command','Stop-Process -Id 40492 -ErrorAction Stop'],check=True)
record={'started_at_utc':datetime.now(timezone.utc).isoformat(),'status':'APPLYING_RUNTIME18','applied':[],'new_api_pid':None}
try:
    for item in items:
        target=R/item['path'];before=item['baseline_before_any_profile_revision']
        assert sha(target)==before['sha256'] if before else not target.exists()
        temporary=target.with_name(target.name+'.profile243.tmp')
        with temporary.open('xb') as stream:stream.write((W/item['path']).read_bytes());stream.flush();os.fsync(stream.fileno())
        assert sha(temporary)==item['final237']['sha256']
        os.replace(temporary,target);record['applied'].append(item['path'])
    assert all(sha(R/item['path'])==item['final237']['sha256'] for item in items)
    descriptor={'name':'bounded128m-3000-v1','manifest_bytes':134217728,'max_rows':3000,'max_depth':32,'max_nodes':4000000,'max_json_io_bytes':17179869184}
    marker={'name':descriptor['name'],'sha256':hashlib.sha256(json.dumps(descriptor,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    assert marker['sha256']=='db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4'
    config=D/'first-group-training-priority/source-profile237-root-20261018.json'
    write(config,{'schema_version':1,'kind':'ROOT_SELECTED_SOURCE_MANIFEST_PROFILE','manifest_profile':marker,'source_manifest_sha256':pins[names[0]]})
    env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',GEOAI_DATA_ROOT=str(D),PYTHONPATH=os.pathsep.join([str(R/'.runtime'),str(R/'backend')]),GEOAI_CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174')
    with (E/'profile243-api-stdout-root-20261018.log').open('xb') as out,(E/'profile243-api-stderr-root-20261018.log').open('xb') as err:
        process=subprocess.Popen([sys.executable,str(E/'profile237-api-entrypoint-root-20261018.py')],cwd=R/'backend',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
    record['new_api_pid']=process.pid
    for attempt in range(40):
        try:new_health,new_cors=get('/api/health',2);break
        except Exception:
            if process.poll() is not None:raise RuntimeError('API_STARTUP_FAILED')
            time.sleep(.5)
    else:raise RuntimeError('API_STARTUP_TIMEOUT')
    new_dashboard,_=get('/api/dashboard')
    assert all(dashboard[key]==new_dashboard[key] for key in ('datasets','models','jobs','analyses'))
    assert new_health['authentication']==health['authentication'] and new_cors==cors
    assert catalog()==catalog_before and all(sha(D/name)==pin for name,pin in pins.items())
    record.update(status='RUNTIME18_APPLIED_API_HEALTH_VERIFIED_STATUS_SMOKE_PENDING',profile_config_sha256=sha(config),
      protected_pins_preserved=True,catalog_records_preserved=True,health=new_health,cors=new_cors,
      dashboard_before=dashboard,dashboard_after=new_dashboard,tests_copied=0,collector_started=False,training_started=False,
      external_deployment=False)
except Exception as exc:
    record.update(status='APPLY_OR_API_FAILED_ROOT_RECOVERY_REQUIRED',issue=type(exc).__name__)
    raise
finally:
    record['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    write(E/'profile243-runtime-application-root-20261018.json',record)
print(json.dumps(record,ensure_ascii=True),flush=True)
