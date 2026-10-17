"""Freeze138 pure quality report preparation evidence, without operating writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2]
P='evidence/integration/'
def record(name):
    raw=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
assert record('backend/app/data/quality_mask_bundle.py')['sha256']=='72750fe9f1299a878a589e66ac1e0d53b01eddfc3af6237915e6e16bce623945'
assert record('tests/test_quality_mask_bundle.py')['sha256']=='1bfa06a5a21346af4c8d30390c6deaaf4690138eced2e6e99eccf46c5c70ffa6'
documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/138_quality_mask_bundle.md']:
    text=path.read_text('utf-8')
    if 'understanding' in path.parts and path.name!='GATE_TEMPLATE.md':
        for field in ('updated_at','source_commit','evidence_paths','confidence','status'):
            if not re.search(r'^\|\s*'+field+r'\s*\|',text,re.M):errors.append(path.name+': missing '+field)
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|',line):
                for name in re.findall(r'`([^`]+)`',line):
                    references+=1
                    if not (ROOT/name).exists():errors.append('missing evidence '+name)
    for value in re.findall(r'\]\(([^)]+)\)',text):
        name=unquote(value.strip('<>').split('#',1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:',name):continue
        links+=1
        if not (path.parent/name).exists():errors.append(path.name+': missing link '+name)
faq=len(re.findall(r'^## \d+\.',(ROOT/'docs/understanding/presentations/FAQ.md').read_text('utf-8'),re.M))
assert faq==10 and not errors,errors
assert (ROOT/'docs/understanding/GATE_TEMPLATE.md').read_bytes()==(ROOT/'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md').read_bytes()
audit={'checked_at':datetime.now().astimezone().isoformat(),'understanding_markdown':len(documents),'implementation_markdown':1,'local_links':links,'metadata_evidence_references':references,'numbered_faq':faq,'errors':errors,'reference_templates_byte_identical':True}
closeout={'status': '138_PURE_QUALITY_REPORT_BYTES_UNREGISTERED_MANIFEST_PATCH', 'focused': {'passed': 9, 'seconds': 1.103, 'log': 'evidence/integration/quality-mask-bundle-agent-20261018.log'}, 'related': {'passed': 39, 'seconds': 9.865, 'log': 'evidence/integration/quality-mask-bundle-root-related-20261018.log'}, 'independent': {'schema_version': 1, 'scope': 'INDEPENDENT_QUALITY_MASK_BUNDLE_TEMP_FIXTURES_ONLY', 'status': 'TESTED_SYNTHETIC', 'tests_run': 7, 'tests': 7, 'passed': 7, 'failures': 0, 'errors': 0, 'skipped': 0, 'elapsed_seconds': 1.4408524999889778, 'seconds': 1.4408524999889778, 'source_sha256': '72750fe9f1299a878a589e66ac1e0d53b01eddfc3af6237915e6e16bce623945', 'test_sha256': '1bfa06a5a21346af4c8d30390c6deaaf4690138eced2e6e99eccf46c5c70ffa6', 'git_baseline': 'f01752a699497e94bece097865c862e1173d5bf1', 'separate_git_baseline_matches': {'backend/app/dataset_registry.py': True, 'backend/app/ml/per_scene_normalization_files.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_quality_mask_grid.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'scripts/collect_samples.py': True, 'scripts/collect_training_grid.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True}, 'existing_source_unchanged': {'backend/app/dataset_registry.py': True, 'backend/app/ml/per_scene_normalization_files.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_quality_mask_grid.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'scripts/collect_samples.py': True, 'scripts/collect_training_grid.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True}, 'observations': [{'fixture': 'actual fresh TempStore SQLite +6bandGTiff+checkerboardGTiff+reportbytes', 'registry_fixture_setup_writes': 3, 'consumer_gets': 6, 'counts': {'valid_pixels': 128, 'invalid_pixels': 128, 'total_pixels': 256}, 'source_manifest_quality': 'RAW', 'mask_manifest_quality': 'STAGED', 'database_and_all_files_unchanged_after_consumption': True, 'preparer_registry_or_file_operations': 0, 'scientific_accuracy_validated': False, 'execution_authorized': False}, {'counterexample': 'nodata0', 'prepared': True, 'consumer_status': 'BLOCKED', 'issue': 'MASK_INTRINSIC_VALIDITY_UNSUPPORTED', 'all_files_unchanged': True}, {'counterexample': 'value255', 'prepared': True, 'consumer_status': 'BLOCKED', 'issue': 'MASK_VALUES_NOT_BINARY', 'all_files_unchanged': True}, {'counterexample': 'restricted', 'prepared': True, 'consumer_status': 'BLOCKED', 'issue': 'ACCESS_DECLARATION_BLOCKED', 'all_files_unchanged': True}], 'fixture_scope': {'actual': 'fresh temporary GTiff files/report bytes and SQLite DatasetVersion registry; readonly SQL consumption', 'mocked': 'I/O denial guards, write denial guards, call counters and custom type poison only; no mocked successful consumer responses'}, 'operating_data_access': False, 'operating_writes': 0, 'training': 0, 'inference': 0, 'api_or_ui_changed': False, 'frontend_build_browser_required': False, 'limitations': ['Producer prepares bytes/drafts only; explicit test caller supplies missing report metadata.', 'TempStore registration setup is synthetic fixture creation, not preparation or operating registration.', '128/256 is binary syntax/count evidence, not semantic quality, scientific accuracy, or a minimum policy approval.', 'Legacy nodata=0, missing image descriptions and label/AOI-combined collector masks remain unresolved.', 'No source files, old tests, operating data, main or UI were edited.']}, 'integrity': {'recorded_at': '2026-10-18T05:51:04.341007+09:00', 'protected_files_checked': 141, 'protected_changes': [], 'existing_source_checked': 314, 'existing_source_changes': [], 'expected_changed_existing_sources': [], 'unchanged_existing_source_files': 314, 'previous_evidence_checked': 1275, 'previous_evidence_changes': [], 'catalog_rows': 14, 'catalog_canonical_sha256': '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b', 'reserved_bytes_preserved': 136314880, 'existing_execution_workflow_model_and_other_sources_unchanged': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0}, 'understanding_updated': True, 'ui_api_connected': False, 'backend_full_rerun_this_unit': False, 'frontend_build_browser_rerun_this_unit': False, 'operating_collection_training_registry_approval_deployment_workflow_dispatch': 0, 'report_metadata_missing_by_design': ['source', 'spatial', 'temporal', 'quality_status', 'access_class'], 'automatic_quality_promotion': False, 'artifact_bytes_verified': False, 'source_authority_verified': False, 'scientific_accuracy_validated': False, 'execution_authorized': False, 'workflow_supported': False, 'next_internal_candidate': '139_CALLER_REPORT_METADATA_COMPLETION_CONTRACT'}
closeout['documentation_validation']=audit
closeout['recorded_at']=audit['checked_at']
closeout['source_records']={n:record(n) for n in ['backend/app/data/quality_mask_bundle.py','tests/test_quality_mask_bundle.py']}
processes=json.loads((ROOT/P/'quality-mask-bundle-final-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status']=='ACTIVE' and processes['collector_training_processes_observed']==0
closeout['live_processes']=processes
closeout['operating_inventory']=json.loads((ROOT/P/'quality-mask-bundle-operating-inventory-20261018.json').read_text('utf-8'))
closeout['source_authority_and_report_metadata_not_invented']=True
closeout['bounded_declaration_subset_is_not_full_upstream_schema_or_file_validation']=True
closeout['report_bytes_require_separate_explicit_caller_storage']=True
closeout['previous_full_backend']={'unit':137,'passed':1358,'skipped':1,'seconds':484.770}
closeout['previous_frontend']={'unit':137,'passed':271,'build_modules':112,'build_seconds':13.48}
closeout['separately_updated_status_documents_reviewed']=json.loads((ROOT/P/'quality-mask-bundle-separate-status-docs-20261018.json').read_text('utf-8'))
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
names=set(snapshot['files'])|(publish-tracked)|changed
target=ROOT/P/'quality-mask-bundle-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='f01752a699497e94bece097865c862e1173d5bf1'
snapshot['source_commit_reason']='Published137 baseline plus138 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=False
snapshot['reported_status']['latest_quality_mask_bundle_preparation']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
