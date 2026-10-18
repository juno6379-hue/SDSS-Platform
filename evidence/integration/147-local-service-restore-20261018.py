"""Restore the existing app's loopback development mode; no token or code change."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import socket

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'evidence/integration'
OUTPUT = EVIDENCE / '147-local-service-restore-20261018-start.json'


def state():
    path = ROOT / 'data/catalog.sqlite3'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as conn:
        rows = conn.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
    return {'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'rows': len(rows),
            'canonical_sha256': hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True,
                                                       separators=(',', ':')).encode()).hexdigest(),
            'legacy_jobs': sum(row[0] == 'jobs' for row in rows)}


if OUTPUT.exists():
    raise RuntimeError('One-time launch record exists; inspect existing process, do not repeat.')
if os.environ.get('GEOAI_API_TOKEN'):
    raise RuntimeError('Unexpected token configuration; preserve and inspect before proceeding.')
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1', 8002)) == 0:
        raise RuntimeError('Port 8002 already serves a process.')
before = state()
assert before['rows'] == 14 and before['legacy_jobs'] == 0
assert before['canonical_sha256'] == '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
env = os.environ.copy()
env['GEOAI_DATA_ROOT'] = str(ROOT / 'data')
env['PYTHONPATH'] = os.pathsep.join([str(ROOT / '.runtime'), str(ROOT / 'backend')])
env['PYTHONIOENCODING'] = 'utf-8'
command = ['python', '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8002']
record = {'observed_at': datetime.now().astimezone().isoformat(), 'catalog_before': before,
          'command': command, 'explicit_data_root': env['GEOAI_DATA_ROOT'],
          'authentication_mode': 'EXISTING_APP_DEFAULT_WITH_TOKEN_UNSET_LOOPBACK_BINDING_ONLY',
          'token_created_or_changed': False, 'source_or_authorization_code_changed': False,
          'startup_recovery_target_count_before': 0, 'POST_requests': 0,
          'status': 'PREPARED'}
with OUTPUT.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
with (EVIDENCE / '147-local-service-restore-20261018-stdout.log').open('xb') as out, \
     (EVIDENCE / '147-local-service-restore-20261018-stderr.log').open('xb') as err:
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                               stdout=out, stderr=err,
                               creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
record.update(status='LAUNCHED_NOT_YET_HEALTH_VERIFIED', pid=process.pid)
OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pid': process.pid, 'mode': record['authentication_mode']}))
