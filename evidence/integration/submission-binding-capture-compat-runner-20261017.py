"""Deterministic TempStore before/after compatibility; never submits to live API."""
from pathlib import Path
import argparse
import copy
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'backend'), str(ROOT)]
from test_gmais_api import GmaisApiTests, main
from app import job_inputs

def run():
    observations = []
    for case in ['PUBLIC_REGISTERED', 'RESTRICTED_REGISTERED', 'UNREGISTERED']:
        fixture = GmaisApiTests()
        fixture.setUp()
        try:
            payload = fixture.request()
            registered = None
            if case != 'UNREGISTERED':
                registered = fixture.register_input_fixture(payload, access_class='RESTRICTED' if case.startswith('RESTRICTED') else 'PUBLIC')
            legacy_resolution = job_inputs.resolve_job_inputs(main.store, payload['input_refs'])
            with (patch('app.gmais_api.uuid.uuid4', return_value=SimpleNamespace(hex='fixed-capture-compat')),
                 patch('app.gmais_api._now', return_value='2026-10-17T00:00:00.000Z'),
                 patch('app.store.now', return_value='2026-10-17T00:00:00.000Z')):
                with (patch.object(job_inputs, 'resolve_version', wraps=job_inputs.resolve_version) as resolver,
                     patch.object(main.store, 'put', wraps=main.store.put) as put):
                    response = fixture.client.post('/v1/agents/lcluc-agent/jobs', json=payload, headers={'Idempotency-Key': case})
                assert response.status_code == 409
                identifier = response.json()['error']['details']['job_id']
                stored = main.store.get('gmais_jobs', identifier)
                capture = stored.pop('execution_input_binding_capture', None)
                assert resolver.call_count == len(payload['input_refs'])
                assert [call.args[0] for call in put.call_args_list] == ['gmais_jobs', 'gmais_idempotency']
                assert response.json()['error']['details']['input_resolution'] == stored['input_resolution']
                assert not any('capture' in key for key in response.json()['error']['details'])
                assert stored['status']['status'] == 'BLOCKED'
                # Same-key replay after source alteration must not resolve or recapture.
                (fixture.root / payload['input_refs'][0]['uri']).write_bytes(b'changed-after-submission')
                with (patch.object(job_inputs, 'resolve_job_inputs', side_effect=AssertionError('no replay resolution')),
                     patch.object(job_inputs, 'resolve_job_inputs_with_capture', side_effect=AssertionError('no replay capture'), create=True),
                     patch.object(main.store, 'put', side_effect=AssertionError('no replay write'))):
                    replay = fixture.client.post('/v1/agents/lcluc-agent/jobs', json=payload, headers={'Idempotency-Key': case})
                assert replay.status_code == 409 and replay.json() == response.json()
                if capture is not None:
                    assert capture['status'] == ('RECORDED' if registered else 'UNAVAILABLE')
                    if registered:
                        assert capture['expected_envelope']['bindings'][0]['manifest_sha256'] == registered['manifest_sha256']
                    encoded = json.dumps(capture, ensure_ascii=False)
                    assert json.dumps(payload['input_refs'][0]['uri']) not in encoded and str(fixture.root) not in encoded
                observations.append({'case': case, 'legacy_resolution': legacy_resolution, 'status_code': response.status_code,
                    'response': response.json(), 'location': response.headers['Location'], 'stored_job_without_capture': stored,
                    'resolution_calls_for_submission': resolver.call_count, 'submission_put_kinds': [call.args[0] for call in put.call_args_list],
                    'replay_identical_and_no_resolution_or_write': True, 'capture': capture})
        finally:
            fixture.tearDown()
    return observations

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['before', 'after'], required=True)
    args = parser.parse_args()
    results = run()
    baseline = ROOT / 'evidence/integration/submission-binding-capture-compat-before-20261017.json'
    if args.phase == 'before':
        assert all(row['capture'] is None for row in results)
        with baseline.open('x', encoding='utf-8') as stream:
            json.dump({'scope': 'TEMPSTORE_SYNTHETIC_PRE_CHANGE_NOT_LIVE_API', 'cases': results}, stream, ensure_ascii=False, indent=2)
    else:
        old = json.loads(baseline.read_text(encoding='utf-8'))['cases']
        for left, right in zip(old, results):
            assert right['capture'] is not None
            normalized = copy.deepcopy(right)
            normalized['capture'] = None
            assert left == normalized, left['case']
        (ROOT / 'evidence/integration/submission-binding-capture-compat-after-20261017.json').write_text(
            json.dumps({'scope': 'TEMPSTORE_SYNTHETIC_POST_CHANGE_NOT_LIVE_API', 'old_response_and_job_without_capture_deep_equal': True, 'cases': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'phase': args.phase, 'cases': len(results), 'status': 'PASS', 'live_api_submissions': 0}))
