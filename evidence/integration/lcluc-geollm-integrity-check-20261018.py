"""Read-only live preservation against the published 110 baseline."""
from pathlib import Path
import datetime
import hashlib
import json
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'be029c15b7966e8f64331349c54bb8508dabe3e8'
old = json.loads((ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json').read_text('utf-8'))
previous = json.loads((ROOT/'evidence/integration/recovery-commit-contract-preflight-20261017.json').read_text('utf-8'))
allowed = {'scripts/register_collection.py', 'backend/app/ml/service.py'}


def digest(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


for name, expected in previous['protected_references'].items():
    path = Path(name)
    assert path.exists() == expected['exists'], name
    if path.exists():
        assert digest(path) == {k: expected[k] for k in ('sha256', 'bytes')}, name
changes = []
for name, expected in old['files'].items():
    if name.startswith(('backend/', 'frontend/', 'scripts/', 'tests/')) and digest(ROOT/name) != expected:
        changes.append(name)
assert set(changes) <= allowed, changes
git_changes = subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT).decode().splitlines()
assert set(git_changes) == allowed, git_changes
prior_evidence = [name for name in old['files'] if name.startswith('evidence/')]
assert all(digest(ROOT/name) == old['files'][name] for name in prior_evidence)
for name in ('scripts/collect_training_parallel.py', 'backend/app/data/budget.py', 'backend/app/main.py', 'backend/app/gmais_api.py'):
    assert (ROOT/name).read_bytes() == subprocess.check_output(['git', 'show', BASE+':'+name], cwd=ROOT), name
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro', uri=True) as connection:
    rows = connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
catalog = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
assert catalog == '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
result = {'recorded_at': datetime.datetime.now().isoformat(), 'git_base': BASE,
          'protected_files_checked': len(previous['protected_references']), 'protected_changes': [],
          'previous_evidence_checked': len(prior_evidence), 'previous_evidence_changes': [],
          'existing_source_changes': sorted(changes), 'catalog_rows': len(rows),
          'git_tracked_source_changes': sorted(git_changes),
          'catalog_sha256': catalog, 'operating_registrations_collection_training_deployment': 0,
          'geoquery_main_gmais_frontend_changed': False,
          'scope': 'LOCAL_PROTECTED_BYTES_AND_CATALOG_NOT_REMOTE_OR_ATOMIC_FILESYSTEM_ASSURANCE'}
target = ROOT/'evidence/integration/lcluc-geollm-live-integrity-final-20261018.json'
assert not target.exists()
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(result, ensure_ascii=False))
