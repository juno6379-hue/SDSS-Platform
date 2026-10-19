import copy
import hashlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient

from app.workflow_node_input_handoff import compare_workflow_node_input_handoff, _digest
from app.workflow_node_input_handoff_api import (create_workflow_node_input_handoff_router,
    parse_handoff_request, validate_handoff_response, MAX_BODY_BYTES, MAX_INNER_BYTES, RequestTooLarge)
from test_workflow_node_input_handoff import fixture


PATH='/v1/workflows/node-input-handoff'


def envelope(workflow=None, proposal=None):
    base, proposed=fixture()
    workflow=base if workflow is None else workflow
    proposal=proposed if proposal is None else proposal
    return dict(workflow_request_json=json.dumps(workflow,ensure_ascii=False,indent=2),
        pinned_workflow_request_sha256=_digest(workflow),selected_node_id='private-node',
        proposed_job_metadata_json=json.dumps(proposal,ensure_ascii=False,indent=2))


def raw(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')


class WorkflowNodeHandoffApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(create_workflow_node_input_handoff_router())
        self.client=TestClient(app)

    def tearDown(self):self.client.close()

    def post(self,body=None):
        return self.client.post(PATH,content=raw(envelope()) if body is None else body,
            headers={'Content-Type':'application/json'})

    def assert_error(self,response,status,code):
        self.assertEqual(response.status_code,status,response.text)
        messages={'INVALID_REQUEST':'Invalid handoff request.',
            'REQUEST_TOO_LARGE':'Handoff request exceeds limits.',
            'RESOURCE_UNAVAILABLE':'Handoff comparison is unavailable.'}
        self.assertEqual(response.json(),{'error':{'code':code,'message':messages[code],'retryable':False}})
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_match_wrapper_raw_sha_one_worker_call_no_store_and_immutable(self):
        workflow,proposal=fixture();before=copy.deepcopy((workflow,proposal));body=raw(envelope(workflow,proposal))
        threads=[]
        def compare(*args):
            threads.append(threading.current_thread().name)
            return compare_workflow_node_input_handoff(*args)
        with (patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff',side_effect=compare) as call,
                patch('app.store.Store.get',side_effect=AssertionError('no Store'))):
            response=self.post(body)
        self.assertEqual(response.status_code,200,response.text)
        value=response.json();self.assertEqual(set(value),{'extension','approval_status','present_in_upstream_openapi','request_sha256','result'})
        self.assertEqual(value['extension'],'greenblue.workflow-node-input-handoff.rfc1')
        self.assertEqual(value['approval_status'],'INTERNAL_REVIEW');self.assertIs(value['present_in_upstream_openapi'],False)
        self.assertEqual(value['request_sha256'],hashlib.sha256(body).hexdigest())
        self.assertEqual(value['result']['status'],'MATCH');self.assertEqual(call.call_count,1)
        self.assertIn('worker',threads[0].lower());self.assertEqual((workflow,proposal),before)
        self.assertNotIn('file:///private',response.text);self.assertEqual(response.headers['cache-control'],'no-store')

    def test_valid_blocked_and_pin_mismatch_are_200_not_job_validation(self):
        value=envelope();value['pinned_workflow_request_sha256']='b'*64
        response=self.post(raw(value));self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['result']['issues'][0]['code'],'WORKFLOW_PIN_MISMATCH')
        value=envelope();value['proposed_job_metadata_json']='{}'
        response=self.post(raw(value));self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['result']['status'],'BLOCKED')
        self.assertFalse(response.json()['result']['complete_job_validated'])

    def test_outer_and_inner_duplicate_keys_rejected_before_core(self):
        value=envelope();body=raw(value).decode();body=body[:-1]+',"selected_node_id":"other"}'
        cases=[body.encode()]
        for key in ('workflow_request_json','proposed_job_metadata_json'):
            value=envelope();value[key]='{"agent_id":"one","agent_id":"two"}';cases.append(raw(value))
        with patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff') as call:
            for body in cases:self.assert_error(self.post(body),400,'INVALID_REQUEST')
            self.assertEqual(call.call_count,0)

    def test_outer_exact_type_keys_and_invalid_utf8(self):
        for body in (b'\xff',b'\xef\xbb\xbf{}',b'[]',b'null',b'{}',b'{broken'):
            self.assert_error(self.post(body),400,'INVALID_REQUEST')
        for field,value in (('selected_node_id',True),('pinned_workflow_request_sha256','A'*64),
                ('workflow_request_json',{}),('proposed_job_metadata_json',None),('extra','secret')):
            payload=envelope();payload[field]=value
            self.assert_error(self.post(raw(payload)),400,'INVALID_REQUEST')

    def test_nonfinite_float_big_integer_and_scalar_controls(self):
        for token in ('NaN','Infinity','-Infinity','1.0','1e4','2147483648'):
            for key in ('workflow_request_json','proposed_job_metadata_json'):
                payload=envelope();payload[key]='{"value":'+token+'}'
                self.assert_error(self.post(raw(payload)),400,'INVALID_REQUEST')
        payload=envelope();payload['workflow_request_json']='{"value":123456789012345678901234}'
        self.assert_error(self.post(raw(payload)),413,'REQUEST_TOO_LARGE')
        for text in ('{"value":"\\u0000"}','{"value":"\\u0085"}','{"value":"\\ud800"}',json.dumps({'value':'x'*257})):
            payload=envelope();payload['workflow_request_json']=text
            self.assert_error(self.post(raw(payload)),400,'INVALID_REQUEST')
        payload=envelope();payload['selected_node_id']='x\x85'
        self.assert_error(self.post(raw(payload)),400,'INVALID_REQUEST')

    def test_byte_depth_and_atom_budgets(self):
        self.assert_error(self.post(b' '* (MAX_BODY_BYTES+1)),413,'REQUEST_TOO_LARGE')
        payload=envelope();payload['workflow_request_json']=' '* (MAX_INNER_BYTES+1)
        self.assert_error(self.post(raw(payload)),413,'REQUEST_TOO_LARGE')
        payload=envelope();payload['workflow_request_json']='['*13+'0'+']'*13
        self.assert_error(self.post(raw(payload)),413,'REQUEST_TOO_LARGE')
        self.assert_error(self.post(('['*9+'0'+']'*9).encode()),413,'REQUEST_TOO_LARGE')
        payload=envelope();payload['workflow_request_json']='['+','.join(['null']*32769)+']'
        self.assert_error(self.post(raw(payload)),413,'REQUEST_TOO_LARGE')
        payload=envelope();payload['workflow_request_json']=json.dumps({'x':'['*256})
        self.assertEqual(self.post(raw(payload)).status_code,200,'quoted brackets are not structural depth')

    def test_inner_multibyte_utf8_byte_cap(self):
        payload=envelope();payload['workflow_request_json']='한'*(MAX_INNER_BYTES//3+1)
        self.assert_error(self.post(raw(payload)),413,'REQUEST_TOO_LARGE')

    def test_raw_whitespace_changes_outer_sha_not_semantic_workflow_pin(self):
        payload=envelope();first=self.post(raw(payload)).json()
        body=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
        second=self.post(body).json()
        self.assertNotEqual(first['request_sha256'],second['request_sha256'])
        self.assertEqual(first['result'],second['result'])
        self.assertEqual(second['request_sha256'],hashlib.sha256(body).hexdigest())

    def test_unicode_golden_fixture(self):
        path=Path(__file__).resolve().parents[1]/'evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json'
        value=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(_digest(value['workflow_request']),value['sha256'])
        self.assertEqual(hashlib.sha256(value['canonical_json'].encode()).hexdigest(),value['sha256'])
        payload=envelope(value['workflow_request'],value['proposed_job_metadata']);payload['selected_node_id']=value['selected_node_id']
        response=self.post(raw(payload));self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['result']['status'],'MATCH')

    def test_core_exception_safe_503_and_no_exception_leak(self):
        for exception in (RuntimeError('private path'),MemoryError('private bytes'),AssertionError('private token')):
            with patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff',side_effect=exception):
                response=self.post()
            self.assert_error(response,503,'RESOURCE_UNAVAILABLE');self.assertNotIn('private',response.text)

    def test_malformed_response_false_types_hash_counts_raw_and_cycles(self):
        workflow,proposal=fixture();good=compare_workflow_node_input_handoff(workflow,_digest(workflow),'private-node',proposal)
        mutations=[lambda v:v.update(raw={'secret':'file:///private'}),lambda v:v.update(schema_version=True),
            lambda v:v.update(execution_authorized=True),lambda v:v.update(source_files_read=False),
            lambda v:v.update(declarations_match=1),lambda v:v.update(workflow_request_sha256='b'*64),
            lambda v:v.update(pinned_workflow_request_sha256='b'*64),lambda v:v.update(selected_node_sha256='b'*64),
            lambda v:v.update(expected_metadata_sha256='b'*64),lambda v:v.update(proposed_metadata_sha256='b'*64),
            lambda v:v.update(selected_node_index=True),lambda v:v.update(expected_input_count=True),
            lambda v:v.update(proposed_input_count=2),lambda v:v.update(issues=[{}]*325),
            lambda v:v.update(status='BLOCKED',declarations_match=False),lambda v:v.update(scope='private')]
        for mutate in mutations:
            value=copy.deepcopy(good);mutate(value)
            with patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff',return_value=value):
                self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')
        cyclic=copy.deepcopy(good);cyclic['issues']=[cyclic]
        with patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff',return_value=cyclic):
            self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')

    def test_inherited_auth_dependency(self):
        app=FastAPI()
        async def auth(authorization:str|None=Header(default=None)):
            if authorization!='allowed':raise HTTPException(401,'Unauthorized')
        app.include_router(create_workflow_node_input_handoff_router(),dependencies=[Depends(auth)])
        with TestClient(app) as client:
            with patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff') as call:
                self.assertEqual(client.post(PATH,content=raw(envelope())).status_code,401)
                self.assertEqual(call.call_count,0)
            self.assertEqual(client.post(PATH,content=raw(envelope()),headers={'Authorization':'allowed'}).status_code,200)

    def test_response_issue_actual_list_indices_and_unknown_codes_rejected(self):
        workflow,proposal=fixture()
        good=compare_workflow_node_input_handoff(workflow,_digest(workflow),'private-node',proposal)
        for issue in (dict(code='NODE_SCHEMA_INVALID',side='workflow',node_index=127,input_index=None),
            dict(code='INPUT_SCHEMA_INVALID',side='workflow',node_index=0,input_index=63),
            dict(code='INPUT_SCHEMA_INVALID',side='proposal',node_index=None,input_index=63),
            dict(code='INPUT_ID_MISMATCH',side='comparison',node_index=0,input_index=63),
            dict(code='PRIVATE_PATH',side='workflow',node_index=0,input_index=None)):
            value=copy.deepcopy(good);value.update(status='BLOCKED',declarations_match=False,issues=[issue])
            with patch('app.workflow_node_input_handoff_api.compare_workflow_node_input_handoff',return_value=value):
                self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')

    def test_supported_core_subsets_pass_without_dag_or_execution_claim(self):
        workflow,proposal=fixture()
        workflow['policy']['unknown']='blocked'
        response=self.post(raw(envelope(workflow,proposal)))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['result']['issues'][0]['code'],'WORKFLOW_POLICY_INVALID')
        del workflow['policy']['unknown']
        other=copy.deepcopy(workflow['nodes'][0]);other.update(node_id='other',input_bindings=[],depends_on=['private-node'])
        workflow['nodes'].append(other);workflow['nodes'][0]['depends_on']=['other']
        response=self.post(raw(envelope(workflow,proposal)))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['result']['status'],'MATCH')
        self.assertFalse(response.json()['result']['dag_validated'])
        self.assertFalse(response.json()['result']['execution_authorized'])

    def test_core_existing_contract_and_source_objects_remain_unchanged(self):
        workflow,proposal=fixture();before=copy.deepcopy((workflow,proposal))
        result=compare_workflow_node_input_handoff(workflow,_digest(workflow),'private-node',proposal)
        payload=envelope(workflow,proposal);parsed,w,p=parse_handoff_request(raw(payload))
        self.assertEqual(validate_handoff_response(result,parsed,w,p),result)
        self.assertEqual((workflow,proposal),before)


if __name__=='__main__':unittest.main()
