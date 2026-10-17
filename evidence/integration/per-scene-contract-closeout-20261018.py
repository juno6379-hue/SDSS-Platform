"""Freeze122 declaration-only diagnostic evidence, documentation and raw hashes."""
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
implementation = ROOT/'docs/implementation/122_per_scene_normalization_contract.md'
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
integrity = json.loads((ROOT/'evidence/integration/per-scene-contract-live-integrity-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/per-scene-contract-independent-20261018.json').read_text('utf-8'))
assert independent['passed'] and independent['tests'] == 7
source_sha = hashlib.sha256((ROOT/'backend/app/ml/per_scene_normalization_contract.py').read_bytes()).hexdigest()
test_sha = hashlib.sha256((ROOT/'tests/test_per_scene_normalization_contract.py').read_bytes()).hexdigest()
assert source_sha == independent['helper_sha256'] == 'b2f1f79c5b9773d9588d4e9b560f9df12ed94d2c1e5301b638cc9c432090f8ea'
assert test_sha == '14ed1420561d3b73c6317af48beb9cc71fb851f0d13abe7c435543b8ba94310d'
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '122_PURE_PER_SCENE_NORMALIZATION_DECLARATION_DIAGNOSTIC_VERIFIED',
            'focused': {'passed': 14, 'seconds': .031},
            'independent': {'passed': 7, 'unittest_seconds': .014, 'including_source_audit_seconds': independent['seconds']},
            'existing_boundary_regressions': {'passed': 4, 'seconds': 8.994},
            'root_actual_temp_file_boundary_scenarios': 6,
            'overlapping_test_bundles_are_not_additive': True, 'source_sha256': source_sha, 'test_sha256': test_sha,
            'documentation_validation': audit, 'integrity': integrity,
            'api_ui_workflow_runtime_connected': False, 'execution_authorized': False,
            'artifact_bytes_verified_by_new_helper': False, 'source_authority_verified': False,
            'scientific_accuracy_validated': False, 'workflow_supported_by_new_helper': False,
            'frontend_build_browser_rerun_this_unit': False, 'backend_full_rerun_this_unit': False,
            'reason_no_full_rerun': 'All277 previous source files are byte-identical. New pure unconnected helper tested with independent metadata and existing runtime boundaries; no API/UI contract change.',
            'previous_backend_regression': {'unit': '120/121', 'tests_run': 1184, 'passed': 1183, 'skipped': 1, 'seconds': 399.529},
            'previous_frontend_regression': {'unit': '120/121', 'passed': 261, 'build_modules': 108, 'build_seconds': 21.85},
            'understanding_updated': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0,
            'automation_status': 'ACTIVE', 'automation_interval_minutes': 10, 'collector_training_processes_observed': 0,
            'next_internal_candidate': '123_READ_ONLY_PINNED_PER_SCENE_FILE_PROVENANCE_BOUNDARY_DESIGN'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/per-scene-contract-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '9a79c3db77e3a94936ab74597939b5bf5630e2c3'
snapshot['source_commit_reason'] = 'Published120/121 baseline plus122 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = False
snapshot['reported_status']['latest_per_scene_normalization_declaration_diagnostic'] = closeout
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
