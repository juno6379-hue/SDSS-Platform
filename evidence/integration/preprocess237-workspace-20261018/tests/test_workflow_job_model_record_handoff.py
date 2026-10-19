"""Separate observation wrapper; original 89 and model comparison stay unchanged."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from app import gmais_api
from app import workflow_job_model_record_handoff as wrapper
from app import workflow_job_request_handoff as handoff
from app.model_reference_record_comparison import compare_model_reference_record
from app.store import Store
from app.workflow_node_input_handoff import _digest, _FALSE_FLAGS
from test_workflow_job_request_handoff import full_fixture
import test_model_registration_provenance as model_fixtures


FLAGS = ('authority_verified', 'artifact_bytes_verified', 'execution_authorized',
         'scientific_accuracy_validated', 'model_verified')
KEYS = {'schema_version', 'scope', 'status', 'full_job_comparison',
        'model_reference_comparison', 'identity_projection_performed',
        'model_comparison_calls', *FLAGS}


class Poison:
    def __contains__(self, key): raise AssertionError('no reference/candidate access')
    def __getitem__(self, key): raise AssertionError('no reference/candidate access')
    def __iter__(self): raise AssertionError('no reference/candidate traversal')
    def __repr__(self): raise AssertionError('no reference/candidate serialization')


def fixture():
    workflow, job = full_fixture()
    job['model_ref'] = {'id': 'private-model', 'version': ' v2 ', 'sha256': 'a' * 64,
                        'role': ' model ', 'uri': 'file:///private-checkpoint'}
    return workflow, job, model_fixtures.fixture()


class WorkflowJobModelRecordHandoffTests(unittest.TestCase):
    def checked(self, result, status, calls):
        self.assertEqual(set(result), KEYS)
        self.assertIs(type(result['schema_version']), int)
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['scope'], 'WORKFLOW_FULL_JOB_MODEL_RECORD_OBSERVATION_ONLY')
        self.assertEqual(result['status'], status)
        self.assertIs(type(result['model_comparison_calls']), int)
        self.assertEqual(result['model_comparison_calls'], calls)
        self.assertIs(result['identity_projection_performed'], calls == 1)
        for flag in FLAGS: self.assertIs(result[flag], False)
        if calls == 0: self.assertIsNone(result['model_reference_comparison'])
        return result

    def run_real(self, workflow, job, record=None, pin=None):
        return wrapper.compare_workflow_job_model_record_handoff(workflow,
            _digest(workflow) if pin is None else pin, 'private-node', job, record)

    def test_blocked_original_call_once_exact_arguments_embedded_object_and_no_postgate_access(self):
        workflow, pin, node, job, record = object(), object(), object(), Poison(), Poison()
        original = {'status': 'BLOCKED', 'synthetic_mock': True}
        with patch.object(wrapper, 'compare_workflow_job_request_handoff', return_value=original) as compare89, \
             patch.object(wrapper, 'compare_model_reference_record', side_effect=AssertionError('no 103')) as compare103:
            result = wrapper.compare_workflow_job_model_record_handoff(workflow, pin, node, job, record)
        self.checked(result, 'HANDOFF_BLOCKED', 0)
        self.assertIs(result['full_job_comparison'], original)
        compare89.assert_called_once_with(workflow, pin, node, job)
        compare103.assert_not_called()

    def test_mock_match_without_reference_does_not_touch_candidate(self):
        original = {'status': 'MATCH', 'synthetic_mock': True}
        with patch.object(wrapper, 'compare_workflow_job_request_handoff', return_value=original) as compare89, \
             patch.object(wrapper, 'compare_model_reference_record', side_effect=AssertionError('no 103')):
            result = wrapper.compare_workflow_job_model_record_handoff({}, 'pin', 'node', {}, Poison())
        self.checked(result, 'MODEL_REFERENCE_ABSENT', 0)
        self.assertIs(result['full_job_comparison'], original)
        self.assertEqual(compare89.call_count, 1)

    def test_projection_exact_three_original_values_and_candidate_identity_forwarded(self):
        workflow, job, _ = fixture(); record = Poison(); before = copy.deepcopy(job)
        original = {'status': 'MATCH'}; observed = {'synthetic_mock': True}
        with patch.object(wrapper, 'compare_workflow_job_request_handoff', return_value=original), \
             patch.object(wrapper, 'compare_model_reference_record', return_value=observed) as compare103:
            result = self.run_real(workflow, job, record)
        self.checked(result, 'MODEL_REFERENCE_OBSERVED', 1)
        projected, supplied = compare103.call_args.args
        self.assertEqual(projected, {key: job['model_ref'][key] for key in ('id', 'version', 'sha256')})
        self.assertIsNot(projected, job['model_ref'])
        self.assertIs(supplied, record)
        self.assertIs(result['model_reference_comparison'], observed)
        self.assertEqual(job, before)

    def test_real89_result_and_24_false_flags_unchanged_with_and_without_reference(self):
        workflow, job, record = fixture()
        for has_reference in (False, True):
            actual_job = copy.deepcopy(job)
            if not has_reference: del actual_job['model_ref']
            expected = handoff.compare_workflow_job_request_handoff(workflow, _digest(workflow), 'private-node', actual_job)
            with patch.object(wrapper, 'compare_workflow_job_request_handoff', wraps=handoff.compare_workflow_job_request_handoff) as compare89:
                result = self.run_real(workflow, actual_job, record)
            self.checked(result, 'MODEL_REFERENCE_OBSERVED' if has_reference else 'MODEL_REFERENCE_ABSENT', int(has_reference))
            self.assertEqual(result['full_job_comparison'], expected)
            self.assertEqual(compare89.call_count, 1)
            for flag in (*_FALSE_FLAGS, 'full_job_origin_verified', 'full_job_pin_verified', 'agent_capability_verified', 'model_verified'):
                self.assertIs(result['full_job_comparison'][flag], False)

    def test_real89_date_null_alias_role_and_bbox_block_without_103(self):
        mutations = (
            lambda job: job.update(time_range={'start': 'not-a-date'}),
            lambda job: job.update(model_ref=None),
            lambda job: job['model_ref'].update(version='latest'),
            lambda job: job['model_ref'].update(role=' '),
            lambda job: job['aoi'].update(bbox=[True, -6, 107, -5]),
            lambda job: job.pop('aoi'),
        )
        for mutate in mutations:
            workflow, job, _ = fixture(); mutate(job)
            expected = handoff.compare_workflow_job_request_handoff(workflow, _digest(workflow), 'private-node', job)
            with patch.object(wrapper, 'compare_model_reference_record', side_effect=AssertionError('no 103')):
                result = self.run_real(workflow, job, Poison())
            self.checked(result, 'HANDOFF_BLOCKED', 0)
            self.assertEqual(result['full_job_comparison'], expected)

    def test_real89_decimal_and_uri_string_are_preserved_without_uri_resolution(self):
        for uri in ('', 'file:///private-checkpoint', 'https://example.invalid/model'):
            workflow, job, record = fixture(); job['model_ref']['uri'] = uri
            job['parameters'] = {'decimal': .7, 'negative_zero': -0.0, 'exponent': 1e-7}
            before = copy.deepcopy((workflow, job, record))
            result = self.run_real(workflow, job, record)
            self.checked(result, 'MODEL_REFERENCE_OBSERVED', 1)
            self.assertEqual(result['model_reference_comparison']['status'], 'MATCH_UNVERIFIED')
            self.assertEqual((workflow, job, record), before)

    def test_real103_reachable_states_are_observed_not_outer_approval(self):
        cases = [(None, 'RECORD_NOT_PROVIDED'), (True, 'RECORD_INVALID'),
                 ({'id': 'other-model'}, 'REFERENCE_CONFLICT'),
                 ({'id': 'private-model'}, 'REFERENCE_NOT_COMPARABLE'),
                 (model_fixtures.fixture(), 'MATCH_UNVERIFIED')]
        for record, expected_status in cases:
            workflow, job, _ = fixture()
            with patch.object(wrapper, 'compare_model_reference_record', wraps=compare_model_reference_record) as compare103:
                result = self.run_real(workflow, job, record)
            self.checked(result, 'MODEL_REFERENCE_OBSERVED', 1)
            self.assertEqual(compare103.call_count, 1)
            self.assertEqual(result['model_reference_comparison']['status'], expected_status)
            for flag in FLAGS: self.assertIs(result['model_reference_comparison'][flag], False)

    def test_mock103_status_does_not_rewrite_outer_or_original89_result(self):
        for status in ('REFERENCE_INVALID', 'RECORD_NOT_PROVIDED', 'RECORD_INVALID',
                       'REFERENCE_CONFLICT', 'REFERENCE_NOT_COMPARABLE', 'MATCH_UNVERIFIED'):
            workflow, job, record = fixture(); observed = {'status': status, 'synthetic_mock': True}
            with patch.object(wrapper, 'compare_model_reference_record', return_value=observed):
                result = self.run_real(workflow, job, record)
            self.checked(result, 'MODEL_REFERENCE_OBSERVED', 1)
            self.assertEqual(result['full_job_comparison']['status'], 'MATCH')
            self.assertIs(result['model_reference_comparison'], observed)

    def test_resource_unavailable_and_metadata_pin_block_keep_original_result(self):
        workflow, job, _ = fixture()
        with patch('app.workflow_job_request_handoff._job_request_validator', side_effect=OSError('private-path')), \
             patch.object(wrapper, 'compare_model_reference_record', side_effect=AssertionError('no 103')):
            result = self.run_real(workflow, job, Poison())
        self.checked(result, 'HANDOFF_BLOCKED', 0)
        self.assertEqual(result['full_job_comparison']['validator_status'], 'RESOURCE_UNAVAILABLE')
        self.assertEqual(result['full_job_comparison']['issues'], [{'code': 'RESOURCE_UNAVAILABLE'}])
        with patch.object(wrapper, 'compare_model_reference_record', side_effect=AssertionError('no 103')):
            result = self.run_real(workflow, job, Poison(), pin='b' * 64)
        self.checked(result, 'HANDOFF_BLOCKED', 0)

    def test_cold_factory_schema_read_once_warm_zero_wrapper_adds_no_artifact_io(self):
        workflow, job, record = fixture(); reads = []
        original_read = Path.read_text
        def observed(path, *args, **kwargs):
            reads.append(path)
            return original_read(path, *args, **kwargs)
        gmais_api._job_request_validator.cache_clear()
        try:
            with patch.object(Path, 'read_text', observed):
                first = self.run_real(workflow, job, record)
                self.assertEqual([path.name for path in reads], ['job-request.schema.json'])
                second = self.run_real(workflow, job, record)
                self.assertEqual(len(reads), 1)
            self.assertEqual(first, second)
            self.assertIsNone(first['full_job_comparison']['schema_files_read'])
            with patch.object(Path, 'open', side_effect=AssertionError('warm: no artifact/schema open')), \
                 patch.object(Store, 'get', side_effect=AssertionError('no Store.get')), \
                 patch.object(Store, 'list', side_effect=AssertionError('no Store.list')), \
                 patch.object(Store, 'put', side_effect=AssertionError('no Store.put')), \
                 patch('socket.socket', side_effect=AssertionError('no network')):
                self.assertEqual(self.run_real(workflow, job, record), first)
        finally:
            gmais_api._job_request_validator.cache_clear()

    def test_supplied_candidate_unknown_cycle_is_not_copied_or_resolved(self):
        workflow, job, record = fixture(); record['unknown'] = record
        record['dataset_version'] = Poison()
        result = self.run_real(workflow, job, record)
        self.checked(result, 'MODEL_REFERENCE_OBSERVED', 1)
        self.assertEqual(result['model_reference_comparison']['status'], 'MATCH_UNVERIFIED')
        self.assertIs(record['unknown'], record)

    def test_89_and_103_exceptions_propagate_without_synthetic_success(self):
        workflow, job, record = fixture()
        for target in ('compare_workflow_job_request_handoff', 'compare_model_reference_record'):
            error = RuntimeError('private-internal-error')
            with patch.object(wrapper, target, side_effect=error), self.assertRaises(RuntimeError) as caught:
                self.run_real(workflow, job, record)
            self.assertIs(caught.exception, error)
