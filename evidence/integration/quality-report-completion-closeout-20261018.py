"""Freeze139 explicit metadata completion evidence; no operating writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2];P='evidence/integration/'
def record(name):
    raw=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/139_quality_report_completion.md']:
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
closeout={'status': '139_EXPLICIT_METADATA_UNREGISTERED_REPORT_MANIFEST_COMPLETION', 'focused': {'passed': 9, 'seconds': 1.234, 'log': 'evidence/integration/quality-report-completion-agent-final-20261018.log'}, 'related': {'passed': 48, 'seconds': 12.067, 'log': 'evidence/integration/quality-report-completion-root-related-final2-20261018.log'}, 'independent': {'schema_version': 1, 'scope': 'INDEPENDENT_EXPLICIT_QUALITY_REPORT_COMPLETION_TEMP_ONLY', 'status': 'TESTED_SYNTHETIC', 'tests': 8, 'passed': 8, 'skipped': 0, 'failures': 0, 'errors': 0, 'seconds': 2.0615961000003153, 'test_names': ['test_01_frozen_sha_no_store_or_schema_io_imports', 'test_02_exact_full_caller_metadata_and_detached_bytes', 'test_03_metadata_invalid_before_producer_noio', 'test_04_untrusted_parent_typed_flags_refs_bytes_and_partial_failures', 'test_05_producer_argument_mutation_cannot_change_verification_snapshot', 'test_06_actual_temp_complete_manifest_schema_sqlite_consumption', 'test_07_preparation_is_not_access_quality_or_mask_conversion', 'test_08_post_validation_parent_mutation_old_sha_reproduction_and_fixed_snapshot'], 'source_sha256': 'd98c9d52e8add04b5a620d78d4e988e633477f761003ae646f6dc99906efab39', 'test_sha256': '86f3f04a7778bd688ccb922e9dc59108dee6340d9ffbce0fa97b1894b51be07d', 'git_baseline': '200d22c3c7f146f795c26442eec1bd971733770d', 'separate_git_baseline_matches': {'backend/app/data/quality_mask_bundle.py': True, 'tests/test_quality_mask_bundle.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/ml/per_scene_normalization_files.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_quality_mask_grid.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'scripts/collect_samples.py': True, 'scripts/collect_training_grid.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True}, 'old_sources_unchanged': {'backend/app/data/quality_mask_bundle.py': True, 'tests/test_quality_mask_bundle.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/ml/per_scene_normalization_files.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_quality_mask_grid.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'scripts/collect_samples.py': True, 'scripts/collect_training_grid.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True}, 'observations': [{'actual': 'fresh Temp GTiff image6/mask1 +complete caller-metadata report +SQLite3versions', 'fixture_registry_setup_writes': 3, 'readonly_consumer_gets': 6, 'counts': {'valid_pixels': 128, 'invalid_pixels': 128, 'total_pixels': 256}, 'source_quality': 'RAW', 'report_quality': 'STAGED', 'files_and_db_unchanged': True, 'approval': False}, {'counterexample': 'restricted_image_public_report', 'completion_prepared': True, 'consumer': 'BLOCKED', 'code': 'ACCESS_DECLARATION_BLOCKED', 'image_access_preserved': 'RESTRICTED', 'explicit_report_access_preserved': 'PUBLIC', 'files_and_db_unchanged': True, 'approval': False}, {'counterexample': 'nodata0', 'completion_prepared': True, 'consumer': 'BLOCKED', 'code': 'MASK_INTRINSIC_VALIDITY_UNSUPPORTED', 'image_access_preserved': 'PUBLIC', 'explicit_report_access_preserved': 'PUBLIC', 'files_and_db_unchanged': True, 'approval': False}, {'counterexample': 'value255', 'completion_prepared': True, 'consumer': 'BLOCKED', 'code': 'MASK_VALUES_NOT_BINARY', 'image_access_preserved': 'PUBLIC', 'explicit_report_access_preserved': 'PUBLIC', 'files_and_db_unchanged': True, 'approval': False}, {'explicit_mock': 'producer dict mutated immediately after successful typed validation', 'initial_source_sha256': '0ef9c2930df1224eeb1f130b80b0dd15d799776d734cf713805abb08e05240e9', 'reconstructed_initial_source_bytes_sha_verified': True, 'final_source_sha256': 'd98c9d52e8add04b5a620d78d4e988e633477f761003ae646f6dc99906efab39', 'results': [{'version': 'initial_exact_sha', 'returned_bytes_match_fixed_sha': False}, {'version': 'final_frozen_sha', 'returned_bytes_match_fixed_sha': True}], 'operating_concurrency_test': False}], 'actual_scope': 'fresh Temp files, complete manifest96schema, actual SQLite version setup then readonlySQL131/133 consumption', 'mock_scope': 'I/O/write denial guards, producer call counter and explicitly malformed/argument-mutating138 parent only; no mocked successful131/133 responses', 'operating_data_access': False, 'operating_writes': 0, 'training': 0, 'inference': 0, 'api_ui_changed': False, 'frontend_build_browser_required': False, 'limitations': ['Pure completion preserves caller statements; no report/image QA equality or cross-access authority policy is verified.', 'Synthetic registration occurs only during explicit Temp fixture setup, not in product completion.', '128/256 is observed binary count, not scientific or institutional approval.', 'Legacy nodata0 and label/AOI-derived masks, actual production/registration/approval remain separate.']}, 'integrity': {'recorded_at': '2026-10-18T06:00:05.054094+09:00', 'protected_files_checked': 141, 'protected_changes': [], 'existing_source_checked': 316, 'existing_source_changes': [], 'expected_changed_existing_sources': [], 'unchanged_existing_source_files': 316, 'previous_evidence_checked': 1291, 'previous_evidence_changes': [], 'catalog_rows': 14, 'catalog_canonical_sha256': '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b', 'reserved_bytes_preserved': 136314880, 'existing_execution_workflow_model_and_other_sources_unchanged': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0}, 'understanding_updated': True, 'ui_api_connected': False, 'backend_full_rerun_this_unit': False, 'frontend_build_browser_rerun_this_unit': False, 'operating_collection_training_registry_approval_deployment_workflow_dispatch': 0, 'automatic_quality_promotion': False, 'artifact_bytes_verified': False, 'source_authority_verified': False, 'scientific_accuracy_validated': False, 'execution_authorized': False, 'workflow_supported': False, 'next_internal_candidate': '140_EXPLICIT_NEW_PATH_REPORT_STORAGE_WITHOUT_OVERWRITE_OR_REGISTRATION'}

closeout['recorded_at']=audit['checked_at'];closeout['documentation_validation']=audit
closeout['integrity']=json.loads((ROOT/P/'quality-report-completion-live-integrity-final-20261018.json').read_text('utf-8'))
assert not closeout['integrity']['protected_changes'] and not closeout['integrity']['existing_source_changes'] and not closeout['integrity']['previous_evidence_changes']
closeout['source_records']={n:record(n) for n in ['backend/app/data/quality_report_completion.py','tests/test_quality_report_completion.py']}
assert closeout['source_records']['backend/app/data/quality_report_completion.py']['sha256']==closeout['independent']['source_sha256']
assert closeout['source_records']['tests/test_quality_report_completion.py']['sha256']==closeout['independent']['test_sha256']
processes=json.loads((ROOT/P/'quality-report-completion-final-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status']=='ACTIVE' and processes['collector_training_processes_observed']==0
closeout['live_processes']=processes
closeout['operating_inventory']=json.loads((ROOT/P/'quality-report-completion-operating-inventory-20261018.json').read_text('utf-8'))
closeout['previous_full_backend']={'unit':137,'passed':1358,'skipped':1,'seconds':484.770}
closeout['previous_frontend']={'unit':137,'passed':271,'build_modules':112,'build_seconds':13.48}
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
names=set(snapshot['files'])|(publish-tracked)|changed
target=ROOT/P/'quality-report-completion-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='200d22c3c7f146f795c26442eec1bd971733770d'
snapshot['source_commit_reason']='Published138 baseline plus139 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=False
snapshot['reported_status']['latest_quality_report_metadata_completion']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
