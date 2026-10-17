"""Freeze143 explicit quality report CLI evidence; no operating writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2];P='evidence/integration/'
def record(name):
    raw=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/143_quality_report_cli.md']:
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
closeout={'status': '143_EXPLICIT_QUALITY_REPORT_CLI_ONLY', 'focused': {'passed': 11, 'seconds': 12.558, 'log': 'evidence/integration/quality-report-cli-agent-20261018.log'}, 'related': {'passed': 90, 'seconds': 37.707, 'log': 'evidence/integration/quality-report-cli-root-related-20261018.log'}, 'independent': {'schema_version': 1, 'scope': 'INDEPENDENT_EXPLICIT_REPORT_CLI_TEMP_ONLY', 'git_baseline': 'e3262a3acb09f89a48124cfc9f32c20bb923975a', 'tests': 10, 'passed': 9, 'skipped': 1, 'skip_reasons': ['actual symlink unavailable winerror=1314 errno=22'], 'failures': 0, 'errors': 0, 'seconds': 33.00781900000584, 'source_sha256': 'a6fb6388674ef41ab30329ff55dcb1291e1221cb7d9d8068c7dd6689f5eed87d', 'test_sha256': '37dd83beb849cc985ce4539d959be88b5de464731c21194816ec7e3cb8f0c3d1', 'test_names': ['test_00_frozen_source_and_test_hashes', 'test_01_actual_subprocess_inspect_without_catalog_and_no_store_calls', 'test_02_actual_register_replay_and_readonly_consumers', 'test_03_missing_invalid_catalog_and_schema_no_creation', 'test_04_actual_argument_errors_and_help_do_not_leak_secret', 'test_05_actual_strict_json_and_size_before_constructor', 'test_05b_repeated_options_and_missing_sources_no_registration', 'test_06_inprocess_inspect_child_tamper_and_mutation', 'test_07_inprocess_post_constructor_error_and_real_commit_uncertainty', 'test_08_actual_input_symlink_permission_skip'], 'separate_git_baseline_matches': {'backend/app/data/quality_report_preflight.py': True, 'tests/test_quality_report_preflight.py': True, 'backend/app/data/quality_report_storage.py': True, 'backend/app/data/quality_report_completion.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/store.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True, 'backend/app/data/quality_report_registration.py': True, 'tests/test_quality_report_registration.py': True}, 'old_sources_unchanged': {'backend/app/data/quality_report_preflight.py': True, 'tests/test_quality_report_preflight.py': True, 'backend/app/data/quality_report_storage.py': True, 'backend/app/data/quality_report_completion.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/store.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True, 'backend/app/data/quality_report_registration.py': True, 'tests/test_quality_report_registration.py': True}, 'observations': [{'actual': 'subprocess inspect with no catalog.sqlite3', 'same_files': True, 'inprocess_guard_Store_and_SQL_calls': 0}, {'actual': 'subprocess report-only registration 2 to 3 rows, byte-identical replay and readonly131133', 'counts': {'valid_pixels': 128, 'invalid_pixels': 128, 'total_pixels': 256}, 'operating_registration': 0}, {'explicit_fault_injection': 'constructor / before commit / actual commit then error or contaminated return', 'actual_post_commit_rows': 3, 'rollback_retry_delete': 0}], 'actual_scope': 'Fresh Temp GTiff/SQLite fixture, subprocess inspect/register/replay, readonly131133; no existing product test cases executed.', 'mock_scope': 'Explicit inprocess constructor and child-output faults, actual-commit-then-error, post-copy mutable output mutation.', 'operating_store_access': False, 'operating_writes': 0, 'training': 0, 'inference': 0, 'api_ui_changed': False, 'frontend_build_browser_required': False, 'limitations': ['Store constructor is intentionally used for register after readonly catalog checks; its mkdir/CREATE IF NOT EXISTS are normal no-op intent, not a universal physical-write guarantee.', 'Constructor-started or malformed post-registration output can hide a committed report; UNCONFIRMED does not mean rollback or absence.', 'Sequential filesystem/SQLite observations are not atomic, an OS sandbox, resource/SLA guarantee or institution/scientific/execution approval.', 'Actual symlink creation depends on Windows privilege; permission failures are SKIP, not mock successes.']}, 'integrity': {'recorded_at': '2026-10-18T06:45:04.962231+09:00', 'protected_files_checked': 141, 'protected_changes': [], 'existing_source_checked': 324, 'existing_source_changes': [], 'expected_changed_existing_sources': [], 'unchanged_existing_source_files': 324, 'previous_evidence_checked': 1366, 'previous_evidence_changes': [], 'catalog_rows': 14, 'catalog_canonical_sha256': '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b', 'reserved_bytes_preserved': 136314880, 'existing_execution_workflow_model_and_other_sources_unchanged': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0}, 'understanding_updated': True, 'web_ui_api_connected': False, 'backend_full_rerun_this_unit': False, 'frontend_build_browser_rerun_this_unit': False, 'operating_collection_training_registry_approval_deployment_workflow_dispatch': 0, 'temporary_subprocess_inspect_register_tested': True, 'operating_cli_inspect_register_invocations': 0, 'automatic_quality_promotion': False, 'source_authority_verified': False, 'scientific_accuracy_validated': False, 'execution_authorized': False, 'workflow_supported': False, 'atomic_file_registry_snapshot': False, 'hostile_filesystem_confinement': False, 'automatic_retry_or_rollback': False, 'next_internal_candidate': '144_NEW_COLLECTION_BAND_AND_QUALITY_MASK_DECLARATION_INTEGRATION_REVIEW'}
closeout['recorded_at']=audit['checked_at'];closeout['documentation_validation']=audit
closeout['integrity']=json.loads((ROOT/P/'quality-report-cli-live-integrity-final-20261018.json').read_text('utf-8'))
assert not closeout['integrity']['protected_changes'] and not closeout['integrity']['existing_source_changes'] and not closeout['integrity']['previous_evidence_changes']
closeout['source_records']={n:record(n) for n in ['scripts/quality_report_cli.py','tests/test_quality_report_cli.py']}
assert closeout['source_records']['scripts/quality_report_cli.py']['sha256']==closeout['independent']['source_sha256']
assert closeout['source_records']['tests/test_quality_report_cli.py']['sha256']==closeout['independent']['test_sha256']
processes=json.loads((ROOT/P/'quality-report-cli-final-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status']=='ACTIVE' and processes['collector_training_processes_observed']==0
closeout['live_processes']=processes
closeout['operating_inventory']=json.loads((ROOT/P/'quality-report-cli-operating-inventory-20261018.json').read_text('utf-8'))
closeout['previous_full_backend']={'unit':137,'passed':1358,'skipped':1,'seconds':484.770}
closeout['previous_frontend']={'unit':137,'passed':271,'build_modules':112,'build_seconds':13.48}
closeout['separately_updated_status_documents_reviewed']=json.loads((ROOT/P/'quality-report-cli-separate-status-docs-20261018.json').read_text('utf-8'))
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
names=set(snapshot['files'])|(publish-tracked)|changed
target=ROOT/P/'quality-report-cli-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='e3262a3acb09f89a48124cfc9f32c20bb923975a'
snapshot['source_commit_reason']='Published142 baseline plus143 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=False
snapshot['reported_status']['latest_explicit_quality_report_cli']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
