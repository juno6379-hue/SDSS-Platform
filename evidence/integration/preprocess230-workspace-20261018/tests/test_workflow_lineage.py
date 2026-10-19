"""Workflow 전역 계보 예산·raw 본문 신원·선검증·비실행 companion 회귀."""
import copy
import hashlib
import json
import os
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import test_dataset_lineage as fixtures
import test_gmais_api as app_fixtures
from app.workflow_lineage import validate_workflow_lineage, WorkflowLineageRequestError
from app.workflow_lineage_api import create_workflow_lineage_router


class WorkflowLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.DatasetLineageTests();self.fixture.setUp();self.store=self.fixture.store
        self.ref=self.fixture.dataset('workflow-root')
        app=FastAPI();app.include_router(create_workflow_lineage_router(lambda:self.store));self.client=TestClient(app)
        self.old_store=app_fixtures.main.store;app_fixtures.main.store=self.store
        self.main_client=TestClient(app_fixtures.main.app)
        self.auth=patch.dict(os.environ,{'GEOAI_API_TOKEN':''});self.auth.start()
        self.uri='/v1/workflows/lineage-validation'

    def tearDown(self):
        self.auth.stop();self.main_client.close();self.client.close()
        app_fixtures.main.store=self.old_store;self.fixture.tearDown()

    def node(self,name,refs=None,deps=()):
        return {'node_id':name,'agent_id':'lcluc-agent','capability_id':'landcover.change_detection',
                'depends_on':list(deps),'input_bindings':[self.ref] if refs is None else refs}

    def plan(self,nodes=None):
        return {'schema_version':'0.2.0','workflow_run_id':'workflow-current-fixture','trace_id':'trace-current-fixture',
                'nodes':nodes or [self.node('source')],
                'policy':{'on_blocked':'STOP_DEPENDENTS','max_parallel':2,'require_human_approval':True}}

    def inspect(self,payload,**limits):
        before=self.fixture.files(self.store);original=copy.deepcopy(payload)
        with patch.object(self.store,'put',side_effect=AssertionError('조회가 Registry를 변경했습니다.')):
            with patch.object(app_fixtures.main.pool,'submit',side_effect=AssertionError('조회가 실행을 제출했습니다.')):
                result=validate_workflow_lineage(self.store,payload,**limits)
        self.assertEqual(before,self.fixture.files(self.store));self.assertEqual(payload,original)
        self.assertEqual(result['mode'],'PLAN_ONLY');self.assertEqual(result['status'],'BLOCKED')
        for key in ('can_execute','execution_started','authorization_verified','execution_authorized','scientific_approval'):
            self.assertIs(result[key],False)
        self.assertEqual(result['network_requests'],0);self.assertEqual(result['source_files_written'],0)
        for text in ('PRIVATE-URI','PRIVATE-ROLE','PRIVATE-PARAMETER','PRIVATE-ASSET',str(self.store.root)):
            self.assertNotIn(text,json.dumps(result))
        return result

    def test_cross_node_cache_empty_inputs_and_node_binding_identity_are_explicit(self):
        refs=[dict(self.ref,uri='PRIVATE-URI',role='PRIVATE-ROLE')]
        plan=self.plan([self.node('dependent',refs,['source']),self.node('empty',[]),self.node('source',refs)])
        plan['policy']['unimplemented_parameter']='PRIVATE-PARAMETER'
        import app.workflow_lineage as module
        with patch('app.workflow_lineage.verify_dataset_lineage',wraps=module.verify_dataset_lineage) as verify:
            result=self.inspect(plan)
        self.assertEqual(verify.call_count,1);self.assertEqual(len(result['diagnostics']),1)
        self.assertEqual(result['limits']['node_checks_performed'],1)
        self.assertEqual(result['topological_order'],['empty','source','dependent'])
        self.assertEqual([node['node_id'] for node in result['nodes']],['dependent','empty','source'])
        self.assertEqual([binding['diagnostic_index'] for binding in result['bindings']],[0,0])
        self.assertTrue(result['bindings'][1]['reused'])
        self.assertFalse(result['nodes'][1]['inputs_complete'])
        self.assertIn('INPUT_REFS_REQUIRED',{row['code'] for row in result['blockers']})
        self.assertFalse(result['lineage_integrity_verified'])

    def test_all_input_lineage_success_still_does_not_authorize_workflow(self):
        result=self.inspect(self.plan([self.node('a'),self.node('b',deps=['a','a'])]))
        self.assertTrue(result['lineage_integrity_verified'])
        self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['can_execute'])
        self.assertTrue(all(node['inputs_complete'] for node in result['nodes']))

    def test_global_conflicting_hashes_are_blocked_but_distinct_versions_are_allowed(self):
        plan=self.plan([self.node('a'),self.node('b',[dict(self.ref,sha256='a'*64)])])
        with patch('app.workflow_lineage.verify_dataset_lineage',side_effect=AssertionError('상충 참조 해시')):
            result=self.inspect(plan)
        self.assertEqual(len(result['blockers']),2)
        self.assertEqual({row['code'] for row in result['blockers']},{'WORKFLOW_INPUT_REFERENCE_CONFLICT'})
        self.assertEqual({row['node_id'] for row in result['blockers']},{'a','b'})
        self.assertFalse(result['current_assets_revalidated'])
        second=self.fixture.dataset('workflow-root',version='2')
        valid=self.inspect(self.plan([self.node('a'),self.node('b',[second])]))
        self.assertTrue(valid['lineage_integrity_verified']);self.assertEqual(len(valid['diagnostics']),2)

    def test_schema_and_entire_dag_fail_before_any_registry_or_hash_lookup(self):
        cases=[{},self.plan([self.node('a'),self.node('a')]),self.plan([self.node('a',deps=['missing'])]),
               self.plan([self.node('a',deps=['a'])]),self.plan([self.node('a',deps=['b']),self.node('b',deps=['a'])])]
        bad=self.plan();bad['nodes'][0]['input_bindings'][0]=dict(self.ref,sha256='BAD');cases.append(bad)
        for body in cases:
            with self.subTest(body=body),patch.object(self.store,'get',side_effect=AssertionError('무효 DAG Registry 조회')):
                with patch('app.workflow_lineage.verify_dataset_lineage',side_effect=AssertionError('무효 DAG 해시')):
                    with self.assertRaises(WorkflowLineageRequestError):
                        validate_workflow_lineage(self.store,body)
                    response=self.client.post(self.uri,json=body)
            self.assertEqual(response.status_code,400)
            app_fixtures.GmaisApiTests().validate('error.schema.json',response.json())

    def test_workflow_node_ref_and_unique_limits_stop_all_asset_checks(self):
        cases=[(self.plan([self.node('a'),self.node('b')]),{'max_workflow_nodes':1},'WORKFLOW_NODE_LIMIT',False),
               (self.plan([self.node('node-'+str(i),[]) for i in range(129)]),{},'WORKFLOW_NODE_LIMIT',False),
               (self.plan([self.node('a',[self.ref]*65)]),{},'WORKFLOW_INPUT_REF_LIMIT',True),
               (self.plan([self.node('a',[dict(self.ref,id='unknown-'+str(i)) for i in range(33)])]),{},'WORKFLOW_UNIQUE_ROOT_LIMIT',True)]
        for body,limits,code,dag in cases:
            with self.subTest(code=code),patch('app.workflow_lineage.verify_dataset_lineage',side_effect=AssertionError('상한 초과 해시')):
                result=self.inspect(body,**limits)
            self.assertFalse(result['available']);self.assertEqual(result['reason'],'CHECK_LIMIT_REACHED')
            self.assertEqual(result['bindings'],[]);self.assertEqual(result['diagnostics'],[]);self.assertEqual(result['nodes'],[])
            self.assertEqual(result['dag_validated'],dag);self.assertEqual(result['blockers'][0]['code'],code)

    def test_global_budget_has_partial_node_bindings_and_cache_after_exhaustion(self):
        other=self.fixture.dataset('workflow-other')
        body=self.plan([self.node('a'),self.node('b',[other]),self.node('c')])
        result=self.inspect(body,max_total_nodes=1,max_nodes_per_root=1)
        self.assertEqual(result['reason'],'CHECK_LIMIT_REACHED');self.assertTrue(result['available'])
        self.assertEqual([row['checked'] for row in result['bindings']],[True,False,True])
        self.assertEqual(result['limits']['node_checks_performed'],1)
        self.assertTrue(result['bindings'][2]['reused'])
        self.assertEqual([node['inputs_complete'] for node in result['nodes']],[True,False,True])

    def test_repeat_requests_recheck_current_assets_and_keep_source_state_unchanged(self):
        body=self.plan()
        self.assertTrue(self.inspect(body)['lineage_integrity_verified'])
        (self.store.root/'PRIVATE-ASSET-workflow-root-1.bin').write_bytes(b'changed asset')
        result=self.inspect(body)
        self.assertFalse(result['lineage_integrity_verified'])
        self.assertIn('LINEAGE_INTEGRITY_FAILED',{row['code'] for row in result['blockers']})

    def test_missing_dynamic_and_acl_blockers_remain_indexed_without_hidden_ancestor_ids(self):
        hidden=self.fixture.dataset('workflow-undisclosed')
        private=self.fixture.dataset('workflow-private',parents=[hidden],access='CONFIDENTIAL')
        cases=[(dict(self.ref,id='not-registered'),'DATASET_VERSION_NOT_FOUND'),
               (dict(self.ref,version='latest'),'LINEAGE_REF_NOT_PINNED'),
               (private,'LINEAGE_ACL_NOT_IMPLEMENTED')]
        for reference,code in cases:
            with self.subTest(code=code):
                result=self.inspect(self.plan([self.node('checked',[reference])]))
                self.assertIn({'node_id':'checked','input_index':0,'code':code},result['blockers'])
                self.assertFalse(result['lineage_integrity_verified'])
                self.assertNotIn(hidden['id'],json.dumps(result))

    def test_http_request_sha_binds_exact_received_bytes_not_canonical_numbers(self):
        body=self.plan();body['policy']['value']=0.1
        first=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
        second=first.replace(b'0.1',b'1e-1')+b'\n'
        for raw in (first,second):
            before=self.fixture.files(self.store)
            response=self.client.post(self.uri,content=raw,headers={'Content-Type':'application/json'})
            self.assertEqual(response.status_code,200,response.text)
            result=response.json()
            self.assertEqual(result['request_sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(result['extension'],'greenblue.workflow-lineage-validation.rfc1')
            self.assertEqual(result['evaluation_scope'],'CURRENT_WORKFLOW_TRANSITIVE_LINEAGE_PLAN_ONLY')
            self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(before,self.fixture.files(self.store))
        self.assertNotEqual(hashlib.sha256(first).hexdigest(),hashlib.sha256(second).hexdigest())

    def test_nonstandard_json_and_raw_private_schema_values_are_not_reflected(self):
        for token in ('NaN','Infinity','-Infinity'):
            raw=json.dumps(self.plan()).replace('"max_parallel": 2','"max_parallel": 2, "unimplemented": '+token)
            with patch('app.workflow_lineage.verify_dataset_lineage',side_effect=AssertionError('비표준 JSON 해시')):
                response=self.client.post(self.uri,content=raw,headers={'Content-Type':'application/json'})
            self.assertEqual(response.status_code,400);self.assertNotIn(token,response.text)
        body=self.plan();body['nodes'][0]['PRIVATE-URI']='PRIVATE-PARAMETER'
        response=self.client.post(self.uri,json=body)
        self.assertEqual(response.status_code,400);self.assertNotIn('PRIVATE-',response.text)

    def test_internal_projection_failure_is_503_and_actual_main_auth_and_plan_stay_unchanged(self):
        body=self.plan()
        before=self.main_client.post('/v1/workflows/plan',json=body).json()
        with patch('app.workflow_lineage.verify_dataset_lineage',side_effect=ValueError('PRIVATE-INTERNAL-PATH')):
            failed=self.client.post(self.uri,json=body)
        self.assertEqual(failed.status_code,503);self.assertNotIn('PRIVATE-INTERNAL-PATH',failed.text)
        app_fixtures.GmaisApiTests().validate('error.schema.json',failed.json())
        with patch.dict(os.environ,{'GEOAI_API_TOKEN':'temporary-workflow-lineage-token'}):
            self.assertEqual(self.main_client.post(self.uri,json=body).status_code,401)
            allowed=self.main_client.post(self.uri,json=body,headers={'Authorization':'Bearer temporary-workflow-lineage-token'})
        self.assertEqual(allowed.status_code,200,allowed.text)
        after=self.main_client.post('/v1/workflows/plan',json=body).json()
        # 기존 응답의 시각만 달라질 수 있고 기존 계획/차단 근거는 보존된다.
        for result in (before,after):
            result['policy_resolution'].pop('evaluated_at',None)
            for node in result['nodes']:
                node['input_resolution'].pop('evaluated_at',None)
        self.assertEqual(before,after)
        for kind in ('jobs','gmais_jobs','gmais_results','traces','gmais_traces','workflow_runs','analyses','models'):
            self.assertEqual(self.store.list(kind),[])
