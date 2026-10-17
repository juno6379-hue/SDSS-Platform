"""Read-only preservation audit; never initializes the operating Store."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
pre = json.loads((ROOT/'evidence/integration/model-error-read-preflight-20261018.json').read_text('utf-8'))
protected = json.loads((ROOT/'evidence/integration/recovery-commit-contract-preflight-20261017.json').read_text('utf-8'))['protected_references']


def record(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return {'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


for name, expected in protected.items():
    path = Path(name)
    assert path.exists() == expected['exists'], name
    if path.exists():
        assert record(path) == {k: expected[k] for k in ('sha256', 'bytes')}, name
old = pre['snapshot']['files']
authorized = {'backend/app/main.py', 'frontend/src/ModelReview.tsx',
              'tests/test_model_registration_provenance_api.py', 'tests/test_workflow_job_model_record_handoff_api.py'}
source = [n for n in old if n.startswith(('backend/', 'frontend/', 'scripts/', 'tests/'))]
changed = [n for n in source if record(ROOT/n) != old[n]]
assert set(changed) == authorized, changed
previous = [n for n in old if n.startswith('evidence/')]
assert all(record(ROOT/n) == old[n] for n in previous)
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro', uri=True) as conn:
    rows = conn.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
catalog = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert len(rows) == 14 and catalog == '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
legacy = []
for kind, identifier, body in rows:
    if kind != 'models':
        continue
    model = json.loads(body)
    path = ROOT/'data/models'/identifier/'report.json'
    report = json.loads(path.read_text('utf-8')) if path.is_file() else {}
    legacy.append({'id': identifier, 'status': model.get('status'),
                   'version_declaration_present': 'model_version_declaration' in model,
                   'training_report_sha_present': 'training_report_sha256' in model,
                   'saved_report_exists': path.is_file(), 'saved_report_error_analysis_present': 'error_analysis' in report})
result = {'recorded_at': datetime.now().astimezone().isoformat(),
          'protected_files_checked': len(protected), 'protected_changes': [],
          'existing_source_checked': len(source), 'authorized_existing_source_changes': sorted(changed),
          'unexpected_existing_source_changes': [], 'previous_evidence_checked': len(previous),
          'previous_evidence_changes': [], 'catalog_rows': len(rows), 'catalog_canonical_sha256': catalog,
          'operating_models_read_only_observations': legacy,
          'reserved_bytes_preserved': 136314880,
          'operating_collection_training_registry_deployment_workflow_dispatch': 0}
(ROOT/'evidence/integration/model-error-read-live-integrity-20261018.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
