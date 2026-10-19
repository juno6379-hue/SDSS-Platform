"""Synthetic declarations and isolated routers; no operating app or Job POST."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import gmais_api, workflow_job_request_handoff as handoff
from app import workflow_job_request_handoff_api as handoff_api
from app import workflow_job_registration_handoff as registration
from app.model_reference_contract import model_reference_issue
from app.workflow_node_input_handoff import _digest
import test_agent_capability_contract as previous
from test_schema_formats import job_fixture
from test_workflow_job_request_handoff import full_fixture
from test_workflow_job_request_handoff_api import envelope, raw, PATH


ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = (
    ('gmais', '78a39d0298113f6da4e67cb8bd2902b563f90276f938b19ed64e17be585bd802'),
    ('handoff', '3ab99c8b90f0aea185d2ff4d6339407ef646fdd859d27f432f3cc1b0f9f352e8'),
)


def model(**changes):
    return dict(id='private-model', version='v1', sha256='a' * 64, **changes)


class ModelReferenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name, expected_sha in ORIGINALS:
            path = ROOT / ('evidence/integration/model-ref-original-' + name + '-20261017.py')
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
                raise AssertionError('Original model contract evidence changed')
            spec = importlib.util.spec_from_file_location('app._model_ref_original_' + name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            setattr(cls, 'original_' + name, module)

    def exercise(self, module, path, body, replay=False):
        return previous.AgentCapabilityContractTests.exercise(self, module, path, body, replay=replay)

    def test_pure_valid_absent_and_immutable_without_io(self):
        values = [None, model(), model(role='model'), model(uri='not-a-normalized-uri')]
        values += [dict(id=' x ', version=' v1 ', role=' role ')]
        before = copy.deepcopy(values)
        with patch('builtins.open', side_effect=AssertionError('pure helper has no I/O')):
            for value in values:
                self.assertIsNone(model_reference_issue(value))
        self.assertEqual(values, before)

    def test_text_type_whitespace_control_surrogate_and_length_boundaries(self):
        for field in ('id', 'version', 'role'):
            for value in ('', ' ', '\t', '\n', 'x\x00', 'x\x1f', 'x\x7f', 'x\x80', 'x\x9f', '\ud800', 'a' * 257, None, 1, True, [], {}):
                ref = model(); ref[field] = value
                with self.subTest(field=field, value=repr(value)):
                    self.assertEqual(model_reference_issue(ref), 'MODEL_REFERENCE_INVALID')
            for value in ('a', 'a' * 256, '한국 모델'):
                ref = model(); ref[field] = value
                self.assertIsNone(model_reference_issue(ref))

    def test_aliases_only_are_stripped_casefolded_and_character_errors_win(self):
        for value in ('latest', 'current', 'LATEST', ' Current ', ' latest '):
            ref = model(); ref['version'] = value
            self.assertEqual(model_reference_issue(ref), 'MODEL_VERSION_NOT_PINNED')
            ref['role'] = ' '
            self.assertEqual(model_reference_issue(ref), 'MODEL_REFERENCE_INVALID')
        for value in ('v1', ' v1 ', 'latest-1', 'currently', '1.0.0'):
            ref = model(); ref['version'] = value
            self.assertIsNone(model_reference_issue(ref))
            self.assertEqual(ref['version'], value)

    def test_helper_does_not_enforce_sha_uri_unknown_key_or_resolve_version(self):
        for ref in (dict(id='m', version='v1'), dict(id='m', version='v1', sha256='bad', uri=1, unknown=True)):
            self.assertIsNone(model_reference_issue(ref))
        for ref in ({}, {'id': 'm'}, [], 'model', 1, True):
            self.assertEqual(model_reference_issue(ref), 'MODEL_REFERENCE_INVALID')

    def test_new_invalid_submission_400_envelope_before_store_factory(self):
        get_store = Mock(side_effect=AssertionError('invalid declaration must not reach Store'))
        app = FastAPI(); app.include_router(gmais_api.create_router(get_store))
        with TestClient(app) as client:
            for field in ('id', 'version', 'role'):
                for value in (' ', 'x\x00', '\ud800', 'a' * 257):
                    job = job_fixture(); job['model_ref'] = model(); job['model_ref'][field] = value
                    response = client.post('/v1/agents/lcluc-agent/jobs', content=json.dumps(job),
                        headers={'Content-Type': 'application/json', 'Idempotency-Key': 'isolated-model-ref'})
                    self.assertEqual(response.status_code, 400, response.text)
                    error = response.json()['error']
                    self.assertEqual(set(error), {'code', 'message', 'trace_id', 'retryable'})
                    self.assertEqual(error['code'], 'INVALID_REQUEST')
                    self.assertEqual(error['trace_id'], 'unknown')
                    self.assertIs(error['retryable'], False)
            for value in ('latest', ' Current '):
                job = job_fixture(); job['model_ref'] = model(); job['model_ref']['version'] = value
                response = client.post('/v1/agents/lcluc-agent/jobs', json=job,
                    headers={'Idempotency-Key': 'isolated-model-ref'})
                self.assertEqual(response.status_code, 400)
                self.assertIn('latest/current', response.json()['error']['message'])
        get_store.assert_not_called()

    def test_prior_schema_null_type_shape_sha_and_uri_errors_are_identical(self):
        for ref in (None, [], {'id': 'm', 'version': 'latest'},
                    dict(id=1, version='v1', sha256='a' * 64),
                    dict(id='m', version='latest', sha256='bad'),
                    dict(id='m', version='v1', sha256='a' * 64, uri=1),
                    dict(id='m', version='v1', sha256='a' * 64, role=True)):
            job = job_fixture(); job['model_ref'] = ref
            args = (job, 'lcluc-agent', 'isolated-model-ref')
            self.assertEqual(gmais_api._validate_job(*args), self.original_gmais._validate_job(*args))
            responses, calls, _ = self.exercise(gmais_api, '/v1/agents/lcluc-agent/jobs', job)
            self.assertEqual(responses[0][0], 400)
            self.assertEqual(calls, [])

    def test_existing_manual_sha_branch_still_precedes_new_text_guard(self):
        job = job_fixture(); job['model_ref'] = dict(id=' ', version='latest', sha256='bad')
        validator = Mock(); validator.iter_errors.return_value = iter(())
        with patch.object(gmais_api, '_job_request_validator', return_value=validator), \
             patch.object(gmais_api, 'model_reference_issue', side_effect=AssertionError('SHA must win')):
            value, message = gmais_api._validate_job(job, 'lcluc-agent', 'isolated-model-ref')
        validator.iter_errors.return_value = iter(())
        with patch.object(self.original_gmais, '_job_request_validator', return_value=validator):
            baseline = self.original_gmais._validate_job(job, 'lcluc-agent', 'isolated-model-ref')
        self.assertIsNone(value)
        self.assertEqual((value, message), baseline)
        self.assertIn('SHA-256', message)

    def test_fixed_absent_padded_boundary_and_role_submission_replay_unchanged(self):
        for ref in (None, model(), dict(id=' x ', version=' v1 ', sha256='a' * 64, role=' role '),
                    dict(id='a' * 256, version='a' * 256, sha256='a' * 64, role='a' * 256)):
            job = job_fixture()
            if ref is not None: job['model_ref'] = ref
            before = copy.deepcopy(job)
            expected = self.exercise(self.original_gmais, '/v1/agents/lcluc-agent/jobs', job, replay=True)
            actual = self.exercise(gmais_api, '/v1/agents/lcluc-agent/jobs', job, replay=True)
            self.assertEqual(actual, expected)
            responses, accesses, records = actual
            self.assertTrue(all(item[0] == 409 for item in responses))
            self.assertTrue(all(item[2]['error']['code'] == 'MODEL_NOT_READY' for item in responses))
            self.assertFalse(any(item[:2] in (('list', 'models'), ('get', 'models')) for item in accesses))
            self.assertEqual(len(records['gmais_jobs']), 1)
            self.assertEqual(len(records['gmais_idempotency']), 1)
            self.assertEqual(records['gmais_results'], [])
            self.assertEqual(job, before)

    def test_workflow_response_access_order_and_records_unchanged(self):
        workflow, _ = full_fixture()
        self.assertEqual(self.exercise(gmais_api, '/v1/workflows/plan', workflow),
                         self.exercise(self.original_gmais, '/v1/workflows/plan', workflow))

    def test_full_job_original_result_and_failure_priority_preserved(self):
        refs = [None, model(), dict(id='m', version=' latest ', sha256='a' * 64),
                dict(id=' ', version='latest', sha256='a' * 64),
                dict(id='m', version=' v1 ', sha256='a' * 64, role=' role '),
                dict(id='a' * 257, version='v1', sha256='a' * 64),
                dict(id='m', version='v1', sha256='a' * 64, role='\ud800')]
        for ref in refs:
            workflow, job = full_fixture()
            if ref is not None: job['model_ref'] = ref
            args = (workflow, _digest(workflow), 'private-node', job)
            self.assertEqual(handoff.compare_workflow_job_request_handoff(*args),
                             self.original_handoff.compare_workflow_job_request_handoff(*args))
        workflow, job = full_fixture(); job['model_ref'] = None
        result = handoff.compare_workflow_job_request_handoff(workflow, _digest(workflow), 'private-node', job)
        self.assertEqual(result['issues'], [{'code': 'FULL_JOB_SCHEMA_INVALID'}])

    def test_rfc1_and_rfc2_exact_responses_preserved_for_model_declarations(self):
        app = FastAPI(); app.include_router(handoff_api.create_workflow_job_request_handoff_router())
        with TestClient(app) as client:
            for ref in (None, model(), dict(id=' ', version='latest', sha256='a' * 64),
                        dict(id='m', version='latest', sha256='a' * 64)):
                workflow, job = full_fixture()
                if ref is not None: job['model_ref'] = ref
                for version in (1, 2):
                    body = envelope(workflow, job)
                    if version == 2: body['contract_version'] = 2
                    encoded = raw(body)
                    with patch.object(handoff_api, 'compare_workflow_job_request_handoff',
                                      side_effect=self.original_handoff.compare_workflow_job_request_handoff), \
                         patch.object(registration, 'compare_workflow_job_request_handoff',
                                      side_effect=self.original_handoff.compare_workflow_job_request_handoff):
                        expected = client.post(PATH, content=encoded)
                    actual = client.post(PATH, content=encoded)
                    self.assertEqual(actual.status_code, 200, actual.text)
                    self.assertEqual((actual.content, dict(actual.headers)), (expected.content, dict(expected.headers)))
