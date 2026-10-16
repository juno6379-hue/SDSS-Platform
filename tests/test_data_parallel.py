"""네트워크 없이 2worker 동시성, 중앙 정산, 공유 중단을 확인한다."""
from pathlib import Path
import sys
import threading
import unittest
import io
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.data.parallel import run_two_workers
from app.data import service


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


if __name__ == "__main__":
    unittest.main()
