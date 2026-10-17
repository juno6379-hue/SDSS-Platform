"""Freeze133 explicit binary-mask literal value counts."""
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
implementation = ROOT/'docs/implementation/133_registered_binary_mask_values.md'
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
integrity = json.loads((ROOT/'evidence/integration/binary-mask-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/binary-mask-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/registered_binary_mask_values.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_registered_binary_mask_values.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256']
assert test_sha == independent['test_sha256']
runtime = json.loads((ROOT/'evidence/integration/binary-mask-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 7 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/binary-mask-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
assert not integrity['protected_changes'] and not integrity['existing_source_changes'] and not integrity['previous_evidence_changes']
processes = json.loads((ROOT/'evidence/integration/binary-mask-live-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status'] == 'ACTIVE' and processes['collector_training_processes_observed'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at':now,'status':'133_EXPLICIT_BINARY_MASK_LITERAL_VALUE_COUNTS_UNVERIFIED',
    'focused':{'passed':9,'seconds':7.291},'related':{'passed':40,'seconds':16.334,'composition':'9 new values +10 mask grid +10 quality files +11 DatasetVersion'},
    'independent':{'passed':independent['tests'],'skipped':0,'seconds':independent['seconds']},
    'root_actual_temp_file_scenarios':7,'overlapping_test_bundles_are_not_additive':True,
    'source_sha256':source_sha,'test_sha256':test_sha,'documentation_validation':audit,
    'integrity':integrity,'operating_inventory':inventory,'live_processes':processes,
    'exact19_output_and_ten_unverified_flags_always_false':True,
    'parent132_observation_preserved_and_semantics_false_scope_unchanged':True,
    'store_get_calls_valid_path':3,'image_file_snapshots_valid_path':2,'mask_file_snapshots_valid_path':3,
    'requires_full_parent132_success_before_values':True,'third_fixed_sha_snapshot_precedes_mask_values':True,
    'explicit_source_mask_semantics_exact4_internal_contract_not_official_standard':True,
    'mask_single_band_uint8_nodata_none_all_valid_flags_required':True,
    'one_literal_mask_band_read_after_header_recheck':True,
    'counts_only_when_all_steps_succeed':True,'all_zero_not_automatically_rejected_by_quality_policy':True,
    'image_pixel_or_read_masks_calls_by_reader':0,'model_or_torch_load_by_reader':0,
    'quality_report_verified':False,'quality_mask_verified':False,'mask_semantics_verified':False,
    'registry_aoi_verified':False,'source_authority_verified':False,'minimum_validity_policy_verified':False,
    'scientific_accuracy_validated':False,'execution_authorized':False,'state_dict_verified':False,'workflow_supported':False,
    'mask_byte_limit':16*1024**2,'mask_pixel_limit':1024**2,
    'parent130_batch_runtime_api_ui_connected':False,
    'store_database_json_predecode_not_bounded_by_postdecode_tree_limit':True,
    'gdal_parser_cpu_rss_time_and_all_external_io_not_os_isolated':True,
    'sequential_registry_and_file_snapshots_are_not_atomic':True,
    'frontend_build_browser_rerun_this_unit':False,'backend_full_rerun_this_unit':False,
    'reason_no_full_rerun':'Previous sources unchanged. New unconnected binary-mask diagnostic covered by focused, related and independent real Temp files; no external API/UI contract change.',
    'previous_backend_regression':{'unit':'120/121','tests_run':1184,'passed':1183,'skipped':1,'seconds':399.529},
    'previous_frontend_regression':{'unit':'120/121','passed':261,'build_modules':108,'build_seconds':21.85},
    'understanding_updated':True,'operating_collection_training_registry_deployment_workflow_dispatch':0,
    'operating_model_or_raster_load':0,'automation_status':'ACTIVE','automation_interval_minutes':10,
    'collector_training_processes_observed':0,
    'next_internal_candidate':'134_JOIN_ANNUAL_SPATIAL_AND_EXPLICIT_MASK_DIAGNOSTICS_WITHOUT_EXECUTION_APPROVAL'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/binary-mask-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '45d4000077ff4746cb6d6e84e68e752be80bfbdc'
snapshot['source_commit_reason'] = 'Published132 baseline plus133 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_explicit_binary_mask_literal_value_counts'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
