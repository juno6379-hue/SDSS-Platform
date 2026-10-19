"""중단 조사에서 예약 손실이나 성급한 재개 허용이 없는지 검증한다."""
import hashlib
import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data.recovery import inspect_recovery, build_recovery_plan, validate_recovery_plan


class RecoveryInspectionTests(unittest.TestCase):
    def fixture(self, root, key="batch-1"):
        config = {"years": [2023]}
        directory = root / "first-group-training-esri-v1/sources" / key
        directory.mkdir(parents=True)
        (directory / "config.json").write_text(json.dumps(config), encoding="utf-8")
        ledger = root / "first-group-training-budget/global-ledger.json"
        ledger.parent.mkdir()
        ledger.write_text(json.dumps({"additional_maximum_bytes": 1000,
            "new_charged_bytes": 110, "external_research_metadata_body_bytes": 10,
            "batches": {key: {"status": "pending", "reserved_bytes": 100, "charged_bytes": 100,
                "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}}}), encoding="utf-8")
        return directory, ledger

    def test_interrupted_worker_preserves_full_reservation_and_every_source_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, ledger = self.fixture(root)
            (directory / "window-state.json").write_text('{"http_body_bytes": 40, "http_body_bytes_measured": 12}')
            (directory / "image.part").write_bytes(b"partial bytes")
            ledger.with_suffix(".execution.lock").touch()
            before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = inspect_recovery(root)
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            self.assertEqual(result["pending_reserved_bytes"], 100)
            self.assertEqual(result["remaining_budget_bytes"], 890)
            self.assertFalse(result["automatic_resume_allowed"])
            self.assertFalse(result["process_health_verified"])
            batch = result["pending_batches"][0]
            self.assertTrue(batch["config_matches_ledger"])
            self.assertEqual(batch["partial_files"][0]["bytes"], 13)
            self.assertFalse(batch["settlement_authorized"])

    def test_terminal_worker_file_alone_does_not_authorize_settlement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, _ = self.fixture(root)
            (directory / "worker-result.json").write_text('{"charged_bytes": 40}')
            batch = inspect_recovery(root)["pending_batches"][0]
            self.assertTrue(batch["worker_terminal_evidence_present"])
            self.assertFalse(batch["settlement_authorized"])

    def test_coordinator_report_lag_does_not_replace_ledger_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / "first-group-training-esri-v1/run-result.json").write_text('{"new_charged_upper_bound_bytes": 10}')
            result = inspect_recovery(root)
            self.assertEqual(result["run_result_ledger_delta_bytes"], 100)
            self.assertTrue(result["ledger_internal_sum_matches"])
            self.assertEqual(result["remaining_budget_bytes"], 890)

    def test_corrupt_worker_json_is_visible_and_never_terminal_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, _ = self.fixture(root)
            (directory / "worker-result.json").write_text('{broken')
            batch = inspect_recovery(root)["pending_batches"][0]
            self.assertTrue(batch["artifacts"]["worker-result.json"]["invalid_json"])
            self.assertFalse(batch["worker_terminal_evidence_present"])

    def test_untrusted_batch_path_cannot_escape_source_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, ledger_path = self.fixture(root)
            ledger = json.loads(ledger_path.read_text())
            ledger["batches"]["../../../outside"] = ledger["batches"].pop("batch-1")
            ledger_path.write_text(json.dumps(ledger))
            with self.assertRaises(ValueError):
                inspect_recovery(root)


class RecoveryPlanTests(unittest.TestCase):
    fixture = RecoveryInspectionTests.fixture

    def prepare(self, root):
        directory, ledger = self.fixture(root)
        (root / 'first-group-training-esri-v1/annual-window-report.json').write_text('{"scenes":[]}')
        (directory / 'window-state.json').write_text('{"http_body_bytes":40,"http_body_bytes_measured":12}')
        return directory, ledger

    def test_same_snapshot_has_stable_id_and_no_source_byte_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            before = {str(path): path.read_bytes() for path in root.rglob('*') if path.is_file()}
            first, second = build_recovery_plan(root), build_recovery_plan(root)
            self.assertEqual(first, second)
            validation = validate_recovery_plan(root, first)
            self.assertTrue(validation['valid_for_review'])
            self.assertEqual(validation['status'], 'VALID_BLOCKED')
            self.assertFalse(validation['execution_authorized'])
            self.assertFalse(first['execution_authorized'])
            self.assertEqual(first['batches'][0]['proposed_refund_bytes'], 0)
            self.assertEqual(first['snapshot']['pending_reserved_bytes'], 100)
            self.assertEqual(first['process_evidence']['state'], 'NOT_VERIFIED')
            self.assertEqual(before, {str(path): path.read_bytes() for path in root.rglob('*') if path.is_file()})

    def test_each_protected_snapshot_change_rejects_previous_plan(self):
        for target in ('ledger', 'manifest', 'config', 'state', 'terminal', 'lock', 'partial'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                directory, ledger = self.prepare(root)
                partial = directory / 'image.part'
                partial.write_bytes(b'1111')
                plan = build_recovery_plan(root)
                if target == 'ledger':
                    value = json.loads(ledger.read_text())
                    value['new_charged_bytes'] = 111
                    ledger.write_text(json.dumps(value))
                elif target == 'manifest':
                    (root / 'first-group-training-esri-v1/annual-window-report.json').write_text('{"scenes":[],"changed":true}')
                elif target == 'config':
                    (directory / 'config.json').write_text('{"years":[2024]}')
                elif target == 'state':
                    (directory / 'window-state.json').write_text('{"http_body_bytes":41}')
                elif target == 'terminal':
                    (directory / 'worker-result.json').write_text('{}')
                elif target == 'lock':
                    ledger.with_suffix('.execution.lock').touch()
                else:
                    # 동일 크기 파일의 내용 변화도 stale이다.
                    partial.write_bytes(b'2222')
                result = validate_recovery_plan(root, plan)
                self.assertFalse(result['valid_for_review'])
                self.assertIn('SNAPSHOT_STALE', result['errors'])
                self.assertNotEqual(plan['plan_id'], build_recovery_plan(root)['plan_id'])

    def test_plan_tampering_is_rejected_even_with_recomputed_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            plan = build_recovery_plan(root)
            for field, value in (('execution_authorized', True), ('prohibited_actions', []), ('blockers', [])):
                with self.subTest(field=field):
                    tampered = copy.deepcopy(plan)
                    tampered[field] = value
                    body = {key: val for key, val in tampered.items() if key != 'plan_id'}
                    tampered['plan_id'] = 'collection-recovery-' + hashlib.sha256(json.dumps(body,
                        sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                    validation = validate_recovery_plan(root, tampered)
                    self.assertFalse(validation['valid_for_review'])
                    self.assertIn('PLAN_CONTENT_MISMATCH', validation['errors'])

    def test_incomplete_terminal_never_authorizes_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory, _ = self.prepare(root)
            plan = build_recovery_plan(root)
            codes = {entry['code'] for entry in plan['blockers']}
            self.assertTrue({'WORKER_TERMINAL_MISSING', 'SOURCE_REPORT_MISSING', 'PROCESS_HEALTH_UNVERIFIED'} <= codes)
            (directory / 'worker-result.json').write_text('{}')
            (directory / 'annual-window-report.json').write_text('{}')
            plan = build_recovery_plan(root)
            self.assertFalse(plan['execution_authorized'])
            self.assertIn('COORDINATOR_APPLY_NOT_IMPLEMENTED', {entry['code'] for entry in plan['blockers']})
            self.assertFalse(plan['batches'][0]['settlement_authorized'])

    def test_changing_snapshot_during_inspection_cannot_generate_plan(self):
        with patch('app.data.recovery.inspect_recovery', side_effect=[{'version': 1}, {'version': 2}]):
            with self.assertRaises(ValueError):
                build_recovery_plan(Path('.'))

    def test_missing_or_corrupt_manifest_is_a_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertIn('MANIFEST_MISSING_OR_INVALID', {entry['code'] for entry in build_recovery_plan(root)['blockers']})
            (root / 'first-group-training-esri-v1/annual-window-report.json').write_text('{bad')
            plan = build_recovery_plan(root)
            self.assertTrue(plan['snapshot']['manifest']['invalid_json'])
            self.assertFalse(plan['execution_authorized'])

    def test_artifact_symlink_cannot_read_outside_data_root(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            directory, _ = self.prepare(root)
            external = Path(outside) / 'external.json'
            external.write_text('{"private":"outside"}')
            link = directory / 'worker-result.json'
            try:
                link.symlink_to(external)
            except OSError:
                self.skipTest('이 환경에서 symlink 생성 권한 없음')
            with self.assertRaises(ValueError):
                build_recovery_plan(root)

    def test_unc_batch_key_is_rejected_before_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, ledger = self.prepare(root)
            value = json.loads(ledger.read_text())
            value['batches']['\\\\not-a-real-host\\share'] = value['batches'].pop('batch-1')
            ledger.write_text(json.dumps(value))
            original = Path.resolve
            calls = []
            def resolve(path, *args, **kwargs):
                calls.append(str(path))
                return original(path, *args, **kwargs)
            with patch.object(Path, 'resolve', resolve), self.assertRaises(ValueError):
                build_recovery_plan(root)
            self.assertFalse(any('not-a-real-host' in value for value in calls))

    def test_redirected_artifact_is_rejected_before_reading_target(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            directory, _ = self.prepare(root)
            source = directory / 'worker-result.json'
            target = Path(outside) / 'private.json'
            original = Path.resolve
            def resolve(path, *args, **kwargs):
                return target if path == source else original(path, *args, **kwargs)
            with patch.object(Path, 'resolve', resolve), self.assertRaises(ValueError):
                build_recovery_plan(root)

    def test_cli_reuses_identical_plan_and_writes_stale_validation_only_to_evidence(self):
        script_path = Path(__file__).resolve().parents[1] / 'scripts/plan_collection_recovery.py'
        spec = importlib.util.spec_from_file_location('recovery_plan_cli_test', script_path)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            root = workspace / 'data'
            directory, _ = self.prepare(root)
            with patch.object(script, 'ROOT', workspace):
                outputs = []
                for _ in range(2):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        self.assertEqual(script.main(['--data-root', str(root)]), 0)
                    outputs.append(json.loads(stream.getvalue()))
                self.assertEqual(outputs[0]['plan_id'], outputs[1]['plan_id'])
                self.assertTrue(outputs[0]['created'])
                self.assertFalse(outputs[1]['created'])
                with self.assertRaises(ValueError):
                    script.write_new_evidence(root / 'forbidden.json', {})
                (directory / 'window-state.json').write_text('{"http_body_bytes":99}')
                before = {str(path): path.read_bytes() for path in root.rglob('*') if path.is_file()}
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(script.main(['--data-root', str(root), '--validate', outputs[0]['evidence']]), 2)
                self.assertEqual(before, {str(path): path.read_bytes() for path in root.rglob('*') if path.is_file()})
