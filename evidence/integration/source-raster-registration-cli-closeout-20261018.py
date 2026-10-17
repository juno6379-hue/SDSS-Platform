"""Freeze146 source raster registration CLI evidence; no operating writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2];P='evidence/integration/'
def record(name):
    raw=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/146_source_raster_registration_cli.md']:
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
closeout={'status': '146_EXPLICIT_SOURCE_RASTER_REGISTRATION_CLI', 'focused': {'tests': 13, 'passed': 12, 'skipped': 1, 'seconds': 10.075, 'log': 'evidence/integration/source-raster-registration-cli-agent-20261018.log'}, 'related': {'tests': 127, 'passed': 126, 'skipped': 1, 'seconds': 46.97, 'log': 'evidence/integration/source-raster-registration-cli-root-related-20261018.log'}, 'independent': {'schema_version': 1, 'scope': 'INDEPENDENT_SOURCE_RASTER_REGISTRATION_CLI_TEMP_ONLY', 'git_baseline': 'f4565f5ff9b743cfd51cea087bbcf7d2e840729f', 'tests': 11, 'passed': 10, 'skipped': 1, 'skip_reasons': ['actual symlink unavailable winerror=1314 errno=22'], 'failures': 0, 'errors': 0, 'seconds': 25.698676500003785, 'source_sha256': 'befa11f07709501a10b440409e2dad495a8ee04570f30d9347818522a0511de8', 'test_sha256': '1f3b2e82a24accf68a0bc7a4464846ffb3890c61b2b3d1997d46d2e4c65517c4', 'test_names': ['test_00_frozen_source_and_tests', 'test_01_actual_external_cwd_source2_cli_report_cli_and_readonly_consumers', 'test_02_actual_raw_staged_accept_and_type_quality_upgrade_reject', 'test_03_actual_conflict_preserves_original_and_uncertainty', 'test_04_actual_opaque_raster_restricted_and_unresolved_lineage_are_unapproved', 'test_05_actual_strict_json_bad_args_catalog_and_sha_no_registration', 'test_06_inprocess_constructor_register_and_actual_post_commit_faults', 'test_07_inprocess_validator_and_return_record_mutation_private_copy', 'test_08_actual_manifest_symlink_permission_skip', 'test_09_actual_catalog_and_sidecar_artifacts_block_before_constructor', 'test_10_actual_hardlink_to_catalog_block_before_constructor'], 'old_sources_unchanged': {'backend/app/data/quality_report_preflight.py': True, 'tests/test_quality_report_preflight.py': True, 'backend/app/data/quality_report_storage.py': True, 'backend/app/data/quality_report_completion.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/store.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True, 'backend/app/data/quality_report_registration.py': True, 'tests/test_quality_report_registration.py': True, 'scripts/quality_report_cli.py': True, 'scripts/collect_samples.py': True, 'scripts/collect_training_grid.py': True}, 'separate_git_baseline_matches': {'backend/app/data/quality_report_preflight.py': True, 'tests/test_quality_report_preflight.py': True, 'backend/app/data/quality_report_storage.py': True, 'backend/app/data/quality_report_completion.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/store.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True, 'backend/app/data/quality_report_registration.py': True, 'tests/test_quality_report_registration.py': True, 'scripts/quality_report_cli.py': True, 'scripts/collect_samples.py': True, 'scripts/collect_training_grid.py': True}, 'observations': [{'actual': 'external cwd/no PYTHONPATH new CLI image+mask two explicit registrations -> caller Python140 file preparation ->143 inspect/register ->131133 readonly', 'python_source_registration_setup': 0, 'initial_empty_catalog_setup': True, 'source_rows': 2, 'report_rows': 1, 'counts': {'valid_pixels': 128, 'invalid_pixels': 128, 'total_pixels': 256}, 'replay_all_db_files_unchanged': True}, {'actual_counterexample': 'opaque bytes + declared raster + RESTRICTED + nonexistent lineage parent accepted as unapproved metadata/hash registration', 'native_GTIFF_or_parent_ACL_verification': False, 'scientific_or_execution_approval': False}, {'explicit_fault_injection': 'constructor/before-register/real-commit-then-error/contaminated-record', 'actual_after_commit_rows': 1, 'rollback_retry_delete': 0}, {'actual_self_reference_prevention': 'catalog and case alias plus journal/wal/shm artifact paths rejected before Store constructor', 'writes_during_cli': 0}, {'actual_catalog_hardlink': 'created in explicit Temp, samefile true; rejected before constructor', 'writes_during_cli': 0}], 'initial_evidence_preserved': {'py': '7ec323d589b0e6c36a8948c8063da61936b26407e5f8f97034023a5ef0118e19', 'json': '937ee950a0a5ff851e812699823c9a177d94abadf596d720235ee44f8cbc6ca8', 'log': 'd8be04881897d7b28d2b54bc412abec5b1436a322830cd837358e1025f6d0d3a'}, 'initial_result': '8 PASS / 1 SKIP / 21.7476992s before catalog artifact alias hardening; not a final alias safety result', 'actual_scope': 'native Temp GTiffs, empty-catalog setup, new CLI two subprocess source registrations from external cwd with no PYTHONPATH, explicit Python140 preparation,143 subprocess report and131133readonly', 'mock_scope': 'inprocess constructor/validator/return faults and actual-commit-then-error; symlink permission unavailable is SKIP', 'operating_writes': 0, 'operating_collection': 0, 'network_requests': 0, 'training': 0, 'inference': 0, 'api_ui_changed': False, 'frontend_build_browser_required': False, 'limitations': ['Declared raster plus matching SHA is not native GTiff/header/band/pixel/QA validation; opaque bytes can register unapproved.', 'No parent lineage resolution, institution/source authority, ACL or scientific/execution approval is granted.', 'Store constructor and registration can have effects before an exception; UNCONFIRMED does not claim rollback/absence and no automatic retry/delete occurs.', 'Two source CLI calls and later report preparation/registration are explicit sequential caller actions, not one atomic transaction.', 'Only Temp roots are used; operating data/ledgers/reservations/models are not opened or changed.']}, 'integrity': {'recorded_at': '2026-10-18T07:37:50.195302+09:00', 'protected_files_checked': 141, 'protected_changes': [], 'existing_source_checked': 432, 'existing_source_changes': [], 'unexpected_existing_source_changes': [], 'expected_changed_existing_sources': [], 'unchanged_existing_source_files': 432, 'previous_evidence_checked': 1416, 'previous_evidence_changes': [], 'catalog_rows': 14, 'catalog_canonical_sha256': '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b', 'reserved_bytes_preserved': 136314880, 'existing_execution_workflow_model_and_other_sources_unchanged': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0}, 'understanding_updated': True, 'web_ui_api_changed': False, 'backend_full_rerun_this_unit': False, 'frontend_build_browser_rerun_this_unit': False, 'operating_collection_training_registry_approval_deployment_workflow_dispatch': 0, 'metadata_guessed': False, 'source_artifacts_rewritten': False, 'automatic_report_storage': False, 'native_raster_or_lineage_parent_validated': False, 'scientific_accuracy_validated': False, 'execution_authorized': False, 'workflow_supported': False, 'next_internal_candidate': '147_EXPLICIT_VERIFIED_LOCAL_LCLUC_WORKFLOW_REPORT_EVIDENCE_VIEW'}
closeout['recorded_at']=audit['checked_at'];closeout['documentation_validation']=audit
closeout['integrity']=json.loads((ROOT/P/'source-raster-registration-cli-live-integrity-final-20261018.json').read_text('utf-8'))
assert not closeout['integrity']['protected_changes'] and not closeout['integrity']['unexpected_existing_source_changes'] and not closeout['integrity']['previous_evidence_changes']
closeout['source_records']={n:record(n) for n in ['scripts/register_dataset_version.py','tests/test_source_raster_registration_cli.py']}
assert closeout['source_records']['scripts/register_dataset_version.py']['sha256']==closeout['independent']['source_sha256']
assert closeout['source_records']['tests/test_source_raster_registration_cli.py']['sha256']==closeout['independent']['test_sha256']
processes=json.loads((ROOT/P/'source-raster-registration-cli-final-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status']=='ACTIVE' and processes['collector_training_processes_observed']==0
closeout['live_processes']=processes
closeout['operating_inventory']=json.loads((ROOT/P/'source-raster-registration-cli-operating-inventory-20261018.json').read_text('utf-8'))
closeout['previous_full_backend']={'unit':145,'passed':1431,'skipped':1,'seconds':332.720}
closeout['previous_frontend']={'unit':137,'passed':271,'build_modules':112,'build_seconds':13.48}


closeout['catalog_self_reference_reproduction']=json.loads((ROOT/P/'source-raster-registration-cli-self-catalog-reproduction-20261018.json').read_text('utf-8'))
closeout['pre_hardening_tests']={'focused':{'passed':9,'seconds':9.491},'related':{'passed':123,'seconds':36.632},'independent':{'passed':8,'skipped':1,'seconds':21.7476992},'reason':'Catalog self-reference guard was not yet present; all initial raw logs preserved.'}
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
pre=json.loads((ROOT/P/'source-raster-registration-cli-preflight-20261018.json').read_text('utf-8'))
names=set(snapshot['files'])|set(pre['tracked_source_baseline'])|(publish-tracked)|changed
target=ROOT/P/'source-raster-registration-cli-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='f4565f5ff9b743cfd51cea087bbcf7d2e840729f'
snapshot['source_commit_reason']='Published145 baseline plus146 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=False
snapshot['reported_status']['latest_source_raster_registration_cli']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
