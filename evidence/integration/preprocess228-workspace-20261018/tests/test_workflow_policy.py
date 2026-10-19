"""합성 DAG의 계획 진단시험. local-clean 노드는 실제 실행 가능/모델 승인 상태가 아니다."""
import copy
import random
import unittest

from app.workflow_policy import diagnose_workflow_blocking


class WorkflowPolicyTests(unittest.TestCase):
    def node(self,identifier,dependencies=(),blocked=False):
        return {'node_id':identifier,'depends_on':list(dependencies),
                'blockers':[{'code':'EXPLICIT_SYNTHETIC_LOCAL_BLOCKER'}] if blocked else []}

    def diagnose(self,nodes,mode='STOP_DEPENDENTS'):
        result=diagnose_workflow_blocking(nodes,{'on_blocked':mode})
        self.assertFalse(result['execution_authorized'])
        for node in result['nodes']:
            self.assertFalse(node['execution_authorized'])
            self.assertNotIn(node['diagnostic_status'],('READY','RUNNING','SUCCEEDED'))
        return result,{node['node_id']:node for node in result['nodes']}

    def test_stop_dependents_only_follows_actual_dependency_paths(self):
        nodes=[self.node('source',blocked=True),self.node('dependent',['source']),self.node('leaf',['dependent']),self.node('independent')]
        result,by_id=self.diagnose(nodes)
        self.assertEqual(result['local_blocking_node_ids'],['source'])
        for identifier in ('dependent','leaf'):
            self.assertEqual(by_id[identifier]['upstream_blocked_by'],['source'])
            self.assertEqual(by_id[identifier]['local_blockers'],[])
        self.assertEqual(by_id['source']['upstream_blocked_by'],[])
        self.assertEqual(by_id['source']['blocking_cause_node_ids'],['source'])
        self.assertEqual(by_id['independent']['blocking_cause_node_ids'],[])
        self.assertEqual(by_id['independent']['diagnostic_status'],'NO_BLOCKING_CAUSE_IDENTIFIED')
        self.assertTrue(all(not node['policy_blocked_by'] for node in result['nodes']))

    def test_diamond_paths_do_not_duplicate_root_causes(self):
        nodes=[self.node('root',blocked=True),self.node('left',['root']),self.node('right',['root']),self.node('merge',['left','right'])]
        _,by_id=self.diagnose(nodes)
        self.assertEqual(by_id['merge']['upstream_blocked_by'],['root'])
        self.assertEqual(by_id['merge']['blocking_cause_node_ids'],['root'])

    def test_multiple_local_seeds_and_local_plus_upstream_causes_stay_distinct(self):
        nodes=[self.node('a',blocked=True),self.node('b',['a'],True),self.node('c',blocked=True),self.node('merge',['b','c'])]
        _,by_id=self.diagnose(nodes)
        self.assertEqual(by_id['b']['upstream_blocked_by'],['a'])
        self.assertEqual(by_id['b']['blocking_cause_node_ids'],['a','b'])
        self.assertEqual(by_id['merge']['upstream_blocked_by'],['a','b','c'])
        self.assertEqual(by_id['merge']['blocking_cause_node_ids'],['a','b','c'])
        self.assertEqual(by_id['c']['upstream_blocked_by'],[])

    def test_fail_all_adds_only_nonancestor_other_local_seeds_as_policy_causes(self):
        nodes=[self.node('a',blocked=True),self.node('b',['a']),self.node('c',blocked=True),self.node('independent')]
        _,by_id=self.diagnose(nodes,'FAIL_ALL')
        self.assertEqual(by_id['b']['upstream_blocked_by'],['a'])
        self.assertEqual(by_id['b']['policy_blocked_by'],['c'])
        self.assertEqual(by_id['a']['policy_blocked_by'],['c'])
        self.assertEqual(by_id['c']['policy_blocked_by'],['a'])
        self.assertEqual(by_id['independent']['upstream_blocked_by'],[])
        self.assertEqual(by_id['independent']['policy_blocked_by'],['a','c'])
        for node in by_id.values():
            self.assertEqual(node['blocking_cause_node_ids'],['a','c'])
            self.assertNotIn(node['node_id'],node['upstream_blocked_by']+node['policy_blocked_by'])

    def test_fail_all_without_local_seed_does_not_invent_policy_blocking(self):
        for mode in ('STOP_DEPENDENTS','FAIL_ALL'):
            result,by_id=self.diagnose([self.node('a'),self.node('b',['a'])],mode)
            self.assertEqual(result['local_blocking_node_ids'],[])
            self.assertTrue(all(node['diagnostic_status']=='NO_BLOCKING_CAUSE_IDENTIFIED' for node in by_id.values()))

    def test_many_orderings_are_deterministic_including_blocker_and_dependency_order(self):
        nodes=[self.node('a',blocked=True),self.node('b',['a']),self.node('c',blocked=True),self.node('d',['a','b','c'])]
        nodes[0]['blockers']=[{'code':'Z','input_index':1},{'code':'A','input_index':0}]
        for mode in ('STOP_DEPENDENTS','FAIL_ALL'):
            expected,_=self.diagnose(nodes,mode)
            for seed in range(12):
                shuffled=copy.deepcopy(nodes);rng=random.Random(seed);rng.shuffle(shuffled)
                for node in shuffled:
                    rng.shuffle(node['depends_on']);rng.shuffle(node['blockers'])
                self.assertEqual(self.diagnose(shuffled,mode)[0],expected)

    def test_schema_valid_repeated_dependencies_and_opaque_identifiers_are_supported(self):
        once=[self.node(' ',blocked=True),self.node('next',[' '])]
        repeated=copy.deepcopy(once);repeated[1]['depends_on']=[' ',' ',' ']
        original=copy.deepcopy(repeated)
        for mode in ('STOP_DEPENDENTS','FAIL_ALL'):
            self.assertEqual(self.diagnose(repeated,mode)[0],self.diagnose(once,mode)[0])
        self.assertEqual(repeated,original)

    def test_original_graph_and_policy_are_unchanged_and_output_is_detached(self):
        nodes=[self.node('a',blocked=True),self.node('b',['a'])]
        nodes[0]['blockers'][0]['details']={'indexes':[0,1]}
        policy={'on_blocked':'STOP_DEPENDENTS','max_parallel':2}
        before=copy.deepcopy((nodes,policy))
        result=diagnose_workflow_blocking(nodes,policy)
        self.assertEqual((nodes,policy),before)
        result['nodes'][0]['local_blockers'][0]['details']['indexes'].append(99)
        self.assertEqual((nodes,policy),before)

    def test_invalid_policy_duplicate_nodes_dependencies_missing_self_and_cycle_are_rejected(self):
        valid=[self.node('a')]
        for policy in (None,{},'STOP_DEPENDENTS',{'on_blocked':'IGNORE'},{'on_blocked':None}):
            with self.subTest(policy=policy),self.assertRaises(ValueError):
                diagnose_workflow_blocking(valid,policy)
        graphs=[[],None,[self.node('a'),self.node('a')],
                [self.node('a',['missing'])],[self.node('a',['a'])],
                [self.node('a',['b']),self.node('b',['a'])],
                [{'node_id':'a','depends_on':[],'blockers':['not-an-object']}],
                [{'node_id':'a','depends_on':'b','blockers':[]}]]
        for graph in graphs:
            with self.subTest(graph=graph),self.assertRaises(ValueError):
                diagnose_workflow_blocking(graph,{'on_blocked':'STOP_DEPENDENTS'})


if __name__=='__main__':
    unittest.main()
