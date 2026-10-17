"""No existing product edits and no operating mutation in this pure-helper unit."""
from pathlib import Path
import datetime,hashlib,json,re,sqlite3
ROOT=Path(__file__).resolve().parents[2]
e=ROOT/'evidence/integration'
pre=json.loads((e/'model-provenance-preflight-20261017.json').read_text('utf-8'))
def rec(p):
    b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
protected=[n for n,v in pre['protected_references'].items() if Path(n).exists()!=v['exists'] or (Path(n).exists() and rec(Path(n))!={k:v[k] for k in ['sha256','bytes']})]
core=[n for n,sha in pre['unchanged_contract_baseline'].items() if rec(ROOT/n)['sha256']!=sha]
old_product=[n for n,v in pre['tracked_baseline'].items() if n.startswith(('backend/','frontend/','tests/','scripts/','data/')) and rec(ROOT/n)!=v]
old_evidence=[n for n,v in pre['tracked_baseline'].items() if n.startswith('evidence/') and rec(ROOT/n)!=v]
assert not protected and not core and not old_product and not old_evidence,(protected,core,old_product,old_evidence)
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as con:
    rows=con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert sha==pre['catalog_records_baseline']['canonical_records_sha256']
tests={}
for label in ['focused','related','independent']:
    name='evidence/integration/model-provenance-'+label+'-20261017.log'
    t=(ROOT/name).read_text('utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',t)
    assert m and re.search(r'^OK$',t,re.M),t[-1200:]
    tests[label]={'passed':int(m[1]),'seconds':float(m[2]),'log':name}
out={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'scope':'NEW_UNWIRED_PURE_HELPER_NOT_APPROVAL_OR_RESOLVER','tests':tests,'protected_references_checked':len(pre['protected_references']),'protected_reference_changes':protected,'existing_contracts_checked':len(pre['unchanged_contract_baseline']),'existing_contract_changes':core,'existing_product_changes':old_product,'previous_evidence_files_checked':sum(n.startswith('evidence/') for n in pre['tracked_baseline']),'previous_evidence_changes':old_evidence,'catalog_records':len(rows),'catalog_canonical_sha256':sha,'catalog_unchanged':True,'operating_registrations':0,'job_posts':0,'new_qa_or_training_executed':False,'full_regression_rerun_in_latest_unit':False,'previous_full_regression':{'tests_run':998,'passed':997,'skipped':1,'seconds':366.134,'log':'evidence/integration/model-version-api-full-tests-corrected-20261017.log'},'full_regression_scope_reason':'New pure helper has no existing product callers; targeted contract, registration compatibility and independent tests plus raw-byte preservation are used. Previous whole suite is retained as previous evidence.','direct_ui_change':False,'frontend_tests_build_browser_rerun':False,'ui_reason':'No endpoint or UI caller introduced; existing ModelReview and approval gates unchanged.','live_observation':'evidence/integration/model-provenance-catalog-observation-20261017.json'}
(e/'model-provenance-live-integrity-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
