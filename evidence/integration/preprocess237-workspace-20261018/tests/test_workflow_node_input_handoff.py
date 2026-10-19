import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from app.workflow_node_input_handoff import compare_workflow_node_input_handoff, _FALSE_FLAGS


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def fixture():
    ref = dict(id='private-dataset', version='v1', sha256='a'*64,
        role='imagery', uri='file:///private/source.tif')
    workflow = dict(schema_version='0.2.0', workflow_run_id='private-workflow',
        trace_id='private-trace', nodes=[dict(node_id='private-node', agent_id='agent',
        capability_id='land-cover', depends_on=[], input_bindings=[ref])],
        policy=dict(on_blocked='STOP_DEPENDENTS', max_parallel=1, require_human_approval=True))
    proposal = dict(agent_id='agent', capability_id='land-cover',
        execution_context=dict(trace_id='private-trace'), input_refs=[copy.deepcopy(ref)])
    return workflow, proposal


class WorkflowNodeInputHandoffTests(unittest.TestCase):
    def compare(self, workflow=None, proposal=None, pin=None, node='private-node'):
        base, proposed = fixture()
        workflow = base if workflow is None else workflow
        proposal = proposed if proposal is None else proposal
        return compare_workflow_node_input_handoff(workflow,
            digest(workflow) if pin is None else pin, node, proposal)

    def test_match_is_private_nonexecuting_and_immutable(self):
        workflow, proposal = fixture()
        before = copy.deepcopy((workflow, proposal))
        with patch('builtins.open', side_effect=AssertionError('no IO')):
            result = self.compare(workflow, proposal)
        self.assertEqual(result['status'], 'MATCH')
        self.assertTrue(result['declarations_match'])
        self.assertEqual((workflow, proposal), before)
        self.assertTrue(all(result[key] is False for key in _FALSE_FLAGS))
        for key in ('network_requests', 'source_files_read', 'source_files_written',
                    'database_calls', 'registry_calls', 'resolver_calls', 'executor_calls'):
            self.assertIs(type(result[key]), int)
            self.assertEqual(result[key], 0)
        encoded = json.dumps(result)
        for secret in ('private-dataset', 'private-workflow', 'private-node', 'private-trace', 'file:///private'):
            self.assertNotIn(secret, encoded)

    def test_entire_request_pin_includes_policy_other_nodes_and_dependencies(self):
        workflow, proposal = fixture()
        second = copy.deepcopy(workflow['nodes'][0]); second.update(node_id='other', input_bindings=[])
        workflow['nodes'].append(second)
        pin = digest(workflow)
        for mutate in (lambda w:w['policy'].update(max_parallel=2),
                       lambda w:w['nodes'][1].update(agent_id='changed'),
                       lambda w:w['nodes'][1].update(depends_on=['private-node']),
                       lambda w:w['nodes'][0].update(timeout_seconds=5)):
            changed = copy.deepcopy(workflow); mutate(changed)
            result = self.compare(changed, proposal, pin)
            self.assertEqual(result['issues'][0]['code'], 'WORKFLOW_PIN_MISMATCH')
        # Dict key insertion order does not affect canonical request identity.
        self.assertEqual(self.compare(dict(reversed(list(workflow.items()))), proposal, pin)['status'], 'MATCH')

    def test_identity_and_ordered_input_field_mismatches(self):
        workflow, proposal = fixture()
        mutations = [('AGENT_ID_MISMATCH', lambda p:p.update(agent_id='other')),
            ('CAPABILITY_ID_MISMATCH', lambda p:p.update(capability_id='other')),
            ('TRACE_ID_MISMATCH', lambda p:p['execution_context'].update(trace_id='other'))]
        for field in ('id', 'version', 'sha256', 'role', 'uri'):
            value = 'b'*64 if field == 'sha256' else 'changed'
            mutations.append(('INPUT_'+field.upper()+'_MISMATCH',
                lambda p, f=field, v=value:p['input_refs'][0].update({f:v})))
        for code, mutate in mutations:
            with self.subTest(code=code):
                changed = copy.deepcopy(proposal); mutate(changed)
                result = self.compare(workflow, changed)
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertIn(code, [i['code'] for i in result['issues']])

    def test_role_uri_presence_and_empty_uri_preserved(self):
        workflow, proposal = fixture()
        for field in ('role', 'uri'):
            changed = copy.deepcopy(proposal); del changed['input_refs'][0][field]
            self.assertEqual(self.compare(workflow, changed)['status'], 'BLOCKED')
            changed_workflow = copy.deepcopy(workflow)
            del changed_workflow['nodes'][0]['input_bindings'][0][field]
            self.assertEqual(self.compare(changed_workflow, changed)['status'], 'MATCH')
            self.assertEqual(self.compare(changed_workflow, proposal)['status'], 'BLOCKED')
        workflow['nodes'][0]['input_bindings'][0]['uri']=''
        proposal['input_refs'][0]['uri']=''
        self.assertEqual(self.compare(workflow, proposal)['status'], 'MATCH')

    def test_same_id_different_versions_valid_conflicting_sha_invalid(self):
        workflow, proposal = fixture()
        ref=copy.deepcopy(proposal['input_refs'][0]); ref.update(version='v2',sha256='b'*64)
        workflow['nodes'][0]['input_bindings'].append(ref)
        proposal['input_refs'].append(copy.deepcopy(ref))
        self.assertEqual(self.compare(workflow, proposal)['status'], 'MATCH')
        reversed_proposal=copy.deepcopy(proposal); reversed_proposal['input_refs'].reverse()
        self.assertEqual(self.compare(workflow, reversed_proposal)['status'], 'BLOCKED')
        workflow['nodes'][0]['input_bindings'][1]['version']='v1'
        self.assertEqual(self.compare(workflow, proposal)['issues'][0]['code'], 'INPUT_IDENTITY_CONFLICT')

    def test_selected_node_empty_missing_ambiguous(self):
        workflow, proposal = fixture()
        self.assertEqual(self.compare(workflow, proposal,node='missing')['issues'][0]['code'], 'SELECTED_NODE_NOT_FOUND')
        workflow['nodes'].append(copy.deepcopy(workflow['nodes'][0]))
        self.assertEqual(self.compare(workflow, proposal)['issues'][0]['code'], 'NODE_ID_AMBIGUOUS')
        workflow['nodes'].pop(); workflow['nodes'][0]['input_bindings']=[]
        self.assertEqual(self.compare(workflow, proposal)['issues'][0]['code'], 'SELECTED_INPUTS_REQUIRED')

    def test_nonselected_empty_and_dag_cycle_do_not_claim_dag_validation(self):
        workflow, proposal = fixture()
        other=copy.deepcopy(workflow['nodes'][0]);other.update(node_id='other',input_bindings=[],depends_on=['private-node'])
        workflow['nodes'][0]['depends_on']=['other'];workflow['nodes'].append(other)
        result=self.compare(workflow, proposal)
        self.assertEqual(result['status'],'MATCH')
        self.assertIs(result['dag_validated'],False)

    def test_global_input_and_node_budgets(self):
        workflow, proposal = fixture()
        workflow['nodes'][0]['input_bindings']*=64
        proposal['input_refs']*=64
        self.assertEqual(self.compare(workflow,proposal)['status'],'MATCH')
        second=copy.deepcopy(workflow['nodes'][0]);second.update(node_id='other',input_bindings=[copy.deepcopy(proposal['input_refs'][0])])
        workflow['nodes'].append(second)
        self.assertEqual(self.compare(workflow,proposal)['issues'][0]['code'],'WORKFLOW_INPUT_LIMIT')
        workflow['nodes']=[dict(node_id=str(i),agent_id='a',capability_id='c',depends_on=[],input_bindings=[]) for i in range(129)]
        self.assertEqual(self.compare(workflow,proposal)['issues'][0]['code'],'WORKFLOW_NODE_COUNT_INVALID')

    def test_unknown_metadata_and_full_job_not_accepted(self):
        workflow,proposal=fixture()
        for target, field, value in ((workflow,'extra',{}),(workflow['policy'],'extension',{}),
            (workflow['nodes'][0],'aoi',{}),(proposal,'aoi',{}),
            (proposal['execution_context'],'purpose','science'),(proposal['input_refs'][0],'manifest_sha256','a'*64)):
            target[field]=value
            self.assertEqual(self.compare(workflow,proposal)['status'],'BLOCKED')
            del target[field]

    def test_typed_scalars_bounds_controls_surrogates_and_unpinned_version(self):
        workflow,proposal=fixture()
        changed=copy.deepcopy(workflow);changed['policy']['on_blocked']='X'*1000000
        self.assertEqual(self.compare(changed,proposal)['status'],'BLOCKED')
        for value in (True,1.0,0,2147483648,10**100):
            changed=copy.deepcopy(workflow);changed['policy']['max_parallel']=value
            self.assertEqual(self.compare(changed,proposal)['status'],'BLOCKED')
        for value in ('x'*257,'\x00','\x85','\ud800','   ',[],True):
            changed=copy.deepcopy(proposal);changed['input_refs'][0]['id']=value
            self.assertEqual(self.compare(workflow,changed)['status'],'BLOCKED')
        class Explosive:
            def __eq__(self, other):
                raise AssertionError('must reject before equality')
        changed=copy.deepcopy(proposal);changed['input_refs'][0]['uri']=Explosive()
        self.assertEqual(self.compare(workflow,changed)['issues'][0]['code'],'INPUT_URI_INVALID')
        for value in ('latest',' CURRENT '):
            changed=copy.deepcopy(proposal);changed['input_refs'][0]['version']=value
            self.assertEqual(self.compare(workflow,changed)['status'],'BLOCKED')
        self.assertEqual(self.compare(workflow,proposal,pin='A'*64)['status'],'BLOCKED')
        self.assertEqual(self.compare(workflow,proposal,node='x'*257)['status'],'BLOCKED')

    def test_recursive_containers_rejected_before_serialization(self):
        workflow,proposal=fixture();pin=digest(workflow)
        cases=[]
        cyclic={};cyclic['cycle']=cyclic
        cases.append((cyclic,proposal))
        w=copy.deepcopy(workflow);w['nodes'][0]['input_bindings'][0]['uri']=w;cases.append((w,proposal))
        p=copy.deepcopy(proposal);p['execution_context']['trace_id']=p;cases.append((workflow,p))
        w=copy.deepcopy(workflow);w['policy']['extension']=w;cases.append((w,proposal))
        for w,p in cases:
            result=compare_workflow_node_input_handoff(w,pin,'private-node',p)
            self.assertEqual(result['status'],'BLOCKED')

    def test_dependency_shape_unknown_self_rejected_duplicate_preserved(self):
        workflow,proposal=fixture()
        for deps in (['missing'],['private-node'],[[]],['x']*129):
            changed=copy.deepcopy(workflow);changed['nodes'][0]['depends_on']=deps
            self.assertEqual(self.compare(changed,proposal)['status'],'BLOCKED')

        other=copy.deepcopy(workflow['nodes'][0]);other.update(node_id='other',input_bindings=[])
        workflow['nodes'].append(other);workflow['nodes'][0]['depends_on']=['other','other']
        self.assertEqual(self.compare(workflow,proposal)['status'],'MATCH')

    def test_proposed_empty_count_mismatch_and_crossnode_conflict(self):
        workflow,proposal=fixture();proposal['input_refs']=[]
        self.assertEqual(self.compare(workflow,proposal)['issues'][0]['code'],'INPUT_COUNT_INVALID')
        workflow,proposal=fixture();proposal['input_refs']*=2
        self.assertEqual(self.compare(workflow,proposal)['issues'][0]['code'],'INPUT_COUNT_MISMATCH')
        second=copy.deepcopy(workflow['nodes'][0]);second['node_id']='other'
        second['input_bindings'][0]['sha256']='b'*64;workflow['nodes'].append(second)
        self.assertEqual(self.compare(workflow,proposal)['issues'][0]['code'],'INPUT_IDENTITY_CONFLICT')


if __name__=='__main__':
    unittest.main()
