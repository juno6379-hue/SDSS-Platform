"""Sorted-layer graph invariants and cold-loaded original caller equivalence."""
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import gmais_api, workflow_lineage, workflow_policy
from app.store import Store
from app.workflow_dependency_order import topological_order


ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = {
    'gmais_api': '18f1b7185a4d458d968b0c484f22ae29233cb6617aeb3f63f14ec1e9054f6aed',
    'workflow_lineage': '26230f2619ed32442b9dfb2187ae8972d74d3a260e6b7d018ed4a859236c56bf',
    'workflow_policy': 'c75e8e5e46e71a42f6e15c290f51c9c5ad08b3219bc825b7b598520e8f999205',
}


def node(identifier, dependencies=(), empty=False):
    return {'node_id': identifier, 'agent_id': 'lcluc-agent',
        'capability_id': 'landcover.change_detection', 'depends_on': list(dependencies),
        'input_bindings': [] if empty else [{'id': 'synthetic-input', 'version': '1', 'sha256': 'a' * 64}]}


def plan(nodes):
    return {'schema_version': '0.2.0', 'workflow_run_id': 'workflow-layer-fixture',
        'trace_id': 'trace-layer-fixture', 'nodes': nodes,
        'policy': {'on_blocked': 'STOP_DEPENDENTS', 'max_parallel': 2, 'require_human_approval': True}}


class RecordingStore(Store):
    def __init__(self, root, calls):
        self.calls = calls
        super().__init__(root)

    def get(self, kind, identifier):
        self.calls.append(('get', kind, identifier))
        return super().get(kind, identifier)

    def list(self, kind):
        self.calls.append(('list', kind))
        return super().list(kind)

    def put(self, kind, record):
        raise AssertionError('plan/lineage must never write a record')


class WorkflowDependencyOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = {}
        for name, checksum in ORIGINALS.items():
            path = ROOT / ('evidence/integration/workflow-dependency-order-original-' + name + '-20261017.py')
            if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise AssertionError('Original Workflow source evidence changed')
            spec = importlib.util.spec_from_file_location('app._dependency_original_' + name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.original[name] = module

    def test_sorted_ready_layers_are_not_global_heap_order(self):
        graph = {'a': set(), 'b': {'a'}, 'z': set()}
        self.assertEqual(topological_order(graph), ['a', 'z', 'b'])
        self.assertNotEqual(topological_order(graph), ['a', 'b', 'z'])
        self.assertEqual(topological_order(dict(reversed(list(graph.items())))), ['a', 'z', 'b'])

    def test_empty_diamond_disconnected_repeated_edges_and_cycles(self):
        self.assertEqual(topological_order({}), [])
        self.assertEqual(topological_order({'d': ['c', 'b'], 'b': ['a', 'a'], 'c': ['a'], 'a': [], 'z': []}),
                         ['a', 'z', 'b', 'c', 'd'])
        for graph in ({'a': ['a']}, {'a': ['b'], 'b': ['a']}, {'z': [], 'a': ['b'], 'b': ['a']}):
            self.assertIsNone(topological_order(graph))
        # Unknown-edge validation belongs to callers. An unfulfilled edge just stalls this helper.
        self.assertIsNone(topological_order({'a': ['unknown']}))

    def test_input_sets_are_copied_aliases_unchanged_and_no_io(self):
        shared = {'a'}; graph = {'a': set(), 'b': shared, 'c': shared}
        before = copy.deepcopy(graph)
        with patch('builtins.open', side_effect=AssertionError('no file open')), \
             patch.object(Path, 'open', side_effect=AssertionError('no Path.open')), \
             patch('socket.socket', side_effect=AssertionError('no network')):
            order = topological_order(graph)
        self.assertEqual(order, ['a', 'b', 'c'])
        self.assertEqual(graph, before)
        self.assertIs(graph['b'], shared); self.assertIs(graph['c'], shared)

    def exercise_plan(self, module, body):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []; store = RecordingStore(Path(temporary), calls)
            def factory(): calls.append(('factory',)); return store
            manifests = module._agent_manifests()
            def inspect_manifests(): calls.append(('manifests',)); return copy.deepcopy(manifests)
            validator = module._workflow_plan_validator
            def validate(): calls.append(('schema',)); return validator()
            app = FastAPI(); app.include_router(module.create_router(factory))
            with patch.object(module, '_agent_manifests', side_effect=inspect_manifests), \
                 patch.object(module, '_workflow_plan_validator', side_effect=validate), \
                 patch.object(module, '_now', return_value='2026-10-17T00:00:00.000Z'), TestClient(app) as client:
                response = client.post('/v1/workflows/plan', json=body)
            with store.connect() as connection:
                records = connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
            return (response.status_code, response.content, dict(response.headers)), calls, records

    def test_plan_exact_responses_headers_io_order_layers_and_no_execution(self):
        graphs = [[node('a'), node('b', ['a']), node('z')],
                  [node('d', ['b', 'c']), node('c', ['a']), node('b', ['a', 'a']), node('a')],
                  [node('empty', empty=True), node('source')]]
        for nodes in graphs:
            for mode in ('STOP_DEPENDENTS', 'FAIL_ALL'):
                body = plan(nodes); body['policy']['on_blocked'] = mode; before = copy.deepcopy(body)
                expected = self.exercise_plan(self.original['gmais_api'], body)
                actual = self.exercise_plan(gmais_api, body)
                self.assertEqual(actual, expected)
                self.assertEqual(actual[0][0], 200)
                self.assertEqual(actual[1][:3], [('schema',), ('manifests',), ('factory',)])
                self.assertEqual(actual[2], [])
                self.assertEqual(body, before)
        body = plan(graphs[0]); result = self.exercise_plan(gmais_api, body)[0][1]
        import json
        value = json.loads(result)
        self.assertEqual(value['topological_order'], ['a', 'z', 'b'])
        self.assertIs(value['execution_started'], False); self.assertIs(value['can_execute'], False)

    def test_plan_schema_duplicate_unknown_self_cycle_priority_before_manifest_or_store(self):
        cases = [{}, plan([node('a'), node('a')]), plan([node('a', ['unknown'])]),
                 plan([node('a', ['a'])]), plan([node('a', ['b']), node('b', ['a'])])]
        malformed = plan([node('a', ['unknown'])]); malformed['nodes'][0]['input_bindings'][0]['sha256'] = 'bad'; cases.append(malformed)
        for body in cases:
            expected = self.exercise_plan(self.original['gmais_api'], body)
            actual = self.exercise_plan(gmais_api, body)
            self.assertEqual(actual, expected)
            self.assertEqual(actual[0][0], 400)
            self.assertEqual(actual[1], [('schema',)])
            self.assertEqual(actual[2], [])

    def exercise_lineage(self, module, body, **limits):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []; store = RecordingStore(Path(temporary), calls)
            verify = module.verify_dataset_lineage
            def inspect(*args, **kwargs): calls.append(('verify',)); return verify(*args, **kwargs)
            with patch.object(module, 'verify_dataset_lineage', side_effect=inspect):
                try:
                    result = ('return', module.validate_workflow_lineage(store, body, **limits))
                except ValueError as error:
                    result = ('error', type(error).__name__, str(error))
            with store.connect() as connection:
                records = connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
            return result, calls, records

    def test_lineage_real_tempstore_response_io_order_and_layers_unchanged(self):
        for body in (plan([node('a'), node('b', ['a', 'a']), node('z')]),
                     plan([node('empty', empty=True), node('source')])):
            before = copy.deepcopy(body)
            actual = self.exercise_lineage(workflow_lineage, body)
            self.assertEqual(actual, self.exercise_lineage(self.original['workflow_lineage'], body))
            self.assertEqual(actual[0][0], 'return')
            self.assertEqual(actual[1][0], ('verify',))
            self.assertEqual(actual[2], [])
            value = actual[0][1]
            self.assertIs(value['can_execute'], False); self.assertIs(value['execution_authorized'], False)
            self.assertEqual(body, before)

    def test_lineage_schema_limits_node_limit_and_dag_checks_keep_exact_priority(self):
        cycle = plan([node('a', ['b']), node('b', ['a'])])
        distinct_roots = plan([node('a'), node('b')])
        distinct_roots['nodes'][1]['input_bindings'][0]['id'] = 'different-synthetic-root'
        cases = [({}, {'max_depth': True}), (cycle, {'max_depth': True}),
            (plan([node('a'), node('a')]), {'max_workflow_nodes': 1}),
            (plan([node('a', ['unknown']), node('a', ['a'])]), {}),
            (plan([node('a', ['unknown'])]), {}), (plan([node('a', ['a'])]), {}),
            (cycle, {}), (cycle, {'max_workflow_nodes': 1}), (cycle, {'max_input_refs': 1}),
            (plan([node('a'), node('b')]), {'max_input_refs': 1}),
            (distinct_roots, {'max_unique_roots': 1})]
        for body, limits in cases:
            actual = self.exercise_lineage(workflow_lineage, body, **limits)
            expected = self.exercise_lineage(self.original['workflow_lineage'], body, **limits)
            self.assertEqual(actual, expected)
            self.assertEqual(actual[2], [])
            if actual[0][0] == 'error' or not actual[0][1]['available']:
                self.assertEqual(actual[1], [])

    def policy_outcome(self, module, nodes, policy):
        try: return ('return', module.diagnose_workflow_blocking(nodes, policy))
        except ValueError as error: return ('error', type(error).__name__, str(error))

    def test_policy_sorted_layers_propagation_modes_and_copied_blockers_unchanged(self):
        nodes = [{'node_id': 'a', 'depends_on': [], 'blockers': [{'code': 'SYNTHETIC_BLOCKER', 'details': ['fixture']}]},
                 {'node_id': 'b', 'depends_on': ['a', 'a'], 'blockers': []},
                 {'node_id': 'z', 'depends_on': [], 'blockers': []}]
        before = copy.deepcopy(nodes)
        for mode in ('STOP_DEPENDENTS', 'FAIL_ALL'):
            policy = {'on_blocked': mode}
            actual = self.policy_outcome(workflow_policy, nodes, policy)
            self.assertEqual(actual, self.policy_outcome(self.original['workflow_policy'], nodes, policy))
            self.assertEqual(actual[1]['topological_order'], ['a', 'z', 'b'])
            self.assertIs(actual[1]['execution_authorized'], False)
            actual[1]['nodes'][0]['local_blockers'][0]['details'].append('result-only')
            self.assertEqual(nodes, before)

    def test_policy_validation_and_blocker_json_failure_before_cycle_preserved(self):
        a = {'node_id': 'a', 'depends_on': ['b'], 'blockers': []}
        b = {'node_id': 'b', 'depends_on': ['a'], 'blockers': []}
        nan = copy.deepcopy(a); nan['blockers'] = [{'code': 'SYNTHETIC', 'value': math.nan}]
        invalid = copy.deepcopy(a); invalid['blockers'] = [{'code': ' '}]
        unknown = copy.deepcopy(a); unknown['depends_on'] = ['unknown']
        own = copy.deepcopy(a); own['depends_on'] = ['a']
        for nodes, policy in (([a, b], {}), ([], {'on_blocked': 'STOP_DEPENDENTS'}),
            ([a, a], {'on_blocked': 'STOP_DEPENDENTS'}), ([unknown], {'on_blocked': 'STOP_DEPENDENTS'}),
            ([own], {'on_blocked': 'STOP_DEPENDENTS'}), ([a, b], {'on_blocked': 'STOP_DEPENDENTS'}),
            ([nan, b], {'on_blocked': 'STOP_DEPENDENTS'}), ([invalid, b], {'on_blocked': 'STOP_DEPENDENTS'})):
            self.assertEqual(self.policy_outcome(workflow_policy, nodes, policy),
                             self.policy_outcome(self.original['workflow_policy'], nodes, policy))
