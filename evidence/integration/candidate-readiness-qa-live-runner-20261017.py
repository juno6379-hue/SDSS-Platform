"""Root single QA invocation with sampled resource observations; no training flags."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil

root = Path(__file__).resolve().parents[2]
directory = root / 'evidence/integration'
command = [sys.executable, 'scripts/assess_staged_candidate.py',
    '--data-root', 'data',
    '--candidate', 'data/first-group-candidate-qa-stage-20261017/candidate.json',
    '--candidate-sha256', '2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158',
    '--staging-receipt', 'data/first-group-candidate-qa-stage-20261017/staging-receipt.json',
    '--staging-receipt-sha256', 'b8224cb3eb5c5ef0accf0cab10359401d792719e6fd8cae0b610279e759404dd',
    '--policy', 'data/first-group/experiment-esri-v003-2020-2025.json',
    '--policy-sha256', '01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7',
    '--old-readiness', 'data/first-group/readiness-resume-20261017.json',
    '--old-readiness-sha256', '6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db',
    '--output-dir', 'data/first-group-candidate-readiness-qa-20261017']
environment = dict(os.environ)
environment.update(PROJ_NETWORK='OFF', GDAL_PAM_ENABLED='NO',
    GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_VRT_ENABLE_PYTHON='NO',
    PYTHONIOENCODING='cp949')
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.monotonic()
peak = 0
samples = 0
stop_reason = None
with (directory / 'candidate-readiness-qa-live-cli-20261017.log').open('xb') as stdout, (directory / 'candidate-readiness-qa-live-stderr-20261017.log').open('xb') as stderr:
    process = subprocess.Popen(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
        stdout=stdout, stderr=stderr, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    probe = psutil.Process(process.pid)
    while process.poll() is None:
        try:
            processes = [probe, *probe.children(recursive=True)]
            memory = sum(p.memory_info().rss for p in processes if p.is_running())
            peak = max(peak, memory)
            samples += 1
        except psutil.NoSuchProcess:
            pass
        if time.monotonic() - start > 600:
            stop_reason = 'TIMEOUT_600_SECONDS'
        elif peak > 2 * 1024**3:
            stop_reason = 'SAMPLED_PROCESS_TREE_RSS_OVER_2_GIB'
        if stop_reason:
            process.terminate()
            break
        time.sleep(1)
    exit_code = process.wait(timeout=30)
result = {'started_at': started_at, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'elapsed_seconds': round(time.monotonic() - start, 3), 'exit_code': exit_code,
    'sampled_peak_process_tree_rss_bytes': peak, 'samples': samples, 'sample_interval_seconds': 1,
    'stop_reason': stop_reason, 'timeout_seconds': 600, 'sampled_rss_stop_threshold_bytes': 2 * 1024**3,
    'os_hard_memory_cap': False, 'command': command, 'environment_overrides': {k: environment[k] for k in
        ['PROJ_NETWORK', 'GDAL_PAM_ENABLED', 'GDAL_DISABLE_READDIR_ON_OPEN', 'GDAL_VRT_ENABLE_PYTHON', 'PYTHONIOENCODING']},
    'execute_requested': False, 'resume_requested': False}
with (directory / 'candidate-readiness-qa-live-execution-20261017.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print(json.dumps({k: result[k] for k in ['elapsed_seconds', 'exit_code', 'sampled_peak_process_tree_rss_bytes', 'stop_reason']}, ensure_ascii=True))
sys.exit(0 if exit_code == 0 and stop_reason is None else 1)
