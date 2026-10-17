"""임시 Registry의 계보 RFC HTTP 진단·인증 상속·기존 namespace 불변을 검증한다."""
import copy
from datetime import datetime
import json
import os
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import test_dataset_lineage as core_fixtures
import test_gmais_api as app_fixtures
from app.dataset_lineage_api import create_dataset_lineage_router


class DatasetLineageApiTests(unittest.TestCase):
    def setUp(self):
        self.fixture = core_fixtures.DatasetLineageTests(); self.fixture.setUp()
        self.store = self.fixture.store
        self.root = self.fixture.dataset('http-root')
        app = FastAPI(); app.include_router(create_dataset_lineage_router(lambda: self.store))
        self.client = TestClient(app)
        self.original_store = app_fixtures.main.store
        app_fixtures.main.store = self.store
        self.auth = patch.dict(os.environ, {'GEOAI_API_TOKEN': ''}); self.auth.start()
        self.main_client = TestClient(app_fixtures.main.app)

    def tearDown(self):
        self.main_client.close(); self.client.close(); self.auth.stop()
        app_fixtures.main.store = self.original_store
        self.fixture.tearDown()

    def request(self, ref=None, **limits):
        return dict(root_ref=copy.deepcopy(ref or self.root), **limits)

    def verify(self, body=None):
        body = self.request() if body is None else body
        before = self.fixture.files(self.store); original = copy.deepcopy(body)
        with patch.object(self.store, 'put', side_effect=AssertionError('조회가 Registry를 변경했습니다.')):
            with patch.object(app_fixtures.main.pool, 'submit', side_effect=AssertionError('조회가 Job을 제출했습니다.')):
                response = self.client.post('/v1/datasets/lineage/verify', json=body)
        self.assertEqual(self.fixture.files(self.store), before)
        self.assertEqual(body, original)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response

    def diagnostic(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['extension'], 'greenblue.dataset-lineage-verification.rfc1')
        self.assertEqual(body['approval_status'], 'INTERNAL_REVIEW')
        self.assertFalse(body['present_in_upstream_openapi'])
        self.assertEqual(body['evaluation_scope'], 'CURRENT_LOCAL_ASSET_CHECK_NOT_EXECUTION_AUTHORIZATION')
        start = datetime.fromisoformat(body['assessment_started_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(body['assessment_finished_at'].replace('Z', '+00:00'))
        self.assertIsNotNone(start.tzinfo); self.assertLessEqual(start, end)
        diagnostic = body['diagnostic']
        for envelope in (body, diagnostic):
            for field in ('authorization_verified', 'execution_authorized', 'scientific_approval'):
                self.assertIs(envelope[field], False)
        self.assertEqual(diagnostic['network_requests'], 0); self.assertEqual(diagnostic['source_files_written'], 0)
        encoded = json.dumps(body)
        for secret in ('PRIVATE-ASSET', 'PRIVATE-QUALITY', 'PRIVATE-CREDENTIAL', str(self.store.root), 'artifact_uri', 'source_uri'):
            self.assertNotIn(secret, encoded)
        return diagnostic

    def error(self, response, code, status):
        self.assertEqual(response.status_code, status, response.text)
        app_fixtures.GmaisApiTests().validate('error.schema.json', response.json())
        self.assertEqual(response.json()['error']['code'], code)
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_public_transitive_and_distinct_fixed_versions_are_current_checks(self):
        first = self.fixture.dataset('http-temporal', version='1')
        second = self.fixture.dataset('http-temporal', version='2', parents=[first])
        result = self.diagnostic(self.verify(self.request(second)))
        self.assertTrue(result['lineage_integrity_verified']); self.assertTrue(result['current_assets_revalidated'])
        self.assertEqual(result['status'], 'INTEGRITY_VERIFIED')
        self.assertEqual({node['version'] for node in result['nodes']}, {'1', '2'})

    def test_invalid_body_is_400_before_registry_or_hash_work(self):
        cases = [None, [], {}, {'root_ref': dict(self.root, uri='PRIVATE-URL')},
                 self.request(sha='unknown'), {'root_ref': dict(self.root, sha256='A' * 64)},
                 self.request(max_depth=True), self.request(max_nodes=False), self.request(max_depth=-1),
                 self.request(max_depth=65), self.request(max_nodes=0), self.request(max_nodes=1025),
                 {'root_ref': dict(self.root, id=123)}, {'root_ref': dict(self.root, version='')}]
        for value in cases:
            with self.subTest(value=value), patch('app.dataset_lineage_api.verify_dataset_lineage', side_effect=AssertionError('무효 요청이 코어를 호출했습니다.')) as core:
                response = self.client.post('/v1/datasets/lineage/verify', json=value)
                self.error(response, 'INVALID_REQUEST', 400)
                self.assertNotIn('PRIVATE-URL', response.text)
                core.assert_not_called()
        response = self.client.post('/v1/datasets/lineage/verify', content='{"root_ref":bad PRIVATE-RAW-PATH', headers={'Content-Type':'application/json'})
        self.error(response, 'INVALID_REQUEST', 400); self.assertNotIn('PRIVATE-RAW-PATH', response.text)

    def test_missing_wrong_hash_and_dynamic_versions_return_blocked_diagnostics(self):
        for ref, code in ((dict(self.root, id='http-missing'), 'DATASET_VERSION_NOT_FOUND'),
                          (dict(self.root, sha256='b' * 64), 'LINEAGE_INTEGRITY_FAILED'),
                          (dict(self.root, version='latest'), 'LINEAGE_REF_NOT_PINNED'),
                          (dict(self.root, version='current'), 'LINEAGE_REF_NOT_PINNED'),
                          (dict(self.root, version=' LATEST '), 'LINEAGE_REF_NOT_PINNED')):
            with self.subTest(ref=ref):
                result = self.diagnostic(self.verify(self.request(ref)))
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertIn(code, {issue['code'] for issue in result['blockers']})

    def test_restricted_root_and_parent_never_disclose_or_resolve_private_ancestors(self):
        hidden = self.fixture.dataset('http-undisclosed')
        restricted = self.fixture.dataset('http-private', parents=[hidden], access='CONFIDENTIAL')
        public = self.fixture.dataset('http-public', parents=[restricted])
        for ref in (restricted, public):
            with self.subTest(ref=ref), patch.object(self.store, 'get', wraps=self.store.get) as lookup:
                response = self.verify(self.request(ref))
                result = self.diagnostic(response)
                self.assertIn('LINEAGE_ACL_NOT_IMPLEMENTED', {issue['code'] for issue in result['blockers']})
                self.assertNotIn(hidden['id'], response.text)
                self.assertEqual(len(lookup.call_args_list), 1 if ref == restricted else 2)

    def test_same_request_rechecks_asset_changes_instead_of_replaying_success(self):
        first = self.diagnostic(self.verify())
        self.assertTrue(first['lineage_integrity_verified'])
        (self.store.root / 'PRIVATE-ASSET-http-root-1.bin').write_bytes(b'changed since previous check')
        second = self.diagnostic(self.verify())
        self.assertFalse(second['lineage_integrity_verified'])
        self.assertIn('LINEAGE_INTEGRITY_FAILED', {issue['code'] for issue in second['blockers']})

    def test_depth_and_node_limits_are_forwarded_and_enforced(self):
        parent = self.fixture.dataset('http-parent')
        child = self.fixture.dataset('http-child', parents=[parent])
        for limits, code in (({'max_depth': 0}, 'LINEAGE_DEPTH_LIMIT'), ({'max_nodes': 1}, 'LINEAGE_NODE_LIMIT')):
            result = self.diagnostic(self.verify(self.request(child, **limits)))
            self.assertIn(code, {issue['code'] for issue in result['blockers']})
        result = self.diagnostic(self.verify(self.request(child, max_depth=1, max_nodes=2)))
        self.assertTrue(result['lineage_integrity_verified'])

    def test_cycles_conflicting_hashes_and_missing_parent_keep_core_blockers(self):
        a, b = self.fixture.ref('http-a'), self.fixture.ref('http-b')
        self.fixture.dataset('http-a', parents=[b]); self.fixture.dataset('http-b', parents=[a])
        parent = self.fixture.dataset('http-parent')
        conflicting = self.fixture.dataset('http-conflict', parents=[parent, dict(parent, sha256='c' * 64)])
        missing = self.fixture.dataset('http-missing-parent', parents=[self.fixture.ref('not-registered-parent')])
        for root, code in ((a, 'LINEAGE_CYCLE'), (conflicting, 'LINEAGE_REFERENCE_CONFLICT'),
                           (missing, 'DATASET_VERSION_NOT_FOUND')):
            with self.subTest(code=code):
                result = self.diagnostic(self.verify(self.request(root)))
                self.assertFalse(result['lineage_integrity_verified'])
                self.assertIn(code, {issue['code'] for issue in result['blockers']})

    def test_core_structured_registry_failure_stays_a_sanitized_blocked_diagnostic(self):
        import sqlite3
        with patch.object(self.store, 'get', side_effect=sqlite3.DatabaseError('PRIVATE-DATABASE-PATH')):
            response = self.verify()
        result = self.diagnostic(response)
        self.assertIn('DATASET_REGISTRY_UNAVAILABLE', {issue['code'] for issue in result['blockers']})
        self.assertNotIn('PRIVATE-DATABASE-PATH', response.text)

    def test_projection_removes_nested_sensitive_extensions(self):
        from app.dataset_lineage import verify_dataset_lineage
        core = verify_dataset_lineage(self.store, **dict(dataset_id=self.root['id'], version=self.root['version'], sha256=self.root['sha256']))
        secret = 'PRIVATE-UNEXPECTED-URI-CREDENTIAL'
        core['raw_manifest'] = secret; core['limits']['path'] = secret
        core['root_ref']['uri'] = secret; core['nodes'][0]['credential'] = secret
        with patch('app.dataset_lineage_api.verify_dataset_lineage', return_value=core):
            response = self.verify()
        self.diagnostic(response); self.assertNotIn(secret, response.text)

    def test_runtime_errors_and_inconsistent_core_results_fail_closed_without_details(self):
        from app.dataset_lineage import verify_dataset_lineage
        valid = verify_dataset_lineage(self.store, self.root['id'], self.root['version'], self.root['sha256'])
        for field, value in (('root_ref', dict(self.root, id='wrong-root')), ('execution_authorized', True), ('network_requests', 1), ('lineage_integrity_verified', False)):
            with self.subTest(field=field):
                bad = copy.deepcopy(valid); bad[field] = value
                with patch('app.dataset_lineage_api.verify_dataset_lineage', return_value=bad):
                    response = self.verify()
                self.error(response, 'RESOURCE_UNAVAILABLE', 503)
        with patch('app.dataset_lineage_api.verify_dataset_lineage', side_effect=RuntimeError('PRIVATE-CREDENTIAL-PATH')):
            response = self.verify()
        self.error(response, 'RESOURCE_UNAVAILABLE', 503); self.assertNotIn('PRIVATE-CREDENTIAL-PATH', response.text)

    def test_actual_main_app_inherits_token_dependency_and_preserves_legacy_namespace(self):
        self.store.put('datasets', {'id':'explicit-legacy-row', 'kind':'legacy-contract-fixture'})
        legacy = self.main_client.get('/api/datasets').json()
        before = self.fixture.files(self.store)
        with patch.dict(os.environ, {'GEOAI_API_TOKEN':'temporary-lineage-contract-token'}):
            denied = self.main_client.post('/v1/datasets/lineage/verify', json=self.request())
            self.assertEqual(denied.status_code, 401)
            accepted = self.main_client.post('/v1/datasets/lineage/verify', json=self.request(),
                headers={'Authorization':'Bearer temporary-lineage-contract-token'})
        self.diagnostic(accepted)
        self.assertEqual(legacy, self.main_client.get('/api/datasets').json())
        self.assertEqual(self.fixture.files(self.store), before)
        for kind in ('jobs', 'gmais_jobs', 'gmais_results', 'traces', 'gmais_traces', 'analyses', 'models', 'workflow_runs'):
            self.assertEqual(self.store.list(kind), [])
