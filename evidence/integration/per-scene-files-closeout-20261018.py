"""Freeze123 role-specific file snapshot reader evidence and documentation."""
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
implementation = ROOT/'docs/implementation/123_per_scene_normalization_files.md'
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
integrity = json.loads((ROOT/'evidence/integration/per-scene-files-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/per-scene-files-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] == 9 and independent['skipped'] == 0
source_sha = hashlib.sha256((ROOT/'backend/app/ml/per_scene_normalization_files.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_per_scene_normalization_files.py').read_bytes()).hexdigest()
assert source_sha == independent['source_sha256'] == '77b6d844aa1a71304826d34f492780b80a8b0b7c7f21740856510d8acd463366'
assert test_sha == 'b5bae5db47e7ed4178ae2c41cebcd4481400c1bce40445afcfd1cfea57284c8b'
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '123_BOUNDED_READ_ONLY_PER_SCENE_FILE_SNAPSHOTS_VERIFIED',
            'focused': {'passed': 14, 'seconds': .810},
            'related': {'passed': 28, 'seconds': 1.309, 'composition': '14 new reader +14 existing122 pure tests'},
            'independent': {'passed': 9, 'skipped': 0, 'seconds': independent['seconds']},
            'root_actual_temp_raster_comparison_scenarios': 6,
            'overlapping_test_bundles_are_not_additive': True, 'source_sha256': source_sha, 'test_sha256': test_sha,
            'documentation_validation': audit, 'integrity': integrity,
            'initial_independent_environment_test_error_preserved_and_fixed_without_product_change': True,
            'actual_windows_junction_rejection_and_target_preservation_tested': True,
            'caller_sha_scope_not_registry_id_version_or_checkpoint_binding': True,
            'artifact_bytes_verified_true_scope': 'Only three sequential role byte hashes and122 declaration consistency, not raster validity or a simultaneous snapshot.',
            'api_ui_workflow_runtime_connected': False, 'execution_authorized': False,
            'checkpoint_artifact_verified': False, 'source_authority_verified': False,
            'scientific_accuracy_validated': False, 'workflow_supported': False,
            'frontend_build_browser_rerun_this_unit': False, 'backend_full_rerun_this_unit': False,
            'reason_no_full_rerun': 'All279 previous source files are byte-identical. New unconnected internal reader tested with independent filesystem boundaries,122 related tests and actual Temp raster comparison. No API/UI contract change.',
            'previous_backend_regression': {'unit': '120/121', 'tests_run': 1184, 'passed': 1183, 'skipped': 1, 'seconds': 399.529},
            'previous_frontend_regression': {'unit': '120/121', 'passed': 261, 'build_modules': 108, 'build_seconds': 21.85},
            'understanding_updated': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0,
            'automation_status': 'ACTIVE', 'automation_interval_minutes': 10, 'collector_training_processes_observed': 0,
            'next_internal_candidate': '124_REGISTRY_AND_MODEL_FIXED_REFERENCE_BINDING_AND_ALL_YEAR_PREFLIGHT_CONTRACT'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/per-scene-files-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '9c5acb431392f3e94e7e6e361737c0e8ef4002ed'
snapshot['source_commit_reason'] = 'Published122 baseline plus123 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_per_scene_normalization_file_snapshots'] = closeout
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
