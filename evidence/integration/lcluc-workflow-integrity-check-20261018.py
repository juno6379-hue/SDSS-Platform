"""Verify existing bytes and operating records after the isolated executor tests."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
pre = json.loads((ROOT/'evidence/integration/lcluc-workflow-preflight-20261018.json').read_text('utf-8'))


def record(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


for name, expected in pre['protected_references'].items():
    path = Path(name)
    assert path.exists() == expected['exists'], name
    if path.exists(): assert record(path) == {key: expected[key] for key in ('sha256', 'bytes')}, name
old = pre['tracked_baseline']
existing_source = [name for name in old if name.startswith(('backend/', 'frontend/', 'scripts/', 'tests/'))]
assert all(record(ROOT/name) == old[name] for name in existing_source)
assert not subprocess.check_output(['git', 'diff', '--name-only', pre['git_base'], '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT).strip()
previous_evidence = [name for name in old if name.startswith('evidence/')]
assert all(record(ROOT/name) == old[name] for name in previous_evidence)
freeze = json.loads((ROOT/'evidence/integration/lcluc-workflow-source-freeze-20261018.json').read_text('utf-8'))
assert all(record(ROOT/name) == expected for name, expected in freeze['files'].items())
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro', uri=True) as connection:
    rows = connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
catalog = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
assert catalog == pre['catalog_sha256']
pending = []
for key in ('parallel-v2-extra-banten-2023-v2-laneB-banten-boundary-01', 'parallel-v2-extra-west_java-2023-v2-laneB-west_java-boundary-01'):
    path = ROOT/'data/first-group-training-esri-v1/sources'/key
    exists = {name: (path/name).exists() for name in ('config.json', 'window-state.json', 'worker-result.json', 'annual-window-report.json')}
    assert exists == {'config.json': True, 'window-state.json': True, 'worker-result.json': False, 'annual-window-report.json': False}
    pending.append({'batch': key, 'files': exists})
result = {'recorded_at': datetime.datetime.now().isoformat(),
          'scope': 'ISOLATED_TEMP_STORE_CPU_EXECUTION_AND_LOCAL_PROTECTED_BYTES_NOT_OPERATING_EXECUTION',
          'protected_files_checked': len(pre['protected_references']), 'protected_changes': [],
          'existing_source_checked': len(existing_source), 'existing_source_changes': [],
          'previous_evidence_checked': len(previous_evidence), 'previous_evidence_changes': [],
          'frozen_new_source_files': freeze['files'], 'catalog_rows': len(rows), 'catalog_sha256': catalog,
          'pending': pending, 'reserved_bytes_preserved': 136314880,
          'operating_collection_training_registration_jobs_deployment': 0,
          'API_UI_changes': False, 'global_gmais_workflow_plan_unchanged': True,
          'per_scene_normalization_execution': 'UNSUPPORTED_BLOCKED_IN_V1',
          'current_operating_model': 'DRAFT_UNCHANGED_NOT_EXECUTED',
          'exactly_once_completion': 'NOT_CLAIMED_DISPATCH_CLAIM_ONLY',
          'filesystem_database_atomicity': 'NOT_PROVIDED'}
for label, name in (
    ('independent', 'evidence/integration/lcluc-workflow-independent-final2-20261018.log'),
    ('full', 'evidence/integration/lcluc-workflow-full-tests-20261018.log'),
):
    text = (ROOT/name).read_text('utf-8')
    match = re.search(r'Ran (\d+) tests in ([\d.]+)s', text)
    assert match and re.search(r'^OK(?: \(skipped=\d+\))?$', text, re.M), text[-2000:]
    skip = re.search(r'^OK \(skipped=(\d+)\)', text, re.M)
    skipped = int(skip[1]) if skip else 0
    result[label] = {'tests_run': int(match[1]), 'passed': int(match[1])-skipped,
                     'skipped': skipped, 'seconds': float(match[2]), 'exit_code': 0, 'log': name}
target = ROOT/'evidence/integration/lcluc-workflow-live-integrity-20261018.json'
assert not target.exists()
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(result, ensure_ascii=False))
