"""Pure membership and original-handler equivalence using isolated temporary stores."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import gmais_api
from app.agent_capability_contract import agent_capability_issue
from app.store import Store
from test_schema_formats import job_fixture
from test_workflow_job_request_handoff import full_fixture


ORIGINAL = Path(__file__).resolve().parents[1] / 'evidence/integration/agent-capability-original-gmais-20261017.py'
ORIGINAL_SHA256 = '3f6db80820360086ea3b52ecf4282e0d953a62b9aea3e159775aea624c7481b6'


class RecordingStore(Store):
    def __init__(self, root, calls):
        self.calls = calls
        super().__init__(root)

    def list(self, kind):
        self.calls.append(('list', kind))
        return super().list(kind)

    def get(self, kind, identifier):
        self.calls.append(('get', kind, identifier))
        return super().get(kind, identifier)

    def put(self, kind, record):
        self.calls.append(('put', kind))
        return super().put(kind, record)


class AgentCapabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA256:
            raise AssertionError('Original pre-refactor handler evidence changed')
        spec = importlib.util.spec_from_file_location('app._agent_capability_original93', ORIGINAL)
        cls.original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.original)

    def exercise(self, module, path, body, manifests=None, replay=False):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []
            store = RecordingStore(Path(temporary), calls)
            def get_store():
                calls.append(('factory',))
                return store
            app = FastAPI()
            app.include_router(module.create_router(get_store))
            selected = module._agent_manifests() if manifests is None else manifests
            with patch.object(module, '_agent_manifests', return_value=copy.deepcopy(selected)), \
                 patch.object(module, '_now', return_value='2026-10-17T00:00:00.000Z'), \
                 patch.object(module.uuid, 'uuid4', return_value=SimpleNamespace(hex='2' * 32)), \
                 patch('app.store.now', return_value='2026-10-17T00:00:00.000Z'), TestClient(app) as client:
                responses = []
                for _ in range(2 if replay else 1):
                    response = client.post(path, json=body, headers={'Idempotency-Key': 'isolated-capability-contract'})
                    responses.append((response.status_code, dict(response.headers), response.json()))
            accesses = copy.deepcopy(calls)
            records = {kind: Store.list(store, kind) for kind in ('gmais_jobs', 'gmais_idempotency', 'gmais_results')}
            return responses, accesses, records

    def equivalent(self, path, body, manifests=None, replay=False):
        before = copy.deepcopy((body, manifests))
        baseline = self.exercise(self.original, path, body, manifests, replay)
        actual = self.exercise(gmais_api, path, body, manifests, replay)
        self.assertEqual(actual, baseline)
        self.assertEqual((body, manifests), before)
        return actual

    def test_pure_registration_only_and_input_immutable(self):
        agent = {'capabilities': [{'capability_id': 'registered'}, {'capability_id': 'other'}], 'readiness': 'BLOCKED'}
        before = copy.deepcopy(agent)
        with patch('builtins.open', side_effect=AssertionError('no I/O')):
            self.assertIsNone(agent_capability_issue(agent, 'registered'))
            self.assertEqual(agent_capability_issue(agent, 'missing'), 'INVALID_REQUEST')
            self.assertEqual(agent_capability_issue(None, 'registered'), 'AGENT_NOT_IMPLEMENTED')
        self.assertEqual(agent, before)
        self.assertEqual(agent_capability_issue({'capabilities': []}, 'registered'), 'INVALID_REQUEST')

    def test_existing_membership_types_and_malformed_manifest_exceptions(self):
        self.assertIsNone(agent_capability_issue({'capabilities': [{'capability_id': 1}]}, True))
        self.assertEqual(agent_capability_issue({'capabilities': [{'capability_id': '1'}]}, 1), 'INVALID_REQUEST')
        for agent, error in (({}, KeyError), ({'capabilities': [{}]}, KeyError),
                             ({'capabilities': None}, TypeError), ({'capabilities': ['text']}, TypeError)):
            with self.subTest(agent=agent), self.assertRaises(error):
                agent_capability_issue(agent, 'registered')

    def test_missing_agent_submit_409_before_store(self):
        job = job_fixture()
        job['agent_id'] = 'unregistered-agent'
        responses, calls, records = self.equivalent('/v1/agents/unregistered-agent/jobs', job)
        self.assertEqual(responses[0][0], 409)
        self.assertEqual(responses[0][2]['error']['code'], 'AGENT_NOT_IMPLEMENTED')
        self.assertEqual(calls, [])
        self.assertTrue(all(not value for value in records.values()))

    def test_wrong_capability_submit_400_before_store(self):
        job = job_fixture()
        job['capability_id'] = 'unregistered-capability'
        responses, calls, _ = self.equivalent('/v1/agents/lcluc-agent/jobs', job)
        self.assertEqual(responses[0][0], 400)
        self.assertEqual(responses[0][2]['error']['code'], 'INVALID_REQUEST')
        self.assertEqual(calls, [])

    def test_schema_rejection_still_precedes_registration(self):
        job = job_fixture()
        job.update(agent_id='unregistered-agent', time_range={'start': 'not-a-date'})
        responses, calls, _ = self.equivalent('/v1/agents/unregistered-agent/jobs', job)
        self.assertEqual(responses[0][0], 400)
        self.assertEqual(responses[0][2]['error']['code'], 'INVALID_REQUEST')
        self.assertEqual(calls, [])

    def test_normal_blocked_submit_and_replay_keep_all_responses_records_and_access_order(self):
        responses, calls, records = self.equivalent('/v1/agents/lcluc-agent/jobs', job_fixture(), replay=True)
        self.assertTrue(all(item[0] == 409 for item in responses))
        self.assertTrue(all(item[2]['error']['code'] == 'MODEL_NOT_READY' for item in responses))
        self.assertEqual(calls[0:2], [('factory',), ('list', 'gmais_idempotency')])
        self.assertEqual(len(records['gmais_jobs']), 1)
        self.assertEqual(len(records['gmais_idempotency']), 1)
        self.assertEqual(records['gmais_results'], [])

    def test_external_registered_agent_retains_not_implemented_blocked_submit(self):
        job = job_fixture()
        job.update(agent_id='flood-drought-agent', capability_id='flood-drought')
        responses, _, records = self.equivalent('/v1/agents/flood-drought-agent/jobs', job)
        self.assertEqual(responses[0][0], 409)
        self.assertEqual(responses[0][2]['error']['code'], 'AGENT_NOT_IMPLEMENTED')
        self.assertEqual(records['gmais_jobs'][0]['status']['status'], 'BLOCKED')

    def test_submit_keeps_first_matching_manifest_with_duplicate_ids(self):
        first = next(agent for agent in gmais_api._agent_manifests() if agent['agent_id'] == 'lcluc-agent')
        last = copy.deepcopy(first)
        last['capabilities'] = [{'capability_id': 'last-only'}]
        responses, _, _ = self.equivalent('/v1/agents/lcluc-agent/jobs', job_fixture(), [first, last])
        self.assertEqual(responses[0][2]['error']['code'], 'MODEL_NOT_READY')
        responses, calls, _ = self.equivalent('/v1/agents/lcluc-agent/jobs', job_fixture(), [last, first])
        self.assertEqual(responses[0][0], 400)
        self.assertEqual(calls, [])

    def test_workflow_unknown_wrong_capability_and_readiness_keep_full_response(self):
        for agent_id, capability in (('unregistered-agent', 'missing'), ('lcluc-agent', 'missing'),
                                     ('lcluc-agent', 'landcover.change_detection'), ('flood-drought-agent', 'flood-drought')):
            workflow, _ = full_fixture()
            workflow['nodes'][0].update(agent_id=agent_id, capability_id=capability)
            responses, calls, records = self.equivalent('/v1/workflows/plan', workflow)
            self.assertEqual(responses[0][0], 200)
            self.assertEqual(responses[0][2]['status'], 'BLOCKED')
            self.assertEqual(calls[0], ('factory',))
            self.assertFalse(any(item[0] == 'put' for item in calls))
            self.assertTrue(all(not value for value in records.values()))

    def test_workflow_keeps_last_matching_manifest_with_duplicate_ids(self):
        workflow, _ = full_fixture()
        workflow['nodes'][0].update(agent_id='lcluc-agent', capability_id='landcover.change_detection')
        first = next(agent for agent in gmais_api._agent_manifests() if agent['agent_id'] == 'lcluc-agent')
        last = copy.deepcopy(first)
        last['capabilities'] = [{'capability_id': 'last-only'}]
        responses, _, _ = self.equivalent('/v1/workflows/plan', workflow, [first, last])
        blockers = responses[0][2]['nodes'][0]['blockers']
        self.assertEqual(blockers[0]['code'], 'INVALID_REQUEST')
        responses, _, _ = self.equivalent('/v1/workflows/plan', workflow, [last, first])
        self.assertEqual(responses[0][2]['nodes'][0]['blockers'][0]['code'], 'MODEL_NOT_READY')

    def test_ready_manifest_does_not_start_submit_or_workflow_execution(self):
        selected = next(agent for agent in gmais_api._agent_manifests() if agent['agent_id'] == 'lcluc-agent')
        selected['readiness'] = 'READY'
        responses, _, records = self.equivalent('/v1/agents/lcluc-agent/jobs', job_fixture(), [selected])
        self.assertEqual(responses[0][0], 409)
        self.assertEqual(records['gmais_jobs'][0]['status']['status'], 'BLOCKED')
        workflow, _ = full_fixture()
        workflow['nodes'][0].update(agent_id='lcluc-agent', capability_id='landcover.change_detection')
        responses, _, _ = self.equivalent('/v1/workflows/plan', workflow, [selected])
        self.assertIs(responses[0][2]['execution_started'], False)
        self.assertIs(responses[0][2]['can_execute'], False)
