"""Real stored declarations + local replay; never an observed executor capture."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.execution_input_binding import compare_execution_input_bindings
from backend.app.job_snapshot import project_job_input_snapshot

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')

def read_records():
    connection = sqlite3.connect((ROOT / 'data/catalog.sqlite3').as_uri() + '?mode=ro', uri=True)
    try:
        return connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
    finally:
        connection.close()

before = read_records()
jobs = [(key, body) for kind, key, body in before if kind == 'gmais_jobs']
assert len(jobs) == 2
observations = []
false_fields = ['execution_authorized', 'ready_for_execution', 'ready_for_training', 'scientific_approval', 'acl_verified', 'registry_verified', 'training_authorized', 'pixels_verified', 'toc_tou_protected', 'executor_connected', 'artifact_bytes_verified', 'manifest_bytes_verified']
for ordinal, (identifier, body) in enumerate(jobs, 1):
    original_body_sha = hashlib.sha256(body.encode('utf-8')).hexdigest()
    job = json.loads(body)
    snapshot = project_job_input_snapshot(job, identifier)
    assert snapshot['reason'] == 'LEGACY_SNAPSHOT_NOT_RECORDED' and snapshot['available'] is False
    status, request = job['status'], job['request']
    assert identifier == job['id'] == job['job_id'] == status['job_id']
    assert job['agent_id'] == status['agent_id'] == request['agent_id']
    assert status['trace_id'] == request['execution_context']['trace_id']
    bindings = []
    for index, ref in enumerate(request['input_refs']):
        assert 'manifest_sha256' not in ref
        row = {'input_index': index, **{key: ref[key] for key in ['id', 'version', 'sha256']}}
        if 'role' in ref:
            row['role'] = ref['role']
        bindings.append(row)
    expected = {'job_id': identifier, 'agent_id': job['agent_id'], 'trace_id': status['trace_id'], 'bindings': bindings}
    scenarios = []
    supplied = copy.deepcopy(expected)
    scenarios.append(('SAME_STORED_DECLARATIONS_LOCAL_REPLAY', supplied, 'UNKNOWN'))
    backfilled = copy.deepcopy(supplied)
    for row in backfilled['bindings']:
        row['manifest_sha256'] = 'f' * 64  # Synthetic declaration, not a queried Registry value.
    scenarios.append(('SYNTHETIC_MANIFEST_PIN_ADDED_LOCAL_REPLAY', backfilled, 'UNKNOWN'))
    changed = copy.deepcopy(supplied)
    changed['bindings'][0]['version'] = 'local-replay-version-change'
    assert changed['bindings'][0]['version'] != expected['bindings'][0]['version']
    scenarios.append(('SYNTHETIC_VERSION_CHANGE_LOCAL_REPLAY', changed, 'BLOCKED'))
    changed_trace = copy.deepcopy(supplied)
    changed_trace['trace_id'] = 'local-replay-trace-change'
    assert changed_trace['trace_id'] != expected['trace_id']
    scenarios.append(('SYNTHETIC_TRACE_CHANGE_LOCAL_REPLAY', changed_trace, 'BLOCKED'))
    outputs = []
    pristine = copy.deepcopy(expected)
    digest = hashlib.sha256(canonical(bindings)).hexdigest()
    for label, candidate, expected_status in scenarios:
        result = compare_execution_input_bindings(expected, candidate)
        assert result['status'] == expected_status and result['expected_bindings_sha256'] == digest
        assert all(result[key] is False for key in false_fields)
        assert all(result[key] == 0 for key in ['database_calls', 'resolver_calls', 'executor_calls', 'network_requests', 'source_files_written'])
        encoded = json.dumps(result, ensure_ascii=False)
        for scalar in [expected['job_id'], expected['agent_id'], expected['trace_id']] + [v for row in bindings for key, v in row.items() if key != 'input_index']:
            assert json.dumps(scalar, ensure_ascii=False) not in encoded
        outputs.append({'scenario': label, 'expected_status': expected_status, 'observed': result})
    assert expected == pristine
    observations.append({'stored_job_ordinal': ordinal, 'record_body_sha256': original_body_sha, 'legacy_submission_snapshot_not_recorded': True, 'recorded_manifest_pins': 0, 'input_count': len(bindings), 'request_uri_excluded_from_minimal_binding_contract': True, 'expected_from_stored_request_not_trusted_submission_capture': True, 'supplied_from_local_replay_not_executor_capture': True, 'observations': outputs})
after = read_records()
assert before == after
catalog_sha = hashlib.sha256(json.dumps(after, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
assert len(after) == 14 and catalog_sha == '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
record = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope': 'REAL_STORED_REQUEST_DECLARATIONS_WITH_LOCAL_REPLAY_NOT_EXECUTOR_CAPTURE', 'root_catalog_read_only': True, 'stored_jobs_checked': 2, 'local_replay_observations': 8, 'unit_tests_included_in_count': False, 'stored_jobs': observations, 'catalog_records': len(after), 'catalog_canonical_sha256': catalog_sha, 'catalog_and_job_bodies_unchanged': True, 'actual_executor_connected': False, 'actual_job_executed': False, 'manifest_or_artifact_bytes_verified': False, 'training_executed': False}
(ROOT / 'evidence/integration/execution-input-binding-live-validation-20261017.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': 'PASS', 'stored_jobs': 2, 'local_replay_observations': 8, 'unknown': 4, 'blocked': 4, 'catalog_unchanged': True, 'actual_executor_capture': False}))
