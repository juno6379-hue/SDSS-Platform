import asyncio
import copy
import json
import threading
import unittest
from unittest.mock import patch
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
import test_stored_current_binding_preflight as fixtures
from app.dataset_registry import register_version
from app.stored_current_binding_preflight import inspect_stored_current_binding_preflight
from app.stored_current_binding_preflight_api import create_stored_current_binding_preflight_router,RESPONSE_SCHEMA,validate_preflight_response
from app.job_execution_binding_capture_api import create_job_execution_binding_capture_router


class CurrentInputPreflightApiTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.StoredCurrentBindingPreflightTests();self.fixture.setUp()
        self.store=self.fixture.store
        self.app=FastAPI();self.router=create_stored_current_binding_preflight_router(lambda:self.store)
        self.app.include_router(self.router);self.app.include_router(create_job_execution_binding_capture_router(lambda:self.store))
        self.client=TestClient(self.app)

    def tearDown(self):self.client.close();self.fixture.tearDown()

    def get(self,job_id='job-test'):return self.client.get('/v1/jobs/'+job_id+'/input-preflight')

    def test_positive_match_exact_schema_and_current_io(self):
        with patch.object(self.store,'get',wraps=self.store.get) as get:response=self.get()
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['status'],'MATCH')
        self.assertEqual([call.args[0] for call in get.call_args_list],['gmais_jobs','dataset_versions'])
        self.assertEqual(response.headers['cache-control'],'no-store');Draft202012Validator(RESPONSE_SCHEMA).validate(response.json())
        self.assertEqual(validate_preflight_response(response.json(),'job-test'),response.json())

    def test_quality_blocked_and_pin_match_remains_200_blocked(self):
        register_version(self.store,dict(self.fixture.fixture.fixture.manifest,version='raw',quality_status='RAW'))
        self.fixture.save_job([dict(self.fixture.ref,version='raw')])
        response=self.get();self.assertEqual(response.status_code,200,response.text)
        value=response.json();self.assertEqual(value['status'],'BLOCKED');self.assertEqual(value['binding_comparison']['status'],'MATCH')
        self.assertFalse(value['current_quality_public_diagnostics_passed'])

    def test_legacy_unknown_and_old_get_payload_unchanged(self):
        job=copy.deepcopy(self.fixture.job);job.pop('execution_input_binding_capture');self.store.put('gmais_jobs',job)
        old_path='/v1/jobs/job-test/execution-input-binding'
        before=self.client.get(old_path).json();response=self.get()
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['status'],'UNKNOWN')
        self.assertEqual(response.json()['resolver_pass_calls'],0)
        self.assertEqual(self.client.get(old_path).json(),before)

    def test_literal_invalid_400_get_zero_and_auth_inherited(self):
        for literal in ('x'*257,'x%20','x%C2%85'):
            if literal=='x%20':continue  # trailing ordinary space remains a supported literal.
            with patch.object(self.store,'get',side_effect=AssertionError('get')):response=self.get(literal)
            self.assertEqual(response.status_code,400);self.assertEqual(response.json()['error']['code'],'INVALID_REQUEST')
            self.assertIs(response.json()['error']['retryable'],False);self.assertEqual(response.headers['cache-control'],'no-store')
        app=FastAPI()
        async def auth(authorization:str|None=Header(default=None)):
            if authorization!='allowed':raise HTTPException(401,'Unauthorized')
        app.include_router(create_stored_current_binding_preflight_router(lambda:self.store),dependencies=[Depends(auth)])
        with TestClient(app) as client:self.assertEqual(client.get('/v1/jobs/job-test/input-preflight').status_code,401)

    def test_missing_and_resource_errors_safe_no_store(self):
        response=self.get('missing');self.assertEqual(response.status_code,404)
        self.assertEqual(response.json(),{'error':{'code':'JOB_NOT_FOUND','message':'Job was not found.','retryable':False}})
        for error in (RuntimeError('secret path'),AssertionError('private failure'),ValueError('secret')):
            with patch('app.stored_current_binding_preflight_api.inspect_stored_current_binding_preflight',side_effect=error):response=self.get()
            self.assertEqual(response.status_code,503);self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertNotIn('secret',response.text);self.assertNotIn('private',response.text)
        self.assertEqual(self.get().status_code,200,'lock leaked on error')

    def test_current_resolver_resource_maps_503(self):
        with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=MemoryError('secret')):response=self.get()
        self.assertEqual(response.status_code,503);self.assertEqual(response.json()['error']['code'],'RESOURCE_UNAVAILABLE')

    def test_malformed_safe_response_rejected_before_serialization(self):
        good=inspect_stored_current_binding_preflight(self.store,'job-test')
        mutations=[lambda v:v.update(raw_job={'private':'path'}),lambda v:v.update(schema_version=True),
                   lambda v:v.update(request_job_sha256='e'*64),lambda v:v.update(current_input_count=True),
                   lambda v:v.update(current_quality_public_observed_count=0),lambda v:v.update(current_blockers=[{}]*769),
                   lambda v:v.update(execution_authorized=True),lambda v:v['binding_comparison'].update(database_calls=False),
                   lambda v:v['binding_comparison'].update(raw='secret'),lambda v:v['binding_comparison'].update(ready_for_training=True),
                   lambda v:v['binding_comparison'].update(request_job_sha256='e'*64),lambda v:v['binding_comparison'].update(issues=[{}]*513),
                   lambda v:v['binding_comparison'].update(supplied_bindings_sha256='e'*64),lambda v:v.update(binding_comparison=None)]
        for mutate in mutations:
            value=copy.deepcopy(good);mutate(value)
            with patch('app.stored_current_binding_preflight_api.inspect_stored_current_binding_preflight',return_value=value):response=self.get()
            self.assertEqual(response.status_code,503)
            self.assertNotIn('secret',response.text)

    def test_status_count_null_and_unknown_or_nested_code_contradictions(self):
        good=inspect_stored_current_binding_preflight(self.store,'job-test')
        for mutate in (lambda v:v.update(status='UNKNOWN'),lambda v:v.update(store_read_observed=False),
                       lambda v:v.update(resolver_pass_calls=0),lambda v:v.update(current_resolution_status='NOT_RUN'),
                       lambda v:v.update(issues=[{'code':'secret'}]),lambda v:v.update(issues=[{'code':{}}]),
                       lambda v:v.update(current_blocker_count=1)):
            value=copy.deepcopy(good);mutate(value)
            with self.assertRaises(ValueError):validate_preflight_response(value,'job-test')
        cycle=copy.deepcopy(good);cycle['issues']=[{'code':cycle}]
        with self.assertRaises(ValueError):validate_preflight_response(cycle,'job-test')


    def test_quality_integrity_and_same_pass_capture_count_coherence(self):
        register_version(self.store,dict(self.fixture.fixture.fixture.manifest,version='raw-check',quality_status='RAW'))
        self.fixture.save_job([dict(self.fixture.ref,version='raw-check')])
        blocked=inspect_stored_current_binding_preflight(self.store,'job-test')
        self.assertEqual(validate_preflight_response(blocked,'job-test'),blocked)
        for mutate in (lambda v:v.update(current_integrity_verified_count=0),
                       lambda v:v.update(current_quality_public_observed_count=0),
                       lambda v:v.update(current_quality_public_diagnostics_passed=True),
                       lambda v:v.update(current_blockers=v['current_blockers']*2,current_blocker_count=2)):
            value=copy.deepcopy(blocked);mutate(value)
            with self.assertRaises(ValueError):validate_preflight_response(value,'job-test')
        # Registry/URI failures explain integrity false, not merely quality diagnostics.
        failed=copy.deepcopy(blocked)
        failed.update(current_integrity_verified_count=0,current_quality_public_observed_count=1,
                      current_quality_public_diagnostics_passed=True,current_blockers=[{'code':'INPUT_URI_MISMATCH','input_index':0}],
                      current_blocker_count=1,current_capture_status='UNAVAILABLE',binding_comparison=None,issues=[{'code':'CURRENT_CAPTURE_UNAVAILABLE'}])
        self.assertEqual(validate_preflight_response(failed,'job-test'),failed)
        for mutate in (lambda v:v.update(current_quality_public_diagnostics_passed=False),
                       lambda v:v.update(current_integrity_verified_count=1),
                       lambda v:v.update(current_capture_status='RECORDED',binding_comparison=blocked['binding_comparison'],issues=[{'code':'CURRENT_INPUT_DIAGNOSTICS_BLOCKED'}])):
            value=copy.deepcopy(failed);mutate(value)
            with self.assertRaises(ValueError):validate_preflight_response(value,'job-test')

    def test_worker_thread_and_single_busy_gate(self):
        started=threading.Event();release=threading.Event();calls=[];main=threading.get_ident()
        good=inspect_stored_current_binding_preflight(self.store,'job-test')
        def work(*args):
            calls.append(threading.get_ident());started.set();release.wait(5);return good
        responses=[]
        def request():responses.append(self.get())
        with patch('app.stored_current_binding_preflight_api.inspect_stored_current_binding_preflight',side_effect=work):
            thread=threading.Thread(target=request);thread.start()
            try:
                self.assertTrue(started.wait(3));busy=self.get()
                self.assertEqual(busy.status_code,429);self.assertEqual(busy.headers['retry-after'],'1')
                self.assertIs(busy.json()['error']['retryable'],True);self.assertEqual(busy.headers['cache-control'],'no-store')
            finally:release.set();thread.join(5)
        self.assertEqual(responses[0].status_code,200);self.assertNotEqual(calls[0],main)
        self.assertEqual(self.get().status_code,200)

    def test_cancelled_request_keeps_gate_until_actual_worker_finishes(self):
        started=threading.Event();release=threading.Event();finished=threading.Event()
        good=inspect_stored_current_binding_preflight(self.store,'job-test')
        endpoint=next(route.endpoint for route in self.router.routes if route.path.endswith('/input-preflight'))
        def work(*args):
            started.set()
            try:release.wait(5);return good
            finally:finished.set()
        async def scenario():
            first=asyncio.create_task(endpoint('job-test'))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait,3))
                first.cancel()
                try:await first
                except asyncio.CancelledError:pass
                busy=await endpoint('job-test');self.assertEqual(busy.status_code,429)
            finally:release.set()
            self.assertTrue(await asyncio.to_thread(finished.wait,3))
            # finished marks core return; worker validation/finally may finish just afterwards.
            for _ in range(100):
                next_response=await endpoint('job-test')
                if next_response.status_code!=429:break
                await asyncio.sleep(.01)
            self.assertEqual(next_response.status_code,200)
        with patch('app.stored_current_binding_preflight_api.inspect_stored_current_binding_preflight',side_effect=work):asyncio.run(scenario())

    def test_baseexception_not_swallowed_in_endpoint(self):
        endpoint=next(route.endpoint for route in self.router.routes if route.path.endswith('/input-preflight'))
        class Stop(BaseException):pass
        async def scenario():
            with self.assertRaises(Stop):await endpoint('job-test')
        with patch('app.stored_current_binding_preflight_api.inspect_stored_current_binding_preflight',side_effect=Stop()):asyncio.run(scenario())
        self.assertEqual(self.get().status_code,200)

    def test_openapi_getonly_error_contract(self):
        path='/v1/jobs/{job_id}/input-preflight'
        schema=self.client.get('/openapi.json').json()['paths'][path]
        self.assertEqual(set(schema),{'get'})
        self.assertEqual(set(schema['get']['responses'])-{'422'},{'200','400','404','429','503'})
        self.assertEqual(self.client.post('/v1/jobs/job-test/input-preflight').status_code,405)


if __name__=='__main__':unittest.main()
