"""저장 제출 진단 조회가 현재 재검증·권한 부여·민감정보 노출을 하지 않는지 확인한다."""
import copy
import json
import os
from unittest.mock import patch
import unittest

import test_gmais_api as fixtures
from app.job_snapshot import project_job_input_snapshot
from app.dataset_registry import register_version


class JobInputSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GmaisApiTests()
        self.fixture.setUp()
        self.client, self.root = self.fixture.client, self.fixture.root
        self.store = fixtures.main.store
        payload = self.fixture.request()
        self.fixture.register_input_fixture(payload)
        response, self.status = self.fixture.submit_blocked('snapshot-contract-fixture', payload)
        self.job_id = self.status['job_id']
        self.recorded = response.json()['error']['details']['input_resolution']
        self.original = self.store.get('gmais_jobs', self.job_id)
        self.uri = '/v1/jobs/' + self.job_id + '/input-resolution'

    def tearDown(self):
        self.fixture.tearDown()

    def files(self):
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def read(self, headers=None):
        before = self.files()
        original_get = self.store.get
        kinds = []
        def get(kind, identifier):
            kinds.append(kind)
            self.assertEqual(kind, 'gmais_jobs', '저장 Job 이외의 현재 Registry를 읽었습니다.')
            return original_get(kind, identifier)
        with patch.object(self.store, 'get', side_effect=get), patch.object(self.store, 'put', side_effect=AssertionError('GET wrote catalog')):
            with patch('app.dataset_registry.resolve_version', side_effect=AssertionError('GET revalidated registry')):
                with patch('app.job_inputs.resolve_job_inputs', side_effect=AssertionError('GET revalidated inputs')):
                    with patch('app.sdss_results.asset_sha256', side_effect=AssertionError('GET hashed current asset')):
                        response = self.client.get(self.uri, headers=headers)
        self.assertEqual(kinds, ['gmais_jobs'])
        self.assertEqual(before, self.files())
        return response

    def assert_envelope(self, body):
        self.assertEqual(set(body), {'extension', 'approval_status', 'job_id', 'trace_id', 'available', 'reason',
                                    'snapshot', 'current_files_revalidated', 'execution_authorized', 'scientific_approval'})
        self.assertEqual(body['extension'], 'greenblue.job-input-snapshot.rfc1')
        self.assertEqual(body['approval_status'], 'INTERNAL_REVIEW')
        self.assertEqual(body['job_id'], self.job_id)
        for field in ('current_files_revalidated', 'execution_authorized', 'scientific_approval'):
            self.assertIs(body[field], False)

    def test_recorded_snapshot_survives_asset_deletion_and_preserves_status_schema(self):
        (self.root / self.original['request']['input_refs'][0]['uri']).unlink()
        response = self.read()
        self.assertEqual(response.status_code, 200)
        body = response.json(); self.assert_envelope(body)
        self.assertTrue(body['available'])
        self.assertEqual(body['reason'], 'RECORDED_SNAPSHOT')
        self.assertEqual(body['snapshot'], self.recorded)
        status = self.client.get('/v1/jobs/' + self.job_id).json()
        self.fixture.validate('job-status.schema.json', status)
        self.assertEqual(status, self.status)
        self.assertEqual(self.store.get('gmais_jobs', self.job_id), self.original)
        self.assertEqual(self.store.list('gmais_results'), [])

    def test_legacy_without_snapshot_is_explicit_and_does_not_revalidate(self):
        job = copy.deepcopy(self.original); job.pop('input_resolution')
        self.store.put('gmais_jobs', job)
        response = self.read()
        self.assertEqual(response.status_code, 200)
        body = response.json(); self.assert_envelope(body)
        self.assertFalse(body['available'])
        self.assertEqual(body['reason'], 'LEGACY_SNAPSHOT_NOT_RECORDED')
        self.assertIsNone(body['snapshot'])

    def test_missing_job_uses_existing_error_contract(self):
        response = self.client.get('/v1/jobs/not-existing-snapshot-job/input-resolution')
        self.assertEqual(response.status_code, 404)
        self.fixture.validate('error.schema.json', response.json())
        self.assertEqual(response.json()['error']['code'], 'JOB_NOT_FOUND')

    def test_nested_extensions_are_removed_and_approval_fields_are_forced_false(self):
        job = copy.deepcopy(self.original)
        secret = 'PRIVATE-SIGNED-URL-AND-CREDENTIAL'
        job['request']['parameters'] = {'api_key': secret}
        snapshot = job['input_resolution']; snapshot['credential'] = secret
        snapshot.update(ready_for_execution=True, scientific_approval=True, status='BLOCKED')
        entry = snapshot['resolved'][0]
        entry.update(authorization_verified=True, status='BLOCKED', quality_status='RAW', blocker_codes=['INPUT_QUALITY_NOT_VALIDATED'],
                     uri=secret, path=secret, internal_exception=secret)
        snapshot['blockers'] = [{'input_index': 0, 'code': 'INPUT_QUALITY_NOT_VALIDATED', 'signed_url': secret}]
        self.store.put('gmais_jobs', job)
        body = self.read().json(); self.assert_envelope(body)
        self.assertTrue(body['available'])
        self.assertNotIn(secret, json.dumps(body))
        self.assertFalse(body['snapshot']['ready_for_execution'])
        self.assertFalse(body['snapshot']['scientific_approval'])
        self.assertFalse(body['snapshot']['resolved'][0]['authorization_verified'])
        for field in ('request', 'uri', 'path', 'credential', 'internal_exception', 'signed_url'):
            self.assertNotIn('"' + field + '"', json.dumps(body))

    def test_corrupt_snapshot_types_metadata_indices_and_ref_identity_are_rejected(self):
        changes = [
            lambda s: s.update(schema_version=True), lambda s: s.update(scope='PRIVATE-SCOPE'),
            lambda s: s.update(evaluated_at='secret internal timestamp'), lambda s: s.update(resolved={}),
            lambda s: s.update(input_integrity_verified='true'), lambda s: s.update(network_requests=True),
            lambda s: s['resolved'][0].update(input_index=True), lambda s: s['resolved'][0].update(id='other'),
            lambda s: s['resolved'][0].update(version='2'), lambda s: s['resolved'][0].update(sha256='a' * 64),
            lambda s: s['resolved'][0].update(integrity_verified='true'),
            lambda s: s.update(blockers=[{'input_index': 0, 'code': 'INPUT_INTEGRITY_FAILED'}]),
            lambda s: s.update(status='APPROVED'), lambda s: s.update(source_files_written=1),
        ]
        for change in changes:
            with self.subTest(change=change):
                job = copy.deepcopy(self.original); change(job['input_resolution'])
                self.store.put('gmais_jobs', job)
                body = self.read().json(); self.assert_envelope(body)
                self.assertFalse(body['available'])
                self.assertEqual(body['reason'], 'SNAPSHOT_INVALID')
                self.assertIsNone(body['snapshot'])

    def test_corrupt_job_trace_agent_and_job_identity_are_rejected_without_echo(self):
        for target in ('trace', 'agent', 'job'):
            with self.subTest(target=target):
                job = copy.deepcopy(self.original)
                field = {'trace': 'trace_id', 'agent': 'agent_id', 'job': 'job_id'}[target]
                job['status'][field] = 'PRIVATE-CORRUPTED-IDENTITY'
                self.store.put('gmais_jobs', job)
                body = self.read().json(); self.assert_envelope(body)
                self.assertEqual(body['trace_id'], 'unknown')
                self.assertEqual(body['reason'], 'SNAPSHOT_INVALID')
                self.assertNotIn('PRIVATE-CORRUPTED-IDENTITY', json.dumps(body))

    def test_quality_and_acl_contradictions_cannot_claim_verified_snapshot(self):
        for field, value in (('quality_status', 'RAW'), ('quality_status', 'REJECTED'),
                             ('access_class', 'RESTRICTED'), ('access_class', 'CONFIDENTIAL')):
            with self.subTest(field=field,value=value):
                job = copy.deepcopy(self.original)
                job['input_resolution']['resolved'][0][field] = value
                self.store.put('gmais_jobs', job)
                body = self.read().json()
                self.assertEqual(body['reason'], 'SNAPSHOT_INVALID')
                self.assertIsNone(body['snapshot'])

    def test_impossible_empty_failure_and_dynamic_verified_snapshots_are_rejected(self):
        job = copy.deepcopy(self.original)
        job['input_resolution']['resolved'][0].update(integrity_verified=False, status='BLOCKED')
        job['input_resolution']['input_integrity_verified'] = False
        self.store.put('gmais_jobs', job)
        self.assertEqual(self.read().json()['reason'], 'SNAPSHOT_INVALID')
        job = copy.deepcopy(self.original)
        job['request']['input_refs'][0]['version'] = 'latest'
        job['input_resolution']['resolved'][0]['version'] = 'latest'
        self.store.put('gmais_jobs', job)
        self.assertEqual(self.read().json()['reason'], 'SNAPSHOT_INVALID')

    def test_real_source_generated_missing_dynamic_conflict_and_acl_snapshots_remain_readable(self):
        refs_for_quality = []
        template = copy.deepcopy(self.store.list('dataset_versions')[0]['manifest'])
        for suffix, quality, access in (('raw', 'RAW', 'PUBLIC'), ('private', 'VALIDATED', 'CONFIDENTIAL')):
            manifest = dict(template, dataset_id='snapshot-source-' + suffix, quality_status=quality, access_class=access)
            register_version(self.store, manifest)
            refs_for_quality.append({'id': manifest['dataset_id'], 'version': manifest['version'], 'sha256': manifest['sha256']})
        variants = [
            [dict(self.original['request']['input_refs'][0], id='missing-fixture')],
            [dict(self.original['request']['input_refs'][0], version='latest')],
            [self.original['request']['input_refs'][0], dict(self.original['request']['input_refs'][0], sha256='b' * 64)],
        ] + [[ref] for ref in refs_for_quality]
        for index, refs in enumerate(variants):
            with self.subTest(index=index):
                payload = copy.deepcopy(self.original['request']); payload['input_refs'] = refs
                response, status = self.fixture.submit_blocked('real-source-snapshot-' + str(index), payload)
                self.uri = '/v1/jobs/' + status['job_id'] + '/input-resolution'
                body = self.read().json()
                self.assertTrue(body['available'])
                self.assertEqual(body['snapshot'], response.json()['error']['details']['input_resolution'])

    def test_missing_and_null_snapshot_are_distinct(self):
        job = copy.deepcopy(self.original); job['input_resolution'] = None
        self.store.put('gmais_jobs', job)
        body = self.read().json()
        self.assertEqual(body['reason'], 'SNAPSHOT_INVALID')
        self.assertIsNone(body['snapshot'])

    def test_output_is_detached_from_stored_object(self):
        original = copy.deepcopy(self.original)
        projected = project_job_input_snapshot(original, self.job_id)
        projected['snapshot']['resolved'][0]['blocker_codes'].append('INPUT_INTEGRITY_FAILED')
        self.assertEqual(original, self.original)

    def test_new_route_inherits_existing_token_dependency(self):
        with patch.dict(os.environ, {'GEOAI_API_TOKEN': 'temporary-contract-test-token'}):
            denied = self.client.get(self.uri)
            self.assertEqual(denied.status_code, 401)
            self.assertNotIn('RECORDED_SNAPSHOT', denied.text)
            allowed = self.read(headers={'Authorization': 'Bearer temporary-contract-test-token'})
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()['available'])
