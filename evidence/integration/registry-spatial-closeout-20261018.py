"""Freeze130 sampled WGS84 raster envelope containment in same-record Registry bbox."""
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
implementation = ROOT/'docs/implementation/130_registry_spatial_normalization.md'
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
integrity = json.loads((ROOT/'evidence/integration/registry-spatial-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/registry-spatial-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/registry_spatial_normalization.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_registry_spatial_normalization.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256']
assert test_sha == '9e2b162a6a1e7ec2b9ca08deb1949b5b495cd1f750bf25f5fb4172d95e9cdeb7'
runtime = json.loads((ROOT/'evidence/integration/registry-spatial-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 7 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/registry-spatial-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '130_SAMPLED_RASTER_ENVELOPE_AND_REGISTRY_BBOX_CONTAINMENT_VERIFIED',
            'focused': {'passed': 10, 'seconds': 17.669},
            'related': {'passed': 41, 'seconds': 61.722, 'composition': '10 new spatial +11 prior129 raster grid +11 prior128 temporal +9 prior127 annual batch'},
            'independent': {'passed': independent['tests'], 'skipped': 0, 'seconds': independent['seconds']},
            'root_actual_temp_registered_scene_scenarios': 7,
            'overlapping_test_bundles_are_not_additive': True, 'source_sha256': source_sha, 'test_sha256': test_sha,
            'documentation_validation': audit, 'integrity': integrity, 'operating_inventory': inventory,
            'spatial_not_checked_does_not_mean_files_were_unread': True,
            'finite_edge_densification_is_approximation_not_guaranteed_exact_footprint_bound': True,
            'registry_bbox_containment_is_not_whole_province_coverage_or_aoi_authority': True,
            'gtiff_driver_only_header_reads_from_same_sha_checked_copied_bytes': True,
            'pixel_values_quality_mask_and_registry_aoi_verified': False,
            'one_checkpoint_load_per_valid_batch': True,
            'registered_utc_temporal_year_declarations_bound_to_actual_same_image_record': True,
            'physical_acquisition_year_or_authority_verified': False,
            'no_extra_temporal_registry_get_calls': True,
            'distinct_image_registry_keys_do_not_prove_distinct_physical_scenes_or_temporal_independence': True,
            'explicit_scene_extensions_and_lineage_roles_are_internal_contract_not_official_authority': True,
            'public_declaration_read_policy_is_not_acl_and_quality_state_is_not_qa_approval': True,
            'store_database_json_predecode_is_not_memory_bounded_by_new_postdecode_tree_checks': True,
            'checkpoint_manifest_is_caller_metadata': False, 'actual124_model_join_completed': True,
            'requested_year_batch_read_completed': True, 'registry_temporal_year_binding_completed': True,
            'physical_acquisition_year_verified': False, 'parent127_temporal_year_verified_remains_false': True,
            'temporary_untrained_checkpoint_loaded_with_cpu_weights_only': True,
            'all_year_quality_mask_or_runtime_binding_completed': False,
            'api_ui_workflow_runtime_connected': False, 'execution_authorized': False,
            'state_dict_verified': False, 'source_authority_verified': False,
            'scientific_accuracy_validated': False, 'workflow_supported': False,
            'frontend_build_browser_rerun_this_unit': False, 'backend_full_rerun_this_unit': False,
            'reason_no_full_rerun': 'All293 previous source files are byte-identical. New internal same-record Registry bbox and sampled-envelope postdiagnostic tested with actual Temp CPU checkpoint/Registry/rasters, independent failures and124/125 related regressions. No API/UI contract change.',
            'previous_backend_regression': {'unit': '120/121', 'tests_run': 1184, 'passed': 1183, 'skipped': 1, 'seconds': 399.529},
            'previous_frontend_regression': {'unit': '120/121', 'passed': 261, 'build_modules': 108, 'build_seconds': 21.85},
            'separately_updated_status_documents_reviewed': [{'path': 'docs/16_충분학습자료_단계별수집계획.md', 'baseline_sha256': 'ed4c28907f7297ed4312cb53a8aefe3e926a120ac77bdebcf29b9cb3596d45b1', 'reviewed_working_sha256': 'b993c3eaada306a5d73a14199345af3e3a3852d5748e896085d49465fd5d7323', 'changes': '03:54 KST observation timestamps and stagnation durations only; protected manifest/ledger hashes, counters and reservations unchanged', 'authored_by_unit130_implementation_team': False}, {'path': 'docs/20_대량수집_학습_통합실행.md', 'baseline_sha256': '3b9680fb8b5e5725cbd322b656e9fc7b5a093753230061c1635a434063f87882', 'reviewed_working_sha256': 'bdd32f6f4946a5d0c730a2de80fe0065963ab4206b044e20c146ae164f6d3788', 'changes': '03:54 KST observation timestamps and stagnation durations only; protected manifest/ledger hashes, counters and reservations unchanged', 'authored_by_unit130_implementation_team': False}],
            'understanding_updated': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0,
            'operating_model_or_raster_load': 0, 'automation_status': 'ACTIVE',
            'automation_interval_minutes': 10, 'collector_training_processes_observed': 0,
            'next_internal_candidate': '131_REGISTERED_QUALITY_REPORT_AND_EXPLICIT_MASK_READ_CONTRACT'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/registry-spatial-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '759eac034a0921f898aaf9b5e175421a222ec63f'
snapshot['source_commit_reason'] = 'Published129 baseline plus130 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_registry_bbox_sampled_envelope_postdiagnostic'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
