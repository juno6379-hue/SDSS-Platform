"""Root explicit application of reviewed265 runtime3/test6 and project regression."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,tempfile,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data';W=E/'selection265-workspace-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
approval=read(E/'selection268-approval-root-20261018.json')
assert approval['status']=='ROOT_APPROVED_REVIEWED265_NINE_OWNED_FILES'
assert sha(R/approval['review_ref']['path'])==approval['review_ref']['sha256']
assert sha(W/'freeze265.json')=='718e757240a69c1351f5ffbbfa1ec248fc1daab2493720d0e5ea23419be1922e'
assert sha(W/'application265-manifest.json')=='368ed88ec4b23c14bc55de1139b58f8f6c80ea653fd0ed19343cd42f64c33f1f'
freeze=read(W/'freeze265.json');manifest=read(W/'application265-manifest.json')
assert freeze['final_portable']['passed']==96 and freeze['final_portable']['exit_code']==0
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded|prepare_priority_candidate164)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
operating={n:sha(D/n) for n in ['first-group-training-esri-v1/annual-window-report.json','first-group-training-budget/global-ledger.json','first-group-training-priority/latest-candidate.json','first-group-training-priority/latest-bare-review.json','first-group-training-priority/source-profile237-root-20261018.json']}
assert operating==approval['operating_pins']
rows=manifest['runtime']+manifest['test_bundle'];assert len(rows)==9
for row in rows:
    dest=R/row['path'];src=W/row['path']
    assert sha(src)==row['final']['sha256'] and src.stat().st_size==row['final']['bytes']
    if 'main_baseline' in row:assert sha(dest)==row['main_baseline']['sha256']
    else:assert row['main_must_be_absent'] and not dest.exists()
protected={n:pin for n,pin in read(E/'selection260-workspace-20261018/freeze260.json')['protected_main'].items() if n not in {x['path'] for x in rows}}
assert all(sha(R/n)==pin for n,pin in protected.items())
archive=E/'selection268-main-baseline-root-20261018';archive.mkdir(exist_ok=False)
for row in manifest['runtime']:
    p=archive/row['path'];p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((R/row['path']).read_bytes())
    assert sha(p)==row['main_baseline']['sha256']
result={'status':'APPLICATION_STARTED_NO_COLLECTOR_AUTHORIZED','at_utc':datetime.now(timezone.utc).isoformat(),'operating_pins_before':operating,'copied':[],'runtime_files':3,'test_bundle_files':6,'training_started':False,'collector_started':False,'server_restarted':False}
try:
    for row in rows:
        dest=R/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
        if 'main_baseline' in row:
            assert sha(dest)==row['main_baseline']['sha256']
            temp=dest.with_name(dest.name+'.root268-new')
            with temp.open('xb') as f:f.write((W/row['path']).read_bytes())
            assert sha(temp)==row['final']['sha256'];os.replace(temp,dest)
        else:
            with dest.open('xb') as f:f.write((W/row['path']).read_bytes())
        assert sha(dest)==row['final']['sha256'];result['copied'].append(row['path'])
    assert all(sha(D/n)==pin for n,pin in operating.items())
    temporary=tempfile.TemporaryDirectory(prefix='selection268-tests-',dir=E)
    task_temp=Path(temporary.name).resolve();assert task_temp.is_relative_to(E.resolve())
    child="import sys,unittest;sys.path[:0]=['backend','tests','scripts','.runtime'];unittest.main(module=None,argv=['selection268','test_deficit_metadata_selection260','test_selection265_contract','test_deficit_candidate_guard','test_collect_deficit_guarded','test_targeted_collection_hooks','test_targeted_candidate_quality_policy','test_data_recovery','-q'])"
    started=time.monotonic()
    try:
        environment=dict(os.environ,TEMP=str(task_temp),TMP=str(task_temp),TMPDIR=str(task_temp),PYTHONIOENCODING='utf-8',DATA=str(task_temp/'data'))
        with (E/'selection268-project-regression-root-20261018.log').open('xb') as log:
            p=subprocess.Popen([sys.executable,'-X','utf8','-c',child],cwd=R,env=environment,stdout=log,stderr=subprocess.STDOUT)
            print(json.dumps({'status':'NINE_FILES_APPLIED_PROJECT_TESTS_RUNNING','pid':p.pid}),flush=True);code=p.wait()
    finally:
        assert task_temp.is_relative_to(E.resolve());temporary.cleanup()
    log=(E/'selection268-project-regression-root-20261018.log').read_text('utf-8')
    result.update(test_exit_code=code,regression_elapsed_seconds=round(time.monotonic()-started,3),tests=96,project_log_sha256=sha(E/'selection268-project-regression-root-20261018.log'))
    assert code==0 and 'Ran 96 tests' in log and log.rstrip().endswith('OK')
    assert all(sha(R/row['path'])==row['final']['sha256'] for row in rows)
    assert all(sha(R/n)==pin for n,pin in protected.items())
    assert all(sha(D/n)==pin for n,pin in operating.items())
    result.update(status='RUNTIME3_TEST6_APPLIED_PROJECT96_VERIFIED',operating_pins_preserved=True,protected_unowned_files_preserved=True)
except Exception as exc:
    result.update(status='APPLICATION_OR_PROJECT_TESTS_BLOCKED_PARTIAL_PRESERVED',issue_type=type(exc).__name__,automatic_retry_allowed=False)
finally:
    result['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    write(E/'selection268-application-root-20261018.json',result)
print(json.dumps(result),flush=True)
if result['status']!='RUNTIME3_TEST6_APPLIED_PROJECT96_VERIFIED':raise SystemExit(2)
