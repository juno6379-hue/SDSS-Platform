from pathlib import Path
import json,hashlib,re,sqlite3,datetime,subprocess
ROOT=Path(__file__).resolve().parents[2]
pre=json.loads((ROOT/'evidence/integration/recovery-commit-contract-preflight-20261017.json').read_text('utf-8'))
def record(path):
 b=path.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
for name,p in pre['protected_references'].items():
 f=Path(name);assert f.exists()==p['exists']
 if f.exists():assert record(f)=={k:p[k] for k in ('sha256','bytes')}
old=pre['tracked_baseline']
changed=[n for n,p in old.items() if n.startswith(('backend/','frontend/','tests/','scripts/','data/')) and record(ROOT/n)!=p]
assert not changed,changed
additional_core={}
for name in ['scripts/collect_training_parallel.py','backend/app/data/budget.py']:
 original=subprocess.check_output(['git','show',pre['git_base_commit']+':'+name],cwd=ROOT)
 current=(ROOT/name).read_bytes();assert current==original,name
 additional_core[name]={'git_base_commit':pre['git_base_commit'],'sha256':hashlib.sha256(original).hexdigest(),'raw_bytes_unchanged':True}
assert record(ROOT/'backend/app/data/recovery_commit_contract.py')['sha256']=='d5c6ba7be180ab4e91454ec9d6d745d791263cedc4f347aaa96651914b13e388'
assert record(ROOT/'tests/test_recovery_commit_contract.py')['sha256']=='536232af37d06b81045e33a127fdaa4ae234782a1e1c14df592e32e7b0d1c78e'
previous_evidence=[n for n in old if n.startswith('evidence/')]
assert all(record(ROOT/n)==old[n] for n in previous_evidence)
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as c:
 rows=c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();assert sha==pre['catalog_sha256']
pending=[]
for key in ['parallel-v2-extra-banten-2023-v2-laneB-banten-boundary-01','parallel-v2-extra-west_java-2023-v2-laneB-west_java-boundary-01']:
 parent=ROOT/'data/first-group-training-esri-v1/sources'/key
 states={n:(parent/n).exists() for n in ['config.json','window-state.json','worker-result.json','annual-window-report.json']}
 assert states=={'config.json':True,'window-state.json':True,'worker-result.json':False,'annual-window-report.json':False},states
 pending.append({'batch':key,'artifact_exists':states})
out={'recorded_at':datetime.datetime.now().isoformat(),'scope':'PURE_CALLER_DECLARATION_TESTS_AND_TRACKED_PROTECTED_PRESERVATION_NOT_REAL_JOURNAL_OR_RECOVERY_EXECUTION','protected_references_checked':len(pre['protected_references']),'protected_reference_changes':[],'previous_evidence_files_checked':len(previous_evidence),'previous_evidence_file_changes':[],'existing_code_changes':changed,'catalog_records':len(rows),'catalog_sha256':sha,'catalog_unchanged':True,'actual_pending_batches':pending,'new_contract_applied_to_real_pending':False,'reason':'Terminal/reconciliation phase evidence missing; no synthetic operation identity or after-pins invented for real pending batches.','reserved_bytes_preserved':136314880,'real_journal_created':False,'collector_or_settle_changed':False,'operating_collection_training_qa_deployment':False,'live_jobs_or_model_registrations':0,'ui_changed':False,'full_regression_rerun_in_latest_unit':False,'previous_full_regression':json.loads((ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json').read_text('utf-8'))['reported_status']['current_regression']}
out['additional_core_git_baseline_checks']=additional_core
for label in ['focused','related','independent']:
 suffix=label+'-final2' if label in ('focused','related') else 'independent-final3'
 log='evidence/integration/recovery-commit-contract-'+suffix+'-20261017.log';text=(ROOT/log).read_text('utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
 assert m and re.search(r'^OK(?: \(skipped=\d+\))?$',text,re.M),text[-1200:]
 skip=re.search(r'^OK \(skipped=(\d+)\)',text,re.M);skipped=int(skip[1]) if skip else 0
 out[label]={'tests_run':int(m[1]),'passed':int(m[1])-skipped,'skipped':skipped,'seconds':float(m[2]),'log':log,'exit_code':0}
(ROOT/'evidence/integration/recovery-commit-contract-live-integrity-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
