"""Freeze135 explicit caller rational minimum-validity policy diagnostic."""
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
implementation = ROOT/'docs/implementation/135_annual_mask_policy.md'
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
integrity = json.loads((ROOT/'evidence/integration/mask-policy-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/mask-policy-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/annual_mask_policy.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_annual_mask_policy.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256']
assert test_sha == independent['test_sha256']
runtime = json.loads((ROOT/'evidence/integration/mask-policy-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 7 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/mask-policy-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
assert not integrity['protected_changes'] and not integrity['existing_source_changes'] and not integrity['previous_evidence_changes']
processes = json.loads((ROOT/'evidence/integration/mask-policy-live-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status'] == 'ACTIVE' and processes['collector_training_processes_observed'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at':now,'status':'135_EXPLICIT_CALLER_RATIONAL_MASK_POLICY_DIAGNOSTICS',
    'focused':{'passed':8,'seconds':5.938,'log':'evidence/integration/annual-mask-policy-agent-20261018-focused.log'},'related':{'passed':26,'seconds':42.071,'composition':'8 new policy +9 annual join +9 binary mask'},
    'independent':{'passed':independent['tests'],'skipped':0,'seconds':independent['seconds']},
    'root_actual_temp_file_scenarios':7,'overlapping_test_bundles_are_not_additive':True,
    'source_sha256':source_sha,'test_sha256':test_sha,'documentation_validation':audit,
    'integrity':integrity,'operating_inventory':inventory,'live_processes':processes,
    'exact20_output_and_nine_unverified_flags_always_false':True,
    'caller_explicit_exact_four_key_policy_required_without_default':True,
    'numerator_zero_to_denominator_integer_denominator_one_to_million':True,
    'bool_float_string_policy_counts_not_coerced':True,
    'full_request_and_policy_snapshotted_before_any_io':True,
    'parent134_full_success_before_all_counts_validation_and_policy_evaluation':True,
    'all_counts_exact_three_builtin_integers_and_sum_pixel_bound_validated_before_any_policy_comparison':True,
    'integer_cross_product_comparison_without_division_or_rounding':True,
    'all_years_evaluated_even_if_one_policy_threshold_not_met':True,
    'policy_not_met_still_has_all_parent134_file_and_mask_io_completed':True,
    'nested_parent134_preserved_and_aggregate_artifact_true_only_if_all_policy_rows_met':True,
    'additional_registry_file_checkpoint_pixel_reads_over134':0,
    'model_checkpoint_load_valid_path':1,'store_get_calls_valid_path_formula':'1+6N',
    'mask_read_calls_valid_path_formula':'N','image_pixel_read_calls':0,
    'quality_report_verified':False,'quality_mask_verified':False,'mask_semantics_verified':False,
    'registry_aoi_verified':False,'source_authority_verified':False,
    'scientific_accuracy_validated':False,'execution_authorized':False,'state_dict_verified':False,'workflow_supported':False,
    'threshold_selection_and_agency_quality_policy_authority_not_verified':True,
    'runtime_api_ui_connected':False,
    'store_database_json_predecode_not_bounded_by_postdecode_tree_limit':True,
    'gdal_parser_cpu_rss_time_and_all_external_io_not_os_isolated':True,
    'ambient_torch_allowlist_unchanged_and_not_cpu_rss_time_isolated':True,
    'sequential_registry_and_file_snapshots_are_not_atomic':True,
    'frontend_build_browser_rerun_this_unit':False,'backend_full_rerun_this_unit':False,
    'reason_no_full_rerun':'Previous sources unchanged. New unconnected rational policy diagnostic covered by focused, related and independent actual Temp files/untrained checkpoint; no external API/UI contract change.',
    'previous_backend_regression':{'unit':'120/121','tests_run':1184,'passed':1183,'skipped':1,'seconds':399.529},
    'previous_frontend_regression':{'unit':'120/121','passed':261,'build_modules':108,'build_seconds':21.85},
    'understanding_updated':True,'operating_collection_training_registry_deployment_workflow_dispatch':0,
    'operating_model_or_raster_load':0,'automation_status':'ACTIVE','automation_interval_minutes':10,
    'collector_training_processes_observed':0,
    'next_internal_candidate':'136_EXPLICIT_PER_SCENE_DIAGNOSTIC_SERVICE_CONTRACT_WITHOUT_EXECUTION_OR_APPROVAL'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/mask-policy-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '9a14fc62f7dd5dda6b1df8b2b0b241a17a12f28d'
snapshot['source_commit_reason'] = 'Published134 baseline plus135 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_explicit_caller_rational_mask_policy_diagnostic'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
