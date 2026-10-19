import copy
import hashlib
import json
import threading
import unittest
from unittest.mock import patch

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient

from app.workflow_job_request_handoff import compare_workflow_job_request_handoff
from app.workflow_job_request_handoff_api import (create_workflow_job_request_handoff_router,
    parse_full_job_handoff_request, validate_full_job_handoff_response, MAX_BODY_BYTES, MAX_INNER_BYTES)
from app.workflow_node_input_handoff import _digest
from test_workflow_job_request_handoff import full_fixture

PATH='/v1/workflows/full-job-input-handoff'
MODULE='app.workflow_job_request_handoff_api.'


def envelope(workflow=None,job=None):
    w,j=full_fixture();w=w if workflow is None else workflow;j=j if job is None else job
    return dict(workflow_request_json=json.dumps(w,ensure_ascii=False,indent=2),
        pinned_workflow_request_sha256=_digest(w),selected_node_id='private-node',
        full_job_request_json=json.dumps(j,ensure_ascii=False,indent=2))


def raw(value): return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')


class WorkflowJobRequestHandoffApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(create_workflow_job_request_handoff_router());self.client=TestClient(app)
    def tearDown(self): self.client.close()
    def post(self,body=None): return self.client.post(PATH,content=raw(envelope()) if body is None else body,headers={'Content-Type':'application/json'})
    def assert_error(self,r,status,code):
        messages={'INVALID_REQUEST':'Invalid full Job handoff request.','REQUEST_TOO_LARGE':'Full Job handoff request exceeds limits.','RESOURCE_UNAVAILABLE':'Full Job handoff comparison is unavailable.'}
        self.assertEqual(r.status_code,status,r.text)
        self.assertEqual(r.json(),{'error':{'code':code,'message':messages[code],'retryable':False}})
        self.assertEqual(r.headers['cache-control'],'no-store')

    def test_match_worker_wrapper_rawbody_sha_privacy_no_store(self):
        e=envelope();before=copy.deepcopy(e);body=raw(e);threads=[]
        def execute(*args):
            threads.append(threading.current_thread().name);return compare_workflow_job_request_handoff(*args)
        with patch(MODULE+'compare_workflow_job_request_handoff',side_effect=execute) as spy,patch('app.store.Store.get',side_effect=AssertionError('no Store')):
            r=self.post(body)
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(e,before);self.assertEqual(spy.call_count,1)
        self.assertIn('worker',threads[0].lower());v=r.json()
        self.assertEqual(set(v),{'extension','approval_status','present_in_upstream_openapi','request_sha256','result'})
        self.assertEqual(v['extension'],'greenblue.workflow-full-job-input-handoff.rfc1');self.assertEqual(v['approval_status'],'INTERNAL_REVIEW')
        self.assertIs(v['present_in_upstream_openapi'],False);self.assertEqual(v['request_sha256'],hashlib.sha256(body).hexdigest())
        self.assertEqual(v['result']['status'],'MATCH');self.assertEqual(r.headers['cache-control'],'no-store')
        for secret in ('private-node','private-purpose','file:///private','private-trace'):self.assertNotIn(secret,r.text)

    def test_decimal_exponent_negative_zero_and_server_observation(self):
        for token in ('1.0','1e0','-0.0','1e-7','5e-324','0e-999'):
            e=envelope();j=json.loads(e['full_job_request_json']);j['parameters']={'value':'TOKEN'}
            e['full_job_request_json']=json.dumps(j).replace('"TOKEN"',token)
            r=self.post(raw(e));self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()['result']['full_job_request_sha256'],_digest(json.loads(e['full_job_request_json'])))
        e=envelope();e['full_job_request_json']=e['full_job_request_json'].replace('106.1','"106.1"')
        self.assertEqual(self.post(raw(e)).json()['result']['validator_status'],'INVALID')

    def test_valid_schema_blocked_and_metadata_blocked_are_200(self):
        for mutate in (lambda j:j.pop('aoi'),lambda j:j['input_refs'][0].update(role='changed'),
                lambda j:j['aoi'].update(bbox=[True,-6,106,-5]),lambda j:j['aoi'].update(bbox=[106,-6,105,-5]),
                lambda j:j['execution_context'].update(workflow_run_id='other')):
            w,j=full_fixture();mutate(j);r=self.post(raw(envelope(w,j)))
            self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['result']['status'],'BLOCKED')
        e=envelope();e['pinned_workflow_request_sha256']='b'*64
        self.assertEqual(self.post(raw(e)).status_code,200)

    def test_early_parsed_scalar_and_workflow_schema_blocked(self):
        for key,value in (('full_job_request_json','[]'),('full_job_request_json','{}'),('workflow_request_json','{}')):
            e=envelope();e[key]=value;r=self.post(raw(e))
            self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['result']['status'],'BLOCKED')

    def test_duplicate_outer_workflow_fulljob_and_invalid_utf8(self):
        e=envelope();b=raw(e)
        bodies=[b[:-1]+b',"selected_node_id":"private-node"}',b'\xff',b'{}',b'{"x":NaN}']
        for key in ('workflow_request_json','full_job_request_json'):
            changed=copy.deepcopy(e);changed[key]='{"x":1,"x":2}';bodies.append(raw(changed))
        with patch(MODULE+'compare_workflow_job_request_handoff',side_effect=AssertionError('must not call')) as spy:
            for body in bodies:self.assert_error(self.post(body),400,'INVALID_REQUEST')
            self.assertEqual(spy.call_count,0)

    def test_nonfinite_overflow_underflow_int53_and_surrogate_rejected(self):
        for token in ('NaN','Infinity','-Infinity','1e309','1e-999','-1e-999','9007199254740992','-9007199254740992','0e99999999999999999999999999999','0e-99999999999999999999999999999','1e-99999999999999999999999999999','"\\ud800"'):
            e=envelope();e['full_job_request_json']='{"parameters":{"value":'+token+'}}'
            self.assert_error(self.post(raw(e)),400,'INVALID_REQUEST')
        e=envelope();e['full_job_request_json']='{"parameters":{"value":9007199254740991}}'
        self.assertEqual(self.post(raw(e)).status_code,200)

    def test_quoted_numeric_no_coercion_and_workflow_remains_integer_only(self):
        e=envelope();e['workflow_request_json']=e['workflow_request_json'].replace('"max_parallel": 1','"max_parallel": 1.0')
        self.assert_error(self.post(raw(e)),400,'INVALID_REQUEST')
        e=envelope();e['full_job_request_json']=e['full_job_request_json'].replace('106.1','true')
        r=self.post(raw(e));self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['result']['validator_status'],'INVALID')

    def test_body_inner_string_key_atom_depth_numeric_budgets(self):
        cases=[b' '* (MAX_BODY_BYTES+1)]
        for text in (' '* (MAX_INNER_BYTES+1),'['*25+'0'+']'*25,json.dumps({'parameters':{'x':'a'*4097}}),
                json.dumps({'parameters':{'k'*257:0}}),json.dumps({'parameters':list(range(17000))}),
                '{"parameters":{"x":0.'+'1'*128+'}}'):
            e=envelope();e['full_job_request_json']=text;cases.append(raw(e))
        for body in cases:self.assert_error(self.post(body),413,'REQUEST_TOO_LARGE')

    def test_exact_envelope_identity_and_no_source_coercion(self):
        for mutate in (lambda e:e.update(extra=1),lambda e:e.pop('selected_node_id'),lambda e:e.update(full_job_request_json={}),
                lambda e:e.update(selected_node_id=' '),lambda e:e.update(pinned_workflow_request_sha256='A'*64)):
            e=envelope();mutate(e);self.assert_error(self.post(raw(e)),400,'INVALID_REQUEST')

    def test_core_resource_and_unexpected_exception_503_private(self):
        with patch('app.workflow_job_request_handoff._job_request_validator',side_effect=OSError('private/path')):
            self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')
        with patch(MODULE+'compare_workflow_job_request_handoff',side_effect=RuntimeError('private/path')):
            self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')

    def test_typed_false_io_schema_read_counts_and_hash_corruption_fail_closed(self):
        e,w,j=parse_full_job_handoff_request(raw(envelope()));base=compare_workflow_job_request_handoff(w,e['pinned_workflow_request_sha256'],e['selected_node_id'],j)
        mutations=[lambda r:r.update(extra='private'),lambda r:r.update(schema_version=True),lambda r:r.update(database_calls=False),
            lambda r:r.update(execution_authorized=True),lambda r:r.update(schema_files_read=0),lambda r:r.update(comparator_calls=True),
            lambda r:r.update(full_job_request_sha256='b'*64),lambda r:r.update(extracted_metadata_sha256='b'*64),
            lambda r:r.update(validator_attempted=False),lambda r:r.update(full_job_schema_validated=False),
            lambda r:r.update(bbox_numeric_order_validated=False),lambda r:r.update(validator_status='NOT_RUN')]
        for mutate in mutations:
            r=copy.deepcopy(base);mutate(r)
            with patch(MODULE+'compare_workflow_job_request_handoff',return_value=r):self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')

    def test_inner_indices_counts_hashes_and_phase_contradictions_fail_closed(self):
        e,w,j=parse_full_job_handoff_request(raw(envelope()));j['input_refs'][0]['role']='changed';e=envelope(w,j)
        base=compare_workflow_job_request_handoff(w,e['pinned_workflow_request_sha256'],e['selected_node_id'],j)
        for mutate in (lambda r:r['metadata_comparison']['issues'][0].update(input_index=1),
                lambda r:r['metadata_comparison'].update(proposed_input_count=2),lambda r:r.update(issues=[]),
                lambda r:r.update(metadata_comparison=None),lambda r:r.update(comparator_calls=0)):
            result=copy.deepcopy(base);mutate(result)
            with patch(MODULE+'compare_workflow_job_request_handoff',return_value=result):self.assert_error(self.post(raw(e)),503,'RESOURCE_UNAVAILABLE')
        e=envelope();e['full_job_request_json']='[]';a,w,j=parse_full_job_handoff_request(raw(e));r=compare_workflow_job_request_handoff(w,a['pinned_workflow_request_sha256'],a['selected_node_id'],j)
        r['full_job_request_sha256']='a'*64
        with patch(MODULE+'compare_workflow_job_request_handoff',return_value=r):self.assert_error(self.post(raw(e)),503,'RESOURCE_UNAVAILABLE')

    def test_router_inherits_auth_dependency(self):
        def auth(authorization: str|None=Header(default=None)):
            if authorization!='Bearer test':raise HTTPException(status_code=401,detail='Unauthorized')
        app=FastAPI(dependencies=[Depends(auth)]);app.include_router(create_workflow_job_request_handoff_router())
        with TestClient(app) as client:
            self.assertEqual(client.post(PATH,content=raw(envelope())).status_code,401)
            self.assertEqual(client.post(PATH,content=raw(envelope()),headers={'Authorization':'Bearer test'}).status_code,200)

    def test_stream_body_limit_and_parser_resource_failures(self):
        with patch(MODULE+'MAX_BODY_BYTES',32):self.assert_error(self.post(),413,'REQUEST_TOO_LARGE')
        with patch(MODULE+'parse_full_job_handoff_request',side_effect=OSError('private')):self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')

    def test_existing_router_response_unchanged(self):
        from app.workflow_node_input_handoff_api import create_workflow_node_input_handoff_router
        from test_workflow_node_input_handoff_api import envelope as old_envelope
        app=FastAPI();app.include_router(create_workflow_node_input_handoff_router())
        with TestClient(app) as client:
            before=client.post('/v1/workflows/node-input-handoff',content=raw(old_envelope())).json()
            self.assertEqual(self.post().status_code,200)
            after=client.post('/v1/workflows/node-input-handoff',content=raw(old_envelope())).json()
        self.assertEqual(before,after)


if __name__=='__main__':unittest.main()
