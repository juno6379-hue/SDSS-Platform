"""Post-test byte preservation check against the recorded preflight."""
from pathlib import Path
import datetime,hashlib,json,re,sqlite3
ROOT=Path(__file__).resolve().parents[2]
pre=json.loads((ROOT/'evidence/integration/full-job-registration-api-preflight-20261017.json').read_text('utf-8'))
def record(path):
    data=path.read_bytes()
    return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
protected=[]
for name,prior in pre['protected_references'].items():
    path=Path(name)
    if path.exists()!=prior['exists'] or (path.exists() and record(path)!={k:prior[k] for k in ('sha256','bytes')}): protected.append(name)
contracts=[name for name,sha in pre['unchanged_contract_baseline'].items() if record(ROOT/name)['sha256']!=sha]
changed=[name for name,prior in pre['tracked_baseline'].items() if name.startswith(('backend/','frontend/','data/','tests/','scripts/')) and record(ROOT/name)!=prior]
assert not protected and not contracts
assert set(changed) <= set(pre['authorized_existing_code_changes']),changed
assert {'backend/app/workflow_job_request_handoff_api.py','frontend/src/FullJobHandoff.tsx'} <= set(changed)
prior_evidence=[name for name in pre['tracked_baseline'] if name.startswith('evidence/')]
prior_evidence_changes=[name for name in prior_evidence if record(ROOT/name)!=pre['tracked_baseline'][name]]
assert not prior_evidence_changes,prior_evidence_changes
with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as con:
    rows=con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
catalog_sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert catalog_sha==pre['catalog_records_baseline']['canonical_records_sha256']
log='evidence/integration/full-job-registration-api-full-tests-20261017.log'
text=(ROOT/log).read_text('utf-8')
match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
assert match and re.search(r'^OK \(skipped=1\)',text,re.M),text[-1500:]
total=int(match[1]);seconds=float(match[2])
out={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'TRACKED_PROTECTED_INPUTS_CORE_CATALOG_NOT_FULL_WORKSPACE_OR_ATOMIC_SNAPSHOT','protected_references_checked':len(pre['protected_references']),'protected_reference_changes':protected,'existing_contracts_checked':len(pre['unchanged_contract_baseline']),'existing_contract_changes':contracts,'previous_tracked_code_data_test_frontend_changes':changed,'only_authorized_existing_code_changes':True,'catalog_records':len(rows),'catalog_canonical_sha256':catalog_sha,'catalog_unchanged':True,'existing_gmais_job_bodies_unchanged':True,'live_new_job_posts':0,'capture_backfills':0,'actual_executor_connected':False,'new_qa_or_training_executed':False,'full_regression_status':'COMPLETED','full_regression':{'tests_run':total,'passed':total-1,'skipped':1,'seconds':seconds,'exit_code':0,'log':log},'post_full_preservation_rechecked':True}
for label,name in [('related','full-job-registration-api-related'),('independent','full-job-registration-api-independent')]:
    path='evidence/integration/'+name+'-20261017.log'
    content=(ROOT/path).read_text('utf-8')
    result=re.search(r'Ran (\d+) tests in ([\d.]+)s',content)
    assert result and re.search(r'^OK$',content,re.M)
    out[label]={'passed':int(result[1]),'seconds':float(result[2]),'log':path}
out['previous_evidence_files_checked']=len(prior_evidence)
out['previous_evidence_file_changes']=prior_evidence_changes
out['new_function_evidence_class']='TESTED_SYNTHETIC'
out['new_qa_or_training_executed_scope']='No new operating project QA or formal training; synthetic fixture tests remain included in full regression'
out['synthetic_fixture_tests_in_full_regression']=True
out['direct_ui_change']=True
out['direct_ui_change_reason']='Explicit opt-in RFC2 within existing manual fullJob panel; v1 default remains. API/UI tests and actual browser evidence recorded separately.'
out['live_job_submission_tested']=False
out['live_api_evidence']='evidence/integration/full-job-registration-api-live-api-20261017.json'
out['live_ui_evidence']='evidence/integration/full-job-registration-api-live-ui-20261017.json'
out['frontend']={}
for label,name in [('related_adapters','related'),('all_tests','tests'),('independent','independent')]:
    path='evidence/integration/full-job-registration-ui-'+name+'-20261017.log'
    content=(ROOT/path).read_text('utf-8')
    assert re.search(r'^# fail 0$',content,re.M),content[-1000:]
    out['frontend'][label]={'passed':int(re.search(r'^# pass (\d+)',content,re.M)[1]),'log':path}
build='evidence/integration/full-job-registration-ui-build-20261017.log'
content=(ROOT/build).read_text('utf-8')
out['frontend']['production_build']={'modules':int(re.search(r'(\d+) modules transformed',content)[1]),'seconds':float(re.search(r'built in ([\d.]+)s',content)[1]),'log':build,'existing_chunk_size_warning':True}
(ROOT/'evidence/integration/full-job-registration-api-live-integrity-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
