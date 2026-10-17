"""Freeze131 registered quality report and explicit opaque-mask binding reader."""
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
implementation = ROOT/'docs/implementation/131_registered_quality_mask_files.md'
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
integrity = json.loads((ROOT/'evidence/integration/quality-mask-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/quality-mask-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/registered_quality_mask_files.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_registered_quality_mask_files.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256']
assert test_sha == '6a10deb09606af535512bd61aa5806f0cc3421fbd0b8a577342cc4877cd80b49'
runtime = json.loads((ROOT/'evidence/integration/quality-mask-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 7 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/quality-mask-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '131_REGISTERED_QUALITY_REPORT_AND_EXPLICIT_OPAQUE_MASK_BYTES_BOUND',
    'focused': {'passed': 10, 'seconds': 5.212},
    'initial_focused_before_review_field_correction': {'passed':10,'seconds':4.242,'raw_log_preserved':True},
    'related': {'passed':48,'seconds':11.419,'composition':'10 new quality reader +11 DatasetVersion +13 registered scene +14 normalization files'},
    'independent': {'passed':independent['tests'],'skipped':0,'seconds':independent['seconds']},
    'root_actual_temp_file_scenarios':7,'overlapping_test_bundles_are_not_additive':True,
    'source_sha256':source_sha,'test_sha256':test_sha,'documentation_validation':audit,
    'integrity':integrity,'operating_inventory':inventory,
    'new_internal_exact_five_key_quality_evidence_envelope_not_upstream_or_official_standard':True,
    'review_parser_error_role_issue_fixed_and_independently_verified':True,
    'old123_and124_parser_sources_unchanged':True,
    'separate_registry_keys_can_alias_same_physical_image_or_mask_bytes':True,
    'file_not_checked_means_no_recorded_sha_match_not_zero_io':True,
    'report_binding_or_registry_partial_flags_are_not_all_file_success_or_qa_approval':True,
    'quality_report_verified':False,'quality_mask_verified':False,'raster_header_verified':False,
    'state_dict_verified':False,'source_authority_verified':False,'access_authorization_verified':False,
    'scientific_accuracy_validated':False,'execution_authorized':False,'workflow_supported':False,
    'image_byte_limit':64*1024**2,'report_byte_limit':2*1024**2,'mask_byte_limit':16*1024**2,
    'mask_semantics_header_grid_pixels_or_metric_policy_verified':False,
    'model_or_raster_parsing_performed_by_new_reader':False,'parent130_batch_runtime_api_ui_connected':False,
    'store_database_json_predecode_not_bounded_by_postdecode_tree_limit':True,
    'sequential_registry_and_file_snapshots_are_not_atomic':True,
    'frontend_build_browser_rerun_this_unit':False,'backend_full_rerun_this_unit':False,
    'reason_no_full_rerun':'All295 previous source files are byte-identical. New unconnected per-scene Registry and bounded byte reader tested with actual Temp rasters/opaque mask and independent fixed references/JSON/limits plus DatasetVersion/125/123 related regressions. No external API/UI contract change.',
    'previous_backend_regression':{'unit':'120/121','tests_run':1184,'passed':1183,'skipped':1,'seconds':399.529},
    'previous_frontend_regression':{'unit':'120/121','passed':261,'build_modules':108,'build_seconds':21.85},
    'understanding_updated':True,'operating_collection_training_registry_deployment_workflow_dispatch':0,
    'operating_model_or_raster_load':0,'automation_status':'ACTIVE','automation_interval_minutes':10,
    'collector_training_processes_observed':0,
    'next_internal_candidate':'132_ACTUAL_MASK_HEADER_AND_IMAGE_GRID_ALIGNMENT_READ_ONLY'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/quality-mask-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = 'e4ed88724aa96b3b08ffb574511e06bd4dc91a80'
snapshot['source_commit_reason'] = 'Published130 baseline plus131 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_registered_quality_mask_fixed_reference_read'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
