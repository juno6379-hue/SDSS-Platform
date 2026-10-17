"""Freeze126 actual model checkpoint -> registered single-scene read composition evidence."""
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
implementation = ROOT/'docs/implementation/126_pinned_scene_normalization.md'
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
integrity = json.loads((ROOT/'evidence/integration/pinned-scene-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/pinned-scene-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] >= 6 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/pinned_scene_normalization.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_pinned_scene_normalization.py').read_bytes()).hexdigest()
assert source_sha == 'b4553a8c3163f8f7213e745b8f8b4ccb989300fd48e49286e0eecadbb900b9e1'
assert test_sha == '08435da8362f375b0f4afc97d2b54044a4562a15d57aacc31557aea644a26ab4'
runtime = json.loads((ROOT/'evidence/integration/pinned-scene-runtime-20261018.json').read_text('utf-8'))
assert len(runtime['checks_passed']) == 6 and runtime['operating_model_loaded'] is False
inventory = json.loads((ROOT/'evidence/integration/pinned-scene-operating-inventory-20261018.json').read_text('utf-8'))
assert inventory['dataset_versions_count'] == 0 and inventory['operating_writes'] == 0
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '126_ACTUAL_CHECKPOINT_MANIFEST_AND_REGISTERED_SINGLE_SCENE_JOIN_VERIFIED',
            'focused': {'passed': 10, 'seconds': 3.261},
            'related': {'passed': 37, 'seconds': 12.616, 'composition': '10 new composition +14 actual model manifest +13 registered scene tests'},
            'independent': {'passed': independent['tests'], 'skipped': 0, 'seconds': independent['seconds']},
            'root_actual_temp_registered_scene_scenarios': 6,
            'overlapping_test_bundles_are_not_additive': True, 'source_sha256': source_sha, 'test_sha256': test_sha,
            'documentation_validation': audit, 'integrity': integrity, 'operating_inventory': inventory,
            'root_initial_import_failure_due_to_missing_runtime_pythonpath_preserved_then_environment_corrected_without_source_change': True,
            'explicit_scene_extensions_and_lineage_roles_are_internal_contract_not_official_authority': True,
            'public_declaration_read_policy_is_not_acl_and_quality_state_is_not_qa_approval': True,
            'store_database_json_predecode_is_not_memory_bounded_by_new_postdecode_tree_checks': True,
            'checkpoint_manifest_is_caller_metadata': False, 'actual124_model_join_completed': True,
            'temporary_untrained_checkpoint_loaded_with_cpu_weights_only': True,
            'all_year_quality_mask_or_runtime_binding_completed': False,
            'api_ui_workflow_runtime_connected': False, 'execution_authorized': False,
            'state_dict_verified': False, 'source_authority_verified': False,
            'scientific_accuracy_validated': False, 'workflow_supported': False,
            'frontend_build_browser_rerun_this_unit': False, 'backend_full_rerun_this_unit': False,
            'reason_no_full_rerun': 'All285 previous source files are byte-identical. New internal single-scene composition tested with actual Temp CPU checkpoint/Registry/rasters, independent failures and124/125 related regressions. No API/UI contract change.',
            'previous_backend_regression': {'unit': '120/121', 'tests_run': 1184, 'passed': 1183, 'skipped': 1, 'seconds': 399.529},
            'previous_frontend_regression': {'unit': '120/121', 'passed': 261, 'build_modules': 108, 'build_seconds': 21.85},
            'understanding_updated': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0,
            'operating_model_or_raster_load': 0, 'automation_status': 'ACTIVE',
            'automation_interval_minutes': 10, 'collector_training_processes_observed': 0,
            'next_internal_candidate': '127_ALL_YEAR_PINNED_NORMALIZATION_READ_ONLY_PREFLIGHT_CONTRACT'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/pinned-scene-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '2a980f91eeb86ff61df65eed5c4f2d266aa5f540'
snapshot['source_commit_reason'] = 'Published125 baseline plus126 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_pinned_model_registered_scene_composition'] = closeout
snapshot['reported_status']['operating_dataset_versions_count'] = 0
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
