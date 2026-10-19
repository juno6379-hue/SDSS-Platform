"""운영 카탈로그와 분리한 API→추론→변화지도→보고서 연계 시험.

성공 경로의 전문가 평가는 명시적 mock이다. 합성 fixture의 실제 독립 정확도 증거가 아니다.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from fastapi.testclient import TestClient

_bootstrap = tempfile.TemporaryDirectory()
_previous_root = os.environ.get('GEOAI_DATA_ROOT')
os.environ['GEOAI_DATA_ROOT'] = _bootstrap.name
from app import main
if _previous_root is None:
    os.environ.pop('GEOAI_DATA_ROOT', None)
else:
    os.environ['GEOAI_DATA_ROOT'] = _previous_root
from app.store import Store


@unittest.skipUnless(importlib.util.find_spec('torch'), '명시적 CPU fixture 추론에 torch 필요')
class MLOpsSDSSFlowTests(unittest.TestCase):
    def setUp(self):
        import torch
        from app.ml.network import TinyUNet
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous = main.store
        main.store = Store(self.root)
        self.client = TestClient(main.app)
        self.threads = torch.get_num_threads()
        torch.set_num_threads(1)
        model = TinyUNet(3)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.zero_()
            model.head.bias[1] = 1
        # 합성이라는 메타데이터를 보존한다. 실제 evaluate_model은 이 모델을 거부해야 한다.
        self.checkpoint = self.root / 'fixture.pt'
        torch.save({'state_dict': model.state_dict(), 'manifest': {'bands': [1, 2, 3], 'scale': .0001,
                   'offset': 0, 'patch_size': 16, 'synthetic': True, 'reference_kind': 'synthetic_fixture_only',
                   'provenance': []}}, self.checkpoint)
        self.sha = hashlib.sha256(self.checkpoint.read_bytes()).hexdigest()
        self.model = main.store.put('models', {'id': 'isolated-fixture-model', 'status': 'Draft',
            'checkpoint_path': 'fixture.pt', 'checkpoint_sha256': self.sha, 'independent_evaluation': False,
            'synthetic': True, 'reference_kind': 'synthetic_fixture_only', 'fixture_only': True,
            'source': 'temporary_test_root_not_production', 'history': []})
        self.profile = {'driver': 'GTiff', 'width': 16, 'height': 16, 'transform': from_origin(500000, 9000000, 10, 10),
                        'crs': 'EPSG:32748', 'nodata': 255}
        self.write('input.tif', np.full((3, 16, 16), 1000, dtype='uint16'))
        self.write('expert-fixture.tif', np.ones((16, 16), dtype='uint8'))

    def tearDown(self):
        import torch
        main.store = self.previous
        torch.set_num_threads(self.threads)
        self.temp.cleanup()

    def write(self, name, values, transform=None):
        if values.ndim == 2:
            values = values[None]
        with rasterio.open(self.root / name, 'w', **{**self.profile, 'transform': transform or self.profile['transform'],
                            'count': values.shape[0], 'dtype': values.dtype}) as output:
            output.write(values)

    def wait(self, response):
        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()['id']
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            job = self.client.get(f'/api/jobs/{job_id}').json()
            if job['status'] in ('succeeded', 'failed'):
                return job
            time.sleep(.025)
        self.fail('임시 통합 시험 작업이 완료되지 않음')

    def evaluation_payload(self):
        return {'image_path': 'input.tif', 'label_path': 'expert-fixture.tif', 'output_id': 'fixture-eval',
                'reference_kind': 'expert_independent', 'label_provenance': 'MOCK ONLY; not ground truth',
                'reviewer': 'test-harness', 'group': 'fixture-independent-group'}

    def simulate_review(self):
        original_call = main.call
        def fixture_dispatch(module, function, payload, with_root=True):
            if function == 'evaluate_model':
                # 평가 응답 경계만 mock하며 추론·변화·지도·보고서는 실제 구현을 실행한다.
                return {'reference_kind': 'expert_independent', 'checkpoint_sha256': self.sha,
                        'fixture_only': True, 'independence_basis': 'mock_contract_only_no_accuracy_claim'}
            return original_call(module, function, payload, with_root)
        with patch.object(main, 'call', side_effect=fixture_dispatch):
            job = self.wait(self.client.post('/api/models/isolated-fixture-model/evaluate', json=self.evaluation_payload()))
        self.assertEqual(job['status'], 'succeeded', job)
        for status in ('Validated', 'Approved'):
            response = self.client.post('/api/models/isolated-fixture-model/transition', json={'status': status, 'reason': '임시 mock 계약 시험 전용'})
            self.assertEqual(response.status_code, 200, response.text)

    def test_real_evaluator_rejects_synthetic_and_review_gate_stays_closed(self):
        readiness = self.client.get('/api/models/isolated-fixture-model/readiness').json()
        self.assertEqual(readiness['allowed_transitions'], [])
        self.assertFalse(readiness['can_deploy'])
        response = self.client.post('/api/models/isolated-fixture-model/transition', json={'status': 'Validated', 'reason': '사용자 승인 요청만으로 우회 불가'})
        self.assertEqual(response.status_code, 409)
        job = self.wait(self.client.post('/api/models/isolated-fixture-model/evaluate', json=self.evaluation_payload()))
        self.assertEqual(job['status'], 'failed')
        self.assertIn('합성', job['error'])
        self.assertEqual(main.store.get('models', self.model['id'])['status'], 'Draft')

    def test_mock_review_to_real_inference_change_map_report_and_download(self):
        self.simulate_review()
        readiness = self.client.get('/api/models/isolated-fixture-model/readiness').json()
        self.assertTrue(readiness['can_deploy'])
        self.assertTrue(readiness['checkpoint_integrity']['matched'])
        response = self.client.post('/api/models/isolated-fixture-model/deploy')
        self.assertEqual(response.status_code, 200, response.text)
        prediction = self.wait(self.client.post('/api/inference', json={'model_id': self.model['id'], 'image_path': 'input.tif', 'output_id': 'fixture-inference'}))
        self.assertEqual(prediction['status'], 'succeeded', prediction)
        predicted_path = prediction['result']['classification_path']
        with rasterio.open(self.root / predicted_path) as source:
            values = source.read(1)
        self.assertTrue((values == 1).all())
        values[:4, :4] = 4
        self.write('second-date-fixture.tif', values)
        change = self.wait(self.client.post('/api/change', json={'t1_path': predicted_path, 't2_path': 'second-date-fixture.tif', 'output_id': 'fixture-change', 'num_classes': 9}))
        self.assertEqual(change['status'], 'succeeded', change)
        result = change['result']
        self.assertEqual(result['changed_area_m2'], 1600)
        identifier = result['id']
        mapped = self.client.get(f'/api/analyses/{identifier}/map-data')
        self.assertEqual(mapped.status_code, 200, mapped.text)
        data = mapped.json()
        self.assertGreater(data['feature_count'], 0)
        self.assertEqual(data['geojson']['type'], 'FeatureCollection')
        self.assertEqual(data['geojson']['features'][0]['properties']['from_class'], 1)
        self.assertEqual(data['geojson']['features'][0]['properties']['to_class'], 4)
        self.assertEqual(len(data['bbox']), 4)
        report = self.client.get(f'/api/analyses/{identifier}/report')
        self.assertEqual(report.status_code, 200)
        self.assertIn('1600', report.text)
        self.assertIn('fixture-change', report.text)
        query = self.client.post('/api/query', json={'question': '변화 면적', 'analysis_id': identifier}).json()
        self.assertEqual(query['evidence'][0]['id'], identifier)
        for key in ('geotiff_path', 'csv_path', 'geojson_path'):
            artifact = self.client.get('/api/artifacts/' + result[key].replace('\\', '/'))
            self.assertEqual(artifact.status_code, 200, artifact.text[:200] if 'text' in artifact.headers.get('content-type', '') else key)
        self.assertFalse(self.previous is main.store)

    def test_checkpoint_change_after_review_prevents_deployment(self):
        self.simulate_review()
        self.checkpoint.write_bytes(b'modified-isolated-fixture')
        response = self.client.post('/api/models/isolated-fixture-model/deploy')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(self.client.get('/api/models/isolated-fixture-model/readiness').json()['can_deploy'])

    def test_shifted_change_grid_fails_without_fabricated_analysis(self):
        self.write('date1.tif', np.ones((16, 16), dtype='uint8'))
        self.write('date2.tif', np.full((16, 16), 4, dtype='uint8'), from_origin(500005, 9000000, 10, 10))
        job = self.wait(self.client.post('/api/change', json={'t1_path': 'date1.tif', 't2_path': 'date2.tif', 'output_id': 'shifted'}))
        self.assertEqual(job['status'], 'failed')
        self.assertEqual(self.client.get('/api/analyses').json(), [])

    def test_completed_fixture_registration_is_draft_and_cannot_override_approval(self):
        # 등록 계약 전용 합성 보고서다. 실제 학습 실행/성과가 아니라 보관 파일 검증 경계만 시험한다.
        manifest = {'dataset_id': 'registered-fixture-dataset', 'version': 'explicit-fixture-version',
                    'synthetic': True, 'reference_kind': 'synthetic_fixture_only'}
        (self.root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        trained = {'model_id': 'registered-fixture-model', 'training_state': 'completed',
                   'checkpoint_path': 'fixture.pt', 'checkpoint_sha256': self.sha,
                   'dataset_version': manifest['version'], 'synthetic': True,
                   'reference_kind': 'synthetic_fixture_only', 'fixture_only': True}
        (self.root / 'report.json').write_text(json.dumps(trained), encoding='utf-8')
        prepared = {**manifest, 'manifest_path': 'manifest.json'}
        (self.root / 'experiment.json').write_text(json.dumps({'status': 'completed_fixture_contract_only',
                                  'training': trained, 'dataset': prepared}), encoding='utf-8')
        response = self.client.post('/api/models/register-experiment', json={'report_path': 'experiment.json',
                                     'status': 'Approved', 'independent_evaluation': True})
        self.assertEqual(response.status_code, 201, response.text)
        model = response.json()['model']
        self.assertEqual(model['status'], 'Draft')
        self.assertFalse(model['independent_evaluation'])
        self.assertEqual(model['checkpoint_sha256'], self.sha)
        self.assertEqual(model['experiment_report_sha256'], hashlib.sha256((self.root / 'experiment.json').read_bytes()).hexdigest())
        self.assertEqual(self.client.post('/api/models/register-experiment', json={'report_path': 'experiment.json'}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
