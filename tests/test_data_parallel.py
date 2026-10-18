"""네트워크 없이 2worker 동시성, 중앙 정산, 공유 중단을 확인한다."""
from pathlib import Path
import sys
import threading
import unittest
import io
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.data.parallel import run_two_workers
from app.data import service
from app.data.budget import CollectionLedger


class ParallelTests(unittest.TestCase):
    def tearDown(self):
        service.configure_request_circuit(None)
        service.configure_request_spacing(0)
        service.configure_metadata_budget(None)

    def test_metadata_budgets_are_isolated_between_simultaneous_workers(self):
        barrier = threading.Barrier(2)
        class Response(io.BytesIO):
            headers = {}
        def worker(limit):
            service.configure_metadata_budget(limit)
            barrier.wait(timeout=5)
            service._metadata_response(Request(service.STAC_URL))
            return service.metadata_budget_status()
        with patch.object(service,"_open",side_effect=lambda request: Response(b"12345678")), ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, limit) for limit in (10, 20)]
            statuses = [f.result() for f in futures]
        self.assertEqual([s["maximum_bytes"] for s in statuses], [10,20])
        self.assertEqual([s["charged_bytes"] for s in statuses], [8,8])
        self.assertEqual(service.metadata_budget_status()["charged_bytes"], 0)

    def test_first_actual_429_blocks_later_http_without_claiming_new_server_response(self):
        event = threading.Event()
        service.configure_request_circuit(event)
        error = HTTPError(service.PC_STAC_URL + "?sig=secret",429,"Too many",{"Retry-After":"60"},None)
        with patch.object(service,"build_opener") as builder:
            builder.return_value.open.side_effect = error
            with self.assertRaises(HTTPError):
                service._open(Request(service.PC_STAC_URL))
            with self.assertRaises(service.SharedCollectionStop):
                service._open(Request(service.PC_STAC_URL))
            self.assertEqual(builder.return_value.open.call_count,1)
        self.assertTrue(event.is_set())
        reason = service.request_circuit_status()
        self.assertEqual(reason["retry_after"],"60")
        self.assertNotIn("sig",str(reason))
    def test_two_workers_overlap_but_ledger_callbacks_stay_in_parent(self):
        barrier = threading.Barrier(2)
        parent = threading.get_ident()
        worker_ids, callback_ids, final = set(), [], []
        def reserve(job):
            callback_ids.append(threading.get_ident())
            return True
        def work(job):
            worker_ids.add(threading.get_ident())
            barrier.wait(timeout=5)
            return {"value": job}
        def finalize(job, result):
            callback_ids.append(threading.get_ident())
            final.append(result["value"])
        report = run_two_workers([1,2,3,4], reserve, work, finalize)
        self.assertEqual(len(worker_ids), 2)
        self.assertEqual(set(callback_ids), {parent})
        self.assertEqual(sorted(final), [1,2,3,4])
        self.assertEqual(report["submitted_batches"], 4)

    def test_first_rate_limit_event_prevents_queued_third_batch(self):
        event, barrier = threading.Event(), threading.Barrier(2)
        final = []
        def work(job):
            barrier.wait(timeout=5)
            event.set()
            return {"rate_limited": job == 1}
        report = run_two_workers(range(1,20), lambda job: True, work,
            lambda job, result: final.append(job), event)
        self.assertEqual(sorted(final), [1,2])
        self.assertEqual(report["submitted_batches"], 2)
        self.assertTrue(report["circuit_open"])

    def test_unmeasured_failure_is_finalized_without_zero_refund_claim(self):
        final = []
        def work(job):
            raise RuntimeError("unknown interruption")
        run_two_workers([1], lambda job: True, work, lambda job, result: final.append(result))
        self.assertIsInstance(final[0]["unmeasured_worker_failure"], RuntimeError)

    def test_second_reserve_failure_drains_first_worker_and_settles_real_temp_ledger(self):
        for worker_fails in (False, True):
            with self.subTest(worker_fails=worker_fails), tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/'ledger.json'
                path.write_text(json.dumps({'additional_maximum_bytes': 1000, 'historical_ledgers': [],
                    'new_charged_bytes': 0, 'batches': {}, 'rate_limit_active': False}), encoding='utf-8')
                ledger = CollectionLedger(path, [], additional_budget=1000)
                entered, release = threading.Event(), threading.Event()
                original = FileExistsError('synthetic second output collision')
                final = []
                def reserve(job):
                    if job == 2:
                        self.assertTrue(entered.wait(5)); release.set(); raise original
                    return ledger.reserve(str(job), 100, 'a'*64)
                def work(job):
                    entered.set()
                    if not release.wait(5): raise RuntimeError('release timeout')
                    if worker_fails: raise RuntimeError('unknown worker transfer')
                    return {'charged': 17}
                def finalize(job, result):
                    final.append(job)
                    ledger.settle(str(job), 100 if 'unmeasured_worker_failure' in result else result['charged'])
                with self.assertRaises(FileExistsError) as caught:
                    run_two_workers([1, 2, 3], reserve, work, finalize)
                self.assertIs(caught.exception, original)
                self.assertEqual(final, [1])
                state = ledger.snapshot()
                self.assertEqual(set(state['batches']), {'1'})
                self.assertEqual(state['batches']['1']['status'], 'settled')
                self.assertEqual(state['new_charged_bytes'], 100 if worker_fails else 17)

    def test_iterator_failure_drains_existing_worker_before_reraising_original(self):
        entered, release = threading.Event(), threading.Event()
        original = RuntimeError('iterator failed'); final = []
        def jobs():
            yield 1
            self.assertTrue(entered.wait(5)); release.set(); raise original
        def work(job):
            entered.set(); self.assertTrue(release.wait(5)); return {'job': job}
        with self.assertRaises(RuntimeError) as caught:
            run_two_workers(jobs(), lambda job: True, work, lambda job, result: final.append(job))
        self.assertIs(caught.exception, original); self.assertEqual(final, [1])

    def test_submit_failure_finalizes_reserved_job_and_drains_prior_worker(self):
        entered, release = threading.Event(), threading.Event()
        original = RuntimeError('executor rejected second submit')
        real_submit = ThreadPoolExecutor.submit
        calls, reserved, finalized = [], [], []
        def submit(executor, function, job):
            calls.append(job)
            if job == 2:
                self.assertTrue(entered.wait(5)); release.set(); raise original
            return real_submit(executor, function, job)
        def reserve(job): reserved.append(job); return True
        def work(job): entered.set(); self.assertTrue(release.wait(5)); return {'job': job}
        def finalize(job, result): finalized.append((job, result))
        with patch('app.data.parallel.ThreadPoolExecutor.submit', new=submit), self.assertRaises(RuntimeError) as caught:
            run_two_workers([1, 2, 3], reserve, work, finalize)
        self.assertIs(caught.exception, original)
        self.assertEqual(reserved, [1, 2]); self.assertEqual(calls, [1, 2])
        self.assertCountEqual([j for j, _ in finalized], [1, 2])
        self.assertIs(next(v for j, v in finalized if j == 2)['unmeasured_worker_failure'], original)

    def test_finalize_error_after_settlement_never_retries_and_drains_other_job(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'ledger.json'
            path.write_text(json.dumps({'additional_maximum_bytes': 1000, 'historical_ledgers': [],
                'new_charged_bytes': 0, 'batches': {}, 'rate_limit_active': False}), encoding='utf-8')
            ledger = CollectionLedger(path, [], additional_budget=1000)
            barrier = threading.Barrier(2); attempts, reserved = [], []
            original = OSError('manifest publication failed after settlement')
            def reserve(job): reserved.append(job); return ledger.reserve(str(job), 100, 'a'*64)
            def work(job): barrier.wait(5); return {'charged': 10}
            def finalize(job, result):
                attempts.append(job); ledger.settle(str(job), result['charged'])
                if len(attempts) == 1: raise original
            with self.assertRaises(OSError) as caught:
                run_two_workers([1, 2, 3], reserve, work, finalize)
            self.assertIs(caught.exception, original)
            self.assertCountEqual(attempts, [1, 2]); self.assertEqual(reserved, [1, 2])
            self.assertEqual(ledger.snapshot()['new_charged_bytes'], 20)
            self.assertTrue(all(v['status'] == 'settled' for v in ledger.snapshot()['batches'].values()))

    def test_first_coordinator_error_preserved_when_drain_finalize_also_fails(self):
        entered, release = threading.Event(), threading.Event()
        original = FileExistsError('first reservation failure'); final = []
        def reserve(job):
            if job == 2:
                self.assertTrue(entered.wait(5)); release.set(); raise original
            return True
        def work(job): entered.set(); self.assertTrue(release.wait(5)); return {}
        def finalize(job, result): final.append(job); raise OSError('later finalization failure')
        with self.assertRaises(FileExistsError) as caught:
            run_two_workers([1, 2, 3], reserve, work, finalize)
        self.assertIs(caught.exception, original); self.assertEqual(final, [1])

    def test_budget_valueerror_preserves_stop_reason_and_drains_existing_job(self):
        entered, release = threading.Event(), threading.Event(); final = []
        def reserve(job):
            if job == 2:
                self.assertTrue(entered.wait(5)); release.set(); raise ValueError('budget unavailable')
            return True
        def work(job): entered.set(); self.assertTrue(release.wait(5)); return {}
        report = run_two_workers([1, 2, 3], reserve, work, lambda job, result: final.append(job))
        self.assertEqual(final, [1]); self.assertEqual(report['stop_reason'], 'global_budget_remaining_insufficient')
        self.assertEqual(report['submitted_batches'], 1); self.assertEqual(report['finalized_batches'], 1)

    def test_reserve_failure_and_worker_429_still_finalize_once_without_third_submit(self):
        entered, release, event = threading.Event(), threading.Event(), threading.Event()
        original = FileExistsError('second output collision'); final, reserved = [], []
        def reserve(job):
            reserved.append(job)
            if job == 2:
                self.assertTrue(entered.wait(5)); release.set(); raise original
            return True
        def work(job):
            entered.set(); self.assertTrue(release.wait(5)); event.set(); return {'rate_limited': True}
        def finalize(job, result): final.append(job); self.assertTrue(result['rate_limited'])
        with self.assertRaises(FileExistsError) as caught:
            run_two_workers([1, 2, 3], reserve, work, finalize, event)
        self.assertIs(caught.exception, original); self.assertEqual(final, [1])
        self.assertTrue(event.is_set()); self.assertEqual(reserved, [1, 2])


if __name__ == "__main__":
    unittest.main()
