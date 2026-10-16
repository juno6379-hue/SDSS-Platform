"""계획 전용 RFC 확장 계약시험. 실제 모델 실행·Job·Result를 만들지 않는다."""
import copy
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
        for kind in ('jobs', 'gmais_jobs', 'gmais_results', 'analyses', 'models', 'datasets'):
            self.assertEqual(main.store.list(kind), [], kind)

    def assert_invalid(self, body):
        response = self.client.post('/v1/workflows/plan', json=body)
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


if __name__ == '__main__':
    unittest.main()
