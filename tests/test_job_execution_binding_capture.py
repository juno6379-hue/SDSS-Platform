import copy
import hashlib
import json
import threading
import unittest
from unittest.mock import patch
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from app.execution_binding_capture import build_submission_binding_capture, unavailable_capture
from app.job_execution_binding_capture import project_job_execution_binding_capture
from app.job_execution_binding_capture_api import create_job_execution_binding_capture_router, RESPONSE_SCHEMA


class StoredBindingCaptureTests(unittest.TestCase):
    def setUp(self):
        self.identity=dict(job_id='job-test',agent_id='lcluc-agent',trace_id='trace-test',captured_at='2026-10-17T00:00:00Z')
        self.ref=dict(id='secret-dataset',version='1',sha256='a'*64,role='secret-role',uri='private/file.tif')
        row=dict(input_index=0,id=self.ref['id'],version='1',sha256='a'*64,role=self.ref['role'],manifest_sha256='b'*64,integrity_verified=True)
        capture=build_submission_binding_capture([row],**self.identity)
        self.job=dict(id='job-test',job_id='job-test',agent_id='lcluc-agent',
                      status=dict(job_id='job-test',agent_id='lcluc-agent',trace_id='trace-test'),
                      request=dict(agent_id='lcluc-agent',execution_context=dict(trace_id='trace-test'),input_refs=[self.ref]),
                      execution_input_binding_capture=capture)

    def project(self,job=None,job_id='job-test'):
        return project_job_execution_binding_capture(self.job if job is None else job,job_id)

    def test_recorded_schema_counts_hash_privacy_and_approval(self):
        result=self.project();Draft202012Validator(RESPONSE_SCHEMA).validate(result)
        self.assertEqual(result['status'],'RECORDED');self.assertTrue(result['stored_binding_integrity_match'])
        for key in ('request_binding_count','capture_binding_count','manifest_pin_count'):self.assertEqual(result[key],1)
        self.assertEqual(result['request_job_sha256'],hashlib.sha256(b'job-test').hexdigest())
        self.assertEqual(result['expected_bindings_sha256'],self.job['execution_input_binding_capture']['expected_bindings_sha256'])
        for key,value in result.items():
            if type(value) is bool and key!='stored_binding_integrity_match':self.assertIs(value,False)
        encoded=json.dumps(result)
        for raw in ('job-test','lcluc-agent','trace-test','secret-dataset','secret-role','private/file.tif','b'*64):self.assertNotIn(raw,encoded)

    def test_legacy_and_null_capture_distinct_and_malformed_job_precedes_absence(self):
        legacy=copy.deepcopy(self.job);legacy.pop('execution_input_binding_capture')
        result=self.project(legacy);self.assertEqual(result['status'],'LEGACY');self.assertEqual(result['request_binding_count'],1)
        for key in ('capture_binding_count','manifest_pin_count','expected_bindings_sha256'):self.assertIsNone(result[key])
        legacy['execution_input_binding_capture']=None
        self.assertEqual(self.project(legacy)['issues'][0]['code'],'STORED_CAPTURE_INVALID')
        legacy.pop('execution_input_binding_capture');legacy['agent_id']='wrong'
        result=self.project(legacy);self.assertEqual(result['status'],'INVALID');self.assertIsNone(result['request_binding_count'])
        self.assertEqual(result['issues'][0]['code'],'STORED_JOB_INVALID')
        self.assertIsNotNone(result['request_job_sha256'])

    def test_unavailable_fallback_null_time_and_aware_time(self):
        for stamp in (None,self.identity['captured_at']):
            job=copy.deepcopy(self.job);job['execution_input_binding_capture']=unavailable_capture(stamp,'CAPTURE_BOUNDARY_FAILURE')
            result=self.project(job);self.assertEqual(result['status'],'UNAVAILABLE');self.assertEqual(result['request_binding_count'],1)
            self.assertIsNone(result['capture_binding_count']);self.assertFalse(result['stored_binding_integrity_match'])
        job['execution_input_binding_capture']['captured_at']='2026-01-01'
        self.assertEqual(self.project(job)['status'],'INVALID')

    def test_capture_exactkeys_schema_flags_and_zero_types(self):
        for key,value in [('schema_version',True),('status','OTHER'),('extension','bad'),('execution_authorized',True),
                          ('additional_registry_queries',False),('additional_artifact_reads',1),('additional_database_writes',0.0)]:
            job=copy.deepcopy(self.job);job['execution_input_binding_capture'][key]=value
            result=self.project(job);self.assertEqual(result['status'],'INVALID');self.assertEqual(result['request_binding_count'],1)
        for action in ('extra','missing'):
            job=copy.deepcopy(self.job)
            if action=='extra':job['execution_input_binding_capture']['secret']='private'
            else:job['execution_input_binding_capture'].pop('scope')
            self.assertEqual(self.project(job)['status'],'INVALID')

    def test_recorded_timestamp_issues_hash_and_typed_index(self):
        for key,value in [('captured_at',None),('captured_at','2026-01-01'),('expected_bindings_sha256','c'*64),
                          ('issues',[{'code':'CAPTURE_UNAVAILABLE','input_index':None}])]:
            job=copy.deepcopy(self.job);job['execution_input_binding_capture'][key]=value
            self.assertEqual(self.project(job)['status'],'INVALID')
        job=copy.deepcopy(self.job);job['execution_input_binding_capture']['expected_envelope']['bindings'][0]['input_index']=False
        self.assertEqual(self.project(job)['status'],'INVALID')

    def test_unavailable_safe_issue_allowlist_and_no_partial(self):
        valid=unavailable_capture(None,'CAPTURE_ROW_UNAVAILABLE',0)
        for mutate in (lambda c:c.update(issues=[]),lambda c:c.update(issues=[{'code':'secret','input_index':None}]),
                       lambda c:c['issues'][0].update(input_index=True),lambda c:c['issues'][0].update(input_index=1),
                       lambda c:c['issues'][0].update(raw='private'),lambda c:c.update(expected_envelope={}),
                       lambda c:c.update(expected_bindings_sha256='a'*64)):
            job=copy.deepcopy(self.job);job['execution_input_binding_capture']=copy.deepcopy(valid);mutate(job['execution_input_binding_capture'])
            self.assertEqual(self.project(job)['status'],'INVALID')
        job['execution_input_binding_capture']=valid
        self.assertEqual(self.project(job)['status'],'UNAVAILABLE')

    def test_capture_identity_and_request_role_linkage_even_rehashed(self):
        from app.execution_input_binding import compare_execution_input_bindings
        for path,key,value in [('envelope','job_id','other'),('envelope','agent_id','other'),('envelope','trace_id','other'),
                               ('row','id','different'),('row','version','2'),('row','sha256','e'*64),('row','role','different')]:
            job=copy.deepcopy(self.job);cap=job['execution_input_binding_capture'];env=cap['expected_envelope']
            (env if path=='envelope' else env['bindings'][0])[key]=value
            cap['expected_bindings_sha256']=compare_execution_input_bindings(env,env)['expected_bindings_sha256']
            self.assertEqual(self.project(job)['status'],'INVALID')
        job=copy.deepcopy(self.job);job['request']['input_refs'][0].pop('role')
        self.assertEqual(self.project(job)['status'],'INVALID')

    def test_request_identity_indices_types_budgets_and_no_unsafe_serialization(self):
        for mutate in (lambda j:j.update(id='wrong'),lambda j:j['status'].update(trace_id='other'),
                       lambda j:j['request'].update(input_refs=[]),lambda j:j['request'].update(input_refs=[{}]*65),
                       lambda j:j['request']['input_refs'][0].update(sha256=True),
                       lambda j:j['request']['input_refs'][0].update(version='latest'),
                       lambda j:j['request']['input_refs'][0].update(role='x'*257)):
            job=copy.deepcopy(self.job);mutate(job)
            self.assertEqual(self.project(job)['issues'][0]['code'],'STORED_JOB_INVALID')
        cycle=copy.deepcopy(self.job);cycle['request']['input_refs'][0]['role']=cycle
        self.assertEqual(self.project(cycle)['status'],'INVALID')
        for literal in ('x'*257,'x\u0085','\ud800',True):
            result=self.project(job_id=literal);self.assertEqual(result['status'],'INVALID');self.assertIsNone(result['request_job_sha256'])


    def test_identity_selected_fields_bound_before_comparison(self):
        class UnsafeEquality:
            def __eq__(self,other):raise AssertionError('compared before type guard')
        for section,key in ((None,'id'),(None,'job_id'),('status','job_id'),(None,'agent_id'),
                            ('status','agent_id'),('request','agent_id'),('status','trace_id'),('context','trace_id')):
            for value in ('x'*1000000,UnsafeEquality()):
                job=copy.deepcopy(self.job)
                target=job if section is None else job['request']['execution_context'] if section=='context' else job[section]
                target[key]=value
                self.assertEqual(self.project(job)['issues'][0]['code'],'STORED_JOB_INVALID')

    def test_input_immutable_and_no_io_or_registry(self):
        before=copy.deepcopy(self.job)
        with patch('builtins.open',side_effect=AssertionError('file read')),patch('app.dataset_registry.resolve_version',side_effect=AssertionError('registry')):
            result=self.project()
        self.assertEqual(self.job,before)
        result['issues'].append({'code':'local','input_index':None})
        self.assertEqual(self.job,before)

    def client(self,store,auth=False):
        app=FastAPI()
        async def token(authorization:str|None=Header(default=None)):
            if authorization!='allowed':raise HTTPException(401,'Unauthorized')
        app.include_router(create_job_execution_binding_capture_router(lambda:store),dependencies=[Depends(token)] if auth else [])
        return TestClient(app)

    def test_api_one_get_threadpool_no_store_and_no_write(self):
        main=threading.get_ident();calls=[];job=self.job
        class Store:
            def get(self,kind,key):
                calls.append((kind,key,threading.get_ident()));return job
        with self.client(Store()) as client:
            response=client.get('/v1/jobs/job-test/execution-input-binding')
            self.assertEqual(response.status_code,200);self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(len(calls),1);self.assertEqual(calls[0][:2],('gmais_jobs','job-test'));self.assertNotEqual(calls[0][2],main)
            self.assertEqual(response.json(),self.project())

    def test_api_safe_404_503_no_raw_exception(self):
        for error,status,code in ((KeyError('private'),404,'JOB_NOT_FOUND'),(RuntimeError('secret path'),503,'RESOURCE_UNAVAILABLE')):
            class Store:
                def get(self,*args):raise error
            with self.client(Store()) as client:
                response=client.get('/v1/jobs/job-test/execution-input-binding')
                self.assertEqual(response.status_code,status);self.assertEqual(response.json()['error']['code'],code)
                self.assertIs(response.json()['error']['retryable'],False);self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertNotIn('secret',response.text);self.assertNotIn('private',response.text)

    def test_api_invalid_literal_zero_db_and_auth_inheritance(self):
        class Store:
            def get(self,*args):raise AssertionError('no DB')
        with self.client(Store(),auth=True) as client:
            response=client.get('/v1/jobs/'+'x'*257+'/execution-input-binding')
            self.assertEqual(response.status_code,401)
            response=client.get('/v1/jobs/'+'x'*257+'/execution-input-binding',headers={'Authorization':'allowed'})
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['status'],'INVALID')

    def test_openapi_and_method_scope(self):
        class Store:pass
        with self.client(Store()) as client:
            path='/v1/jobs/{job_id}/execution-input-binding'
            schema=client.get('/openapi.json').json()['paths'][path]
            self.assertEqual(set(schema),{'get'});self.assertEqual(set(schema['get']['responses'])-{'422'},{'200','404','503'})
            self.assertEqual(client.post('/v1/jobs/job-test/execution-input-binding').status_code,405)


if __name__=='__main__':unittest.main()
