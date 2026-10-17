"""Read-only preservation proof for the pinned comparison/API/UI unit."""
from pathlib import Path
import datetime
import hashlib
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

baseline = json.loads((ROOT / 'evidence/integration/candidate-qa-comparison-preflight-20261017.json').read_text(encoding='utf-8'))
protected_changes = []
for name, record in baseline['protected_references'].items():
    path = Path(name)
    if path.exists() != record['exists'] or (record['exists'] and (path.stat().st_size != record['bytes'] or digest(path) != record['sha256'])):
        protected_changes.append(name)
contract_changes = [name for name, sha in baseline['unchanged_contract_baseline'].items() if digest(ROOT / name) != sha]
tracked_changes = []
for name, record in baseline['tracked_baseline'].items():
    if name.startswith(('backend/', 'scripts/', 'tests/', 'data/', 'frontend/')) and digest(ROOT / name) != record['sha256']:
        tracked_changes.append(name)
con = sqlite3.connect((ROOT / 'data/catalog.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
rows = con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
con.close()
canonical = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
catalog_ok = len(rows) == baseline['catalog_records_baseline']['rows'] and canonical == baseline['catalog_records_baseline']['canonical_records_sha256']
assert not protected_changes and not contract_changes and catalog_ok
assert sorted(tracked_changes) == sorted(baseline['authorized_existing_code_changes']), tracked_changes
record = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope': 'TRACKED_INPUTS_AND_CORE_CONTRACTS_NOT_FULL_WORKSPACE_OR_ATOMIC_SNAPSHOT', 'protected_references_checked': len(baseline['protected_references']), 'protected_reference_changes': protected_changes, 'existing_contracts_checked': len(baseline['unchanged_contract_baseline']), 'existing_contract_changes': contract_changes, 'previous_tracked_code_data_test_frontend_changes': tracked_changes, 'only_authorized_existing_code_changes': True, 'catalog_records': len(rows), 'catalog_canonical_sha256': canonical, 'catalog_unchanged': catalog_ok, 'new_qa_or_training_executed': False}
(ROOT / 'evidence/integration/candidate-qa-comparison-live-integrity-20261017.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(record, ensure_ascii=True))
