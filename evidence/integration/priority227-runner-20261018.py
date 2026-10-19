"""227: 승인된 기존164 CLI를 새 run-id로 한 번 실행하고 로그를 보존한다."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/first-group-training-esri-v1/annual-window-report.json'
POLICY = ROOT / 'data/first-group/experiment-esri-v003-2020-2025.json'
SOURCE_PIN = '9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
POLICY_PIN = '01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7'
EVIDENCE = ROOT / 'evidence/integration'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


assert SOURCE.stat().st_size <= 64 * 1024**2
assert POLICY.stat().st_size <= 1024**2
assert sha(SOURCE) == SOURCE_PIN and sha(POLICY) == POLICY_PIN
for name in ['data/priority164-guarded227-20261018',
             'evidence/integration/priority164-guarded227-20261018']:
    path = ROOT / name
    assert not path.exists() and not path.is_symlink()
protected = {
    name: sha(ROOT / name) for name in [
        'data/first-group-training-priority/latest-candidate.json',
        'data/first-group-training-priority/candidate-receipt207-20261018.json',
        'evidence/integration/priority164-guarded207-20261018/summary.json']}
args = [sys.executable, '-X', 'utf8', '-u', str(ROOT / 'scripts/prepare_priority_candidate164.py'),
        '--data-root', str(ROOT / 'data'), '--source', str(SOURCE),
        '--source-sha256', SOURCE_PIN, '--policy', str(POLICY),
        '--policy-sha256', POLICY_PIN, '--run-id', 'guarded227-20261018']
with (EVIDENCE / 'priority164-guarded227-20261018.log').open('x', encoding='utf-8') as output:
    child = subprocess.Popen(args, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    launch = {'at': datetime.now(timezone.utc).isoformat(), 'pid': child.pid,
              'command': args, 'source_bytes': SOURCE.stat().st_size,
              'source_sha256': SOURCE_PIN, 'policy_sha256': POLICY_PIN,
              'protected_before': protected, 'automatic_retry_allowed': False}
    with (EVIDENCE / 'priority227-launch-20261018.json').open('x', encoding='utf-8') as stream:
        json.dump(launch, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'STARTED_ONCE', 'pid': child.pid}), flush=True)
    code = child.wait()
    with (EVIDENCE / 'priority227-terminal-20261018.json').open('x', encoding='utf-8') as stream:
        json.dump({'at': datetime.now(timezone.utc).isoformat(), 'exit_code': code,
                   'pid': child.pid, 'automatic_retry_allowed': False}, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'TERMINAL', 'exit_code': code}), flush=True)
    sys.exit(code)
