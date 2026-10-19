"""Apply the reviewed self-contained test bundle and verify the actual project layout."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,tempfile,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';W=E/'preprocess242-test-workspace-20261018';D=R/'data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
assert sha(W/'freeze242.json')=='957558f456dfebb686e0223017214b3b83706dce5013d19ab648d56da7ba0586'
frozen=read(W/'freeze242.json');bundle=frozen['root_main_test_bundle'];assert len(bundle)==10
for item in frozen['evidence']+frozen['tests']:
    path=Path(item['path']);path=path if path.is_absolute() else W/path
    assert sha(path)==item['sha256'] and path.stat().st_size==item['bytes']
runtime=read(E/'profile243-runtime-approval-root-20261018.json')['runtime_files']
assert len(runtime)==18 and all(sha(R/x['path'])==x['final237']['sha256'] for x in runtime)
for item in bundle:
    rel=Path(item['path']);assert rel.parts[0]=='tests' and '..' not in rel.parts
    destination=R/rel;assert destination.resolve()==destination and not destination.exists()
    assert sha(W/rel)==item['sha256'] and (W/rel).stat().st_size==item['bytes']
protected=[D/'first-group-training-esri-v1/annual-window-report.json',D/'first-group-training-budget/global-ledger.json',D/'first-group-training-priority/latest-candidate.json',D/'first-group-training-priority/latest-bare-review.json']
pins={str(p.relative_to(R)):sha(p) for p in protected}
for item in bundle:
    destination=R/item['path'];destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write((W/item['path']).read_bytes())
    assert sha(destination)==item['sha256']
modules=['test_manifest_profile228','test_manifest_profile230','test_manifest_profile237','test_manifest_profile242_portability',
 'test_propose_deficit_centers182','test_collection_status','test_collection_priority_status','test_collection_budget_status']
start=time.monotonic()
temporary=tempfile.TemporaryDirectory(prefix='profile242-main-',dir=R/'evidence')
temporary_path=Path(temporary.name).resolve();assert temporary_path.is_relative_to(R/'evidence') and temporary_path!=R/'evidence'
try:
    env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',GEOAI_DATA_ROOT=str(temporary_path/'data'),
      PYTHONPATH=os.pathsep.join([str(R/'.runtime'),str(R/'backend'),str(R/'tests'),str(R)]))
    command=[sys.executable,'-X','utf8','-m','unittest','-v',*modules]
    with (E/'profile242-main-regression-root-20261018.log').open('xb') as log:
        process=subprocess.Popen(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
        print(json.dumps({'status':'MAIN_LAYOUT_TESTS_STARTED_NOT_COLLECTION','pid':process.pid,'modules':len(modules)}),flush=True)
        code=process.wait()
finally:
    assert temporary_path.is_relative_to((R/'evidence').resolve()) and temporary_path!=(R/'evidence').resolve()
    temporary.cleanup()
stable=all(sha(p)==pins[str(p.relative_to(R))] for p in protected)
runtime_stable=all(sha(R/x['path'])==x['final237']['sha256'] for x in runtime)
out={'status':'TEST_SOURCES_APPLIED_AND_PROJECT_REGRESSION_VERIFIED' if code==0 and stable and runtime_stable else 'TEST_SOURCES_APPLIED_PROJECT_VERIFICATION_FAILED',
 'at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'exit_code':code,
 'test_bundle_count':len(bundle),'test_sources':bundle,'runtime18_unchanged':runtime_stable,'operating_pins_unchanged':stable,
 'protected_pins':pins,'project_layout':str(R),'test_data_root_was_temporary':True,'collector_started':False,'training_started':False}
with (E/'profile242-shared-application-root-20261018.json').open('x',encoding='utf-8') as stream:json.dump(out,stream,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='test_sources'},ensure_ascii=True),flush=True)
if code!=0 or not stable or not runtime_stable:raise SystemExit(2)
