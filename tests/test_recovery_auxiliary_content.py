"""Synthetic available auxiliary references and incomplete legacy coverage contracts."""
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
from backend.app.data import recovery_auxiliary_content as module

ROOT = Path(__file__).resolve().parents[1]


class AuxiliaryContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.manifest = self.output / 'annual-window-report.json'
        self.source_quality = self.output / 'source-quality.tif'
        self.boundary = self.output / 'boundary.geojson'
        self.source_quality.write_bytes(b'SOURCE-Q')
        self.boundary.write_bytes(b'{}')
        self.rows = []
        for index in ('A', 'B'):
            label, quality = self.output / f'label-{index}.tif', self.output / f'quality-{index}.tif'
            label.write_bytes(('LABEL-' + index).encode())
            quality.write_bytes(b'MASK')
            self.rows.append({'label_path': str(label), 'quality_mask_path': str(quality),
                'patch_sha256': {'label': self.sha(label), 'quality': self.sha(quality)},
                'source_window': {'quality_mask_path': str(self.source_quality), 'quality_mask_sha256': self.sha(self.source_quality), 'boundary_path': str(self.boundary), 'boundary_sha256': self.sha(self.boundary)}})
        self.save()

    def tearDown(self): self.temp.cleanup()
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self, raw=None):
        self.manifest.write_text(json.dumps({'scenes': self.rows}) if raw is None else raw, encoding='utf-8')
        self.pin = self.sha(self.manifest)
    def inspect(self, **kwargs): return module.inspect_recovery_auxiliary_content(self.root, self.pin, **kwargs)

    def test_complete_auxiliary_bytes_roles_hash_once_and_originals_preserved(self):
        before = {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        real = module._stream_sha
        with patch.object(module, '_stream_sha', wraps=real) as streamed:
            result = self.inspect()
            self.assertEqual(streamed.call_count, 6)
        self.assertEqual(result['planned_unique_file_count'], 6)
        self.assertEqual(result['actual_local_bytes_read'], 32)
        self.assertEqual(result['content_validation'], 'RECORDED_SHA_MATCH')
        self.assertEqual(result['coverage_status'], 'COMPLETE_REFERENCES')
        self.assertEqual(result['role_coverage']['source_quality']['unique_planned_files'], 1)
        self.assertEqual(len(result['same_digest_different_path_groups']), 1)
        self.assertEqual(result['status'], 'BLOCKED')
        for key in ['pixel_decoder_used', 'label_semantics_validated', 'quality_suitability_validated', 'boundary_authorization_verified', 'geometric_independence_checked', 'ready_for_training', 'training_executed', 'scientific_accuracy_validated', 'settlement_authorized', 'execution_authorized', 'automatic_resume_allowed']:
            self.assertIs(result[key], False)
        self.assertEqual(result['exactly_once_applied'], 'UNKNOWN')
        self.assertEqual(before, {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_legacy_absent_pairs_remain_unknown_without_blocking_recorded_refs(self):
        legacy = copy.deepcopy(self.rows[0]); legacy['source_window'] = {}
        self.rows.append(legacy); self.save()
        result = self.inspect()
        self.assertEqual(result['content_validation'], 'RECORDED_AVAILABLE_SHA_MATCH_PARTIAL')
        self.assertEqual(result['coverage_status'], 'INCOMPLETE_REFERENCES')
        self.assertEqual(result['actual_local_bytes_read'], 32)
        self.assertEqual({item['role'] for item in result['unknown_references']}, {'source_quality', 'boundary'})
        self.assertEqual(result['role_coverage']['boundary']['unknown_reference_rows'], 1)
        self.assertEqual(result['issues'], [])

    def test_no_recorded_references_is_not_reported_as_hash_match(self):
        self.rows = [{}]; self.save()
        result = self.inspect()
        self.assertEqual(result['content_validation'], 'NO_RECORDED_REFERENCES')
        self.assertEqual(result['actual_local_bytes_read'], 0)
        self.assertEqual(len(result['unknown_references']), 4)

    def test_partial_pairs_are_rejected_before_any_stream_without_fallback(self):
        for role, field in [('source', 'quality_mask_sha256'), ('source', 'boundary_path'), ('patch', 'label')]:
            original = copy.deepcopy(self.rows)
            if role == 'source': self.rows[1]['source_window'].pop(field)
            else: self.rows[1]['patch_sha256'].pop(field)
            self.save()
            with patch.object(module, '_stream_sha') as streamed:
                result = self.inspect()
                self.assertEqual(result['content_validation'], 'NOT_STARTED_PLAN_REJECTED')
                self.assertIn('PARTIAL_REFERENCE', {x['code'] for x in result['issues']})
                streamed.assert_not_called()
            self.rows = original

    def test_explicit_null_boolean_empty_uppercase_and_invalid_containers_rejected_pre_hash(self):
        variants = [lambda: self.rows[1]['source_window'].update(quality_mask_path=None, quality_mask_sha256=None),
                    lambda: self.rows[1]['patch_sha256'].__setitem__('label', False),
                    lambda: self.rows[1]['patch_sha256'].__setitem__('quality', ''),
                    lambda: self.rows[1]['source_window'].__setitem__('boundary_sha256', 'A' * 64),
                    lambda: self.rows[1].__setitem__('source_window', True),
                    lambda: self.rows[1].__setitem__('patch_sha256', None)]
        original = copy.deepcopy(self.rows)
        for mutate in variants:
            self.rows = copy.deepcopy(original); mutate(); self.save()
            with patch.object(module, '_stream_sha') as streamed:
                result = self.inspect()
                self.assertEqual(result['coverage_status'], 'PLAN_INVALID')
                streamed.assert_not_called()

    def test_conflicting_canonical_expected_digest_rejects_all_streams(self):
        self.rows[1]['source_window']['boundary_sha256'] = '0' * 64
        self.save()
        with patch.object(module, '_stream_sha') as streamed:
            result = self.inspect()
            self.assertIn('EXPECTED_SHA_CANONICAL_PATH_CONFLICT', {x['code'] for x in result['issues']})
            streamed.assert_not_called()

    def test_same_path_multi_role_same_sha_reuses_hash(self):
        for row in self.rows:
            row['source_window']['boundary_path'] = str(self.source_quality)
            row['source_window']['boundary_sha256'] = self.sha(self.source_quality)
        self.save()
        result = self.inspect()
        self.assertEqual(result['planned_unique_file_count'], 5)
        self.assertEqual(next(f for f in result['files'] if f['path'] == str(self.source_quality))['roles'], ['boundary', 'source_quality'])

    def test_missing_file_is_explicit_issue_not_unknown_legacy_coverage(self):
        self.boundary.unlink()
        with patch.object(module, '_stream_sha') as streamed:
            result = self.inspect()
            self.assertEqual(result['content_validation'], 'NOT_STARTED_PLAN_REJECTED')
            self.assertEqual(result['unknown_references'], [])
            self.assertIn('FILE_MISSING', {x['code'] for x in result['issues']})
            streamed.assert_not_called()

    def test_exact_budget_low_budget_and_type_limits(self):
        self.assertEqual(self.inspect(max_local_bytes=32)['actual_local_bytes_read'], 32)
        for value in [31, 0, -1, True, 32.0, module.MAX_AUXILIARY_BYTES + 1]:
            with patch.object(module, '_stream_sha') as streamed:
                with self.assertRaises(ValueError): self.inspect(max_local_bytes=value)
                streamed.assert_not_called()

    def test_known_content_mismatch_keeps_partial_coverage_distinction(self):
        self.rows[0]['patch_sha256']['label'] = '0' * 64
        self.rows[1]['source_window'] = {}; self.save()
        result = self.inspect()
        self.assertEqual(result['coverage_status'], 'INCOMPLETE_REFERENCES')
        self.assertEqual(result['content_validation'], 'ISSUES_FOUND')
        self.assertIn('CONTENT_SHA_MISMATCH', {x['code'] for x in result['issues']})
        self.assertEqual(result['actual_local_bytes_read'], 32)

    def test_pin_strict_json_and_remote_escape_nonfile_fail_before_stream(self):
        for pin in [None, True, 'A' * 64, '0' * 64]:
            with self.assertRaises(ValueError): module.inspect_recovery_auxiliary_content(self.root, pin)
        for raw in ['{"scenes":[],"scenes":[]}', '{"scenes":NaN}', '{"x":1e999}', '{"scenes":[]}']:
            self.save(raw)
            with self.assertRaises(ValueError): self.inspect()
        for path in ['https://invalid.example/label', '//server/share/label', str(self.workspace / 'outside'), str(self.output)]:
            self.rows[0]['label_path'] = path; self.save()
            with patch.object(module, '_stream_sha') as streamed:
                with self.assertRaises(ValueError): self.inspect()
                streamed.assert_not_called()

    def test_mutation_after_shared_stream_and_manifest_change_fail_closed(self):
        real = module._stream_sha
        def mutate(path, stamp, budget):
            result = real(path, stamp, budget)
            if path == self.boundary: self.source_quality.write_bytes(b'changed')
            return result
        with patch.object(module, '_stream_sha', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.source_quality.write_bytes(b'SOURCE-Q'); self.save()
        def change_manifest(path, stamp, budget):
            result = real(path, stamp, budget); self.manifest.write_text('{}', encoding='utf-8'); return result
        with patch.object(module, '_stream_sha', side_effect=change_manifest):
            with self.assertRaisesRegex(ValueError, 'manifest changed'): self.inspect()

    def test_logical_retarget_and_missing_file_appearing_rejected(self):
        real = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.boundary:
                calls += 1
                if calls >= 3: return self.output / 'other'
            return real(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.boundary.unlink()
        real_stamp = module._file_stamp
        calls = 0
        def appears(path):
            nonlocal calls
            if path == self.boundary:
                calls += 1
                if calls == 2: self.boundary.write_bytes(b'{}')
            return real_stamp(path)
        with patch.object(module, '_file_stamp', side_effect=appears):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_cli_cp949_utf8_existing_input_and_external_output_protection(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_auxiliary_content.py'), '--data-root', str(self.root), '--expected-manifest-sha256', self.pin, '--max-local-bytes', '32', *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'auxiliary.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['actual_local_bytes_read'], 32)
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(cli('--output', self.boundary).returncode, 1)
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / 'no.json'
            self.assertEqual(cli('--output', path).returncode, 1)
            self.assertFalse(path.exists())
        self.manifest.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
