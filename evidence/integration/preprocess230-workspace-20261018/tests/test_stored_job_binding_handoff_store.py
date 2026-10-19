import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import test_stored_job_binding_handoff as fixtures
from app.store import Store
from app.stored_job_binding_handoff import compare_stored_job_binding_handoff
from app.stored_job_binding_handoff_store import inspect_stored_job_binding_handoff


class StoredBindingStoreAdapterTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.StoredJobBindingHandoffTests();fixture.setUp()
        self.job,self.supplied=fixture.job,fixture.supplied
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name))
        self.store.put('gmais_jobs',self.job)

    def tearDown(self):self.temp.cleanup()

    def inspect(self,store=None,job_id='job-test',supplied=None):
        return inspect_stored_job_binding_handoff(self.store if store is None else store,job_id,
                                                self.supplied if supplied is None else supplied)

    def test_temp_store_one_get_inner_match_and_scope(self):
        with patch.object(self.store,'get',wraps=self.store.get) as get:
            result=self.inspect()
        get.assert_called_once_with('gmais_jobs','job-test')
        self.assertEqual(result['store_status'],'OBSERVED');self.assertTrue(result['store_read_attempted']);self.assertTrue(result['store_read_observed'])
        self.assertEqual(result['store_get_calls'],1);self.assertEqual(result['comparison']['status'],'MATCH')
        self.assertEqual(result['comparison']['database_calls'],0)
        self.assertEqual(result['request_job_sha256'],hashlib.sha256(b'job-test').hexdigest())
        false=[v for k,v in result.items() if type(v) is bool and not k.startswith('store_read_')]
        self.assertEqual(len(false),15);self.assertTrue(all(v is False for v in false))
        for k,v in result['comparison'].items():
            if type(v) is bool and k!='declarations_match':self.assertIs(v,False)

    def test_store_origin_observed_is_not_authentication(self):
        class CallerStore:
            def get(inner,kind,key):return self.job
        result=self.inspect(CallerStore())
        self.assertTrue(result['store_read_observed']);self.assertIs(result['stored_job_origin_verified'],False)
        self.assertIs(result['comparison']['stored_job_origin_verified'],False)

    def test_invalid_literal_zero_get_and_no_hash(self):
        for value in (None,True,1,'',' '*2,'x'*257,'x\u0085','\ud800',[]):
            with patch.object(self.store,'get',side_effect=AssertionError('DB')):
                result=self.inspect(job_id=value)
            self.assertEqual(result['store_status'],'INVALID_REQUEST');self.assertEqual(result['store_get_calls'],0)
            self.assertFalse(result['store_read_attempted']);self.assertFalse(result['store_read_observed'])
            self.assertIsNone(result['comparison']);self.assertIsNone(result['request_job_sha256'])

    def test_bad_supplied_does_not_skip_valid_literal_get(self):
        with patch.object(self.store,'get',wraps=self.store.get) as get:
            result=self.inspect(supplied={})
        self.assertEqual(get.call_count,1);self.assertEqual(result['store_status'],'OBSERVED')
        self.assertEqual(result['comparison']['status'],'BLOCKED')

    def test_malformed_return_is_observed_comparison_blocked(self):
        for job in (None,[],{},dict(self.job,agent_id='wrong')):
            with patch.object(self.store,'get',return_value=job) as get:result=self.inspect()
            self.assertEqual(get.call_count,1);self.assertTrue(result['store_read_observed'])
            self.assertEqual(result['store_status'],'OBSERVED');self.assertEqual(result['comparison']['status'],'BLOCKED')

    def test_real_missing_and_keyerror_arity_type_guard(self):
        result=self.inspect(job_id='missing')
        self.assertEqual(result['store_status'],'NOT_FOUND');self.assertEqual(result['issues'],[{'code':'JOB_NOT_FOUND'}])
        class UnsafeEquality:
            def __eq__(self,other):raise AssertionError('unsafe comparison')
        for args in ((),('private',),('job-test','extra'),(False,),(['job-test'],),(UnsafeEquality(),),('x'*1000000,)):
            with patch.object(self.store,'get',side_effect=KeyError(*args)):
                result=self.inspect()
            self.assertEqual(result['store_status'],'RESOURCE_UNAVAILABLE');self.assertFalse(result['store_read_observed'])
        with patch.object(self.store,'get',side_effect=KeyError('job-test')):
            self.assertEqual(self.inspect()['store_status'],'NOT_FOUND')

    def test_expected_resource_errors_safe_and_single_attempt(self):
        errors=(sqlite3.DatabaseError('secret path'),json.JSONDecodeError('private','x',0),UnicodeError('secret'),
                OSError('private'),TypeError('secret'),ValueError('private'),OverflowError('secret'),
                RecursionError('private'),MemoryError('secret'))
        for error in errors:
            with patch.object(self.store,'get',side_effect=error) as get:result=self.inspect()
            self.assertEqual(get.call_count,1);self.assertEqual(result['store_status'],'RESOURCE_UNAVAILABLE')
            self.assertIsNone(result['comparison']);self.assertEqual(result['store_get_calls'],1)
            self.assertNotIn('secret',json.dumps(result));self.assertNotIn('private',json.dumps(result))

    def test_unexpected_and_process_exceptions_propagate(self):
        for error in (RuntimeError('bug'),AssertionError('bug'),KeyboardInterrupt(),SystemExit(3),BaseException('process')):
            with patch.object(self.store,'get',side_effect=error):
                with self.assertRaises(type(error)):self.inspect()

    def test_comparison_error_not_disguised_as_storage_failure(self):
        with patch('app.stored_job_binding_handoff_store.compare_stored_job_binding_handoff',side_effect=ValueError('comparison bug')):
            with self.assertRaises(ValueError):self.inspect()

    def test_legacy_unavailable_and_mismatch_preserve_inner_outcome(self):
        from app.execution_binding_capture import unavailable_capture
        for state in ('LEGACY','UNAVAILABLE'):
            job=copy.deepcopy(self.job)
            if state=='LEGACY':job.pop('execution_input_binding_capture')
            else:job['execution_input_binding_capture']=unavailable_capture(None,'CAPTURE_BOUNDARY_FAILURE')
            self.store.put('gmais_jobs',job)
            self.assertEqual(self.inspect()['comparison']['status'],'UNKNOWN')
            supplied=copy.deepcopy(self.supplied);supplied['trace_id']='different'
            self.assertEqual(self.inspect(supplied=supplied)['comparison']['status'],'BLOCKED')

    def test_no_put_list_registry_file_or_training_and_original_body_unchanged(self):
        with self.store.connect() as connection:
            before=connection.execute('SELECT body FROM records WHERE kind=? AND id=?',('gmais_jobs','job-test')).fetchone()[0]
        supplied=copy.deepcopy(self.supplied)
        with patch.object(self.store,'put',side_effect=AssertionError('put')),patch.object(self.store,'list',side_effect=AssertionError('list')),patch('app.dataset_registry.resolve_version',side_effect=AssertionError('Registry')),patch('app.job_inputs.resolve_job_inputs',side_effect=AssertionError('resolver')),patch('app.ml.service.train_model',side_effect=AssertionError('training')),patch('builtins.open',side_effect=AssertionError('source file')):
            result=self.inspect(supplied=supplied)
        self.assertEqual(supplied,self.supplied)
        with self.store.connect() as connection:
            after=connection.execute('SELECT body FROM records WHERE kind=? AND id=?',('gmais_jobs','job-test')).fetchone()[0]
        self.assertEqual(before,after)
        self.assertEqual(result['comparison'],compare_stored_job_binding_handoff(self.store.get('gmais_jobs','job-test'),'job-test',self.supplied))

    def test_no_job_expected_injection_and_output_privacy(self):
        with self.assertRaises(TypeError):inspect_stored_job_binding_handoff(self.store,'job-test',self.supplied,job=self.job)
        result=self.inspect();encoded=json.dumps(result)
        for raw in ('job-test','lcluc-agent','trace-test','secret-dataset','secret-role','private/file.tif','b'*64):self.assertNotIn(raw,encoded)
        self.assertEqual(set(result['issues']),set())
        result['comparison']['issues'].append({'side':'local','input_index':None,'code':'local'})
        self.assertEqual(self.store.get('gmais_jobs','job-test')['execution_input_binding_capture']['issues'],[])


if __name__=='__main__':unittest.main()
