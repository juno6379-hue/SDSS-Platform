"""명시적 합성 계약 fixture로 Result 게시 차단과 무결성을 시험한다."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gmais_api import create_router
from app.sdss_results import project_result, download_snapshot, local_asset
from app.store import Store


class SdssResultTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = Store(self.root)
        self.path = self.root / 'fixture.geojson'
        self.path.write_text('{"type":"FeatureCollection","features":[]}', encoding='utf-8')
        ref = {'id': 'explicit-contract-fixture', 'version': '1', 'sha256': 'a' * 64}
        self.manifest = {
            'schema_version': '0.2.0', 'result_id': 'result-fixture', 'job_id': 'job-fixture',
            'agent_id': 'lcluc-agent', 'status': 'SCIENTIFIC_VALIDATED',
            'model_ref': ref, 'input_refs': [ref],
            'output_assets': [{'type': 'GeoJSON', 'uri': self.path.name,
                               'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}],
            'spatial': {'bbox': [106, -7, 107, -6], 'crs': 'OGC:CRS84'},
            'validation': {'validation_level': 'INDEPENDENT_SCIENTIFIC', 'report_ref': 'explicit-test-only'},
            'provenance': {'trace_id': 'trace-fixture', 'processing_version': 'contract-test'},
        }
        self.job = {'id': 'job-fixture', 'result_id': 'result-fixture',
                    'status': {'job_id': 'job-fixture', 'agent_id': 'lcluc-agent',
                               'status': 'SUCCEEDED', 'trace_id': 'trace-fixture'},
                    'request': {'input_refs': [ref], 'model_ref': ref,
                                'execution_context': {'trace_id': 'trace-fixture'}}}
        self.save()
        app = FastAPI()
        app.include_router(create_router(lambda: self.store))
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def save(self):
        self.store.put('gmais_results', dict(self.manifest, id='result-fixture'))
        self.store.put('gmais_jobs', self.job)

    def projection(self):
        return project_result(self.store, 'result-fixture')

    def test_verified_identity_projects_layer_and_download(self):
        result = self.projection()
        self.assertTrue(result['publishable'])
        self.assertEqual(len(result['layers']), 1)
        response = self.client.get(result['layers'][0]['href'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.path.read_bytes())
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')

    def test_mock_and_development_never_publish(self):
        for status in ('MOCK_ONLY', 'DEVELOPMENT_ONLY'):
            with self.subTest(status=status):
                self.manifest['status'] = status
                self.save()
                result = self.projection()
                self.assertFalse(result['publishable'])
                self.assertEqual(result['assets'], [])
                self.assertEqual(self.client.get('/v1/results/result-fixture/assets/0').status_code, 409)

    def test_mismatched_job_trace_model_and_inputs_block(self):
        original = copy.deepcopy(self.job)
        for field in ('trace', 'model', 'input', 'status', 'result'):
            with self.subTest(field=field):
                self.job = copy.deepcopy(original)
                if field == 'trace':
                    self.job['status']['trace_id'] = 'other'
                elif field == 'model':
                    self.job['request']['model_ref']['sha256'] = 'b' * 64
                elif field == 'input':
                    self.job['request']['input_refs'] = []
                elif field == 'status':
                    self.job['status']['status'] = 'BLOCKED'
                else:
                    self.job['result_id'] = 'other'
                self.save()
                self.assertFalse(self.projection()['publishable'])

    def test_modified_asset_blocks_download_after_initial_projection(self):
        href = self.projection()['assets'][0]['href']
        self.path.write_text('changed', encoding='utf-8')
        self.assertEqual(self.client.get(href).status_code, 409)
        self.assertEqual(self.projection()['blockers'][0]['code'], 'HASH_MISMATCH')

    def test_remote_and_traversal_assets_are_not_fetched(self):
        for uri in ('https://example.invalid/asset', '../outside.json', 'file:///etc/passwd'):
            with self.subTest(uri=uri):
                self.manifest['output_assets'][0]['uri'] = uri
                self.save()
                self.assertFalse(self.projection()['publishable'])

    def test_malformed_schema_and_missing_records(self):
        self.manifest['provenance'] = 'invalid'
        self.save()
        self.assertEqual(self.projection()['blockers'][0]['code'], 'SCHEMA_MISMATCH')
        self.assertEqual(self.client.get('/v1/results/absent/sdss').status_code, 404)

    def test_missing_asset_and_invalid_bbox_block(self):
        self.path.unlink()
        self.manifest['spatial']['bbox'] = [107, -7, 106, -6]
        self.save()
        codes = {row['code'] for row in self.projection()['blockers']}
        self.assertEqual(codes, {'INVALID_SPATIAL', 'ASSET_UNAVAILABLE'})

    def test_download_reads_one_manifest_snapshot(self):
        original_get = self.store.get
        reads = []
        def counted_get(kind, identifier):
            if kind == 'gmais_results':
                reads.append(identifier)
                if len(reads) > 1:
                    raise AssertionError('검증 후 manifest를 다시 조회했습니다.')
            return original_get(kind, identifier)
        with patch.object(self.store, 'get', side_effect=counted_get):
            response = self.client.get('/v1/results/result-fixture/assets/0')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(reads), 1)

    def test_snapshot_bytes_do_not_change_when_source_is_rewritten(self):
        original = self.path.read_bytes()
        _, snapshot, _ = download_snapshot(self.store, 'result-fixture', 0)
        try:
            self.path.write_bytes(b'rewritten')
            self.assertEqual(snapshot.read(), original)
        finally:
            snapshot.close()

    def test_unc_and_absolute_paths_rejected_before_resolve(self):
        for uri in ('//server/share/file', '\\\\server\\share\\file', 'C:\\secret.txt', '/etc/passwd'):
            with self.subTest(uri=uri), patch.object(Path, 'resolve', side_effect=AssertionError('원격 경로 해석 금지')):
                with self.assertRaises(ValueError):
                    local_asset(self.root, uri)
