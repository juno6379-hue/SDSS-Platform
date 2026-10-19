"""281 isolated local files only. Synthetic STAC; no operational refs opened."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import bare_survey_stac_file as subject
import test_bare_survey_stac_binding as fixture_module


class SurveyStacFileTests(unittest.TestCase):
    def setUp(self):
        fixture = fixture_module.SurveyStacBindingTests(); fixture.setUp()
        self.request = copy.deepcopy(fixture.request)
        self.selected = copy.deepcopy(fixture.selected)
        self.document = copy.deepcopy(fixture.document)
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / self.request['selected_scene']['stac_ref']['path']
        self.path.parent.mkdir(parents=True)
        self.save()

    def save(self):
        self.raw = json.dumps(self.document).encode('utf-8')
        self.path.write_bytes(self.raw)
        self.request['selected_scene']['stac_ref']['sha256'] = hashlib.sha256(self.raw).hexdigest()

    def call(self, **kwargs):
        return subject.read_pinned_survey_stac(self.root, self.request, self.selected, **kwargs)

    def error(self, callback, code=None, observed=None):
        with self.assertRaises(subject.SurveyStacFileError) as caught:
            callback()
        self.assertRegex(str(caught.exception), r'^SURVEY_FILE_[A-Z0-9_]+$')
        if code: self.assertEqual(str(caught.exception), code)
        if observed is not None: self.assertEqual(caught.exception.actual_read_bytes, observed)
        return caught.exception

    def test_single_descriptor_exact_actual_bytes_immutable_and_no_other_input_reads(self):
        original = os.open
        with patch.object(subject.os, 'open', wraps=original) as opened, \
             patch('socket.socket', side_effect=AssertionError('network prohibited')):
            result = self.call(maximum_read_bytes=len(self.raw))
        self.assertEqual(opened.call_count, 1)
        self.assertEqual(Path(opened.call_args.args[0]), self.path)
        self.assertEqual(result.actual_read_bytes, len(self.raw))
        self.assertTrue(result.to_dict()['local_file_pin_and_identity_verified'])
        for key in ('ledger_verified', 'execution_supported', 'quality_eligible', 'training_ready',
                    'source_authenticity_verified', 'remote_asset_verified', 'registry_connected'):
            self.assertIs(result.to_dict()[key], False)
        self.assertFalse((self.root / 'data/source.json').exists())
        before = result.to_dict()
        self.request['seed']['year'] = 2023
        result.to_dict()['stac_ref']['path'] = 'changed'
        self.assertEqual(result.to_dict(), before)
        with self.assertRaises(FrozenInstanceError): result.status = 'approved'

    def test_per_call_budget_shortfall_and_invalid_values_prevent_open(self):
        for value in (0, len(self.raw)-1):
            with patch.object(subject.os, 'open', side_effect=AssertionError('no open')):
                self.error(lambda: self.call(maximum_read_bytes=value), 'SURVEY_FILE_BUDGET_EXCEEDED', 0)
        for value in (True, 1.0, -1, subject.MAX_BYTES+1, None):
            with patch.object(subject.os, 'open', side_effect=AssertionError('no open')):
                self.error(lambda: self.call(maximum_read_bytes=value), 'SURVEY_FILE_BUDGET_INVALID', 0)

    def test_oversized_and_empty_file_prevent_open(self):
        for payload in (b'', b'x'*(subject.MAX_BYTES+1)):
            self.path.write_bytes(payload)
            with patch.object(subject.os, 'open', side_effect=AssertionError('no open')):
                self.error(self.call, 'SURVEY_FILE_BYTE_LIMIT', 0)

    def test_exact_one_mib_file_is_allowed_without_raising_existing_parser_caps(self):
        # Whitespace pads bytes without increasing the existing node/string scope.
        raw = self.raw + b' '*(subject.MAX_BYTES-len(self.raw))
        self.path.write_bytes(raw)
        self.request['selected_scene']['stac_ref']['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.call().actual_read_bytes, subject.MAX_BYTES)

    def test_pin_mismatch_never_calls_binding(self):
        self.request['selected_scene']['stac_ref']['sha256'] = 'f'*64
        with patch.object(subject, 'validate_survey_stac_binding', side_effect=AssertionError('binding forbidden')):
            self.error(self.call, 'SURVEY_FILE_PIN_MISMATCH', len(self.raw))

    def test_request_and_lexical_reference_alias_prevent_open(self):
        for mutation in ('execute', 'alias', 'outside'):
            original = copy.deepcopy(self.request)
            if mutation == 'execute': self.request['execution_supported'] = True
            elif mutation == 'alias': self.request['selected_scene']['stac_ref']['path'] = 'data/SOURCE.JSON'
            else: self.request['selected_scene']['stac_ref']['path'] = 'evidence/integration/stac.json'
            with patch.object(subject.os, 'open', side_effect=AssertionError('no open')):
                self.error(self.call, observed=0)
            self.request = original

    def test_hardlink_real_file_rejected_before_open(self):
        other = self.path.parent / 'other.json'
        os.link(self.path, other)
        with patch.object(subject.os, 'open', side_effect=AssertionError('no open')):
            self.error(self.call, 'SURVEY_FILE_NOT_SINGLE_REGULAR', 0)

    def test_reparse_flag_is_rejected_without_open(self):
        original = Path.lstat
        class Reparse:
            def __init__(self, value): self.value = value; self.st_file_attributes = 0x400
            def __getattr__(self, key): return getattr(self.value, key)
        def changed(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            return Reparse(value) if path == self.path.parent else value
        with patch.object(Path, 'lstat', changed), \
             patch.object(subject.os, 'open', side_effect=AssertionError('no open')):
            self.error(self.call, 'SURVEY_FILE_PARENT_UNSAFE', 0)

    def test_growth_detected_without_reading_appended_bytes(self):
        original = os.read
        def growing(fd, size):
            raw = original(fd, size)
            with self.path.open('ab') as stream: stream.write(b' ')
            return raw
        with patch.object(subject.os, 'read', growing):
            self.error(self.call, 'SURVEY_FILE_CHANGED_DURING_READ', len(self.raw))

    def test_replaced_logical_path_detected_even_when_bytes_match(self):
        replacement = self.path.parent / 'replacement.json'; replacement.write_bytes(self.raw)
        # Windows forbids replacing our open descriptor. Replace immediately
        # after close so the logical-path postcheck is exercised on every OS.
        original = os.close
        def replaced(fd):
            original(fd); os.replace(replacement, self.path)
        with patch.object(subject.os, 'close', replaced):
            self.error(self.call, 'SURVEY_FILE_REPLACED', len(self.raw))

    def test_parent_identity_change_fails_closed(self):
        original = subject._parents; calls = 0
        def changed(path):
            nonlocal calls
            calls += 1
            result = original(path)
            if calls > 1: result[-1] = (result[-1][0], ('simulated-parent-replacement',))
            return result
        with patch.object(subject, '_parents', changed):
            self.error(self.call, 'SURVEY_FILE_PARENT_CHANGED', len(self.raw))

    def test_partial_oserror_observation_and_short_read_are_not_zero_or_refunded(self):
        self.document['padding'] = 'x'*70000; self.save()
        original = os.read
        for mode in ('oserror', 'short'):
            calls = 0
            def interrupted(fd, size):
                nonlocal calls
                calls += 1
                if calls == 1: return original(fd, size)
                if mode == 'oserror': raise OSError('secret-url-or-path-not-exposed')
                return b''
            with patch.object(subject.os, 'read', interrupted):
                error = self.error(self.call, observed=subject.CHUNK_BYTES)
            self.assertNotIn('secret', str(error))

    def test_pure_binding_time_and_unknown_provider_policy_remain_strict(self):
        for key, value in [('datetime', '2024-06-19T02:13:51.024Z'), ('s2:product_uri', 'invented.SAFE')]:
            original = copy.deepcopy(self.document)
            self.document['properties'][key] = value; self.save()
            self.error(self.call, 'SURVEY_FILE_METADATA_BINDING_INVALID', len(self.raw))
            self.document = original

    def test_change_during_pure_binding_is_not_returned_as_verified(self):
        original = subject.validate_survey_stac_binding
        def changed(*args):
            result = original(*args)
            with self.path.open('ab') as stream: stream.write(b' ')
            return result
        with patch.object(subject, 'validate_survey_stac_binding', changed):
            self.error(self.call, 'SURVEY_FILE_CHANGED_AFTER_BINDING', len(self.raw))

    def test_both_import_scopes_return_same_canonical_result(self):
        other = importlib.import_module('backend.app.data.bare_survey_stac_file')
        self.assertEqual(self.call().to_dict(), other.read_pinned_survey_stac(self.root, self.request, self.selected).to_dict())

    def test_independent_parallel_calls_have_no_shared_mutable_budget(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(lambda _: self.call(maximum_read_bytes=len(self.raw)).actual_read_bytes, range(2)))
        self.assertEqual(values, [len(self.raw), len(self.raw)])
        # The API deliberately does not claim these two allowances are one scope.


if __name__ == '__main__': unittest.main()
