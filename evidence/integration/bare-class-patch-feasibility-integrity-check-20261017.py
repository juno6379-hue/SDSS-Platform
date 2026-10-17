from pathlib import Path
import json,hashlib,re,sqlite3,datetime
ROOT=Path(__file__).resolve().parents[2]
pre=json.loads((ROOT/'evidence/integration/bare-class-patch-feasibility-preflight-20261017.json').read_text('utf-8'))
def record(path):
 b=path.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
for name,p in pre['protected_references'].items():
 f=Path(name);assert f.exists()==p['exists']
 if f.exists():assert record(f)=={k:p[k] for k in ('sha256','bytes')}
old=pre['tracked_baseline']
changed=[n for n,p in old.items() if n.startswith(('backend/','frontend/','tests/','scripts/','data/')) and record(ROOT/n)!=p]
assert not changed,changed
old_evidence=[n for n in old if n.startswith('evidence/')]
assert all(record(ROOT/n)==old[n] for n in old_evidence)
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as c:
 rows=c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();assert sha==pre['catalog_sha256']
report_path=ROOT/'data/first-group-candidate-readiness-qa-20261017/readiness.json'
assert record(report_path)['sha256']=='847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019'
report=json.loads(report_path.read_text('utf-8'))
live_path=ROOT/'evidence/integration/bare-class-patch-feasibility-live-20261017.json'
live=json.loads(live_path.read_text('utf-8'))
assert live['status']=='BLOCKED' and live['stored_requirements']['pin_validation']=='PINNED_REPORT_BYTES_AND_STABILITY_VERIFIED'
observed={}
for split in ('train','val','test'):
 E=report['patch_counts_by_split'][split];B=report['class_counts_by_split'][split][7];T=report['policy']['min_class_pixels_per_patch'];R=report['policy']['min_class_patches_per_split'];C=256**2
 n=B-E*(T-1);d=C-T+1;q,rem=divmod(n,d);L=max(0,q+bool(rem));U=min(E,B//T)
 actual=live['by_split'][split]
 assert actual['minimum_contributing_patches_from_aggregate']==L and actual['maximum_contributing_patches_from_aggregate']==U
 assert actual['necessary_total_bare_pixel_shortfall']==max(0,R*T-B)
 assert actual['observed_contributing_patches']==report['class_patch_counts_by_split'][split][7]==0
 observed[split]={'range':[L,U],'observed':actual['observed_contributing_patches'],'necessary_total_shortfall':max(0,R*T-B),'existing_absolute_floor_shortfall':max(0,report['policy']['min_class_pixels_per_split']-B)}
out={'recorded_at':datetime.datetime.now().isoformat(),'scope':'STORED_METADATA_ARITHMETIC_NOT_NEW_PIXEL_QA_TRAINING_OR_COLLECTION','protected_references_checked':len(pre['protected_references']),'protected_reference_changes':[],'previous_evidence_files_checked':len(old_evidence),'previous_evidence_file_changes':[],'existing_code_changes':changed,'catalog_records':len(rows),'catalog_sha256':sha,'catalog_unchanged':True,'live_cli_exit_code':0,'live_result':record(live_path),'independent_arithmetic_matches':True,'by_split':observed,'new_operating_qa_training_collection_deployment':False,'live_job_posts':0,'model_registrations':0,'ui_changed':False,'full_regression_rerun_in_latest_unit':False,'previous_full_regression':json.loads((ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json').read_text('utf-8'))['reported_status']['current_regression']}
for label,suffix in [('focused','focused'),('related','related-corrected'),('independent','independent')]:
 log='evidence/integration/bare-class-patch-feasibility-'+suffix+'-20261017.log';text=(ROOT/log).read_text('utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
 assert m and re.search(r'^OK$',text,re.M),text[-1200:]
 out[label]={'passed':int(m[1]),'seconds':float(m[2]),'log':log,'exit_code':0}
out['initial_related_command_failure']='Two nonexistent module names; corrected command only, initial log retained; no product or test correction.'
(ROOT/'evidence/integration/bare-class-patch-feasibility-live-integrity-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
