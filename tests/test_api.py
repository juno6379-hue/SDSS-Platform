"""API 통합시험: 빈 상태, 실제 작업 실패, 승인 차단과 영속성을 확인한다."""
import os
import hashlib
import tempfile
import time
from threading import Event
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient
# 모듈 초기화도 운영 카탈로그에 접근하지 않도록 import 전에 임시 루트를 지정한다.
_bootstrap = tempfile.TemporaryDirectory()
_previous_root = os.environ.get('GEOAI_DATA_ROOT')
os.environ['GEOAI_DATA_ROOT'] = _bootstrap.name
from app import main
if _previous_root is None:
    os.environ.pop('GEOAI_DATA_ROOT', None)
else:
    os.environ['GEOAI_DATA_ROOT'] = _previous_root
from app.lifecycle import deploy, transition
from app.store import Store


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = main.store
        main.store = Store(Path(self.temp.name))
        self.client = TestClient(main.app)

    def tearDown(self):
        main.store = self.original
        self.temp.cleanup()

    def test_empty_dashboard_has_no_fabricated_models(self):
        self.assertEqual(self.client.get('/api/dashboard').json()['models'], 0)
        self.assertEqual(self.client.get('/api/models').json(), [])
        tools = self.client.get('/api/tools').json()
        self.assertEqual(sum(tool['implemented'] for tool in tools), 1)
        inventory = self.client.get('/api/data/collection-status')
        self.assertEqual(inventory.status_code, 200)
        self.assertEqual(inventory.json()['summary']['expected_cells'], 36)
        self.assertFalse(inventory.json()['summary']['learning_ready'])

    def test_health_reports_selected_storage_without_credentials(self):
        payload = self.client.get('/api/health').json()
        self.assertEqual(payload['status'], 'ok')
        self.assertTrue(payload['ready'])
        self.assertEqual(payload['storage'], 'sqlite-dev')
        self.assertEqual(payload['storage_status']['active_backend'], 'sqlite-dev')
        self.assertEqual(payload['storage_status']['configured_mode'], 'sqlite-dev')
        self.assertFalse(payload['storage_status']['fallback_used'])
        self.assertNotIn('dsn', str(payload).lower())

    def test_health_does_not_promote_blocked_or_degraded_storage(self):
        base = {
            'configured_mode': 'postgres-inspect', 'active_backend': 'postgres-inspect',
            'environment': 'development', 'writable': False, 'fallback_used': False,
            'fallback_reason': None, 'schema_health': {'status': 'IMPLEMENTED_UNVERIFIED'},
        }
        for storage_state, expected in (
            ('BLOCKED_POSTGRES_INSPECTION_ONLY', 'blocked'),
            ('DEGRADED_DEV_FALLBACK', 'degraded'),
        ):
            with self.subTest(storage_state=storage_state), patch.object(
                main.store, 'storage_status', return_value={**base, 'status': storage_state}
            ):
                payload = self.client.get('/api/health').json()
            self.assertEqual(payload['status'], expected)
            self.assertFalse(payload['ready'])

    def test_approval_and_unapproved_inference_are_blocked(self):
        model = main.store.put('models', {'status': 'Draft', 'independent_evaluation': False})
        response = self.client.post(f"/api/models/{model['id']}/transition", json={'status': 'Validated', 'reason': '단위시험'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post(f"/api/models/{model['id']}/deploy").status_code, 409)
        self.assertEqual(self.client.post('/api/inference', json={'model_id': model['id']}).status_code, 409)
        self.assertEqual(self.client.post('/api/timeseries', json={'model_id': model['id']}).status_code, 409)

    def test_authentication_when_token_configured(self):
        os.environ['GEOAI_API_TOKEN'] = 'test-token'
        try:
            self.assertEqual(self.client.get('/api/models').status_code, 401)
            self.assertEqual(self.client.get('/api/data/collection-status').status_code, 401)
            self.assertEqual(self.client.get('/api/models', headers={'Authorization': 'Bearer test-token'}).status_code, 200)
        finally:
            os.environ.pop('GEOAI_API_TOKEN', None)

    def test_failed_job_persists_real_failure(self):
        # 학습 연산 자체는 ML 시험에서 검증하고 여기서는 작업 실패의 영속화만 분리한다.
        with patch.object(main, 'call', side_effect=main.HTTPException(422, '시험용: 입력 파일 없음')):
            job = self.client.post('/api/training', json={'dataset_path': 'missing.json', 'model_id': 'failure-test'}).json()
            for _ in range(100):
                status = self.client.get('/api/jobs/' + job['id']).json()
                if status['status'] in ('failed', 'succeeded'):
                    break
                time.sleep(0.05)
        self.assertEqual(status['status'], 'failed')
        self.assertTrue(status['error'])
        self.assertEqual(main.store.list('models'), [])

    def test_evidence_query_and_report(self):
        analysis = main.store.put('analyses', {'source': 'explicit-test-fixture', 'changed_area_m2': 200})
        answer = self.client.post('/api/query', json={'question': '산림 변화 면적', 'analysis_id': analysis['id']}).json()
        self.assertEqual(answer['evidence'][0]['source'], 'explicit-test-fixture')
        self.assertIn('explicit-test-fixture', self.client.get(f"/api/analyses/{analysis['id']}/report").text)
        self.assertEqual(self.client.get('/api/artifacts/../catalog.sqlite3').status_code, 404)

    def test_restart_marks_incomplete_job_failed(self):
        job = main.store.put('jobs', {'status': 'running'})
        reopened = Store(Path(self.temp.name), recover_jobs=True)
        self.assertEqual(reopened.get('jobs', job['id'])['status'], 'failed')

    def test_lifecycle_keeps_review_history(self):
        model = {'status': 'Draft', 'independent_evaluation': True, 'checkpoint_path': 'models/a.pt'}
        model = transition(model, 'Validated', '독립 평가 근거 검토')
        model = transition(model, 'Approved', '책임자 승인')
        self.assertEqual(deploy(model)['status'], 'Deployed')
        with self.assertRaises(ValueError):
            transition(model, 'Draft', '임의 역전이')

    def test_execution_history_redacts_credentials_and_signed_query(self):
        public = main.public_input({'url': 'https://data.example/a.tif?sig=secret', 'api_key': 'secret', 'nested': {'token': 'secret', 'year': 2021}})
        self.assertEqual(public, {'url': 'https://data.example/a.tif', 'nested': {'year': 2021}})

    def test_pending_evaluation_blocks_duplicate_and_status_changes(self):
        model = main.store.put('models', {'status': 'Draft', 'checkpoint_path': 'models/model.pt', 'independent_evaluation': True})
        main.store.put('jobs', {'status': 'running', 'evaluation_model_id': model['id']})
        self.assertEqual(self.client.post(f"/api/models/{model['id']}/evaluate", json={}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/models/{model['id']}/transition", json={'status': 'Validated', 'reason': '검토'}).status_code, 409)

    def test_retired_model_is_rejected_when_queued_inference_starts(self):
        ready = Event()
        blocker = main.pool.submit(ready.wait, 5)
        model = main.store.put('models', {'status': 'Deployed', 'checkpoint_path': 'models/model.pt'})
        try:
            job = self.client.post('/api/inference', json={'model_id': model['id'], 'image_path': 'image.tif'}).json()
            main.store.put('models', dict(model, status='Retired'))
        finally:
            ready.set()
            blocker.result(timeout=5)
        for _ in range(100):
            status = self.client.get('/api/jobs/' + job['id']).json()
            if status['status'] in ('failed', 'succeeded'):
                break
            time.sleep(.02)
        self.assertEqual(status['status'], 'failed')
        self.assertIn('배포 상태', status['error'])

    def test_deployment_rejects_modified_checkpoint(self):
        checkpoint = Path(self.temp.name) / 'model.pt'
        checkpoint.write_bytes(b'original-test-fixture')
        model = main.store.put('models', {'status': 'Approved', 'checkpoint_path': 'model.pt', 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()})
        checkpoint.write_bytes(b'modified-test-fixture')
        response = self.client.post(f"/api/models/{model['id']}/deploy")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(main.store.get('models', model['id'])['status'], 'Approved')

    def test_evaluation_rejects_changed_checkpoint_and_reports_readiness(self):
        checkpoint = Path(self.temp.name) / 'model.pt'
        checkpoint.write_bytes(b'original')
        model = main.store.put('models', {'status': 'Draft', 'checkpoint_path': 'model.pt',
            'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()})
        checkpoint.write_bytes(b'changed')
        self.assertEqual(self.client.post(f"/api/models/{model['id']}/evaluate", json={}).status_code, 409)
        state = self.client.get(f"/api/models/{model['id']}/readiness").json()
        self.assertFalse(state['checkpoint_integrity']['matched'])
        self.assertEqual(state['allowed_transitions'], [])
        self.assertFalse(state['can_deploy'])

    def test_weight_change_during_evaluation_cannot_create_approval_evidence(self):
        checkpoint = Path(self.temp.name) / 'model.pt'
        checkpoint.write_bytes(b'original')
        model = main.store.put('models', {'status': 'Draft', 'checkpoint_path': 'model.pt',
            'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(), 'independent_evaluation': False})
        def changed(*args, **kwargs):
            checkpoint.write_bytes(b'changed-during-evaluation')
            return {'reference_kind': 'expert_independent'}
        with patch.object(main, 'call', side_effect=changed):
            job = self.client.post(f"/api/models/{model['id']}/evaluate", json={}).json()
            for _ in range(100):
                status = self.client.get('/api/jobs/' + job['id']).json()
                if status['status'] in ('failed', 'succeeded'):
                    break
                time.sleep(.02)
        self.assertEqual(status['status'], 'failed')
        self.assertFalse(main.store.get('models', model['id'])['independent_evaluation'])


if __name__ == '__main__':
    unittest.main()
