"""Freeze136 bounded JSON annual diagnostic service request and safe-summary contracts."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
now = datetime.now().astimezone().isoformat()
documents = list((ROOT/'docs/understanding').rglob('*.md'))
implementation = ROOT/'docs/implementation/136_annual_diagnostics_service.md'
errors, links, references = [], 0, 0
for path in documents+[implementation]:
    text = path.read_text('utf-8')
    if 'understanding' in path.parts and path.name != 'GATE_TEMPLATE.md':
        for field in ('updated_at', 'source_commit', 'evidence_paths', 'confidence', 'status'):
            if not re.search(r'^\|\s*'+field+r'\s*\|', text, re.M):
                errors.append(f'{path.name}: missing {field}')
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|', line):
                for name in re.findall(r'`([^`]+)`', line):
                    references += 1
                    if not (ROOT/name).exists():
                        errors.append('missing evidence '+name)
    for value in re.findall(r'\]\(([^)]+)\)', text):
        name = unquote(value.strip('<>').split('#', 1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:', name):
            continue
        links += 1
        if not (path.parent/name).exists():
            errors.append(f'{path.name}: missing link '+name)
faq = len(re.findall(r'^## \d+\.', (ROOT/'docs/understanding/presentations/FAQ.md').read_text('utf-8'), re.M))
assert faq == 10 and not errors, errors
assert (ROOT/'docs/understanding/GATE_TEMPLATE.md').read_bytes() == (ROOT/'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md').read_bytes()
integrity = json.loads((ROOT/'evidence/integration/diagnostic-service-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/diagnostic-service-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/annual_diagnostics_service.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_annual_diagnostics_service.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256']
assert test_sha == independent['test_sha256']
runtime = json.loads((ROOT/'evidence/integration/diagnostic-service-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 7 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/diagnostic-service-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
assert not integrity['protected_changes'] and not integrity['existing_source_changes'] and not integrity['previous_evidence_changes']
processes = json.loads((ROOT/'evidence/integration/diagnostic-service-live-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status'] == 'ACTIVE' and processes['collector_training_processes_observed'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at':now,'status':'136_BOUNDED_JSON_ANNUAL_DIAGNOSTIC_SERVICE_SAFE_SUMMARY',
    'focused':{'passed': 11, 'seconds': 64.474, 'log': 'evidence/integration/diagnostic-service-agent-20261018-focused-final2.log'},'related':{'passed': 28, 'seconds': 119.021, 'log': 'evidence/integration/diagnostic-service-root-related-final-20261018.log'},
    'independent':{'passed':independent['tests'],'skipped':0,'seconds':independent['seconds']},
    'root_actual_temp_file_scenarios':7,'overlapping_test_bundles_are_not_additive':True,
    'source_sha256':source_sha,'test_sha256':test_sha,'documentation_validation':audit,
    'integrity':integrity,'operating_inventory':inventory,'live_processes':processes,
    'separately_updated_status_documents_reviewed':json.loads((ROOT/'evidence/integration/diagnostic-service-separate-status-docs-20261018.json').read_text('utf-8')),
    'initial_root_attempts_interrupted_before_final_refreeze':{'runtime_log':'evidence/integration/diagnostic-service-runtime-20261018.log','related_log':'evidence/integration/diagnostic-service-root-related-20261018.log','completed_result':False,'interrupted_exit_code':1,'raw_logs_preserved':True},
    'review_hardening':{'exact_builtin_scope_and_row_status_before_projection':True,'independent_core_argument_copies_preserve_fingerprint_and_verification_baseline':True,'escaping_regression_added':True,'old135_and_below_sources_unchanged':True},
    'schema_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('contracts/internal/lcluc-annual-diagnostics-request.schema.json','contracts/internal/lcluc-annual-diagnostics-response.schema.json')},
    'strict_bytes_16kib_utf8_duplicate_float_nonfinite_bigint_surrogate_depth_node_string_limits':True,
    'request_exact_six_keys_capability_and_all_refs_policy_prevalidated_before_io':True,
    'canonical_valid_request_sha256_is_order_and_whitespace_independent_not_authentication':True,
    'parent135_exact_bounded_output_and_full_rows_counts_cross_product_false_flags_revalidated':True,
    'response_exact19_safe_summary_without_nested_registry_paths_or_raw_exception':True,
    'request_and_response_json_schema_draft202012_added':True,
    'runtime_rejects_lexical_float_integer_that_json_schema_can_accept':True,
    'additional_registry_file_checkpoint_pixel_reads_over135':0,
    'model_checkpoint_load_valid_path':1,'store_get_calls_valid_path_formula':'1+6N',
    'mask_read_calls_valid_path_formula':'N','image_pixel_read_calls':0,
    'quality_report_verified':False,'quality_mask_verified':False,'mask_semantics_verified':False,
    'registry_aoi_verified':False,'source_authority_verified':False,
    'scientific_accuracy_validated':False,'execution_authorized':False,'state_dict_verified':False,'workflow_supported':False,
    'threshold_selection_and_agency_quality_policy_authority_not_verified':True,
    'http_router_main_endpoint_ui_or_workflow_connected':False,
    'store_database_json_predecode_not_bounded_by_postdecode_tree_limit':True,
    'gdal_parser_cpu_rss_time_and_all_external_io_not_os_isolated':True,
    'ambient_torch_allowlist_unchanged_and_not_cpu_rss_time_isolated':True,
    'sequential_registry_and_file_snapshots_are_not_atomic':True,
    'frontend_build_browser_rerun_this_unit':False,'backend_full_rerun_this_unit':False,
    'reason_no_full_rerun':'Previous sources unchanged. New nonrouted bounded JSON service and schemas covered by focused, related and independent actual Temp files plus parser/unsafe-parent cases. No external endpoint/UI contract change.',
    'previous_backend_regression':{'unit':'120/121','tests_run':1184,'passed':1183,'skipped':1,'seconds':399.529},
    'previous_frontend_regression':{'unit':'120/121','passed':261,'build_modules':108,'build_seconds':21.85},
    'understanding_updated':True,'operating_collection_training_registry_deployment_workflow_dispatch':0,
    'operating_model_or_raster_load':0,'automation_status':'ACTIVE','automation_interval_minutes':10,
    'collector_training_processes_observed':0,
    'next_internal_candidate':'137_AUTHENTICATED_DIAGNOSTIC_ENDPOINT_AND_UI_INTEGRATION_WITHOUT_EXECUTION_OR_APPROVAL'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/diagnostic-service-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '4c14031cbc46384423dd4761d1bec01ea8e2222e'
snapshot['source_commit_reason'] = 'Published135 baseline plus136 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_bounded_json_annual_diagnostic_service'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
