"""GMAIS v0.2 내부 제안과 로컬 API의 계약시험. 실제 과학 결과를 생성하지 않는다."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'backend'))
SCHEMAS = PROJECT / 'contracts/upstream/GMAIS-v0.2/schemas'

# 단독 실행의 import도 실제 카탈로그를 초기화하지 않게 한다.
_bootstrap = tempfile.TemporaryDirectory()
with patch.dict(os.environ, {'GEOAI_DATA_ROOT': _bootstrap.name}):
    from app import main
from app.store import Store


class GmaisApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.original_store = main.store
        main.store = Store(self.root)
        self.auth = patch.dict(os.environ, {'GEOAI_API_TOKEN': ''})
        self.auth.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.auth.stop()
        main.store = self.original_store
        self.temporary.cleanup()

    def validate(self, name, value):
        schema = json.loads((SCHEMAS / name).read_text(encoding='utf-8'))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)

    def request(self):
        # 명시적 계약 fixture의 실제 파일/해시다. AI-ready/독립 정답이라고 등록하지 않는다.
        path = self.root / 'contract-fixture.json'
        path.write_text('{"purpose":"explicit-contract-test-not-scientific-data"}', encoding='utf-8')
        return {
            'schema_version': '0.2.0', 'agent_id': 'lcluc-agent',
            'capability_id': 'landcover.change_detection',
            'input_refs': [{'id': 'contract-fixture', 'version': '1',
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'uri': 'contract-fixture.json', 'role': 'T1'}],
            'aoi': {'bbox': [106.1, -6.8, 106.2, -6.7], 'crs': 'OGC:CRS84'},
            'requested_outputs': ['COG', 'JSON'],
            'execution_context': {'trace_id': 'trace-explicit-contract-fixture',
                                  'workflow_run_id': 'workflow-explicit-fixture',
                                  'purpose': 'contract-test', 'environment': 'development'},
        }

    def submit_blocked(self, key='isolated-contract-request', payload=None):
        payload = payload or self.request()
        self.validate('job-request.schema.json', payload)
        response = self.client.post('/v1/agents/' + payload['agent_id'] + '/jobs',
                                    json=payload, headers={'Idempotency-Key': key})
        self.assertEqual(response.status_code, 409, response.text)
        self.validate('error.schema.json', response.json())
        # 차단 요청도 조회 가능한 작업으로 남기며 운영 결과는 만들지 않는다.
        location = response.headers.get('Location')
        self.assertTrue(location and location.startswith('/v1/jobs/'), response.text)
        status = self.client.get(location)
        self.assertEqual(status.status_code, 200, status.text)
        job = status.json()
        self.validate('job-status.schema.json', job)
        self.assertEqual(location, '/v1/jobs/' + job['job_id'])
        self.assertEqual(job['agent_id'], payload['agent_id'])
        self.assertEqual(job['trace_id'], payload['execution_context']['trace_id'])
        self.assertEqual(job['status'], 'BLOCKED')
        self.assertNotIn('result_id', job)
        self.assertEqual(response.json()['error']['details']['job_id'], job['job_id'])
        self.assertEqual(response.json()['error']['details']['job_status'], job)
        return response, job

    def test_six_manifests_obey_schema_and_only_lcluc_is_implemented(self):
        response = self.client.get('/v1/agents')
        self.assertEqual(response.status_code, 200)
        items = response.json()['items']
        self.assertEqual(len(items), 6)
        self.assertEqual(len({item['agent_id'] for item in items}), 6)
        for item in items:
            self.validate('agent-manifest.schema.json', item)
            detail = self.client.get('/v1/agents/' + item['agent_id'])
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json(), item)
            self.assertNotIn('runtime_ready', item)
            self.assertNotIn('dataset_ready', item)
            if item['agent_id'] == 'lcluc-agent':
                self.assertEqual(item['model_type'], 'trainable_ml')
                self.assertEqual(item['readiness'], 'BLOCKED')
                self.assertEqual(item['model_approval_status'], 'DRAFT')
            else:
                self.assertEqual(item['readiness'], 'NOT_IMPLEMENTED')
        self.assertEqual(main.store.list('models'), [])
        self.assertEqual(main.store.list('analyses'), [])

    def test_readiness_is_separate_from_manifest_and_does_not_approve_model(self):
        response = self.client.get('/v1/agents/lcluc-agent/readiness')
        self.assertEqual(response.status_code, 200)
        readiness = response.json()
        self.assertEqual(readiness['agent_id'], 'lcluc-agent')
        self.assertEqual(readiness['readiness'], 'BLOCKED')
        self.assertEqual(readiness['model_approval_status'], 'DRAFT')
        self.assertEqual(set(readiness['axes']), {'runtime', 'dataset', 'science', 'deployment', 'contract'})
        self.assertEqual(readiness['axes']['runtime']['state'], 'READY')
        self.assertEqual(readiness['axes']['contract']['state'], 'PROPOSED')
        for name in ('dataset', 'science', 'deployment'):
            self.assertEqual(readiness['axes'][name]['state'], 'BLOCKED')
        for axis in readiness['axes'].values():
            self.assertIn('evidence', axis)
        self.assertTrue(readiness['blockers'])
        manifest = self.client.get('/v1/agents/lcluc-agent').json()
        self.validate('agent-manifest.schema.json', manifest)
        self.assertNotIn('axes', manifest)
        self.assertNotIn('blockers', manifest)
        self.assertEqual(main.store.list('models'), [])

    def test_valid_lcluc_request_persists_blocked_job_and_trace_without_result(self):
        _, job = self.submit_blocked()
        replay = self.client.get('/v1/jobs/' + job['job_id'])
        self.assertEqual(replay.json(), job)
        self.assertTrue(job.get('error_code'))
        # 서로 다른 Store 연결로도 같은 blocked 레코드가 보이는지 확인한다.
        persisted = Store(self.root)
        found = [r for r in persisted.list('gmais_jobs') if r.get('job_id') == job['job_id']]
        self.assertEqual(len(found), 1)
        self.assertEqual(main.store.list('analyses'), [])
        self.assertEqual(main.store.list('models'), [])

    def test_invalid_request_and_missing_idempotency_key_are_rejected(self):
        body = self.request()
        cases = [({}, {'Idempotency-Key': 'invalid-body'}),
                 ({**body, 'unexpected_top_level': True}, {'Idempotency-Key': 'extra-field'}),
                 (body, {})]
        for payload, headers in cases:
            with self.subTest(payload=payload, headers=headers):
                response = self.client.post('/v1/agents/lcluc-agent/jobs', json=payload, headers=headers)
                self.assertEqual(response.status_code, 400, response.text)
                self.validate('error.schema.json', response.json())
        self.assertEqual(main.store.list('gmais_jobs'), [])

    def test_idempotent_replay_preserves_same_blocked_job(self):
        body = self.request()
        first, job = self.submit_blocked('same-request', body)
        second, repeated = self.submit_blocked('same-request', copy.deepcopy(body))
        self.assertEqual(first.headers['Location'], second.headers['Location'])
        self.assertEqual(job, repeated)
        self.assertEqual(len(main.store.list('gmais_jobs')), 1)

    def test_same_idempotency_key_with_different_body_cannot_create_second_job(self):
        body = self.request()
        self.submit_blocked('cannot-reuse-with-other-body', body)
        changed = copy.deepcopy(body)
        changed['parameters'] = {'explicit_fixture_change': True}
        response = self.client.post('/v1/agents/lcluc-agent/jobs', json=changed,
                                    headers={'Idempotency-Key': 'cannot-reuse-with-other-body'})
        self.assertEqual(response.status_code, 409)
        self.validate('error.schema.json', response.json())
        self.assertEqual(response.json()['error']['code'], 'SCHEMA_MISMATCH')
        self.assertEqual(len(main.store.list('gmais_jobs')), 1)

    def test_blocked_results_and_unknown_ids_never_create_result_manifest(self):
        _, job = self.submit_blocked()
        response = self.client.get('/v1/jobs/' + job['job_id'] + '/results')
        self.assertEqual(response.status_code, 409)
        self.validate('error.schema.json', response.json())
        self.assertEqual(response.json()['error']['code'], 'MODEL_NOT_READY')
        for path in ('/v1/jobs/not-existing-job', '/v1/results/not-existing-result'):
            with self.subTest(path=path):
                missing = self.client.get(path)
                self.assertEqual(missing.status_code, 404)
                self.validate('error.schema.json', missing.json())
        self.assertEqual(main.store.list('gmais_results'), [])
        self.assertEqual(main.store.list('analyses'), [])

    def test_external_agent_job_is_blocked_without_invoking_scientific_model(self):
        external = next(item for item in self.client.get('/v1/agents').json()['items']
                        if item['agent_id'] != 'lcluc-agent')
        readiness = self.client.get('/v1/agents/' + external['agent_id'] + '/readiness').json()
        self.assertEqual(readiness['readiness'], 'NOT_IMPLEMENTED')
        self.assertTrue(all(axis['state'] == 'NOT_IMPLEMENTED' for axis in readiness['axes'].values()))
        body = self.request()
        body['agent_id'] = external['agent_id']
        body['capability_id'] = external['capabilities'][0]['capability_id']
        _, job = self.submit_blocked('external-not-implemented', body)
        self.assertEqual(job['error_code'], 'AGENT_NOT_IMPLEMENTED')
        self.assertEqual(main.store.list('gmais_results'), [])


if __name__ == '__main__':
    unittest.main()
