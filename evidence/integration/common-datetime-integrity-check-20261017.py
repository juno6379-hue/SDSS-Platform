"""Post-test byte preservation check against the recorded preflight."""
from pathlib import Path
import datetime,hashlib,json,re,sqlite3
ROOT=Path(__file__).resolve().parents[2]
pre=json.loads((ROOT/'evidence/integration/common-datetime-preflight-20261017.json').read_text('utf-8'))
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
assert set(changed)==set(pre['authorized_existing_code_changes']),changed
with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as con:
    rows=con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
catalog_sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert catalog_sha==pre['catalog_records_baseline']['canonical_records_sha256']
log='evidence/integration/common-datetime-full-tests-20261017.log'
text=(ROOT/log).read_text('utf-8')
match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
assert match and re.search(r'^OK \(skipped=1\)',text,re.M),text[-1500:]
total=int(match[1]);seconds=float(match[2])
out={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'TRACKED_PROTECTED_INPUTS_CORE_CATALOG_NOT_FULL_WORKSPACE_OR_ATOMIC_SNAPSHOT','protected_references_checked':len(pre['protected_references']),'protected_reference_changes':protected,'existing_contracts_checked':len(pre['unchanged_contract_baseline']),'existing_contract_changes':contracts,'previous_tracked_code_data_test_frontend_changes':changed,'only_authorized_existing_code_changes':True,'catalog_records':len(rows),'catalog_canonical_sha256':catalog_sha,'catalog_unchanged':True,'existing_gmais_job_bodies_unchanged':True,'live_new_job_posts':0,'capture_backfills':0,'actual_executor_connected':False,'new_qa_or_training_executed':False,'full_regression_status':'COMPLETED','full_regression':{'tests_run':total,'passed':total-1,'skipped':1,'seconds':seconds,'exit_code':0,'log':log},'post_full_preservation_rechecked':True}
for label,name in [('related','common-datetime-related'),('independent','common-datetime-independent')]:
    path='evidence/integration/'+name+'-20261017.log'
    content=(ROOT/path).read_text('utf-8')
    result=re.search(r'Ran (\d+) tests in ([\d.]+)s',content)
    assert result and re.search(r'^OK$',content,re.M)
    out[label]={'passed':int(result[1]),'seconds':float(result[2]),'log':path}
out['new_function_evidence_class']='TESTED_SYNTHETIC'
out['direct_ui_change']=False
out['direct_ui_change_reason']='Existing submit INVALID_REQUEST 400 and full Job draft schema INVALID 200 BLOCKED remain unchanged; UI agent read-only contract review completed. No frontend change or new browser test.'
out['live_job_submission_tested']=False
(ROOT/'evidence/integration/common-datetime-live-integrity-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
