"""Synthetic read-only terminal evidence classification and accounting boundaries."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.data import recovery_terminal as module

ROOT = Path(__file__).resolve().parents[1]


def digest(doc):
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()


class RecoveryTerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.key = 'batch-a'
        self.directory = self.root / 'first-group-training-esri-v1/sources' / self.key
        self.directory.mkdir(parents=True)
        self.ledger_path = self.root / 'first-group-training-budget/global-ledger.json'
        self.ledger_path.parent.mkdir()
        self.config = {'years': [2023], 'bands': ['blue', 'red'], 'max_total_bytes': 100, 'prior_download_budget_bytes': 0}
        normalized = copy.deepcopy(self.config)
        normalized['periods'] = {'2023': {'start_date': '2023-06-01', 'end_date': '2023-09-30'}}
        self.state = {'config_sha256': digest(normalized), 'http_body_bytes': 60, 'http_body_bytes_measured': 50, 'legacy_charged_bytes_preserved': 0}
        self.worker = {'key': self.key, 'cog_charged_bytes': 60, 'metadata_budget': {'charged_bytes': 8, 'read_body_bytes': 6, 'maximum_bytes': 10}, 'charged_bytes': 68, 'report_path': str(self.directory / 'annual-window-report.json')}
        self.report = {'executed': True, 'status': 'executed_windows_readiness_unverified', 'years': ['2023'], 'common_bands': ['blue', 'red'], 'http_body_bytes_upper_bound': 60, 'http_body_bytes_measured': 50, 'legacy_charged_bytes_preserved': 0, 'prior_download_budget_bytes': 0, 'combined_budget_charged_bytes': 60, 'http_body_bytes': None}
        self.ledger = {'new_charged_bytes': 110, 'additional_maximum_bytes': 1000, 'external_research_metadata_body_bytes': 0, 'batches': {self.key: {'status': 'pending', 'reserved_bytes': 110, 'charged_bytes': 110, 'config_sha256': digest(self.config)}}}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        for name, doc in [('config.json', self.config), ('window-state.json', self.state), ('worker-result.json', self.worker), ('annual-window-report.json', self.report)]:
            (self.directory / name).write_text(json.dumps(doc), encoding='utf-8')
        self.ledger_path.write_text(json.dumps(self.ledger), encoding='utf-8')

    def inspect(self):
        return module.inspect_recovery_terminal(self.root)

    def batch(self):
        return self.inspect()['pending_batches'][0]

    def codes(self):
        return {issue['code'] for issue in self.batch()['issues']}

    def test_consistent_metadata_keeps_full_reservation_and_all_authorizations_false(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = self.inspect()
        batch = report['pending_batches'][0]
        self.assertEqual(batch['classification'], 'CONSISTENT_METADATA')
        self.assertTrue(batch['raw_config_matches_ledger'])
        self.assertTrue(batch['normalized_config_matches_window_state'])
        self.assertEqual(batch['cog_unmeasured_or_reserved_bytes'], 10)
        self.assertEqual(batch['metadata_unmeasured_or_reserved_bytes'], 2)
        self.assertEqual(report['pending_reserved_bytes_preserved'], 110)
        for obj in [report, batch]:
            self.assertEqual(obj['status'], 'BLOCKED')
            for key in ['settlement_authorized', 'execution_authorized', 'automatic_resume_allowed']:
                self.assertIs(obj[key], False)
            self.assertEqual(obj['proposed_refund_bytes'], 0)
            self.assertEqual(obj['aggregate_applied_exactly_once'], 'UNKNOWN')
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_missing_terminal_files_are_missing_not_complete(self):
        (self.directory / 'worker-result.json').unlink()
        (self.directory / 'annual-window-report.json').unlink()
        self.assertEqual(self.batch()['classification'], 'MISSING')
        self.assertEqual(self.batch()['artifact_states']['worker-result.json'], 'MISSING')

    def test_empty_terminal_dict_does_not_prove_completion(self):
        self.worker = {}; self.report = {}; self.save()
        self.assertEqual(self.batch()['classification'], 'INVALID')
        self.assertIn('WORKER_CHARGED_BYTES_INVALID', self.codes())

    def test_invalid_json_duplicate_keys_and_nonfinite_artifacts_classified_invalid(self):
        for raw in ['{}x', '{"key":1,"key":2}', '{"x":NaN}', '{"x":1e999}', '[]']:
            (self.directory / 'worker-result.json').write_text(raw, encoding='utf-8')
            self.assertEqual(self.batch()['artifact_states']['worker-result.json'], 'INVALID')
            self.assertEqual(self.batch()['classification'], 'INVALID')

    def test_boolean_negative_and_float_accounting_values_rejected(self):
        for value in [True, -1, 68.0]:
            self.worker['charged_bytes'] = value; self.save()
            self.assertEqual(self.batch()['classification'], 'INVALID')
        self.worker['charged_bytes'] = 68
        self.state['http_body_bytes'] = False; self.save()
        self.assertEqual(self.batch()['classification'], 'INVALID')

    def test_worker_key_sums_reservation_and_metadata_ranges_checked(self):
        self.worker.update(key='other', charged_bytes=111)
        self.worker['metadata_budget']['read_body_bytes'] = 9
        self.save()
        self.assertTrue({'WORKER_KEY_MISMATCH', 'WORKER_CHARGE_SUM_MISMATCH', 'WORKER_CHARGE_EXCEEDS_RESERVATION', 'METADATA_COUNTER_RANGE_MISMATCH'} <= self.codes())

    def test_raw_and_normalized_config_hashes_are_separate(self):
        self.assertNotEqual(digest(self.config), self.state['config_sha256'])
        self.assertEqual(self.batch()['classification'], 'CONSISTENT_METADATA')
        self.state['config_sha256'] = digest(self.config); self.save()
        self.assertIn('NORMALIZED_CONFIG_STATE_MISMATCH', self.codes())
        self.config['season_start'] = '01-01'; self.save()
        self.assertIn('RAW_CONFIG_LEDGER_MISMATCH', self.codes())

    def test_report_state_counters_context_and_null_body_contract(self):
        self.report.update(http_body_bytes_upper_bound=61, http_body_bytes_measured=51, http_body_bytes=51, years=['2022'], common_bands=['nir'])
        self.save()
        self.assertTrue({'REPORT_STATE_UPPER_MISMATCH', 'REPORT_STATE_MEASURED_MISMATCH', 'REPORT_CONFIG_YEARS_MISMATCH', 'REPORT_CONFIG_BANDS_MISMATCH', 'REPORT_HTTP_BODY_MEASUREMENT_CONTRACT_MISMATCH'} <= self.codes())

    def test_fully_equal_measured_counters_still_do_not_authorize_settlement(self):
        self.state['http_body_bytes_measured'] = 60
        self.report.update(http_body_bytes_measured=60, http_body_bytes=60)
        self.worker['metadata_budget']['read_body_bytes'] = 8
        self.save()
        batch = self.batch()
        self.assertEqual(batch['classification'], 'CONSISTENT_METADATA')
        self.assertEqual(batch['complete_transfer_accounting'], 'UNKNOWN')
        self.assertEqual(batch['source_report_identity_binding'], 'UNKNOWN_NO_CONFIG_DIGEST_IN_REPORT')
        self.assertFalse(batch['settlement_authorized'])

    def test_report_path_wrong_local_and_root_escape_rejected(self):
        self.worker['report_path'] = str(self.directory / 'other.json'); self.save()
        self.assertIn('WORKER_REPORT_PATH_MISMATCH', self.codes())
        self.worker['report_path'] = str(self.workspace / 'outside.json'); self.save()
        with self.assertRaises(ValueError):
            self.inspect()
        self.worker['report_path'] = '//remote/share/report.json'; self.save()
        with self.assertRaises(ValueError):
            self.inspect()

    def test_unsafe_batch_key_and_global_ledger_inconsistency_rejected(self):
        self.ledger['batches']['../outside'] = self.ledger['batches'].pop(self.key); self.save()
        with self.assertRaises(ValueError):
            self.inspect()
        self.ledger['batches'][self.key] = self.ledger['batches'].pop('../outside')
        self.ledger['new_charged_bytes'] = 109; self.save()
        self.assertFalse(self.inspect()['ledger_internal_sum_matches'])
        self.assertEqual(self.batch()['classification'], 'MISMATCH')

    def test_window_upper_cannot_exceed_config_budget(self):
        self.state['http_body_bytes'] = 101; self.save()
        self.assertIn('STATE_CONFIG_BUDGET_EXCEEDED', self.codes())

    def test_evidence_changes_and_missing_file_appearing_during_inspection_rejected(self):
        real = module._fingerprint
        count = 0
        def changing(path):
            nonlocal count
            count += 1
            if count == 6:
                self.ledger_path.write_text('{}', encoding='utf-8')
            return real(path)
        with patch.object(module, '_fingerprint', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.inspect()

    def test_state_legacy_boolean_and_out_of_range_counts_rejected(self):
        self.state['legacy_charged_bytes_preserved'] = False
        self.save()
        self.assertIn('STATE_LEGACY_CHARGED_BYTES_PRESERVED_INVALID', self.codes())
        self.state['legacy_charged_bytes_preserved'] = 61
        self.report['legacy_charged_bytes_preserved'] = 61
        self.save()
        self.assertTrue({'STATE_LEGACY_EXCEEDS_UPPER', 'REPORT_LEGACY_EXCEEDS_UPPER'} <= self.codes())

    def test_legacy_plus_measured_cannot_exceed_upper(self):
        self.state['legacy_charged_bytes_preserved'] = 20
        self.report['legacy_charged_bytes_preserved'] = 20
        self.save()
        self.assertTrue({'STATE_LEGACY_PLUS_MEASURED_EXCEEDS_UPPER', 'REPORT_LEGACY_PLUS_MEASURED_EXCEEDS_UPPER'} <= self.codes())
        self.state['legacy_charged_bytes_preserved'] = 10
        self.report['legacy_charged_bytes_preserved'] = 10
        self.save()
        self.assertEqual(self.batch()['classification'], 'CONSISTENT_METADATA')

    def test_logical_path_retarget_is_rejected_without_symlink_privilege(self):
        real = module._confined
        target = self.directory / 'config.json'
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == target:
                calls += 1
                if calls >= 2:
                    return self.directory / 'other.json'
            return real(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'target changed'):
                self.inspect()

    def test_missing_terminal_appearing_during_inspection_is_rejected(self):
        target = self.directory / 'worker-result.json'
        target.unlink()
        real = module._fingerprint
        calls = 0
        def appears(path):
            nonlocal calls
            if path == target:
                calls += 1
                if calls == 2:
                    target.write_text('{}', encoding='utf-8')
            return real(path)
        with patch.object(module, '_fingerprint', side_effect=appears):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.inspect()

    def test_cli_cp949_stdout_new_evidence_existing_path_and_external_output(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_terminal.py'), '--data-root', str(self.root), *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        self.assertEqual(json.loads(result.stdout)['status'], 'BLOCKED')
        output = self.workspace / 'result.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'BLOCKED')
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(before, output.read_bytes())
        self.assertEqual(cli('--output', self.ledger_path).returncode, 1)
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'no.json'
            self.assertEqual(cli('--output', target).returncode, 1)
            self.assertFalse(target.exists())
        self.ledger_path.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__':
    unittest.main()
