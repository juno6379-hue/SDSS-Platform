"""Harmless executor-only reproduction: no collector, ledger or network."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from app.data.parallel import run_two_workers

entered = threading.Event()
release = threading.Event()
events = []
finalized = []
guard = threading.Lock()


def record(event):
    with guard:
        events.append(event)


def reserve(job):
    record('reserve:'+job)
    if job == 'second':
        if not entered.wait(timeout=5):
            raise RuntimeError('FIRST_WORKER_DID_NOT_ENTER')
        record('second_reserve_raises_FileExistsError')
        release.set()
        raise FileExistsError('SYNTHETIC_PREEXISTING_SECOND_OUTPUT')
    return True


def work(job):
    record('work_enter:'+job)
    entered.set()
    if not release.wait(timeout=5):
        raise RuntimeError('WORK_RELEASE_TIMEOUT')
    # Make executor shutdown wait observably for the already-submitted worker.
    time.sleep(.05)
    record('work_finished:'+job)
    return {'fake': True, 'job': job}


def finalize(job, result):
    record('finalize:'+job)
    finalized.append(job)


started = time.monotonic()
failure = None
try:
    run_two_workers(['first', 'second'], reserve, work, finalize, max_new_batches=2)
except Exception as exc:
    failure = type(exc).__name__
result = {'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'elapsed_seconds': round(time.monotonic()-started, 6),
          'parallel_source_sha256': hashlib.sha256((ROOT/'backend/app/data/parallel.py').read_bytes()).hexdigest(),
          'exception_type': failure, 'events': events, 'finalize_count': len(finalized),
          'worker_completed_before_exception_returned': 'work_finished:first' in events,
          'f1_reproduced': failure == 'FileExistsError' and 'work_finished:first' in events and not finalized,
          'scope': 'Actual existing run_two_workers/ThreadPoolExecutor, two memory-only fake jobs. No170CLI invocation.',
          'main_executed_false_claim': 'Static review only; not reproduced here.',
          'network_calls': 0, 'ledger_writes': 0, 'collector_calls': 0, 'operating_data_writes': 0}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
assert result['f1_reproduced'], result
