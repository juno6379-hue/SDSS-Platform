"""Run 332 isolated tests (focused + portable copy). Never reads operational data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

WORKSPACE = Path(__file__).resolve().parent
FILES = ['backend/app/ml/manifest_resource_profile.py', 'backend/app/ml/split_json_io.py',
         'backend/app/data/targeted_atomic_json.py', 'backend/app/data/budget.py',
         'backend/app/data/ledger_metadata_io.py', 'tests/test_ledger_metadata332.py',
         'tests/fixtures/budget332_legacy.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root, log_name, result_name, extra):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(root), str(root/'tests')]),
               PYTHONDONTWRITEBYTECODE='1')
    start = time.perf_counter()
    with (WORKSPACE/log_name).open('xb') as log:
        code = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_ledger_metadata332'],
                              cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    result = dict(exit_code=code, wall_seconds=time.perf_counter()-start, **extra)
    (WORKSPACE/result_name).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return code


mode = sys.argv[1]
if mode == 'focused':
    sys.exit(run(WORKSPACE, 'focused332-final.log', 'focused332-final-result.json', {}))
if mode == 'portable':
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for name in FILES:
            (root/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WORKSPACE/name, root/name)
        copied = [{'path': name, 'sha256': sha(root/name)} for name in FILES]
        sys.exit(run(root, 'portable332-final.log', 'portable332-final-result.json',
                     {'copied_files': copied, 'baseline_directory_present': (root/'baseline').exists(),
                      'operating_data_copied': False}))
raise SystemExit('mode must be focused or portable')
