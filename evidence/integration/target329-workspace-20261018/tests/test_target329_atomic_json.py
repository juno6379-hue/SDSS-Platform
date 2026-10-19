import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.data import targeted_atomic_json as writer
from backend.app.ml import manifest_resource_profile as profile


class AtomicJSONTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'state.json'
        self.old = b'{"old":1}'
        self.new = b'{"new":2}'
        self.path.write_bytes(self.old)
        self.pin = hashlib.sha256(self.old).hexdigest()

    def run_write(self, payload=None, **options):
        args = dict(role='config', expected_sha256=self.pin, manifest_profile=dict(profile.MARKER))
        args.update(options)
        return writer.replace_json(self.root, self.path, self.new if payload is None else payload, **args)

    def scratch(self):
        return self.path.with_name('.state.json.target329.tmp')

    def test_success_exact_actual_io_and_same_budget(self):
        with profile.scope(profile.NAME) as budget:
            profile.charge(7)
            result = self.run_write()
            self.assertEqual(budget.reads, 7 + 2*len(self.old) + 2*len(self.new))
            self.assertEqual(budget.writes, len(self.new))
            self.assertEqual(result.json_io_bytes, budget.bytes)
        self.assertEqual(self.path.read_bytes(), self.new)
        self.assertTrue(result.committed)
        self.assertFalse(result.coordinator_connected)
        self.assertFalse(self.scratch().exists())

    def test_roles(self):
        for role in ('config', 'ledger', 'source'):
            self.path.write_bytes(self.old)
            result = self.run_write(b'{"scenes":[],"historical_noneligible_patches":[]}', role=role)
            self.assertTrue(result.committed)

    def test_bad_contract_before_open(self):
        for options in ({'role':True}, {'role':'status_report'}, {'expected_sha256':None},
                        {'manifest_profile':True}, {'manifest_profile':dict(profile.MARKER, cap=1)}):
            with self.subTest(options=options), patch.object(Path, 'open', side_effect=AssertionError('open')):
                with self.assertRaises(writer.AtomicJSONWriteError):
                    self.run_write(**options)

    def test_oversize_before_open(self):
        with patch.object(Path, 'open', side_effect=AssertionError('open')):
            with self.assertRaisesRegex(ValueError, 'PAYLOAD_LIMIT'):
                self.run_write(b' ' * (2097152 + 1))

    def test_invalid_json_before_open(self):
        for payload in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[]', b'\xef\xbb\xbf{}', b'{"x":"\x00"}', b'\xff'):
            with self.subTest(payload=payload), patch.object(Path, 'open', side_effect=AssertionError('open')):
                with self.assertRaises(ValueError):
                    self.run_write(payload)

    def test_source_rows_includes_history(self):
        payload = json.dumps({'scenes':[{}]*2999, 'historical_noneligible_patches':[{},{}]}).encode()
        with self.assertRaisesRegex(profile.ProfileResourceError, 'ROW_LIMIT'):
            self.run_write(payload, role='source')
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_depth(self):
        with self.assertRaises(profile.ProfileResourceError):
            self.run_write(b'{"x":' * 33 + b'0' + b'}' * 33)

    def test_wrong_pin_old_unchanged(self):
        with self.assertRaisesRegex(ValueError, 'PIN_MISMATCH'):
            self.run_write(expected_sha256='0'*64)
        self.assertEqual(self.path.read_bytes(), self.old)
        self.assertFalse(self.scratch().exists())

    def test_ledger_old_cap_before_read_open(self):
        with self.path.open('wb') as stream: stream.truncate(8388609)
        with patch.object(Path, 'open', side_effect=AssertionError('open')):
            with self.assertRaisesRegex(profile.ProfileResourceError, 'FILE_LIMIT'):
                self.run_write(role='ledger')

    def test_source_exact_3000_rows(self):
        self.run_write(json.dumps({'scenes':[{}]*2999,
            'historical_noneligible_patches':[{}]}).encode(), role='source')
        self.assertEqual(len(json.loads(self.path.read_bytes())['scenes']), 2999)

    def test_wrong_return_count_is_unknown_conservative(self):
        def wrong(stream, block):
            stream.write(block)
            return True
        with profile.scope(profile.NAME) as budget, patch.object(writer, '_write_once', wrong):
            with self.assertRaisesRegex(ValueError, 'MEASUREMENT_UNKNOWN') as caught:
                self.run_write()
            self.assertEqual(budget.writes, len(self.new))
        self.assertFalse(caught.exception.atomic_json_measurement_known)
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_source_missing_scenes(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_INVALID'):
            self.run_write(b'{}', role='source')

    def test_absent_destination_not_created(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError): self.run_write()
        self.assertFalse(self.path.exists())
        self.assertFalse(self.scratch().exists())

    def test_parent_replacement_detected(self):
        folder = self.root / 'nested'; folder.mkdir()
        self.path = folder / 'state.json'; self.path.write_bytes(self.old)
        original = writer._check_parents
        count = [0]
        def swap(parents):
            count[0] += 1
            if count[0] == 1:
                folder.rename(self.root / 'previous')
                folder.mkdir(); self.path.write_bytes(b'{"foreign":1}')
            original(parents)
        with patch.object(writer, '_check_parents', swap):
            with self.assertRaisesRegex(ValueError, 'PARENT_CHANGED'): self.run_write()
        self.assertEqual(self.path.read_bytes(), b'{"foreign":1}')
        self.assertEqual((self.root/'previous'/'state.json').read_bytes(), self.old)

    def test_existing_temp_never_deleted(self):
        self.scratch().write_bytes(b'foreign')
        with self.assertRaises(FileExistsError):
            self.run_write()
        self.assertEqual(self.scratch().read_bytes(), b'foreign')
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_short_write_charged_and_cleaned(self):
        def partial(stream, block):
            return stream.write(block[:3])
        with profile.scope(profile.NAME) as budget, patch.object(writer, '_write_once', partial):
            with self.assertRaisesRegex(ValueError, 'INCOMPLETE_WRITE') as caught:
                self.run_write()
            self.assertEqual(budget.writes, 3)
            self.assertTrue(caught.exception.atomic_json_measurement_known)
        self.assertFalse(self.scratch().exists())
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_partial_then_exception_charged(self):
        def partial(stream, block):
            stream.write(block[:4])
            raise OSError('test')
        with profile.scope(profile.NAME) as budget, patch.object(writer, '_write_once', partial):
            with self.assertRaises(OSError): self.run_write()
            self.assertEqual(budget.writes, 4)
        self.assertFalse(self.scratch().exists())

    def test_unknown_conservative_charge_preserve(self):
        with profile.scope(profile.NAME) as budget, patch.object(writer, '_measure', side_effect=OSError()):
            with self.assertRaisesRegex(ValueError, 'MEASUREMENT_UNKNOWN') as caught:
                self.run_write()
            self.assertEqual(budget.writes, len(self.new))
            self.assertFalse(caught.exception.atomic_json_measurement_known)
            self.assertTrue(caught.exception.atomic_json_temporary_preserved)
        self.assertTrue(self.scratch().exists())
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_cancel_preserved_and_cleanup(self):
        def cancel(stream, block):
            stream.write(block[:2])
            raise KeyboardInterrupt()
        with patch.object(writer, '_write_once', cancel):
            with self.assertRaises(KeyboardInterrupt) as caught: self.run_write()
        self.assertEqual(caught.exception.atomic_json_commit_outcome, 'NOT_ATTEMPTED')
        self.assertFalse(self.scratch().exists())

    def test_fsync_failure_old_unchanged(self):
        with patch.object(writer, '_sync', side_effect=OSError()):
            with self.assertRaises(OSError): self.run_write()
        self.assertEqual(self.path.read_bytes(), self.old)
        self.assertFalse(self.scratch().exists())

    def test_external_destination_change_never_overwritten(self):
        sync = writer._sync
        def changed(stream):
            sync(stream)
            self.path.write_bytes(b'{"external":3}')
        with patch.object(writer, '_sync', changed):
            with self.assertRaisesRegex(ValueError, 'INPUT_CHANGED'): self.run_write()
        self.assertEqual(self.path.read_bytes(), b'{"external":3}')

    def test_foreign_temp_after_close_preserved(self):
        original = writer._check_parents
        count = [0]
        def swapped(parents):
            original(parents)
            count[0] += 1
            if count[0] == 1:
                alternate = self.root / 'alternate'
                alternate.write_bytes(self.new)
                os.replace(alternate, self.scratch())
        with patch.object(writer, '_check_parents', swapped):
            with self.assertRaisesRegex(ValueError, 'TEMP_CHANGED'): self.run_write()
        self.assertEqual(self.scratch().read_bytes(), self.new)
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_budget_exhaustion_before_temp_open(self):
        with profile.scope(profile.NAME) as budget:
            budget._maximum = len(self.old)-1
            with self.assertRaises(profile.ProfileResourceError): self.run_write()
        self.assertEqual(self.path.read_bytes(), self.old)
        self.assertFalse(self.scratch().exists())

    def test_budget_postread_room_before_replace(self):
        with profile.scope(profile.NAME) as budget:
            budget._maximum = 2*len(self.old) + 2*len(self.new)-1
            with self.assertRaises(profile.ProfileResourceError) as caught: self.run_write()
        self.assertEqual(caught.exception.atomic_json_commit_outcome, 'NOT_ATTEMPTED')
        self.assertEqual(self.path.read_bytes(), self.old)

    def test_postcommit_failure_reports_applied(self):
        digest = profile.bounded_json_digest
        count = [0]
        def fail_final(*args, **kwargs):
            count[0] += 1
            if count[0] == 4: raise OSError('post-read')
            return digest(*args, **kwargs)
        with patch.object(profile, 'bounded_json_digest', fail_final):
            with self.assertRaises(OSError) as caught: self.run_write()
        self.assertTrue(caught.exception.atomic_json_committed)
        self.assertEqual(caught.exception.atomic_json_commit_outcome, 'APPLIED')
        self.assertEqual(self.path.read_bytes(), self.new)

    def test_replace_exception_outcome_unknown(self):
        replace = os.replace
        def replace_then_raise(*args):
            replace(*args)
            raise OSError('after-commit')
        with patch.object(writer.os, 'replace', replace_then_raise):
            with self.assertRaises(OSError) as caught: self.run_write()
        self.assertEqual(caught.exception.atomic_json_commit_outcome, 'UNKNOWN')
        self.assertEqual(self.path.read_bytes(), self.new)

    def test_cooperative_competition_one_winner(self):
        def attempt(_):
            try: return self.run_write().committed
            except (ValueError, OSError): return False
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            results = list(executor.map(attempt, range(2)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.path.read_bytes(), self.new)

    def test_hardlink_rejected(self):
        os.link(self.path, self.root/'link')
        with self.assertRaisesRegex(ValueError, 'PATH_INVALID'): self.run_write()

    def test_value_detached_canonical(self):
        result = writer.replace_json_value(self.root, self.path, {'b':[2], 'a':'가'},
            role='config', expected_sha256=self.pin, manifest_profile=dict(profile.MARKER))
        self.assertEqual(self.path.read_bytes(), '{"a":"가","b":[2]}'.encode())
        self.assertTrue(result.committed)

    def test_value_reject_custom_cycle_nonfinite_surrogate(self):
        cycle = {}; cycle['self'] = cycle
        class Fake(dict): pass
        for value in (Fake(), cycle, {'a':float('nan')}, {'a':'\ud800'}, {True:1}):
            with self.subTest(value=type(value)), patch.object(Path, 'open', side_effect=AssertionError('open')):
                with self.assertRaises(ValueError):
                    writer.replace_json_value(self.root, self.path, value, role='config',
                        expected_sha256=self.pin, manifest_profile=dict(profile.MARKER))


if __name__ == '__main__': unittest.main()
