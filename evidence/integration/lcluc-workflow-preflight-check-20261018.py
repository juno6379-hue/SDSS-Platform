from pathlib import Path
import datetime
import hashlib
import json
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'd264f81378f7fd3a2b07ab69b9193e8b3d651bc9'
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
prior = json.loads((ROOT/'evidence/integration/recovery-commit-contract-preflight-20261017.json').read_text('utf-8'))


def record(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == BASE
assert all(record(ROOT/name) == expected for name, expected in snapshot['files'].items())
protected = prior['protected_references']
for name, expected in protected.items():
    path = Path(name)
    assert path.exists() == expected['exists'], name
    if path.exists(): assert record(path) == {key: expected[key] for key in ('sha256', 'bytes')}, name
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro', uri=True) as connection:
    rows = connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
catalog = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
assert catalog == '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
out = {'recorded_at': datetime.datetime.now().isoformat(), 'git_base': BASE,
       'snapshot_sha256': record(snapshot_path)['sha256'], 'tracked_baseline': snapshot['files'],
       'protected_references': protected, 'protected_files_checked': len(protected),
       'authorized_existing_source_changes': [], 'catalog_rows': len(rows),
       'catalog_sha256': catalog, 'snapshot_files': len(snapshot['files']),
       'scope': 'NEW_LOCAL_EXECUTOR_AND_EXPLICIT_CLI_ONLY_TEMPORARY_FIXTURE_EXECUTION_NOT_OPERATING_DATA',
       'API_UI_implementation_in_this_unit': False}
target = ROOT/'evidence/integration/lcluc-workflow-preflight-20261018.json'
assert not target.exists()
target.write_text(json.dumps(out, ensure_ascii=False, indent=2), 'utf-8')
print('115 baseline verified:', len(snapshot['files']), 'files;', len(protected), 'protected; catalog14 unchanged.')
