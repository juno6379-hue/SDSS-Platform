"""New bounded transport, independent typed observation checks, no operating main."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient

from app import gmais_api
from app import workflow_job_model_record_handoff_api as api
from app import workflow_job_model_record_handoff as chain
from app import model_reference_record_comparison as identity_core
from app import workflow_job_request_handoff_api as legacy
from app.store import Store
from test_workflow_job_request_handoff_api import envelope, raw
from test_workflow_job_model_record_handoff import fixture


PATH = '/v1/workflows/full-job-model-record-handoff'
OLD_PATH = '/v1/workflows/full-job-input-handoff'
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_MAIN = ROOT / 'evidence/integration/workflow-model-record-api-original-main-20261017.py'
ORIGINAL_SHA = '9e68da6ce85c43cb804999962fb7d894f17f3047a45870f95f3e2e853aca4f28'
MISSING = object()


def request_value(record=MISSING):
    workflow, job, candidate = fixture()
    result = envelope(workflow, job)
    if record is not MISSING: result['model_record_json'] = json.dumps(record, ensure_ascii=True)
    return result


def matching_request():
    return request_value(fixture()[2])


class WorkflowJobModelRecordHandoffApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(api.create_workflow_job_model_record_handoff_router())
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def post(self, value=None, body=None):
        return self.client.post(PATH, content=body if body is not None else raw(matching_request() if value is None else value),
                                headers={'Content-Type': 'application/json'})

    def error(self, response, status, code):
        messages = {'INVALID_REQUEST': 'Invalid Workflow model-record handoff request.',
            'REQUEST_TOO_LARGE': 'Workflow model-record handoff request exceeds limits.',
            'RESOURCE_UNAVAILABLE': 'Workflow model-record observation is unavailable.'}
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.json(), {'error': {'code': code, 'message': messages[code], 'retryable': False}})
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_match_raw_body_sha_wrapper_exact_privacy_and_no_store(self):
        body = raw(matching_request())
        with patch.object(Store, '__init__', side_effect=AssertionError('no Store factory')), \
             patch.object(Store, 'get', side_effect=AssertionError('no Store.get')), \
             patch.object(Store, 'list', side_effect=AssertionError('no Store.list')), \
             patch.object(Store, 'put', side_effect=AssertionError('no Store.put')):
            response = self.post(body=body)
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(set(value), {'extension', 'approval_status', 'present_in_upstream_openapi', 'request_sha256', 'result'})
        self.assertEqual(value['extension'], 'greenblue.workflow-full-job-model-record-handoff.rfc1')
        self.assertEqual(value['approval_status'], 'INTERNAL_REVIEW')
        self.assertIs(value['present_in_upstream_openapi'], False)
        self.assertEqual(value['request_sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(value['result']['status'], 'MODEL_REFERENCE_OBSERVED')
        self.assertEqual(value['result']['model_reference_comparison']['status'], 'MATCH_UNVERIFIED')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        for secret in ('private-model', 'file:///private', 'private-node', 'private-purpose', ' v2 ', 'a' * 64):
            self.assertNotIn(secret, response.text)

    def test_worker_same_thread_producer_once_independent103_once_and100_twice(self):
        threads = []
        original_producer = api.compare_workflow_job_model_record_handoff
        original_validator = api.validate_full_job_handoff_response
        original_independent = api.compare_model_reference_record
        def producer(*args): threads.append(('producer', threading.current_thread().name)); return original_producer(*args)
        def validator(*args): threads.append(('validator', threading.current_thread().name)); return original_validator(*args)
        def independent(*args): threads.append(('independent', threading.current_thread().name)); return original_independent(*args)
        with patch.object(api, 'compare_workflow_job_model_record_handoff', side_effect=producer) as produced, \
             patch.object(api, 'validate_full_job_handoff_response', side_effect=validator), \
             patch.object(api, 'compare_model_reference_record', side_effect=independent) as independently, \
             patch.object(chain, 'compare_model_reference_record', wraps=chain.compare_model_reference_record) as production103, \
             patch.object(chain, 'compare_workflow_job_request_handoff', wraps=chain.compare_workflow_job_request_handoff) as original89, \
             patch.object(identity_core, 'inspect_model_registration_provenance', wraps=identity_core.inspect_model_registration_provenance) as inspected:
            response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((produced.call_count, original89.call_count, production103.call_count, independently.call_count, inspected.call_count), (1, 1, 1, 1, 2))
        self.assertEqual(len({thread for _, thread in threads}), 1)
        self.assertIn('worker', threads[0][1].lower())
        result = response.json()['result']
        self.assertEqual(result['model_comparison_calls'], 1)
        self.assertEqual(result['model_reference_comparison']['inspection_calls'], 1)

    def test_record_omitted_json_null_and_scalar_are_distinct_transport_cases(self):
        for value in (request_value(), request_value(None)):
            response = self.post(value)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['result']['model_reference_comparison']['status'], 'RECORD_NOT_PROVIDED')
        for record in (True, [], 1.5, {}):
            response = self.post(request_value(record))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['result']['model_reference_comparison']['status'], 'RECORD_INVALID')
        for record in (None, True, {}, '', '  '):
            value = matching_request(); value['model_record_json'] = record
            self.error(self.post(value), 400, 'INVALID_REQUEST')

    def test_absent_blocked_conflict_and_all_intrinsic_states_stay_200(self):
        value = matching_request(); job = json.loads(value['full_job_request_json']); del job['model_ref']
        value['full_job_request_json'] = json.dumps(job)
        response = self.post(value)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result']['status'], 'MODEL_REFERENCE_ABSENT')
        for mutate in (lambda job: job.update(time_range={'start': 'not-a-date'}),
                       lambda job: job.update(model_ref=None), lambda job: job['model_ref'].update(role=' ')):
            value = matching_request(); job = json.loads(value['full_job_request_json']); mutate(job)
            value['full_job_request_json'] = json.dumps(job); response = self.post(value)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['result']['status'], 'HANDOFF_BLOCKED')
        records = [{'id': 'other-model'}, {'id': 'private-model'}]
        invalid = fixture()[2]; invalid['model_version_declaration'] = None; records.append(invalid)
        conflict = fixture()[2]; conflict['checkpoint_sha256'] = 'c' * 64; records.append(conflict)
        unknown = fixture()[2]; del unknown['training_report_sha256']; records.append(unknown)
        for record in records:
            response = self.post(request_value(record))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['result']['status'], 'MODEL_REFERENCE_OBSERVED')
        value = matching_request(); job = json.loads(value['full_job_request_json']); job['model_ref'].update(version='different', sha256='c' * 64)
        value['full_job_request_json'] = json.dumps(job); response = self.post(value)
        self.assertEqual(response.json()['result']['model_reference_comparison']['issue']['code'], 'VERSION_MISMATCH')

    def test_record_is_strict_parsed_even_when_89_would_block(self):
        value = matching_request(); value['full_job_request_json'] = '{}'
        with patch.object(api, 'compare_workflow_job_model_record_handoff', side_effect=AssertionError('no core')) as core:
            for text in ('', ' ', '{"x":1,"x":2}', '{"x":NaN}', '{"x":1e-999}', '"\\ud800"'):
                value['model_record_json'] = text
                self.error(self.post(value), 400, 'INVALID_REQUEST')
            value['model_record_json'] = '[' * 25 + '0' + ']' * 25
            self.error(self.post(value), 413, 'REQUEST_TOO_LARGE')
        core.assert_not_called()

    def test_strict_duplicate_utf8_envelope_keys_versions_and_workflow_float(self):
        value = matching_request(); body = raw(value)
        bodies = [body[:-1] + b',"selected_node_id":"private-node"}', b'\xff', b'{}', b'[]']
        for key in ('workflow_request_json', 'full_job_request_json', 'model_record_json'):
            changed = copy.deepcopy(value); changed[key] = '{"x":1,"x":2}'; bodies.append(raw(changed))
        for body in bodies: self.error(self.post(body=body), 400, 'INVALID_REQUEST')
        for changes in ({'contract_version': 2}, {'unknown': True}, {'selected_node_id': ''}, {'pinned_workflow_request_sha256': 'bad'}):
            self.error(self.post(dict(value, **changes)), 400, 'INVALID_REQUEST')
        value['workflow_request_json'] = '{"x":1.5}'
        self.error(self.post(value), 400, 'INVALID_REQUEST')

    def test_body_inner_utf8_depth_string_and_numeric_budgets(self):
        self.error(self.post(body=b' ' * (api.MAX_BODY_BYTES + 1)), 413, 'REQUEST_TOO_LARGE')
        for key in ('workflow_request_json', 'full_job_request_json', 'model_record_json'):
            value = matching_request(); value[key] = ' ' * (api.MAX_INNER_BYTES + 1)
            self.error(self.post(value), 413, 'REQUEST_TOO_LARGE')
        value = matching_request(); value['model_record_json'] = '가' * 180000
        self.error(self.post(value), 413, 'REQUEST_TOO_LARGE')
        for text in ('"' + 'x' * 4097 + '"', '[' * 25 + '0' + ']' * 25, '{"x":' + '1' * 129 + '}'):
            value = matching_request(); value['model_record_json'] = text
            self.error(self.post(value), 413, 'REQUEST_TOO_LARGE')
        for text in ('{"x":9007199254740992}', '{"x":1e999}', '{"x":1e-999}'):
            value = matching_request(); value['model_record_json'] = text
            self.error(self.post(value), 400, 'INVALID_REQUEST')

    def test_decimal_record_and_job_are_supported_without_source_normalization(self):
        for token in ('1.0', '1e0', '-0.0', '1e-7', '5e-324', '0e-999'):
            value = matching_request()
            record = json.loads(value['model_record_json']); record['unused'] = 'TOKEN'
            value['model_record_json'] = json.dumps(record).replace('"TOKEN"', token)
            job = json.loads(value['full_job_request_json']); job['parameters']['number'] = 'TOKEN'
            value['full_job_request_json'] = json.dumps(job).replace('"TOKEN"', token)
            before = copy.deepcopy(value); response = self.post(value)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(value, before)
        source = raw(matching_request()); changed = source + b'\n'
        self.assertNotEqual(self.post(body=source).json()['request_sha256'], self.post(body=changed).json()['request_sha256'])

    def test_outer_and_inner89_corrupt_outputs_are_safe503(self):
        value = matching_request(); e, w, j, r = api.parse_workflow_model_record_request(raw(value))
        base = chain.compare_workflow_job_model_record_handoff(w, e['pinned_workflow_request_sha256'], e['selected_node_id'], j, r)
        mutations = (lambda result: result.update(schema_version=True), lambda result: result.update(extra='private'),
            lambda result: result.update(status='MODEL_REFERENCE_ABSENT'), lambda result: result.update(identity_projection_performed=1),
            lambda result: result.update(model_comparison_calls=True), lambda result: result.update(authority_verified=0),
            lambda result: result['full_job_comparison'].update(model_verified=0),
            lambda result: result['full_job_comparison'].update(full_job_request_sha256='c' * 64))
        for mutate in mutations:
            result = copy.deepcopy(base); mutate(result)
            with patch.object(api, 'compare_workflow_job_model_record_handoff', return_value=result):
                self.error(self.post(value), 503, 'RESOURCE_UNAVAILABLE')

    def test_recursive_typed_comparison_rejects_nested100_bool_int_and_forged_fields(self):
        value = matching_request(); e, w, j, r = api.parse_workflow_model_record_request(raw(value))
        base = chain.compare_workflow_job_model_record_handoff(w, e['pinned_workflow_request_sha256'], e['selected_node_id'], j, r)
        mutations = (lambda result: result['model_reference_comparison'].update(inspection_calls=True),
            lambda result: result['model_reference_comparison'].update(model_verified=0),
            lambda result: result['model_reference_comparison']['record_provenance'].update(schema_version=True),
            lambda result: result['model_reference_comparison']['record_provenance'].update(declaration_present=1),
            lambda result: result['model_reference_comparison']['record_provenance'].update(authority_verified=0),
            lambda result: result['model_reference_comparison']['record_provenance'].update(extra='private'),
            lambda result: result['model_reference_comparison']['bindings'].update(version='MISMATCH'))
        for mutate in mutations:
            result = copy.deepcopy(base); mutate(result)
            with patch.object(api, 'compare_workflow_job_model_record_handoff', return_value=result):
                self.error(self.post(value), 503, 'RESOURCE_UNAVAILABLE')

    def test_independent_observation_variation_and_all_exceptions_are_safe503(self):
        with patch.object(api, 'compare_model_reference_record', return_value={'private': True}):
            self.error(self.post(), 503, 'RESOURCE_UNAVAILABLE')
        for target in ('parse_workflow_model_record_request', 'compare_workflow_job_model_record_handoff',
                       'validate_full_job_handoff_response', 'compare_model_reference_record'):
            with patch.object(api, target, side_effect=RuntimeError('C:/private/path')):
                self.error(self.post(), 503, 'RESOURCE_UNAVAILABLE')
        with patch('app.workflow_job_request_handoff._job_request_validator', side_effect=OSError('private-schema')):
            self.error(self.post(), 503, 'RESOURCE_UNAVAILABLE')

    def test_blocked_and_absent_do_not_independently_reinspect103(self):
        for value in (dict(matching_request(), full_job_request_json='{}'), envelope()):
            with patch.object(api, 'compare_model_reference_record', side_effect=AssertionError('no independent comparison')) as compare:
                response = self.post(value)
            self.assertEqual(response.status_code, 200, response.text)
            compare.assert_not_called()

    def test_cold_schema_read_warm_no_artifact_io_and_schema_count_remains_null(self):
        original = Path.read_text; reads = []
        def record(path, *args, **kwargs): reads.append(path.name); return original(path, *args, **kwargs)
        gmais_api._job_request_validator.cache_clear()
        try:
            with patch.object(Path, 'read_text', record):
                first = self.post(); second = self.post()
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(second.json(), first.json())
            self.assertEqual(reads, ['job-request.schema.json'])
            self.assertIsNone(first.json()['result']['full_job_comparison']['schema_files_read'])
            with TestClient(self.client.app) as client, \
                 patch.object(Path, 'open', side_effect=AssertionError('warm no file open')), \
                 patch('socket.create_connection', side_effect=AssertionError('no outbound connection')):
                response = client.post(PATH, content=raw(matching_request()))
            self.assertEqual(response.status_code, 200, response.text)
        finally:
            gmais_api._job_request_validator.cache_clear()

    def test_old_rfc1_and_rfc2_response_bytes_headers_and_parsers_are_unchanged(self):
        legacy_app = FastAPI(); legacy_app.include_router(legacy.create_workflow_job_request_handoff_router())
        combined = FastAPI(); combined.include_router(legacy.create_workflow_job_request_handoff_router()); combined.include_router(api.create_workflow_job_model_record_handoff_router())
        with TestClient(legacy_app) as before, TestClient(combined) as after:
            for value in (envelope(), dict(envelope(), contract_version=2), dict(envelope(), full_job_request_json='{}')):
                expected = before.post(OLD_PATH, content=raw(value)); actual = after.post(OLD_PATH, content=raw(value))
                self.assertEqual((actual.status_code, actual.content, dict(actual.headers)),
                                 (expected.status_code, expected.content, dict(expected.headers)))
        with self.assertRaises(ValueError): legacy.parse_full_job_handoff_request(raw(matching_request()))
        value = dict(matching_request(), contract_version=2)
        self.error(self.post(value), 400, 'INVALID_REQUEST')

    def test_main_wiring_only_two_ast_additions_and_real_auth_dependency(self):
        self.assertEqual(hashlib.sha256(ORIGINAL_MAIN.read_bytes()).hexdigest(), ORIGINAL_SHA)
        before = ast.parse(ORIGINAL_MAIN.read_text(encoding='utf-8-sig'))
        after = ast.parse((ROOT / 'backend/app/main.py').read_text(encoding='utf-8-sig'))
        # 116 adds only this explicit import/include pair; preserve the old 105 guard.
        authorized = ast.parse('from .lcluc_workflow_api import create_lcluc_workflow_router\n'
            'app.include_router(create_lcluc_workflow_router(lambda: store))\n').body
        for expected in authorized:
            matches = [node for node in after.body if ast.dump(node) == ast.dump(expected)]
            self.assertEqual(len(matches), 1)
            after.body.remove(matches[0])
        kept, additions, auth_app = [], [], []
        for node in after.body:
            is_import = isinstance(node, ast.ImportFrom) and node.module == 'workflow_job_model_record_handoff_api'
            is_include = (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'include_router'
                and len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Call)
                and isinstance(node.value.args[0].func, ast.Name) and node.value.args[0].func.id == 'create_workflow_job_model_record_handoff_router')
            (additions if is_import or is_include else kept).append(node)
            if isinstance(node, ast.FunctionDef) and node.name == 'authorized': auth_app.append(node)
            elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'app' for target in node.targets): auth_app.append(node)
        self.assertEqual(len(additions), 2); after.body = kept
        self.assertEqual(ast.dump(after), ast.dump(before))
        namespace = dict(FastAPI=FastAPI, Depends=Depends, Header=Header, Request=Request,
            HTTPException=HTTPException, os=os, secrets=secrets)
        exec(compile(ast.Module(body=auth_app, type_ignores=[]), 'isolated-auth', 'exec'), namespace)
        namespace['app'].include_router(api.create_workflow_job_model_record_handoff_router())
        with patch.dict(os.environ, {'GEOAI_API_TOKEN': 'isolated-token'}), TestClient(namespace['app']) as client, \
             patch.object(api, 'compare_workflow_job_model_record_handoff', wraps=api.compare_workflow_job_model_record_handoff) as core:
            self.assertEqual(client.post(PATH, content=raw(matching_request())).status_code, 401)
            core.assert_not_called()
            self.assertEqual(client.post(PATH, content=raw(matching_request()), headers={'Authorization': 'Bearer isolated-token'}).status_code, 200)
