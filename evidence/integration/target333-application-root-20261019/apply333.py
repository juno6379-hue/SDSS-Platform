"""Apply frozen 332 files to main (333). No operational data I/O; no HTTP."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

E = Path(__file__).resolve().parent
PROJECT = E.parents[2]
W = PROJECT/'evidence/integration/target332-workspace-20261019'
FREEZE_SHA = 'b6f23c4b459f499a5511e2c206d5292ab741dad2e41bd3604fa1a88d3de32584'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


if sha(W/'freeze332.json') != FREEZE_SHA: raise RuntimeError('FREEZE_CHANGED')
freeze = json.loads((W/'freeze332.json').read_text(encoding='utf-8'))
pins = {f['path']: f['sha256'] for f in freeze['files']}
base = {f['path']: f['sha256'] for f in freeze['baseline_checks']}
files = ['backend/app/data/ledger_metadata_io.py', 'backend/app/data/budget.py',
         'tests/test_ledger_metadata332.py', 'tests/fixtures/budget332_legacy.py']
for name in files:
    src = W/name
    if sha(src) != pins['evidence/integration/target332-workspace-20261019/'+name]: raise RuntimeError('SOURCE_CHANGED '+name)
    dst = PROJECT/name
    if name == 'backend/app/data/budget.py':
        if sha(dst) != base[name]: raise RuntimeError('MAIN_BUDGET_NOT_BASELINE')
    elif dst.exists(): raise RuntimeError('MAIN_NEW_FILE_PRESENT '+name)
(E/'archive').mkdir(exist_ok=False)
shutil.copyfile(PROJECT/'backend/app/data/budget.py', E/'archive/budget.py.pre333')
if sha(E/'archive/budget.py.pre333') != base['backend/app/data/budget.py']: raise RuntimeError('ARCHIVE_MISMATCH')
applied = []
for name in files:
    shutil.copyfile(W/name, PROJECT/name)
    if sha(PROJECT/name) != sha(W/name): raise RuntimeError('APPLY_MISMATCH '+name)
    applied.append({'path': name, 'sha256': sha(PROJECT/name)})
record = {'unit': 333, 'at': datetime.now(timezone.utc).isoformat(), 'freeze332_sha256': FREEZE_SHA,
          'applied': applied, 'archived_original': {'path': 'archive/budget.py.pre333',
          'sha256': base['backend/app/data/budget.py']}, 'operating_io': False, 'http': False,
          'collector_connected': False, 'real_ledger_connected': False, 'server_restart': False}
(E/'application.json').open('x', encoding='utf-8').write(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(record, ensure_ascii=False, indent=2))
