"""Freeze132 actual image and mask header/grid diagnostic."""
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
implementation = ROOT/'docs/implementation/132_registered_quality_mask_grid.md'
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
integrity = json.loads((ROOT/'evidence/integration/mask-grid-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/mask-grid-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/registered_quality_mask_grid.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_registered_quality_mask_grid.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256'] == 'd4827f901496607e9bd33e9d4bb9446f19de176592b3a903405fe243e4ee6ec3'
assert test_sha == '3f8031206d0e24a26f5d4408bfe0a0c299ed8ed697ce65750957d53cb0d43641'
runtime = json.loads((ROOT/'evidence/integration/mask-grid-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 7 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/mask-grid-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
assert not integrity['protected_changes'] and not integrity['existing_source_changes'] and not integrity['previous_evidence_changes']
processes = json.loads((ROOT/'evidence/integration/mask-grid-live-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status'] == 'ACTIVE' and processes['collector_training_processes_observed'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '132_REGISTERED_IMAGE_MASK_HEADERS_AND_GRID_MATCHED_UNVERIFIED',
    'focused': {'passed':10,'seconds':6.446},
    'related': {'passed':42,'seconds':29.023,'composition':'10 new grid +10 quality reader +11 raster grid +11 DatasetVersion'},
    'initial_related_wrong_module_name':{'tests_run':32,'passed':31,'import_errors':1,'seconds':26.398,'raw_log_preserved':True,'product_source_change':False},
    'independent':{'passed':independent['tests'],'skipped':0,'seconds':independent['seconds']},
    'root_actual_temp_file_scenarios':7,'overlapping_test_bundles_are_not_additive':True,
    'source_sha256':source_sha,'test_sha256':test_sha,'documentation_validation':audit,
    'integrity':integrity,'operating_inventory':inventory,'live_processes':processes,
    'exact20_output_and_ten_unverified_flags_always_false':True,
    'parent131_observation_preserved_and_header_flag_scope_unchanged':True,
    'store_get_calls_valid_path':3,'image_file_snapshots_valid_path':2,'mask_file_snapshots_valid_path':2,
    'header_requires_full_parent131_success':True,'second_fixed_sha_snapshot_precedes_each_header':True,
    'image_explicit_six_bands_and_actual_descriptions_required':True,'mask_single_band_uint8_required':True,
    'width_height_wkt_affine_bounds_exact_match_required':True,
    'pixel_or_read_masks_calls_by_reader':0,'model_or_torch_load_by_reader':0,
    'quality_report_verified':False,'quality_mask_verified':False,'pixel_values_verified':False,
    'mask_semantics_verified':False,'registry_aoi_verified':False,'source_authority_verified':False,
    'scientific_accuracy_validated':False,'execution_authorized':False,'state_dict_verified':False,'workflow_supported':False,
    'image_byte_limit':64*1024**2,'report_byte_limit':2*1024**2,'mask_byte_limit':16*1024**2,
    'mask_value255_not_interpreted_or_approved':True,'image_dtype_nodata_numeric_model_compatibility_unverified':True,
    'parent130_batch_runtime_api_ui_connected':False,
    'store_database_json_predecode_not_bounded_by_postdecode_tree_limit':True,
    'gdal_parser_cpu_rss_time_and_all_external_io_not_os_isolated':True,
    'sequential_registry_and_file_snapshots_are_not_atomic':True,
    'frontend_build_browser_rerun_this_unit':False,'backend_full_rerun_this_unit':False,
    'reason_no_full_rerun':'All297 previous source files unchanged. New unconnected header/grid diagnostic covered by focused, related and independent real Temp files; no external API/UI contract change.',
    'previous_backend_regression':{'unit':'120/121','tests_run':1184,'passed':1183,'skipped':1,'seconds':399.529},
    'previous_frontend_regression':{'unit':'120/121','passed':261,'build_modules':108,'build_seconds':21.85},
    'publish_pattern_false_positive_corrected':{'cause':'Unbounded sk- regex matched substring of mask-grid evidence filenames','correction':'Require token-start boundary; no allowlisting or findings bypass','local_publish_guard_only':True},
    'understanding_updated':True,'operating_collection_training_registry_deployment_workflow_dispatch':0,
    'operating_model_or_raster_load':0,'automation_status':'ACTIVE','automation_interval_minutes':10,
    'collector_training_processes_observed':0,
    'next_internal_candidate':'133_EXPLICIT_MASK_VALUE_SEMANTICS_AND_BOUNDED_DIAGNOSTIC_NOT_QA_APPROVAL'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/mask-grid-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = 'e994e834b7630f979d037bb52bf366f19a502a87'
snapshot['source_commit_reason'] = 'Published131 baseline plus132 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_registered_quality_mask_header_grid_read'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
