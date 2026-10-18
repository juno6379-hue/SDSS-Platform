import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect_training_priority as priority


def job(province,year,index=0):
    return {'key':f'{province}-{year}-{index}','province':province,'year':year,
        'split':'train','spatial_window_id':str(index),'config':{'province':province,'year':year,'seed':index}}


def scene(province,year,index=99):
    return {'province':province,'year':year,'quality_status':'quality_eligible',
        'spatial_location_id':f'{province}/{index}/patch'}


class PriorityTests(unittest.TestCase):
    def test_deficit_descending_limit_and_original_identity_no_mutation(self):
        jobs=[job('a',2020),job('b',2020),job('c',2020)]
        scenes=[scene('a',2020) for _ in range(27)]+[scene('b',2020) for _ in range(10)]
        snapshot={'batches':{}}
        before=copy.deepcopy((jobs,scenes,snapshot))
        selected=priority.prioritize_jobs(jobs,scenes,snapshot,limit=2)
        self.assertIs(selected[0],jobs[2]);self.assertIs(selected[1],jobs[1])
        self.assertEqual((jobs,scenes,snapshot),before)

    def test_exact_target_covered_excluded_unknown_year_counted_separately(self):
        rows=[scene('a',2020) for _ in range(28)]+[scene('a',2021) for _ in range(50)]
        self.assertEqual(priority.prioritize_jobs([job('a',2020)],rows,{'batches':{}},limit=1),[])
        self.assertEqual(len(priority.prioritize_jobs([job('a',2022)],rows,{'batches':{}},limit=1)),1)

    def test_settled_pending_and_same_spatial_eligible_are_not_retried(self):
        first,second=job('a',2020),job('b',2020)
        digest=priority._digest(first['config'])
        state={'batches':{first['key']:{'status':'settled','config_sha256':digest}}}
        self.assertEqual(priority.prioritize_jobs([first,second],[scene('b',2020,0)],state,limit=2),[])
        state['batches'][first['key']]['status']='pending'
        with self.assertRaisesRegex(ValueError,'PENDING'):priority.prioritize_jobs([first],[],state,limit=1)
        first['config']['changed']=True
        with self.assertRaisesRegex(ValueError,'CONFIG_CHANGED'):priority.prioritize_jobs([first],[],state,limit=1)

    def test_sha_is_existing_ledger_encoding_and_stable_under_queue_order(self):
        jobs=[job('z',2020),job('a',2021),job('a',2020)]
        jobs[0]['config']['unicode']='반텐'
        self.assertEqual(priority._digest(jobs[0]['config']),hashlib.sha256(json.dumps(jobs[0]['config'],sort_keys=True).encode()).hexdigest())
        one=priority.build_priority_plan(jobs,[],{'batches':{}},limit=2)
        two=priority.build_priority_plan(list(reversed(jobs)),[],{'batches':{}},limit=2)
        self.assertEqual(one,two);self.assertEqual([r['year'] for r in one['selected_jobs']],[2020,2021])

    def test_pin_drift_and_limits_fail_closed(self):
        jobs=[job('a',2020)];state={'batches':{}}
        plan=priority.build_priority_plan(jobs,[],state,limit=1)
        self.assertEqual(priority.verify_priority_plan(jobs,[],state,limit=1,expected_sha256=plan['plan_sha256']),jobs)
        for changed in ([scene('a',2020)],):
            with self.assertRaisesRegex(ValueError,'CHANGED'):priority.verify_priority_plan(jobs,changed,state,limit=1,expected_sha256=plan['plan_sha256'])
        for limit in (0,3,True,1.0):
            with self.assertRaises(ValueError):priority.prioritize_jobs(jobs,[],state,limit=limit)
        with self.assertRaises(ValueError):priority.prioritize_jobs(jobs+jobs,[],state,limit=1)

    def test_pending_reservations_plan_preserves_all_values(self):
        row={'status':'pending','config_sha256':'a'*64,'reserved_bytes':123,'charged_bytes':123}
        snapshot={'batches':{'old':row}}
        plan=priority.build_priority_plan([job('new',2020)],[],snapshot,limit=2)
        self.assertEqual(plan['pending_reservations_preserved'][0],{'key':'old','config_sha256':'a'*64,'reserved_bytes':123,'charged_bytes':123})
        self.assertFalse(plan['bare_targeted_256_supported']);self.assertFalse(plan['learning_ready'])

    def test_cli_dry_run_no_writes_and_explicit_execute_subprocess_only(self):
        import collect_training_parallel as legacy
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'data/output';output.mkdir(parents=True)
            config=root/'configs';config.mkdir();(config/'first-group.collection.json').write_text('{}')
            budget=root/'data/first-group-training-budget';budget.mkdir()
            (budget/'global-ledger.json').write_text('{"batches":{}}')
            (output/'annual-window-report.json').write_text('{"scenes":[]}')
            jobs=[job('b',2020),job('a',2020)]
            before={p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            args=['--output',str(output),'--max-batches','2','--continue-unrelated-pending']
            with patch.object(priority,'ROOT',root),patch.object(legacy,'v2_jobs',return_value=jobs),patch.object(legacy,'extra_jobs',return_value=[]),patch.object(priority.subprocess,'run') as run,patch('builtins.print'):
                self.assertEqual(priority.main(args),0);run.assert_not_called()
                self.assertEqual(priority.main(args+['--execute']),2);run.assert_not_called()
                pin=priority.build_priority_plan(jobs,[],{'batches':{}},limit=2)['plan_sha256']
                run.return_value.returncode=0
                self.assertEqual(priority.main(args+['--execute','--expected-plan-sha256',pin]),0)
                command=run.call_args.args[0]
                self.assertIn('--priority-deficit',command);self.assertIn(pin,command)
                self.assertIn('--continue-unrelated-pending',command)
            self.assertEqual({p:p.read_bytes() for p in root.rglob('*') if p.is_file()},before)

    def _collector_fixture(self,root):
        output=root/'data/output';output.mkdir(parents=True)
        configs=root/'configs';configs.mkdir()
        (configs/'first-group.collection.json').write_text(json.dumps({'aois':[{'id':p} for p in ('a','b','c')]}))
        budget=root/'data/first-group-training-budget';budget.mkdir()
        (output/'annual-window-report.json').write_text('{"scenes":[]}')
        state={'batches':{},'combined_maximum_bytes':2**32,'new_charged_bytes':0}
        ledger=SimpleNamespace(path=budget/'global-ledger.json',snapshot=Mock(return_value=state),reserve=Mock(),settle=Mock())
        return output,state,ledger

    def test_actual_collector_hook_wrong_pin_no_reserve_and_own_lock_released(self):
        import collect_training_parallel as legacy
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output,state,ledger=self._collector_fixture(root)
            args=['collector','--output',str(output),'--execute','--max-batches','2','--priority-deficit','--priority-plan-sha256','0'*64]
            with patch.object(legacy,'ROOT',root),patch.object(legacy,'CollectionLedger',return_value=ledger),patch.object(legacy,'v2_jobs',return_value=[job('a',2020)]),patch.object(legacy,'extra_jobs',return_value=[]),patch.object(legacy,'run_two_workers') as coordinator,patch.object(sys,'argv',args):
                try:
                    with self.assertRaisesRegex(ValueError,'PLAN_CHANGED'):legacy.main()
                    coordinator.assert_not_called();ledger.reserve.assert_not_called();ledger.settle.assert_not_called()
                    self.assertFalse(ledger.path.with_suffix('.execution.lock').exists())
                finally:legacy.service.configure_request_circuit(None)

    def test_actual_collector_hook_selected_jobs_and_existing_callbacks(self):
        import collect_training_parallel as legacy
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output,state,ledger=self._collector_fixture(root)
            jobs=[job('c',2020),job('a',2020),job('b',2020)]
            pin=priority.build_priority_plan(jobs,[],state,limit=2)['plan_sha256']
            args=['collector','--output',str(output),'--execute','--max-batches','2','--priority-deficit','--priority-plan-sha256',pin]
            with patch.object(legacy,'ROOT',root),patch.object(legacy,'CollectionLedger',return_value=ledger),patch.object(legacy,'v2_jobs',return_value=jobs),patch.object(legacy,'extra_jobs',return_value=[]),patch.object(legacy,'run_two_workers',return_value={}) as coordinator,patch.object(sys,'argv',args):
                self.assertEqual(legacy.main(),0)
                call=coordinator.call_args.args
                self.assertEqual([j['province'] for j in call[0]],['a','b'])
                self.assertEqual([fn.__name__ for fn in call[1:4]],['reserve','work','finalize'])
                self.assertEqual(call[-1],2)
                self.assertFalse(ledger.path.with_suffix('.execution.lock').exists())


if __name__=='__main__':unittest.main()
