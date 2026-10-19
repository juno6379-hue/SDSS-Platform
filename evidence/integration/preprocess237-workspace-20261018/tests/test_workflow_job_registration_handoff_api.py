import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from app.workflow_job_request_handoff_api import create_workflow_job_request_handoff_router, parse_full_job_handoff_request
from app.workflow_job_registration_handoff import compare_workflow_job_registration_handoff
from test_workflow_job_registration_handoff import registered_fixture
from test_workflow_job_request_handoff_api import envelope, raw, PATH, MODULE

CORE = 'app.workflow_job_registration_handoff.'
ORIGINAL = Path(__file__).resolve().parents[1] / 'evidence/integration/full-job-registration-api-original-20261017.py'
ORIGINAL_SHA = '48dcd410e6e259d1c0d3537cb4cb9585c2f0c8c836ee35a8a9f388197656a98d'


def version_two(workflow=None, job=None):
    if workflow is None and job is None:
        workflow, job = registered_fixture()
    return dict(envelope(workflow, job), contract_version=2)


class WorkflowJobRegistrationApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(create_workflow_job_request_handoff_router())
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def post(self, value=None):
        return self.client.post(PATH, content=raw(version_two() if value is None else value))

    def assert_error(self, response, status, code):
        messages = {'INVALID_REQUEST': 'Invalid full Job handoff request.',
            'REQUEST_TOO_LARGE': 'Full Job handoff request exceeds limits.',
            'RESOURCE_UNAVAILABLE': 'Full Job handoff comparison is unavailable.'}
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.json(), {'error': {'code': code, 'message': messages[code], 'retryable': False}})
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_opt_in_wrapper_exact_and_raw_sha_private(self):
        body = raw(version_two())
        response = self.client.post(PATH, content=body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(set(result), {'extension', 'approval_status', 'present_in_upstream_openapi', 'request_sha256', 'result'})
        self.assertEqual(result['extension'], 'greenblue.workflow-full-job-input-handoff.rfc2')
        self.assertEqual(result['approval_status'], 'INTERNAL_REVIEW')
        self.assertIs(result['present_in_upstream_openapi'], False)
        self.assertEqual(result['request_sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(result['result']['status'], 'MATCH')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        for secret in ('private-node', 'private-purpose', 'file:///private', 'private-trace'):
            self.assertNotIn(secret, response.text)

    def test_exact_integer_version_and_exact_five_keys(self):
        for version in (True, False, 1, 0, 3, 2.0, '2', None, [], {}):
            value = version_two()
            value['contract_version'] = version
            self.assert_error(self.post(value), 400, 'INVALID_REQUEST')
        for mutate in (lambda e: e.update(extra=1), lambda e: e.pop('selected_node_id')):
            value = version_two()
            mutate(value)
            self.assert_error(self.post(value), 400, 'INVALID_REQUEST')

    def test_v1_entire_response_identical_to_pinned_original_router(self):
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), ORIGINAL_SHA)
        spec = importlib.util.spec_from_file_location('app._full_job_original94', ORIGINAL)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        app = FastAPI()
        app.include_router(original.create_workflow_job_request_handoff_router())
        with TestClient(app) as client:
            cases = [envelope(), envelope(*registered_fixture())]
            for mutate in (lambda j: j.pop('aoi'), lambda j: j['input_refs'][0].update(role='changed'),
                           lambda j: j.update(time_range={'start': 'not-a-date'})):
                w, j = registered_fixture()
                mutate(j)
                cases.append(envelope(w, j))
            bodies = [raw(value) for value in cases] + [b'{}', b'\xff', b'{"x":NaN}']
            for body in bodies:
                previous = client.post(PATH, content=body)
                actual = self.client.post(PATH, content=body)
                self.assertEqual((actual.status_code, dict(actual.headers), actual.content),
                                 (previous.status_code, dict(previous.headers), previous.content))
                if actual.status_code == 200:
                    self.assertEqual(actual.json()['extension'], 'greenblue.workflow-full-job-input-handoff.rfc1')

    def test_axis_unknown_unregistered_and_not_run_are_200_blocked(self):
        unknown = envelope()
        unknown['contract_version'] = 2
        w, j = registered_fixture()
        for target in (w['nodes'][0], j): target['capability_id'] = 'missing'
        wrong = version_two(w, j)
        w, j = registered_fixture()
        j['time_range'] = {'start': '2026-02-30T00:00:00Z'}
        for value, expected in ((unknown, 'AGENT_UNKNOWN'), (wrong, 'CAPABILITY_UNREGISTERED'), (version_two(w, j), 'NOT_RUN')):
            response = self.post(value)
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()['result']
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertEqual(result['local_manifest_registration']['status'], expected)
            self.assertEqual(result['local_manifest_registration']['checked'], expected != 'NOT_RUN')

    def test_strict_inner_duplicate_decimal_finite_unicode_and_limits_retained(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}', '{"a":1e-999}', '"\\ud800"'):
            value = version_two()
            value['full_job_request_json'] = text
            self.assert_error(self.post(value), 400, 'INVALID_REQUEST')
        for text in ('[' * 25 + '0' + ']' * 25, ' ' * 524289, '{"parameters":{"x":' + '1' * 129 + '}}'):
            value = version_two()
            value['full_job_request_json'] = text
            self.assert_error(self.post(value), 413, 'REQUEST_TOO_LARGE')
        value = version_two()
        value['full_job_request_json'] = value['full_job_request_json'].replace('106.1', '1.061e2')
        response = self.post(value)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['result']['status'], 'MATCH')
        body = raw(version_two())
        self.assert_error(self.client.post(PATH, content=body[:-1] + b',"contract_version":2}'), 400, 'INVALID_REQUEST')

    def test_corrupt_outer_axis_and_inner_results_are_safe_503(self):
        value = version_two()
        e, w, j = parse_full_job_handoff_request(raw(value))
        base = compare_workflow_job_registration_handoff(w, e['pinned_workflow_request_sha256'], e['selected_node_id'], j)
        mutations = (lambda r: r.update(schema_version=True), lambda r: r.update(extra='private'),
            lambda r: r.update(status='BLOCKED'), lambda r: r.update(actual_capability_supported=True),
            lambda r: r.update(institution_acl_verified=True), lambda r: r.update(execution_authorized=True),
            lambda r: r['local_manifest_registration'].update(status='NOT_RUN'),
            lambda r: r['local_manifest_registration'].update(checked=1),
            lambda r: r['local_manifest_registration'].update(source='private'),
            lambda r: r['local_manifest_registration'].update(raw_manifest={}),
            lambda r: r['full_job_comparison'].update(full_job_request_sha256='b' * 64),
            lambda r: r['full_job_comparison'].update(agent_capability_verified=True))
        for mutate in mutations:
            result = copy.deepcopy(base)
            mutate(result)
            with patch(MODULE + 'compare_workflow_job_registration_handoff', return_value=result):
                self.assert_error(self.post(value), 503, 'RESOURCE_UNAVAILABLE')

    def test_forged_registered_observation_is_503_even_with_consistent_outer_match(self):
        value = envelope()
        value['contract_version'] = 2
        e, w, j = parse_full_job_handoff_request(raw(value))
        result = compare_workflow_job_registration_handoff(w, e['pinned_workflow_request_sha256'], e['selected_node_id'], j)
        result.update(status='MATCH')
        result['local_manifest_registration']['status'] = 'REGISTERED'
        with patch(MODULE + 'compare_workflow_job_registration_handoff', return_value=result):
            self.assert_error(self.post(value), 503, 'RESOURCE_UNAVAILABLE')

    def test_manifest_and_core_exceptions_or_resource_errors_are_private_503(self):
        for manifests in (None, [None], [{}], [{'agent_id': 'x', 'capabilities': [{}]}]):
            with patch('app.gmais_api._agent_manifests', return_value=manifests):
                self.assert_error(self.post(), 503, 'RESOURCE_UNAVAILABLE')
        with patch('app.gmais_api._agent_manifests', side_effect=RuntimeError('private/path')):
            self.assert_error(self.post(), 503, 'RESOURCE_UNAVAILABLE')
        with patch('app.workflow_job_request_handoff._job_request_validator', side_effect=OSError('private/schema')):
            self.assert_error(self.post(), 503, 'RESOURCE_UNAVAILABLE')

    def test_worker_one_comparator_static_lookup_only_and_legacy_independent(self):
        from app.workflow_job_request_handoff import compare_workflow_job_request_handoff
        from app import gmais_api
        manifests = gmais_api._agent_manifests()
        with patch(CORE + 'compare_workflow_job_request_handoff', wraps=compare_workflow_job_request_handoff) as comparator, \
             patch('app.gmais_api._agent_manifests', return_value=manifests) as lookup, \
             patch('app.store.Store.get', side_effect=AssertionError('no Store')):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(comparator.call_count, 1)
        self.assertEqual(lookup.call_count, 2)
        with patch('app.gmais_api._agent_manifests', side_effect=AssertionError('v1 no observation')):
            self.assertEqual(self.post(envelope()).status_code, 200)

    def test_v2_inherits_auth_dependency(self):
        def auth(authorization: str | None = Header(default=None)):
            if authorization != 'Bearer test': raise HTTPException(status_code=401)
        app = FastAPI(dependencies=[Depends(auth)])
        app.include_router(create_workflow_job_request_handoff_router())
        with TestClient(app) as client:
            self.assertEqual(client.post(PATH, content=raw(version_two())).status_code, 401)
            self.assertEqual(client.post(PATH, content=raw(version_two()), headers={'Authorization': 'Bearer test'}).status_code, 200)
