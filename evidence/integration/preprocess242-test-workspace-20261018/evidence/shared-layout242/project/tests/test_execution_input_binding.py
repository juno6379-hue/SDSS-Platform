import copy
import hashlib
import json
import unittest
from unittest.mock import patch
from app.execution_input_binding import compare_execution_input_bindings


class ExecutionInputBindingTests(unittest.TestCase):
    def setUp(self):
        self.envelope = {'job_id': 'job-1', 'agent_id': 'lcluc', 'trace_id': 'trace-1', 'bindings': [
            {'input_index': 0, 'id': 'rain', 'version': '2024', 'sha256': 'a'*64,
             'role': 'reference', 'manifest_sha256': 'b'*64},
            {'input_index': 1, 'id': 'rain', 'version': '2025', 'sha256': 'c'*64,
             'manifest_sha256': 'd'*64}]}

    def result(self, actual=None, expected=None):
        return compare_execution_input_bindings(self.envelope if expected is None else expected,
                                                copy.deepcopy(self.envelope) if actual is None else actual)

    def test_match_different_versions_and_all_false(self):
        result = self.result()
        self.assertEqual(result['status'], 'MATCH')
        self.assertTrue(result['declarations_match'])
        for key in ('execution_authorized','ready_for_execution','ready_for_training','scientific_approval',
                    'acl_verified','registry_verified','training_authorized','pixels_verified','toc_tou_protected',
                    'executor_connected','artifact_bytes_verified','manifest_bytes_verified'):
            self.assertIs(result[key], False)

    def test_order_and_indices(self):
        actual = copy.deepcopy(self.envelope)
        actual['bindings'].reverse()
        self.assertEqual(self.result(actual)['status'], 'BLOCKED')
        for i, row in enumerate(actual['bindings']): row['input_index'] = i
        self.assertEqual(self.result(actual)['status'], 'BLOCKED')

    def test_missing_and_extra(self):
        for count in (1, 3):
            actual = copy.deepcopy(self.envelope)
            if count == 1: actual['bindings'].pop()
            else:
                row = copy.deepcopy(actual['bindings'][0]); row['input_index'] = 2
                actual['bindings'].append(row)
            self.assertEqual(self.result(actual)['status'], 'BLOCKED')

    def test_job_agent_trace_each_mismatch(self):
        for key in ('job_id','agent_id','trace_id'):
            actual = copy.deepcopy(self.envelope); actual[key] += '-changed'
            self.assertEqual(self.result(actual)['status'], 'BLOCKED')

    def test_role_presence_and_hash(self):
        absent = copy.deepcopy(self.envelope); absent['bindings'][0].pop('role')
        self.assertEqual(self.result(absent)['status'], 'BLOCKED')
        self.assertEqual(self.result(absent, absent)['status'], 'MATCH')
        self.assertNotEqual(self.result()['expected_bindings_sha256'], self.result(absent, absent)['expected_bindings_sha256'])
        for bad in (None, '', ' '*2, True):
            actual = copy.deepcopy(self.envelope); actual['bindings'][0]['role'] = bad
            self.assertEqual(self.result(actual)['status'], 'BLOCKED')

    def test_legacy_manifest_not_backfilled(self):
        legacy = copy.deepcopy(self.envelope); legacy['bindings'][0].pop('manifest_sha256')
        for actual in (legacy, self.envelope):
            result = self.result(actual, legacy)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['missing_expected_manifest_pin_count'], 1)
        actual = copy.deepcopy(legacy); actual['trace_id'] = 'different'
        self.assertEqual(self.result(actual, legacy)['status'], 'BLOCKED')

    def test_expected_manifest_missing_or_changed_supplied(self):
        for value in (None, 'e'*64):
            actual = copy.deepcopy(self.envelope)
            if value is None: actual['bindings'][0].pop('manifest_sha256')
            else: actual['bindings'][0]['manifest_sha256'] = value
            self.assertEqual(self.result(actual)['status'], 'BLOCKED')

    def test_same_identity_conflict_both_sides(self):
        for field in ('sha256', 'manifest_sha256'):
            conflict = copy.deepcopy(self.envelope)
            conflict['bindings'][1]['version'] = '2024'
            conflict['bindings'][1]['sha256'] = 'a'*64
            conflict['bindings'][1]['manifest_sha256'] = 'b'*64
            conflict['bindings'][1][field] = 'e'*64
            for expected, actual in ((conflict, self.envelope), (self.envelope, conflict)):
                self.assertEqual(self.result(actual, expected)['status'], 'BLOCKED')

    def test_same_identity_repeated_equal_allowed(self):
        same = copy.deepcopy(self.envelope)
        same['bindings'][1] = copy.deepcopy(same['bindings'][0]); same['bindings'][1]['input_index'] = 1
        self.assertEqual(self.result(same, same)['status'], 'MATCH')

    def test_strict_scalar_types_and_huge_values(self):
        for field, values in {'input_index':[False,0.0,10**400], 'id':[False, 1, [], {}],
                              'version':['latest',' Current ',True], 'sha256':[False,'A'*64,'a'*65],
                              'manifest_sha256':[True,None,'b'*63]}.items():
            for value in values:
                actual = copy.deepcopy(self.envelope); actual['bindings'][0][field] = value
                self.assertEqual(self.result(actual)['status'], 'BLOCKED', (field,type(value)))

    def test_text_limits_controls_and_surrogates(self):
        for value in ('x'*257, '', ' '*256, 'x\x00', 'x\x7f', 'x\u0085', 'x\u009f', '\ud800'):
            for target in ('job_id', 'id', 'role'):
                actual = copy.deepcopy(self.envelope)
                if target == 'job_id': actual[target] = value
                else: actual['bindings'][0][target] = value
                self.assertEqual(self.result(actual)['status'], 'BLOCKED')
        actual = copy.deepcopy(self.envelope); actual['job_id'] = '한'*256
        self.assertEqual(self.result(actual, actual)['status'], 'MATCH')

    def test_exact_keys_cycles_and_budget(self):
        for actual in (None, [], {}, {'cycle':None}):
            self.assertEqual(self.result(actual=actual if actual is not None else [])['status'], 'BLOCKED')
        cycle = copy.deepcopy(self.envelope); cycle['bindings'][0]['role'] = cycle
        self.assertEqual(self.result(cycle)['status'], 'BLOCKED')
        for size in (0,65):
            actual = copy.deepcopy(self.envelope); actual['bindings'] = [{}]*size
            with patch('app.execution_input_binding.json.dumps', side_effect=AssertionError('must not hash invalid expected')):
                self.assertEqual(self.result(actual, actual)['status'], 'BLOCKED')
        actual = copy.deepcopy(self.envelope); actual['bindings'][0]['uri'] = 'private'
        self.assertEqual(self.result(actual)['status'], 'BLOCKED')

    def test_canonical_scope_and_input_immutable_no_io(self):
        before = copy.deepcopy(self.envelope)
        with patch('builtins.open',side_effect=AssertionError('no IO')):
            result = self.result()
        raw = json.dumps(self.envelope['bindings'],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
        self.assertEqual(result['expected_bindings_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.envelope,before)
        other = copy.deepcopy(self.envelope); other['job_id'] = 'other-job'
        self.assertEqual(self.result(other,other)['expected_bindings_sha256'],result['expected_bindings_sha256'])
        self.assertEqual([result[k] for k in ('network_requests','source_files_written','database_calls','resolver_calls','executor_calls')],[0]*5)

    def test_safe_output_no_raw_identity_or_exception(self):
        actual = copy.deepcopy(self.envelope); actual['job_id'] = 'secret-job'; actual['bindings'][0]['role'] = 'secret-role'
        result = self.result(actual)
        encoded = json.dumps(result,ensure_ascii=True)
        for raw in ('secret-job','secret-role','rain','trace-1','a'*64,'b'*64): self.assertNotIn(json.dumps(raw),encoded)
        self.assertEqual(set(result['issues'][0]),{'side','input_index','code'})


if __name__ == '__main__': unittest.main()
