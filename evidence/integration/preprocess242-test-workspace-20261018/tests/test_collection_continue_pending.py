"""Explicit unrelated-job continuation preserves interrupted budget and identity."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.collect_training_parallel import continuation_jobs
from app.data.budget import CollectionLedger
from app.data.parallel import run_two_workers


def digest(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


class ContinuePendingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        prior = self.root/'prior.json'
        prior.write_text(json.dumps({'reserved_or_transferred_bytes_including_prior': 100}), encoding='utf-8')
        self.ledger = CollectionLedger(self.root/'ledger.json', [prior], additional_budget=1000)
        self.jobs = [{'key':'old', 'config':{'year':2023}}, {'key':'new', 'config':{'year':2024}}]
        self.ledger.reserve('old', 400, digest(self.jobs[0]['config']))
        self.before = self.ledger.path.read_bytes()
        self.snapshot = self.ledger.snapshot()

    def test_default_keeps_pending_and_existing_reserve_refuses(self):
        jobs, metadata = continuation_jobs(self.jobs, self.snapshot)
        self.assertEqual(jobs, self.jobs)
        self.assertFalse(metadata['enabled'])
        with self.assertRaisesRegex(RuntimeError, '자동 재실행'):
            self.ledger.reserve(jobs[0]['key'],400,digest(jobs[0]['config']))
        self.assertEqual(self.before,self.ledger.path.read_bytes())

    def test_opt_in_excludes_only_pending_without_mutating_inputs_or_ledger(self):
        original = copy.deepcopy((self.jobs,self.snapshot))
        jobs, metadata = continuation_jobs(self.jobs,self.snapshot,True)
        self.assertEqual([j['key'] for j in jobs],['new'])
        self.assertEqual(metadata['excluded_pending_keys'],['old'])
        self.assertEqual(metadata['observed_pending'][0]['reserved_bytes_preserved'],400)
        self.assertEqual(metadata['refund_bytes'],0)
        self.assertFalse(metadata['settlement_attempted'])
        self.assertFalse(metadata['lock_handover_performed'])
        self.assertEqual(original,(self.jobs,self.snapshot))
        self.assertEqual(self.before,self.ledger.path.read_bytes())

    def test_changed_pending_config_refuses_before_writes(self):
        self.jobs[0]['config']['year']=2025
        with self.assertRaisesRegex(RuntimeError,'설정이 달라'):
            continuation_jobs(self.jobs,self.snapshot,True)
        self.assertEqual(self.before,self.ledger.path.read_bytes())

    def test_settled_is_retained_for_existing_ledger_skip(self):
        self.ledger.reserve('settled',100,digest({'year':2020}))
        self.ledger.settle('settled',50)
        job={'key':'settled','config':{'year':2020}}
        jobs,meta=continuation_jobs(self.jobs+[job],self.ledger.snapshot(),True)
        self.assertIn(job,jobs)
        self.assertFalse(self.ledger.reserve('settled',100,digest(job['config'])))
        self.assertEqual(meta['excluded_pending_keys'],['old'])

    def test_unlisted_pending_is_observed_and_not_invented_or_settled(self):
        jobs,meta=continuation_jobs([self.jobs[1]],self.snapshot,True)
        self.assertEqual(jobs,[self.jobs[1]])
        self.assertEqual(meta['excluded_pending_keys'],[])
        self.assertEqual(meta['observed_pending'][0]['key'],'old')
        self.assertEqual(self.before,self.ledger.path.read_bytes())

    def test_all_pending_leaves_empty_queue_without_worker_or_settlement(self):
        jobs,meta=continuation_jobs([self.jobs[0]],self.snapshot,True)
        def forbidden(*args):
            self.fail('Empty queue must not reserve, execute, or finalize')
        summary=run_two_workers(jobs,forbidden,forbidden,forbidden)
        self.assertEqual(summary['submitted_batches'],0)
        self.assertEqual(self.before,self.ledger.path.read_bytes())

    def test_new_work_uses_same_budget_and_preserves_full_old_reservation(self):
        jobs,_=continuation_jobs(self.jobs,self.snapshot,True)
        self.assertTrue(self.ledger.reserve(jobs[0]['key'],500,digest(jobs[0]['config'])))
        self.ledger.settle('new',200)
        after=self.ledger.snapshot()
        self.assertEqual(after['batches']['old'],self.snapshot['batches']['old'])
        self.assertEqual(after['new_charged_bytes'],600)
        self.assertEqual(after['additional_maximum_bytes'],1000)
        with self.assertRaises(ValueError):
            self.ledger.reserve('too-large',401,digest({}))
        self.assertEqual(self.ledger.snapshot(),after)


if __name__=='__main__':
    unittest.main()
