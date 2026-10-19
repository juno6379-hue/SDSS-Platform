import copy
import unittest
from unittest.mock import patch

from app import gmais_api
from app.workflow_job_registration_handoff import (
    compare_workflow_job_registration_handoff as compare,
    validate_registration_handoff_response, RESULT_KEYS, AXIS_KEYS,
)
from app.workflow_job_request_handoff import compare_workflow_job_request_handoff
from app.workflow_job_request_handoff_api import validate_full_job_handoff_response
from app.workflow_node_input_handoff import _digest
from test_workflow_job_request_handoff import full_fixture


def registered_fixture():
    workflow, job = full_fixture()
    for target in (workflow['nodes'][0], job):
        target.update(agent_id='lcluc-agent', capability_id='landcover.change_detection')
    return workflow, job


def envelope(workflow):
    return {'pinned_workflow_request_sha256': _digest(workflow), 'selected_node_id': 'private-node'}


class WorkflowJobRegistrationHandoffTests(unittest.TestCase):
    def run_compare(self, workflow, job):
        return compare(workflow, _digest(workflow), 'private-node', job)

    def test_registered_is_observation_only_and_inner_preserved(self):
        w, j = registered_fixture()
        before = copy.deepcopy((w, j))
        inner = compare_workflow_job_request_handoff(w, _digest(w), 'private-node', j)
        with patch('app.workflow_job_registration_handoff.compare_workflow_job_request_handoff', wraps=compare_workflow_job_request_handoff) as comparator:
            result = self.run_compare(w, j)
        self.assertEqual(comparator.call_count, 1)
        self.assertEqual(set(result), RESULT_KEYS)
        self.assertEqual(result['full_job_comparison'], inner)
        self.assertEqual(result['status'], 'MATCH')
        self.assertEqual(result['local_manifest_registration'], {'source': 'LOCAL_STATIC_AGENT_MANIFESTS', 'status': 'REGISTERED', 'checked': True})
        self.assertEqual(set(result['local_manifest_registration']), AXIS_KEYS)
        self.assertIs(result['actual_capability_supported'], False)
        self.assertIs(result['institution_acl_verified'], False)
        self.assertIs(result['execution_authorized'], False)
        self.assertIs(inner['agent_capability_verified'], False)
        self.assertEqual((w, j), before)

    def test_unknown_and_unregistered_are_distinct(self):
        w, j = full_fixture()
        result = self.run_compare(w, j)
        self.assertEqual(result['local_manifest_registration']['status'], 'AGENT_UNKNOWN')
        self.assertEqual(result['status'], 'BLOCKED')
        w, j = registered_fixture()
        for target in (w['nodes'][0], j):
            target['capability_id'] = 'missing'
        result = self.run_compare(w, j)
        self.assertEqual(result['local_manifest_registration']['status'], 'CAPABILITY_UNREGISTERED')
        self.assertEqual(result['full_job_comparison']['status'], 'MATCH')

    def test_blocked_inner_never_reads_manifest(self):
        for mutate in (lambda j: j.pop('aoi'), lambda j: j['input_refs'][0].update(role='changed'),
                       lambda j: j.update(time_range={'start': 'not-a-date'})):
            w, j = registered_fixture()
            mutate(j)
            with patch('app.gmais_api._agent_manifests', side_effect=AssertionError('not run')):
                result = self.run_compare(w, j)
                validate_registration_handoff_response(result, envelope(w), w, j, validate_full_job_handoff_response)
            self.assertEqual(result['local_manifest_registration']['status'], 'NOT_RUN')
            self.assertIs(result['local_manifest_registration']['checked'], False)

    def test_manifest_choice_is_first_match_and_readiness_is_ignored(self):
        w, j = registered_fixture()
        first = next(a for a in gmais_api._agent_manifests() if a['agent_id'] == 'lcluc-agent')
        first['readiness'] = 'NOT_IMPLEMENTED'
        last = copy.deepcopy(first)
        last['capabilities'] = [{'capability_id': 'missing'}]
        with patch('app.gmais_api._agent_manifests', return_value=[first, last]):
            self.assertEqual(self.run_compare(w, j)['local_manifest_registration']['status'], 'REGISTERED')
        with patch('app.gmais_api._agent_manifests', return_value=[last, first]):
            self.assertEqual(self.run_compare(w, j)['local_manifest_registration']['status'], 'CAPABILITY_UNREGISTERED')

    def test_two_static_reads_but_only_one_comparator_and_no_store(self):
        w, j = registered_fixture()
        manifests = gmais_api._agent_manifests()
        with patch('app.gmais_api._agent_manifests', return_value=manifests) as lookup, \
             patch('app.workflow_job_registration_handoff.compare_workflow_job_request_handoff', wraps=compare_workflow_job_request_handoff) as comparator, \
             patch('app.store.Store.get', side_effect=AssertionError('no store')):
            result = self.run_compare(w, j)
            validate_registration_handoff_response(result, envelope(w), w, j, validate_full_job_handoff_response)
        self.assertEqual(lookup.call_count, 2)
        self.assertEqual(comparator.call_count, 1)
        self.assertEqual(result['full_job_comparison']['comparator_calls'], 1)
        self.assertIsNone(result['full_job_comparison']['schema_files_read'])

    def test_malformed_local_manifest_fails_closed(self):
        w, j = registered_fixture()
        for manifests in (None, {}, [None], [{}], [{'agent_id': 'x', 'capabilities': None}],
                          [{'agent_id': 'x', 'capabilities': [{}]}], [{'agent_id': 1, 'capabilities': []}]):
            with self.subTest(manifests=manifests), patch('app.gmais_api._agent_manifests', return_value=manifests), self.assertRaises(ValueError):
                self.run_compare(w, j)

    def test_safe_validator_rejects_outer_axis_and_inner_corruption(self):
        w, j = registered_fixture()
        base = self.run_compare(w, j)
        mutations = (lambda r: r.update(extra='private'), lambda r: r.update(schema_version=True),
            lambda r: r.update(actual_capability_supported=True), lambda r: r.update(institution_acl_verified=0),
            lambda r: r.update(execution_authorized=True), lambda r: r.update(status='BLOCKED'),
            lambda r: r['local_manifest_registration'].update(checked=1),
            lambda r: r['local_manifest_registration'].update(source='REMOTE_REGISTRY'),
            lambda r: r['local_manifest_registration'].update(status='NOT_RUN'),
            lambda r: r['local_manifest_registration'].update(agent_id='private'),
            lambda r: r['full_job_comparison'].update(agent_capability_verified=True),
            lambda r: r['full_job_comparison'].update(schema_files_read=0))
        for mutate in mutations:
            result = copy.deepcopy(base)
            mutate(result)
            with self.assertRaises(ValueError):
                validate_registration_handoff_response(result, envelope(w), w, j, validate_full_job_handoff_response)

    def test_forged_consistent_registered_axis_is_rechecked_against_local_source(self):
        w, j = full_fixture()
        result = self.run_compare(w, j)
        result['local_manifest_registration']['status'] = 'REGISTERED'
        result['status'] = 'MATCH'
        with self.assertRaises(ValueError):
            validate_registration_handoff_response(result, envelope(w), w, j, validate_full_job_handoff_response)
