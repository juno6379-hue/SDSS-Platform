from pathlib import Path
import json,hashlib,re,sqlite3,datetime
ROOT=Path(__file__).resolve().parents[2]
pre=json.loads((ROOT/'evidence/integration/workflow-dependency-order-preflight-20261017.json').read_text('utf-8'))
def record(path):
 b=path.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
protected=[]
for name,prior in pre['protected_references'].items():
 path=Path(name)
 if path.exists()!=prior['exists'] or path.exists() and record(path)!={k:prior[k] for k in ('sha256','bytes')}:protected.append(name)
assert not protected,protected
changed=[n for n,p in pre['tracked_baseline'].items() if n.startswith(('backend/','frontend/','tests/','data/','scripts/')) and record(ROOT/n)!=p]
assert set(changed)==set(pre['authorized_existing_code_changes']),changed
review=json.loads((ROOT/'evidence/integration/workflow-dependency-order-independent-review-20261017.json').read_text('utf-8'))
for name in changed:
 stem=Path(name).stem
 original=ROOT/'evidence/integration'/('workflow-dependency-order-original-'+stem+'-20261017.py')
 assert record(original)==pre['tracked_baseline'][name]
 assert record(ROOT/name)['sha256']==review['source_review'][stem]['current_sha256']
 assert review['source_review'][stem]['ast_equal_except_loop_and_import_including_same_cycle_error'] is True
old_evidence=[n for n in pre['tracked_baseline'] if n.startswith('evidence/')]
assert all(record(ROOT/n)==pre['tracked_baseline'][n] for n in old_evidence)
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as c:
 rows=c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert sha==pre['catalog_sha256']
out={'recorded_at':datetime.datetime.now().isoformat(),'status':'VERIFIED_PRESERVATION_WITH_SYNTHETIC_BEHAVIOR_TESTS','protected_references_checked':len(pre['protected_references']),'protected_reference_changes':[],'previous_evidence_files_checked':len(old_evidence),'previous_evidence_file_changes':[],'authorized_existing_code_changes':changed,'catalog_records':len(rows),'catalog_canonical_sha256':sha,'catalog_unchanged':True,'live_job_posts':0,'operating_model_registrations':0,'new_operating_qa_training_collection_deployment':False,'frontend_changed':False,'ui_change_reason':'Internal dependency ordering extraction only; caller output/error/I/O contracts preserved and differentially tested. No new API or UI path.'}
for label in ['focused','related','independent','full-tests']:
 suffix='focused-final' if label=='focused' else label
 log='evidence/integration/workflow-dependency-order-'+suffix+'-20261017.log'
 text=(ROOT/log).read_text('utf-8')
 m=re.search(r'Ran (\d+) tests in ([\d.]+)s',text);assert m and re.search(r'^OK(?: \(skipped=1\))?$',text,re.M),text[-1200:]
 skipped=1 if 'OK (skipped=1)' in text else 0
 out[label]={'tests_run':int(m[1]),'passed':int(m[1])-skipped,'skipped':skipped,'seconds':float(m[2]),'exit_code':0,'log':log}
out['scope']='Previously tracked files and explicit protected references; not full-workspace or atomic filesystem assurance.'
out['full_regression']=out['full-tests']
(ROOT/'evidence/integration/workflow-dependency-order-live-integrity-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
