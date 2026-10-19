import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import test_job_execution_binding_capture as fixtures
from app.execution_binding_capture import unavailable_capture
from app.execution_input_binding import compare_execution_input_bindings
from app.stored_job_binding_handoff import compare_stored_job_binding_handoff


class StoredJobBindingHandoffTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.StoredBindingCaptureTests();fixture.setUp()
        self.job=fixture.job
        self.supplied=copy.deepcopy(self.job['execution_input_binding_capture']['expected_envelope'])

    def compare(self,job=None,supplied=None,job_id='job-test'):
        return compare_stored_job_binding_handoff(self.job if job is None else job,job_id,
                                                self.supplied if supplied is None else supplied)

    def legacy(self,state='LEGACY'):
        job=copy.deepcopy(self.job)
        if state=='LEGACY':job.pop('execution_input_binding_capture')
        else:job['execution_input_binding_capture']=unavailable_capture(None,'CAPTURE_BOUNDARY_FAILURE')
        return job

    def test_recorded_match_and_all_false_no_executor_claim(self):
        result=self.compare()
        self.assertEqual(result['status'],'MATCH');self.assertTrue(result['declarations_match'])
        self.assertEqual(result['stored_capture_status'],'RECORDED')
        self.assertEqual(result['request_binding_count'],1);self.assertEqual(result['stored_expected_binding_count'],1)
        self.assertEqual(result['supplied_binding_count'],1);self.assertEqual(result['issues'],[])
        false=[value for key,value in result.items() if type(value) is bool and key!='declarations_match']
        self.assertEqual(len(false),15);self.assertTrue(all(value is False for value in false))

    def test_no_caller_expected_parameter(self):
        with self.assertRaises(TypeError):compare_stored_job_binding_handoff(self.job,'job-test',self.supplied,expected=self.supplied)

    def test_legacy_unavailable_unknown_not_filled_from_supplied_pins(self):
        for state in ('LEGACY','UNAVAILABLE'):
            for pin in (True,False):
                supplied=copy.deepcopy(self.supplied)
                if not pin:supplied['bindings'][0].pop('manifest_sha256')
                result=self.compare(self.legacy(state),supplied)
                self.assertEqual(result['status'],'UNKNOWN');self.assertEqual(result['stored_capture_status'],state)
                self.assertIsNone(result['expected_bindings_sha256']);self.assertIsNone(result['stored_expected_binding_count'])
                self.assertEqual(result['request_binding_count'],1);self.assertIsNotNone(result['supplied_bindings_sha256'])

    def test_invalid_supplied_wins_over_legacy_unavailable(self):
        for state in ('LEGACY','UNAVAILABLE'):
            for supplied in ({},[],dict(self.supplied,bindings=[])):
                result=self.compare(self.legacy(state),supplied)
                self.assertEqual(result['status'],'BLOCKED');self.assertIsNone(result['supplied_bindings_sha256'])
                self.assertEqual(result['issues'][0]['side'],'supplied')

    def test_legacy_unavailable_visible_identity_mismatch_blocks(self):
        for state in ('LEGACY','UNAVAILABLE'):
            for field in ('job_id','agent_id','trace_id'):
                supplied=copy.deepcopy(self.supplied);supplied[field]='changed'
                self.assertEqual(self.compare(self.legacy(state),supplied)['status'],'BLOCKED')
            for field,value in (('id','other'),('version','2'),('sha256','e'*64),('role','other')):
                supplied=copy.deepcopy(self.supplied);supplied['bindings'][0][field]=value
                self.assertEqual(self.compare(self.legacy(state),supplied)['status'],'BLOCKED')
            supplied=copy.deepcopy(self.supplied);supplied['bindings'][0].pop('role')
            self.assertEqual(self.compare(self.legacy(state),supplied)['status'],'BLOCKED')

    def test_recorded_manifest_pin_missing_changed_or_bad(self):
        for value in (None,'e'*64,True):
            supplied=copy.deepcopy(self.supplied)
            if value is None:supplied['bindings'][0].pop('manifest_sha256')
            else:supplied['bindings'][0]['manifest_sha256']=value
            self.assertEqual(self.compare(supplied=supplied)['status'],'BLOCKED')

    def test_recorded_job_or_capture_invalid_cannot_be_expected(self):
        for mutate in (lambda j:j.update(agent_id='wrong'),lambda j:j['execution_input_binding_capture'].update(expected_bindings_sha256='e'*64),
                       lambda j:j['execution_input_binding_capture'].update(execution_authorized=True),
                       lambda j:j['execution_input_binding_capture'].update(additional_registry_queries=False)):
            job=copy.deepcopy(self.job);mutate(job)
            result=self.compare(job);self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['stored_capture_status'],'INVALID')
        job=copy.deepcopy(self.job);job.pop('execution_input_binding_capture');job['status']['job_id']='wrong'
        self.assertEqual(self.compare(job)['status'],'BLOCKED')

    def test_joint_invalid_safe_reasons_and_job_hash(self):
        job=copy.deepcopy(self.job);job['agent_id']='wrong'
        result=self.compare(job,{})
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual({x['side'] for x in result['issues']},{'stored','supplied'})
        self.assertEqual(result['request_job_sha256'],hashlib.sha256(b'job-test').hexdigest())
        self.assertIsNone(self.compare(job_id='x'*257)['request_job_sha256'])

    def test_order_count_and_index_prevent_handoff(self):
        job=copy.deepcopy(self.job);ref=copy.deepcopy(job['request']['input_refs'][0]);ref['version']='2'
        job['request']['input_refs'].append(ref)
        env=job['execution_input_binding_capture']['expected_envelope']
        row=copy.deepcopy(env['bindings'][0]);row.update(input_index=1,version='2');env['bindings'].append(row)
        job['execution_input_binding_capture']['expected_bindings_sha256']=compare_execution_input_bindings(env,env)['expected_bindings_sha256']
        supplied=copy.deepcopy(env);supplied['bindings'].reverse()
        self.assertEqual(self.compare(job,supplied)['status'],'BLOCKED')
        for index,row in enumerate(supplied['bindings']):row['input_index']=index
        self.assertEqual(self.compare(job,supplied)['status'],'BLOCKED')
        self.assertEqual(self.compare(job,env)['status'],'MATCH')

    def test_supplied_types_limits_cycles_and_conflicts(self):
        for field,value in (('input_index',True),('input_index',10**400),('id','x'*257),('role','x\u0085'),('sha256','A'*64)):
            supplied=copy.deepcopy(self.supplied);supplied['bindings'][0][field]=value
            self.assertEqual(self.compare(supplied=supplied)['status'],'BLOCKED')
        for rows in ([{}]*65,[]):
            self.assertEqual(self.compare(supplied=dict(self.supplied,bindings=rows))['status'],'BLOCKED')
        cycle=copy.deepcopy(self.supplied);cycle['bindings'][0]['role']=cycle
        self.assertEqual(self.compare(supplied=cycle)['status'],'BLOCKED')
        conflict=copy.deepcopy(self.supplied);row=copy.deepcopy(conflict['bindings'][0]);row.update(input_index=1,sha256='e'*64);conflict['bindings'].append(row)
        self.assertEqual(self.compare(supplied=conflict)['status'],'BLOCKED')

    def test_bounded_issues_and_no_identity_or_exception_leak(self):
        supplied=dict(self.supplied,bindings=[{'input_index':False,'id':'secret','version':'latest','sha256':'invalid'}]*64)
        result=self.compare(supplied=supplied)
        self.assertLessEqual(len(result['issues']),512)
        for issue in result['issues']:self.assertEqual(set(issue),{'side','code','input_index'})
        encoded=json.dumps(result)
        for raw in ('job-test','lcluc-agent','trace-test','secret-dataset','secret-role','private/file.tif','b'*64):self.assertNotIn(raw,encoded)

    def test_digest_is_ordered_bindings_only_not_whole_identity(self):
        result=self.compare()
        expected=hashlib.sha256(json.dumps(self.supplied['bindings'],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(result['supplied_bindings_sha256'],expected)
        changed=copy.deepcopy(self.supplied);changed['job_id']='other'
        result=self.compare(supplied=changed);self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['supplied_bindings_sha256'],expected)

    def test_no_io_registry_or_input_mutation(self):
        before=(copy.deepcopy(self.job),copy.deepcopy(self.supplied))
        with patch('builtins.open',side_effect=AssertionError('file')),patch('app.dataset_registry.resolve_version',side_effect=AssertionError('Registry')):
            result=self.compare()
        self.assertEqual((self.job,self.supplied),before)
        self.assertEqual([result[k] for k in ('network_requests','source_files_read','source_files_written','database_calls','registry_calls','resolver_calls','executor_calls')],[0]*7)
        result['issues'].append({'side':'local','code':'local','input_index':None})
        self.assertEqual((self.job,self.supplied),before)


if __name__=='__main__':unittest.main()
