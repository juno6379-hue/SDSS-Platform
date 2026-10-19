"""Manual correction of Root268 test subprocess environment; product bytes unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,tempfile,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data';W=E/'selection265-workspace-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
previous=read(E/'selection268-application-root-20261018.json')
assert previous['status']=='APPLICATION_OR_PROJECT_TESTS_BLOCKED_PARTIAL_PRESERVED' and previous['test_exit_code']==1
prior_log=(E/'selection268-project-regression-root-20261018.log').read_text('utf-8')
assert 'test_import_alone_does_not_load_collector_cli' in prior_log and "No module named \\'app\\'" in prior_log
manifest=read(W/'application265-manifest.json');rows=manifest['runtime']+manifest['test_bundle']
assert all(sha(R/x['path'])==x['final']['sha256'] for x in rows)
pins=previous['operating_pins_before'];assert all(sha(D/n)==p for n,p in pins.items())
environment=dict(os.environ,PYTHONPATH=os.pathsep.join(str(p) for p in [R,R/'.runtime',R/'backend',R/'scripts',R/'tests']),PYTHONIOENCODING='utf-8')
probe=subprocess.run([sys.executable,'-X','utf8','-c','import sys;import app.data.deficit_candidate_guard;assert "scripts.collect_targeted_bare" not in sys.modules'],cwd=R,env=environment,capture_output=True)
assert probe.returncode==0
result={'status':'PROJECT_REVALIDATION_STARTED','at_utc':datetime.now(timezone.utc).isoformat(),'prior268_failure_preserved':True,'cause':'Root268 set parent sys.path but omitted inherited PYTHONPATH for import-isolation subprocess','corrected_import_probe_exit_code':probe.returncode,'product_files_changed':0,'test_sources_changed':0,'collector_started':False,'server_restarted':False,'operating_pins_before':pins}
modules=['test_deficit_metadata_selection260','test_selection265_contract','test_deficit_candidate_guard','test_collect_deficit_guarded','test_targeted_collection_hooks','test_targeted_candidate_quality_policy','test_data_recovery']
start=time.monotonic();temporary=tempfile.TemporaryDirectory(prefix='selection271-tests-',dir=E)
task_temp=Path(temporary.name).resolve();assert task_temp.is_relative_to(E.resolve())
environment.update(TEMP=str(task_temp),TMP=str(task_temp),TMPDIR=str(task_temp),DATA=str(task_temp/'data'))
try:
    with (E/'selection271-project-regression-root-20261018.log').open('xb') as log:
        p=subprocess.Popen([sys.executable,'-X','utf8','-m','unittest',*modules,'-q'],cwd=R,env=environment,stdout=log,stderr=subprocess.STDOUT)
        print(json.dumps({'status':'PROJECT_REGRESSION_WITH_EXPLICIT_SUBPROCESS_PATHS','pid':p.pid}),flush=True);code=p.wait()
    log=(E/'selection271-project-regression-root-20261018.log').read_text('utf-8')
    result.update(exit_code=code,wall_seconds=round(time.monotonic()-start,3),expected_tests=96,log_sha256=sha(E/'selection271-project-regression-root-20261018.log'))
    assert code==0 and 'Ran 96 tests' in log and log.rstrip().endswith('OK')
    assert all(sha(R/x['path'])==x['final']['sha256'] for x in rows)
    assert all(sha(D/n)==p for n,p in pins.items())
    result.update(status='SHARED_PROJECT96_VERIFIED_AFTER_ROOT_ENVIRONMENT_CORRECTION',operating_pins_preserved=True,runtime3_test6_pins_preserved=True)
except Exception as exc:
    result.update(status='PROJECT_REVALIDATION_BLOCKED_PARTIAL_PRESERVED',issue_type=type(exc).__name__,automatic_retry_allowed=False)
finally:
    assert task_temp.is_relative_to(E.resolve());temporary.cleanup()
    result['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    with (E/'selection271-project-validation-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result),flush=True)
if result['status']!='SHARED_PROJECT96_VERIFIED_AFTER_ROOT_ENVIRONMENT_CORRECTION':raise SystemExit(2)
