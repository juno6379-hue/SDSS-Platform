"""Root additive281 application after287 static review and completed285 audit."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time,tempfile,shutil
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';W=E/'survey281-workspace-20261018'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def rd(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--audit-sha256',required=True);a=ap.parse_args()
    start=time.monotonic();audit=E/'deficit285-native-root-20261018.json'
    assert sha(audit)==a.audit_sha256
    av=rd(audit);assert av['status']=='COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED' and av['native_validation_complete'] and av['metadata_two_reads_stable']
    assert not (R/'data/first-group-training-budget/global-ledger.execution.lock').exists()
    assert sha(E/'survey287-static-review-20261018.json')=='90e35d7c2cb9a7031d85b96153e27d76fc2397ac8c7b83d24387879590a9f0ea'
    assert rd(E/'survey287-static-review-20261018.json')['status']=='STATIC_REVIEW_COMPLETED_NO_REQUIRED_PRODUCT_CHANGES_IDENTIFIED'
    assert sha(W/'freeze281-20261018.json')=='42bae67521fbd160506c89cf45aac255567260e1c2203d22c530fd9b55a271f4'
    manifest=W/'patch-manifest281.json';assert sha(manifest)=='ab164cec389ed53dc0949bb37661395170a8e05701667dd45faed479a7fd4353'
    m=rd(manifest);assert {x['path'] for x in m['apply_files']}=={'backend/app/data/bare_survey_stac_file.py','tests/test_bare_survey_stac_file281.py'}
    core=rd(E/'deficit285-reviewed-code-pins-root-20261018.json')['source_pins']
    for n,h in core.items():assert sha(R/n)==h,n
    for x in m['baseline_only_do_not_apply']:assert sha(R/x['path'])==sha(W/x['path'])==x['sha256']
    for x in m['apply_files']:assert not (R/x['path']).exists() and sha(W/x['path'])==x['sha256']
    protected={p:sha(R/p) for p in ['data/first-group-training-esri-v1/annual-window-report.json','data/first-group-training-budget/global-ledger.json','data/first-group-training-priority/latest-candidate.json','data/first-group-training-priority/latest-bare-review.json','data/first-group-training-priority/source-profile237-root-20261018.json']}
    assert protected['data/first-group-training-esri-v1/annual-window-report.json']==av['source_sha256'] and protected['data/first-group-training-budget/global-ledger.json']==av['ledger_sha256']
    for x in m['apply_files']:
        with (R/x['path']).open('xb') as f:f.write((W/x['path']).read_bytes())
    result={'status':'APPLIED_VERIFICATION_PENDING','started_at':datetime.now(timezone.utc).isoformat(),'additive_files':m['apply_files'],'baseline_files_overwritten':0,'audit_sha256':a.audit_sha256,'operating_pins_before':protected,'collector_started':False,'http':0,'training_started':False,'registry_connected':False,'survey_runner_connected':False}
    write(E/'survey288-application-launch-root-20261018.json',result)
    temp=Path(tempfile.mkdtemp(prefix='survey288-',dir=E));assert temp.resolve().is_relative_to(E.resolve())
    env=dict(os.environ,PYTHONPATH=os.pathsep.join(str(R/x) for x in ('backend','tests','.runtime','.')),PYTHONIOENCODING='utf-8',TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))
    command=[sys.executable,'-X','utf8','-m','unittest','-q','test_bare_survey_stac_file281','test_bare_label_survey_contract','test_bare_survey_stac_binding']
    with (E/'survey288-project-regression-root-20261018.log').open('xb') as log:
        child=subprocess.Popen(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:print(json.dumps({'status':'ADDITIVE_TWO_FILES_APPLIED_TESTING','pid':child.pid}),flush=True)
        finally:code=child.wait()
    assert temp.resolve().is_relative_to(E.resolve()) and temp.name.startswith('survey288-')
    shutil.rmtree(temp)
    result.update(exit_code=code,seconds=round(time.monotonic()-start,3),operating_pins_preserved=all(sha(R/p)==h for p,h in protected.items()),core39_pins_preserved=all(sha(R/p)==h for p,h in core.items()),new2_pins_preserved=all(sha(R/x['path'])==x['sha256'] for x in m['apply_files']),project_test_log_sha256=sha(E/'survey288-project-regression-root-20261018.log'),expected_tests=61)
    ok=code==0 and all(result[k] for k in ('operating_pins_preserved','core39_pins_preserved','new2_pins_preserved'))
    result['status']='ADDITIVE_TWO_FILES_APPLIED_PROJECT61_VERIFIED' if ok else 'APPLICATION_OR_TESTS_INCOMPLETE_PRESERVED_NO_RETRY'
    write(E/'survey288-application-root-20261018.json',result);print(json.dumps(result,ensure_ascii=True),flush=True)
    return 0 if ok else 2
if __name__=='__main__':raise SystemExit(main())
