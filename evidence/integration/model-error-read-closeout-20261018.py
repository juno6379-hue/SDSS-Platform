"""Freeze verified 120/121 documentation and raw evidence without changing original data."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
now = datetime.now().astimezone().isoformat()
implementations = [ROOT/'docs/implementation/120_model_error_analysis_read.md', ROOT/'docs/implementation/121_model_error_analysis_ui.md']
documents = list((ROOT/'docs/understanding').rglob('*.md'))
errors, links, references = [], 0, 0
for path in documents+implementations:
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
integrity = json.loads((ROOT/'evidence/integration/model-error-read-live-integrity-20261018.json').read_text('utf-8'))
browser = json.loads((ROOT/'evidence/integration/model-error-read-browser-20261018.json').read_text('utf-8'))
assert not browser['final_fixture_console_errors'] and not browser['legacy_console_errors']
assert browser['legacy_read_disabled'] and browser['model_selection_cleared_result'] and browser['navigation_back_cleared_result']
assert json.loads((ROOT/'evidence/integration/model-error-read-fixture-cleanup-20261018.json').read_text('utf-8'))
raw = (ROOT/'evidence/integration/model-error-read-backend-all-20261018.log').read_text('utf-8')
match = re.search(r'Ran (\d+) tests in ([\d.]+)s', raw)
assert match and 'OK (skipped=1)' in raw
backend = {'tests_run': int(match[1]), 'passed': int(match[1])-1, 'skipped': 1, 'seconds': float(match[2]), 'exit_code': 0}
assert backend['tests_run'] == 1184
audit = {'checked_at': now, 'understanding_markdown': len(documents), 'implementation_markdown': 2,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': '120_121_PINNED_MODEL_ERROR_ANALYSIS_API_AND_UI_VERIFIED',
            'api_focused': {'passed': 14, 'seconds': 2.695}, 'api_related': {'passed': 48, 'seconds': 7.665},
            'route_guards': {'passed': 24, 'seconds': 4.333}, 'root_independent_live_http_scenarios': 6,
            'backend_full': backend, 'frontend_focused': {'passed': 11, 'seconds': 4.141},
            'frontend_full': {'passed': 261, 'seconds': 26.266159}, 'build': {'modules': 108, 'seconds': 21.85, 'exit_code': 0},
            'overlapping_test_bundles_are_not_additive': True,
            'documentation_validation': audit, 'integrity': integrity,
            'browser_proof': 'evidence/integration/model-error-read-browser-20261018.json',
            'browser_scope': 'TESTED_SYNTHETIC_CONSTRUCTED_REPORT_NO_TRAINING_NO_EXECUTABLE_CHECKPOINT',
            'operating_5174_legacy_missing_pins_read_disabled_verified': True,
            'original_user_tab_preserved': True, 'owned_fixture_tabs_and_servers_closed': True,
            'browser_bearer_delay_cancel_corruption_mobile_not_exercised': True,
            'understanding_updated': True, 'scientific_accuracy_validated': False, 'standard_gmais_result': False,
            'operating_collection_training_registry_deployment_workflow_dispatch': 0,
            'automation_status': 'ACTIVE', 'automation_interval_minutes': 10,
            'collector_training_processes_observed': 0,
            'next_internal_candidate': '122_LCLUC_SIX_BAND_PER_SCENE_WORKFLOW_CONTRACT_REVIEW_NO_GATE_RELAXATION'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python', '.git/codex_prepare_publish.py'], cwd=ROOT, check=True)
publish = {n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode('utf-8').split('\0') if n}
tracked = {n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
changed = {n for n in subprocess.check_output(['git', 'diff', '--name-only', '-z'], cwd=ROOT).decode('utf-8').split('\0') if n}
names = set(snapshot['files']) | (publish-tracked) | changed
target = ROOT/'evidence/integration/model-error-read-closeout-20261018.json'
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = '1be3014cfef3d50a940dacf0583155456a670350'
snapshot['source_commit_reason'] = 'Published119 baseline plus120/121 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['current_regression'] = backend
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = True
snapshot['reported_status']['latest_pinned_model_error_analysis_read'] = closeout
snapshot['documentation_validation'] = audit
snapshot['files'] = {n: record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert all(record(n) == expected for n, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=True))
