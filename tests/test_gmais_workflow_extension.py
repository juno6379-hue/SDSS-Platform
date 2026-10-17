"""계획 전용 RFC 확장 계약시험. 실제 모델 실행·Job·Result를 만들지 않는다."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'backend'))
SCHEMAS = PROJECT / 'contracts/upstream/GMAIS-v0.2/schemas'
_bootstrap = tempfile.TemporaryDirectory()
with patch.dict(os.environ, {'GEOAI_DATA_ROOT': _bootstrap.name}):
    from app import main
from app.store import Store
from app.dataset_registry import register_version


class GmaisWorkflowExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_store = main.store
        main.store = Store(Path(self.temporary.name))
        self.auth = patch.dict(os.environ, {'GEOAI_API_TOKEN': ''})
        self.auth.start()
        # 계획 검사가 기존 실행 큐를 호출하면 즉시 실패시킨다.
        self.no_execution = patch.object(main.pool, 'submit', side_effect=AssertionError('plan-only 요청이 실행 큐를 호출했습니다.'))
        self.no_execution.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.no_execution.stop()
        self.auth.stop()
        main.store = self.original_store
        self.temporary.cleanup()

    def validate(self, name, value):
        schema = json.loads((SCHEMAS / name).read_text(encoding='utf-8'))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)

    def node(self, identifier, dependencies=()):
        return {'node_id': identifier, 'agent_id': 'lcluc-agent',
                'capability_id': 'landcover.change_detection', 'depends_on': list(dependencies),
                # 스키마만 유효한 명시적 fixture이며 실제 등록/승인된 데이터가 아니다.
                'input_bindings': [{'id': 'explicit-contract-fixture', 'version': '1', 'sha256': 'a' * 64}],
                'timeout_seconds': 30, 'max_retries': 0}

    def plan(self):
        return {'schema_version': '0.2.0', 'workflow_run_id': 'workflow-plan-only-fixture',
                'trace_id': 'trace-plan-only-fixture', 'nodes': [self.node('landcover')],
                'policy': {'on_blocked': 'STOP_DEPENDENTS', 'max_parallel': 2, 'require_human_approval': True}}

    def assert_no_execution_artifacts(self):
        for kind in ('jobs', 'gmais_jobs', 'gmais_results', 'analyses', 'models', 'datasets',
                     'traces', 'gmais_traces', 'workflow_runs', 'gmais_workflows'):
            self.assertEqual(main.store.list(kind), [], kind)

    def register_input(self, version='1', quality='VALIDATED', access='PUBLIC', content=b'{"explicit_workflow_contract_fixture":true}'):
        root=Path(self.temporary.name)
        asset=root/f'private-input-{version}.json';asset.write_bytes(content)
        report=root/f'quality-{version}.json';report.write_bytes(b'{"contract_fixture":true}')
        manifest={'schema_version':'0.2.0','dataset_id':'registered-workflow-fixture','version':version,
                  'source':{'institution':'contract test','product':'explicit fixture','license':'test only'},
                  'data_type':'document','spatial':{'bbox':[106,-7,107,-6],'crs':'OGC:CRS84'},
                  'temporal':{'start':'2024-01-01T00:00:00Z','end':'2024-12-31T00:00:00Z','calendar':'gregorian'},
                  'quality_status':quality,'quality_report_ref':report.name,'access_class':access,
                  'artifact_uri':asset.name,'sha256':hashlib.sha256(content).hexdigest(),'lineage':[]}
        register_version(main.store,manifest)
        return {'id':manifest['dataset_id'],'version':version,'sha256':manifest['sha256']},asset

    def snapshot_files(self):
        root=Path(self.temporary.name)
        return {str(path.relative_to(root)):path.read_bytes() for path in root.rglob('*') if path.is_file()}

    def readonly_plan(self, body):
        before=self.snapshot_files()
        original=copy.deepcopy(body)
        with patch.object(main.store,'put',side_effect=AssertionError('계획 조회가 Catalog를 변경했습니다.')):
            response=self.client.post('/v1/workflows/plan',json=body)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(body,original)
        self.assertEqual(self.snapshot_files(),before,'원본/Registry/Trace 파일이 변경됐습니다.')
        self.assert_no_execution_artifacts()
        result=response.json()
        self.assertEqual(result['mode'],'PLAN_ONLY');self.assertEqual(result['status'],'BLOCKED')
        self.assertIs(result['can_execute'],False);self.assertIs(result['execution_started'],False)
        self.assertNotIn('job_id',result);self.assertNotIn('result_id',result)
        for node in result['nodes']:
            self.assertEqual(node['status'],'BLOCKED')
            self.assertIs(node['execution_authorized'],False)
            resolution=node['input_resolution']
            self.assertEqual(resolution['scope'],'INPUT_INTEGRITY_ONLY')
            self.assertIs(resolution['ready_for_execution'],False)
            self.assertIs(resolution['scientific_approval'],False)
            self.assertEqual(resolution['network_requests'],0)
            self.assertEqual(resolution['source_files_written'],0)
            self.assertEqual(resolution['evaluation_scope'],'PLAN_REQUEST_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION')
            for blocker in resolution['blockers']:
                expected={'INPUT_REFS_REQUIRED':'DATA_MISSING','DATASET_VERSION_NOT_FOUND':'DATA_MISSING',
                          'INPUT_ACL_NOT_IMPLEMENTED':'FORBIDDEN','DATASET_REGISTRY_UNAVAILABLE':'RESOURCE_UNAVAILABLE',
                          'INPUT_REF_SCHEMA_MISMATCH':'SCHEMA_MISMATCH','INPUT_REF_NOT_PINNED':'SCHEMA_MISMATCH',
                          'INPUT_REF_CONFLICT':'SCHEMA_MISMATCH','INPUT_URI_MISMATCH':'SCHEMA_MISMATCH'}.get(blocker['code'],'DATA_QUALITY')
                self.assertTrue(any(item.get('detail_code')==blocker['code'] and item['code']==expected
                                    and item.get('input_index')==blocker['input_index']
                                    for item in node['blockers']),'입력 실패 코드/index가 노드에 전달되지 않았습니다.')
        return result

    def assert_invalid(self, body):
        # 스키마/DAG 검증 실패는 입력 Registry 조회나 해시 검사에 도달하면 안 된다.
        with patch('app.job_inputs.resolve_job_inputs',side_effect=AssertionError('무효 DAG의 입력을 조회했습니다.')) as resolver:
            with patch('app.workflow_policy.diagnose_workflow_blocking',side_effect=AssertionError('무효 DAG의 차단 정책을 계산했습니다.')) as policy:
                with patch.object(main.store,'get',side_effect=AssertionError('무효 DAG가 Catalog를 조회했습니다.')):
                    response = self.client.post('/v1/workflows/plan', json=body)
                policy.assert_not_called()
            resolver.assert_not_called()
        self.assertEqual(response.status_code, 400, response.text)
        self.validate('error.schema.json', response.json())
        self.assertEqual(response.json()['error']['code'], 'INVALID_REQUEST')
        self.assert_no_execution_artifacts()

    def test_schema_valid_plan_is_blocked_and_never_submits_job_or_result(self):
        body = self.plan()
        self.validate('workflow-plan.schema.json', body)
        original = copy.deepcopy(body)
        response = self.client.post('/v1/workflows/plan', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(body, original)
        self.assertEqual(result['workflow_run_id'], body['workflow_run_id'])
        self.assertEqual(result['trace_id'], body['trace_id'])
        self.assertEqual(result['mode'], 'PLAN_ONLY')
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIs(result['execution_started'], False)
        self.assertIs(result['can_execute'], False)
        self.assertEqual(result['extension']['approval_status'], 'INTERNAL_REVIEW')
        self.assertIs(result['extension']['present_in_upstream_openapi'], False)
        self.assertNotIn('job_id', result)
        self.assertNotIn('result_id', result)
        self.assertEqual(result['nodes'][0]['status'], 'BLOCKED')
        codes = {item['code'] for item in result['nodes'][0]['blockers']}
        self.assertIn('MODEL_NOT_READY', codes)
        self.assertIn('DATA_MISSING', codes)
        self.assert_no_execution_artifacts()

    def test_invalid_schema_fields_are_rejected(self):
        malformed = [None, {}, {**self.plan(), 'unknown_top_level': True}]
        for field, value in (('timeout_seconds', 0), ('max_retries', 6), ('depends_on', 'landcover')):
            body = self.plan()
            body['nodes'][0][field] = value
            malformed.append(body)
        bad_hash = self.plan()
        bad_hash['nodes'][0]['input_bindings'][0]['sha256'] = 'not-a-sha256'
        malformed.append(bad_hash)
        for body in malformed:
            with self.subTest(body=body):
                self.assert_invalid(body)

    def test_duplicate_node_identifiers_are_rejected_even_when_schema_valid(self):
        body = self.plan()
        body['nodes'].append(copy.deepcopy(body['nodes'][0]))
        self.validate('workflow-plan.schema.json', body)
        self.assert_invalid(body)

    def test_unknown_and_self_dependencies_are_rejected(self):
        for dependency in ('missing-node', 'landcover'):
            with self.subTest(dependency=dependency):
                body = self.plan()
                body['nodes'][0]['depends_on'] = [dependency]
                self.validate('workflow-plan.schema.json', body)
                self.assert_invalid(body)

    def test_dependency_cycle_is_rejected(self):
        body = self.plan()
        body['nodes'] = [self.node('a', ['c']), self.node('b', ['a']), self.node('c', ['b'])]
        self.validate('workflow-plan.schema.json', body)
        self.assert_invalid(body)

    def test_unknown_agent_and_wrong_capability_are_never_executable(self):
        for field, value, code in (('agent_id', 'unknown-agent', 'AGENT_NOT_IMPLEMENTED'),
                                   ('capability_id', 'invented.scientific.capability', 'INVALID_REQUEST')):
            with self.subTest(field=field):
                body = self.plan()
                body['nodes'][0][field] = value
                response = self.client.post('/v1/workflows/plan', json=body)
                # 구조는 유효하지만 실행을 허용하지 않는 계획으로 노드별 사유를 반환한다.
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertIs(result['can_execute'], False)
                self.assertIs(result['execution_started'], False)
                self.assertEqual(result['nodes'][0]['status'], 'BLOCKED')
                self.assertIn(code, {item['code'] for item in result['nodes'][0]['blockers']})
                self.assert_no_execution_artifacts()

    def test_topological_order_is_stable_across_input_order_and_repeated_plans(self):
        body = self.plan()
        nodes = [self.node('e', ['c', 'd']), self.node('d', ['b']), self.node('c', ['a']),
                 self.node('b'), self.node('a')]
        expected = ['a', 'b', 'c', 'd', 'e']
        for submitted in (nodes, list(reversed(nodes)), nodes):
            body['nodes'] = copy.deepcopy(submitted)
            self.validate('workflow-plan.schema.json', body)
            response = self.client.post('/v1/workflows/plan', json=body)
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertEqual(result['topological_order'], expected)
            self.assertIs(result['execution_started'], False)
            positions = {node: i for i, node in enumerate(result['topological_order'])}
            for node in submitted:
                self.assertTrue(all(positions[dependency] < positions[node['node_id']] for dependency in node['depends_on']))
            self.assert_no_execution_artifacts()

    def test_registered_public_validated_input_resolves_but_does_not_start_workflow(self):
        ref,asset=self.register_input()
        body=self.plan();body['nodes'][0]['input_bindings']=[dict(ref,uri=asset.name)]
        result=self.readonly_plan(body)
        node=result['nodes'][0];resolution=node['input_resolution']
        self.assertEqual(resolution['status'],'INTEGRITY_VERIFIED')
        self.assertTrue(resolution['input_integrity_verified']);self.assertEqual(resolution['blockers'],[])
        codes={item['code'] for item in node['blockers']}
        self.assertNotIn('DATA_MISSING',codes);self.assertIn('MODEL_NOT_READY',codes)
        encoded=json.dumps(resolution)
        self.assertNotIn(asset.name,encoded);self.assertNotIn(str(asset.parent),encoded)
        self.assertFalse(resolution['resolved'][0]['authorization_verified'])

    def test_input_failures_are_indexed_and_all_bindings_are_reviewed(self):
        good,_=self.register_input()
        variants=[('missing',dict(good,id='unregistered-fixture'),'DATASET_VERSION_NOT_FOUND'),
                  ('wrong-existing-sha',dict(good,sha256='b'*64),'INPUT_INTEGRITY_FAILED'),
                  ('uri',dict(good,uri='https://example.invalid/private'),'INPUT_URI_MISMATCH'),
                  ('dynamic',dict(good,version='latest'),'INPUT_REF_NOT_PINNED')]
        for quality in ('RAW','STAGED','STANDARDIZED','REJECTED'):
            ref,_=self.register_input(version='quality-'+quality,quality=quality)
            code='INPUT_QUALITY_REJECTED' if quality=='REJECTED' else 'INPUT_QUALITY_NOT_VALIDATED'
            variants.append((quality,ref,code))
        for access in ('RESTRICTED','CONFIDENTIAL'):
            ref,_=self.register_input(version='access-'+access,access=access)
            variants.append((access,ref,'INPUT_ACL_NOT_IMPLEMENTED'))
        for label,ref,code in variants:
            with self.subTest(case=label):
                body=self.plan();body['nodes'][0]['input_bindings']=[ref,good]
                node=self.readonly_plan(body)['nodes'][0]
                resolution=node['input_resolution']
                self.assertEqual(resolution['status'],'BLOCKED')
                self.assertTrue(any(item['code']==code and item['input_index']==0 for item in resolution['blockers']))
                self.assertIn('MODEL_NOT_READY',{item['code'] for item in node['blockers']})
                # 같은 version의 다른 SHA 상충은 두 참조 모두 차단하며 나머지는 정상 참조를 계속 검사한다.
                if label!='wrong-existing-sha':
                    self.assertTrue(resolution['resolved'][1]['integrity_verified'])
                encoded=json.dumps(resolution)
                self.assertNotIn('private-input-',encoded);self.assertNotIn('https://example.invalid/private',encoded)

    def test_temporal_versions_are_allowed_but_same_version_conflicting_sha_is_blocked(self):
        first,_=self.register_input()
        second,_=self.register_input(version='2',content=b'{"explicit_workflow_contract_fixture":"T2"}')
        body=self.plan();body['nodes'][0]['input_bindings']=[dict(first,role='T1'),dict(second,role='T2')]
        node=self.readonly_plan(body)['nodes'][0]
        self.assertEqual(node['input_resolution']['blockers'],[])
        self.assertTrue(node['input_resolution']['input_integrity_verified'])
        self.assertIn('MODEL_NOT_READY',{item['code'] for item in node['blockers']})
        body['nodes'][0]['input_bindings']=[first,dict(first,sha256='c'*64)]
        resolution=self.readonly_plan(body)['nodes'][0]['input_resolution']
        conflicts=[item['input_index'] for item in resolution['blockers'] if item['code']=='INPUT_REF_CONFLICT']
        self.assertEqual(conflicts,[0,1]);self.assertFalse(resolution['input_integrity_verified'])

    def test_repeated_plan_rechecks_changed_asset_without_reusing_previous_resolution(self):
        ref,asset=self.register_input()
        body=self.plan();body['nodes'][0]['input_bindings']=[ref]
        first=self.readonly_plan(body)
        self.assertEqual(first['nodes'][0]['input_resolution']['blockers'],[])
        asset.write_bytes(b'{"changed_after_first_plan":true}')
        second=self.readonly_plan(body)
        resolution=second['nodes'][0]['input_resolution']
        self.assertIn('INPUT_INTEGRITY_FAILED',{item['code'] for item in resolution['blockers']})
        self.assertFalse(resolution['input_integrity_verified'])
        self.assertEqual(second['trace_id'],first['trace_id'])

    def test_dependency_and_unimplemented_agent_gates_remain_after_inputs_resolve(self):
        ref,_=self.register_input()
        body=self.plan();body['nodes']=[self.node('dependent',['source']),self.node('source')]
        for node in body['nodes']:
            node['input_bindings']=[ref]
        body['nodes'][0]['agent_id']='flood-drought-agent'
        body['nodes'][0]['capability_id']='flood-drought'
        result=self.readonly_plan(body)
        self.assertEqual(result['topological_order'],['source','dependent'])
        by_id={node['node_id']:node for node in result['nodes']}
        self.assertEqual(by_id['dependent']['depends_on'],['source'])
        for node in by_id.values():
            self.assertEqual(node['input_resolution']['blockers'],[])
            self.assertNotIn('DATA_MISSING',{item['code'] for item in node['blockers']})
        self.assertIn('MODEL_NOT_READY',{item['code'] for item in by_id['source']['blockers']})
        self.assertIn('AGENT_NOT_IMPLEMENTED',{item['code'] for item in by_id['dependent']['blockers']})

    def test_empty_bindings_remain_explicitly_blocked(self):
        body=self.plan();body['nodes'][0]['input_bindings']=[]
        resolution=self.readonly_plan(body)['nodes'][0]['input_resolution']
        self.assertIn('INPUT_REFS_REQUIRED',{item['code'] for item in resolution['blockers']})
        self.assertFalse(resolution['input_integrity_verified'])

    def policy_fixture(self, on_blocked='STOP_DEPENDENTS'):
        ref,_=self.register_input()
        body=self.plan()
        body['policy']['on_blocked']=on_blocked
        body['nodes']=[self.node('grandchild',['child']),self.node('independent'),
                       self.node('child',['source']),self.node('source')]
        for node in body['nodes']:
            node['input_bindings']=[ref]
        return body

    def assert_policy_diagnostics(self, result, on_blocked):
        policy=result['policy_resolution']
        self.assertEqual(policy['schema_version'],1)
        self.assertEqual(policy['scope'],'PLAN_ONLY_DEPENDENCY_DIAGNOSTICS')
        self.assertEqual(policy['on_blocked'],on_blocked)
        self.assertIs(policy['execution_authorized'],False)
        self.assertEqual(policy['topological_order'],result['topological_order'])
        self.assertEqual(policy['local_blocking_node_ids'],['child','grandchild','independent','source'])
        self.assertEqual([node['node_id'] for node in policy['nodes']],['child','grandchild','independent','source'])
        diagnostics={node['node_id']:node for node in policy['nodes']}
        for node in result['nodes']:
            diagnostic=node['dependency_resolution']
            self.assertEqual(diagnostic,diagnostics[node['node_id']])
            self.assertIs(diagnostic['execution_authorized'],False)
            self.assertEqual(diagnostic['diagnostic_status'],'BLOCKING_CAUSES_PRESENT')
            self.assertEqual(sorted(diagnostic['local_blockers'],key=lambda item:json.dumps(item,sort_keys=True)),
                             sorted(node['blockers'],key=lambda item:json.dumps(item,sort_keys=True)))
            self.assertIn('MODEL_NOT_READY',{item['code'] for item in node['blockers']})
            self.assertEqual(node['input_resolution']['blockers'],[])
        return diagnostics

    def test_stop_dependents_diagnostics_include_only_ancestor_local_causes(self):
        body=self.policy_fixture()
        result=self.readonly_plan(body)
        self.assertEqual([node['node_id'] for node in result['nodes']],[node['node_id'] for node in body['nodes']])
        diagnostics=self.assert_policy_diagnostics(result,'STOP_DEPENDENTS')
        expected={'source':[], 'child':['source'], 'grandchild':['child','source'], 'independent':[]}
        for node_id,ancestors in expected.items():
            self.assertEqual(diagnostics[node_id]['upstream_blocked_by'],ancestors)
            self.assertEqual(diagnostics[node_id]['policy_blocked_by'],[])
            self.assertEqual(diagnostics[node_id]['blocking_cause_node_ids'],sorted([node_id]+ancestors))
        # 실제 API의 모든 Agent는 local BLOCKED다. 독립 branch의 무차단을 주장하지 않는다.
        self.assertEqual(diagnostics['independent']['blocking_cause_node_ids'],['independent'])

    def test_fail_all_adds_other_local_causes_without_rewriting_original_blockers(self):
        body=self.policy_fixture()
        stopped=self.readonly_plan(body)
        body['policy']['on_blocked']='FAIL_ALL'
        failed=self.readonly_plan(body)
        diagnostics=self.assert_policy_diagnostics(failed,'FAIL_ALL')
        self.assertEqual(diagnostics['source']['policy_blocked_by'],['child','grandchild','independent'])
        self.assertEqual(diagnostics['grandchild']['upstream_blocked_by'],['child','source'])
        self.assertEqual(diagnostics['grandchild']['policy_blocked_by'],['independent'])
        self.assertEqual(diagnostics['independent']['policy_blocked_by'],['child','grandchild','source'])
        for diagnostic in diagnostics.values():
            self.assertEqual(diagnostic['blocking_cause_node_ids'],['child','grandchild','independent','source'])
        self.assertEqual({node['node_id']:node['blockers'] for node in stopped['nodes']},
                         {node['node_id']:node['blockers'] for node in failed['nodes']})

    def test_policy_diagnostics_are_stable_with_reordered_nodes_and_duplicate_dependencies(self):
        body=self.policy_fixture()
        first=self.readonly_plan(body)
        body['nodes'].reverse()
        for node in body['nodes']:
            node['depends_on']*=2
        second=self.readonly_plan(body)
        self.assertEqual([node['node_id'] for node in second['nodes']],[node['node_id'] for node in body['nodes']])
        self.assertEqual(first['policy_resolution']['nodes'],second['policy_resolution']['nodes'])
        self.assertEqual(first['policy_resolution']['topological_order'],second['policy_resolution']['topological_order'])

    def test_invalid_policy_fields_are_rejected_before_resolution(self):
        for field,value in (('on_blocked','CONTINUE'),('max_parallel',0),('max_parallel',True),
                            ('require_human_approval','false')):
            with self.subTest(field=field,value=value):
                body=self.plan();body['policy'][field]=value
                self.assert_invalid(body)

    def test_policy_limits_and_human_approval_false_never_grant_execution(self):
        body=self.policy_fixture()
        body['policy'].update(max_parallel=100,require_human_approval=False,
                              upstream_permitted_extension='no execution authority')
        result=self.readonly_plan(body)
        self.assert_policy_diagnostics(result,'STOP_DEPENDENTS')
        del body['policy']['require_human_approval']
        result=self.readonly_plan(body)
        self.assertIs(result['policy_resolution']['execution_authorized'],False)

    def test_schema_permitted_opaque_space_identifiers_remain_plan_only(self):
        ref,_=self.register_input()
        body=self.plan();body['nodes']=[self.node(' child ',['  ']),self.node('  ')]
        for node in body['nodes']:
            node['input_bindings']=[ref]
        self.validate('workflow-plan.schema.json',body)
        result=self.readonly_plan(body)
        self.assertEqual(result['topological_order'],['  ',' child '])
        self.assertEqual([node['node_id'] for node in result['nodes']],[' child ','  '])
        diagnostics={node['node_id']:node for node in result['policy_resolution']['nodes']}
        self.assertEqual(diagnostics[' child ']['upstream_blocked_by'],['  '])
        self.assertEqual(diagnostics['  ']['upstream_blocked_by'],[])

    def test_agent_ready_and_verified_inputs_still_do_not_authorize_workflow_execution(self):
        from app.gmais_api import _agent_manifests
        ref,_=self.register_input()
        body=self.plan();body['nodes'][0]['input_bindings']=[ref]
        agents=copy.deepcopy(_agent_manifests())
        for agent in agents:
            if agent['agent_id']=='lcluc-agent':
                agent['readiness']='READY'
        # runtime READY만으로 실제 모델 승인/실행기 부재를 우회하지 않는다.
        with patch('app.gmais_api._agent_manifests',return_value=agents):
            result=self.readonly_plan(body)
        node=result['nodes'][0]
        self.assertEqual(node['input_resolution']['blockers'],[])
        self.assertIn('MODEL_NOT_READY',{item['code'] for item in node['blockers']})


if __name__ == '__main__':
    unittest.main()
