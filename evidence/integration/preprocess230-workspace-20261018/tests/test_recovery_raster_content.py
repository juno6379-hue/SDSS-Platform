"""Tiny local byte fixtures for pinned streaming SHA, budgets and mutation guards."""
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
from backend.app.data import recovery_raster_content as module

ROOT = Path(__file__).resolve().parents[1]


class RasterContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.source = self.output / 'source.bin'
        self.patch_a = self.output / 'patch-a.bin'
        self.patch_b = self.output / 'patch-b.bin'
        self.source.write_bytes(b'source-image')
        self.patch_a.write_bytes(b'same-patch')
        self.patch_b.write_bytes(b'same-patch')
        self.manifest = self.output / 'annual-window-report.json'
        self.rows = [self.row(self.patch_a), self.row(self.patch_b)]
        self.save()

    def tearDown(self): self.temp.cleanup()

    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()

    def row(self, patch):
        return {'source_window': {'path': str(self.source), 'sha256': self.sha(self.source)}, 'image_path': str(patch), 'patch_sha256': {'image': self.sha(patch)}}

    def save(self, raw=None):
        self.manifest.write_text(json.dumps({'scenes': self.rows}) if raw is None else raw, encoding='utf-8')
        self.pin = self.sha(self.manifest)

    def inspect(self, **kwargs): return module.inspect_recovery_raster_content(self.root, self.pin, **kwargs)

    def test_stream_hash_match_unique_path_cache_roles_and_same_digest_groups(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        real = module._stream_sha
        with patch.object(module, '_stream_sha', wraps=real) as streamed:
            result = self.inspect()
            self.assertEqual(streamed.call_count, 3)
        self.assertEqual(result['content_validation'], 'RECORDED_SHA_MATCH')
        self.assertEqual(result['planned_unique_file_count'], 3)
        self.assertEqual(result['actual_local_bytes_read'], 32)
        self.assertEqual(len(result['same_digest_different_path_groups']), 1)
        self.assertEqual(len(result['same_digest_different_path_groups'][0]['files']), 2)
        self.assertEqual(result['same_digest_different_path_groups'][0]['files'][0]['roles'], ['patch'])
        self.assertEqual(result['status'], 'BLOCKED')
        for key in ['pixel_decoder_used', 'label_quality_checked', 'geometric_independence_checked', 'ready_for_training', 'training_executed', 'scientific_accuracy_validated', 'settlement_authorized', 'execution_authorized', 'automatic_resume_allowed']:
            self.assertIs(result[key], False)
        self.assertEqual(result['exactly_once_applied'], 'UNKNOWN')
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_same_path_source_patch_roles_merge_but_identical_cross_role_files_are_distinct(self):
        self.rows = [self.row(self.source)]
        self.save()
        result = self.inspect()
        self.assertEqual(result['planned_unique_file_count'], 1)
        self.assertEqual(result['files'][0]['roles'], ['patch', 'source'])
        self.patch_a.write_bytes(self.source.read_bytes())
        self.rows = [self.row(self.patch_a)]
        self.save()
        result = self.inspect()
        self.assertEqual(len(result['same_digest_different_path_groups']), 1)
        roles = [entry['roles'] for entry in result['same_digest_different_path_groups'][0]['files']]
        self.assertIn(['source'], roles)
        self.assertIn(['patch'], roles)

    def test_expected_manifest_pin_required_and_stale_pin_never_streams(self):
        for value in [None, True, 'A' * 64, 'bad', '0' * 64]:
            with patch.object(module, '_stream_sha') as streamed:
                with self.assertRaises(ValueError): module.inspect_recovery_raster_content(self.root, value)
                streamed.assert_not_called()

    def test_all_reference_sha_validation_and_conflicts_precede_any_hash(self):
        variants = [lambda: self.rows[1]['patch_sha256'].__setitem__('image', True),
                    lambda: self.rows[1]['source_window'].__setitem__('sha256', '0' * 64),
                    lambda: self.rows[1].pop('patch_sha256'),
                    lambda: self.rows[1].__setitem__('image_path', False)]
        original = copy.deepcopy(self.rows)
        for mutate in variants:
            self.rows = copy.deepcopy(original); mutate(); self.save()
            with patch.object(module, '_stream_sha') as streamed:
                result = self.inspect()
                self.assertEqual(result['content_validation'], 'NOT_STARTED_PLAN_REJECTED')
                self.assertEqual(result['actual_local_bytes_read'], 0)
                streamed.assert_not_called()

    def test_missing_file_rejected_in_plan_before_other_content_reads(self):
        self.patch_b.unlink()
        with patch.object(module, '_stream_sha') as streamed:
            result = self.inspect()
            self.assertIn('FILE_MISSING', {x['code'] for x in result['issues']})
            streamed.assert_not_called()

    def test_budget_preflight_low_invalid_and_exact_boundary(self):
        for value in [0, -1, True, 32.0, module.MAX_LOCAL_BYTES + 1, 31]:
            with patch.object(module, '_stream_sha') as streamed:
                with self.assertRaises(ValueError): self.inspect(max_local_bytes=value)
                streamed.assert_not_called()
        result = self.inspect(max_local_bytes=32)
        self.assertEqual(result['actual_local_bytes_read'], 32)
        self.assertEqual(result['content_validation'], 'RECORDED_SHA_MATCH')

    def test_mismatch_does_not_join_verified_same_digest_group(self):
        self.rows[0]['patch_sha256']['image'] = '0' * 64; self.save()
        result = self.inspect()
        self.assertEqual(result['content_validation'], 'ISSUES_FOUND')
        self.assertEqual(result['files'][1]['status'], 'MISMATCH')
        self.assertEqual(result['same_digest_different_path_groups'], [])
        self.assertEqual(result['actual_local_bytes_read'], 32)

    def test_canonical_alias_is_hashed_once_and_distinct_hardlinks_remain_distinct_paths(self):
        self.rows[1]['image_path'] = str(self.output / '../first-group-training-esri-v1/patch-a.bin'); self.save()
        result = self.inspect()
        self.assertEqual(result['planned_unique_file_count'], 2)
        self.assertEqual(result['actual_local_bytes_read'], 22)
        link = self.output / 'hardlink.bin'
        try: os.link(self.patch_a, link)
        except OSError: return
        self.rows[1]['image_path'] = str(link); self.save()
        result = self.inspect()
        self.assertEqual(result['planned_unique_file_count'], 3)
        self.assertEqual(len(result['same_digest_different_path_groups']), 1)

    def test_fixed_chunks_are_bounded_unbuffered_no_unbounded_read(self):
        data = b'x' * (module.CHUNK_BYTES + 3)
        self.source.write_bytes(data)
        self.rows = [self.row(self.patch_a)]; self.save()
        real_open = Path.open
        requests = []
        class Guard:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                requests.append(size)
                if not 0 < size <= module.CHUNK_BYTES: raise AssertionError('Unbounded read')
                return self.stream.read(size)
        def opened(path, mode='r', *args, **kwargs):
            stream = real_open(path, mode, *args, **kwargs)
            if path == self.source and mode == 'rb' and kwargs.get('buffering') == 0: return Guard(stream)
            return stream
        with patch.object(Path, 'open', new=opened):
            result = self.inspect()
        self.assertEqual(result['content_validation'], 'RECORDED_SHA_MATCH')
        self.assertIn(module.CHUNK_BYTES, requests)
        self.assertIn(3, requests)
        self.assertIn(1, requests)

    def test_growth_probe_and_exact_budget_growth_never_exceed_budget(self):
        for extra_allowance in [0, 1]:
            self.source.write_bytes(b'abc')
            stamp = module._file_stamp(self.source)
            budget = {'maximum': 3 + extra_allowance, 'read_bytes': 0}
            real_open = Path.open
            class Growing:
                def __init__(self, stream): self.stream = stream; self.once = False
                def __enter__(self): return self
                def __exit__(self, *args): self.stream.close()
                def fileno(self): return self.stream.fileno()
                def read(inner, size):
                    data = inner.stream.read(size)
                    if not inner.once:
                        inner.once = True
                        with real_open(self.source, 'ab', buffering=0) as out: out.write(b'X')
                    return data
            def opened(path, mode='r', *args, **kwargs):
                stream = real_open(path, mode, *args, **kwargs)
                return Growing(stream) if path == self.source and mode == 'rb' and kwargs.get('buffering') == 0 else stream
            with patch.object(Path, 'open', new=opened):
                with self.assertRaisesRegex(ValueError, 'grew|changed'): module._stream_sha(self.source, stamp, budget)
            self.assertLessEqual(budget['read_bytes'], budget['maximum'])

    def test_early_eof_and_descriptor_replacement_are_rejected(self):
        stamp = module._file_stamp(self.source)
        self.source.write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'changed'): module._stream_sha(self.source, stamp, {'maximum': 100, 'read_bytes': 0})
        real_open = Path.open
        class EarlyEOF:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size): return b''
        def opened(path, mode='r', *args, **kwargs):
            stream = real_open(path, mode, *args, **kwargs)
            return EarlyEOF(stream) if path == self.source and mode == 'rb' and kwargs.get('buffering') == 0 else stream
        stamp = module._file_stamp(self.source)
        with patch.object(Path, 'open', new=opened):
            with self.assertRaisesRegex(ValueError, 'ended before planned size'):
                module._stream_sha(self.source, stamp, {'maximum': 100, 'read_bytes': 0})
        real_fstat = module.os.fstat
        def altered(fd):
            value = real_fstat(fd)
            class Bad:
                st_size = value.st_size + 1
                st_mtime_ns = value.st_mtime_ns
                st_ctime_ns = value.st_ctime_ns
                st_ino = value.st_ino
                st_dev = value.st_dev
            return Bad()
        stamp = module._file_stamp(self.source)
        with patch.object(module.os, 'fstat', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'descriptor'): module._stream_sha(self.source, stamp, {'maximum': 100, 'read_bytes': 0})

    def test_aggregate_and_prior_hashed_file_changes_rejected(self):
        real = module._stream_sha
        def change(path, stamp, budget):
            result = real(path, stamp, budget)
            if path == self.patch_b: self.source.write_bytes(b'changed')
            return result
        with patch.object(module, '_stream_sha', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.source.write_bytes(b'source-image'); self.save()
        def change_manifest(path, stamp, budget):
            result = real(path, stamp, budget); self.manifest.write_text('{}', encoding='utf-8'); return result
        with patch.object(module, '_stream_sha', side_effect=change_manifest):
            with self.assertRaisesRegex(ValueError, 'manifest changed'): self.inspect()

    def test_logical_retarget_and_missing_appearing_rejected(self):
        real_resolve = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.source:
                calls += 1
                if calls >= 3: return self.output / 'other.bin'
            return real_resolve(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.patch_b.unlink()
        real_stamp = module._file_stamp
        calls = 0
        def appears(path):
            nonlocal calls
            if path == self.patch_b:
                calls += 1
                if calls == 2: self.patch_b.write_bytes(b'appeared')
            return real_stamp(path)
        with patch.object(module, '_file_stamp', side_effect=appears):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_strict_json_and_remote_escape_nonfile_never_stream(self):
        for raw in ['{"scenes":[],"scenes":[]}', '{"scenes":NaN}', '{"x":1e999}', '{"scenes":[]}']:
            self.save(raw)
            with self.assertRaises(ValueError): self.inspect()
        for value in ['https://invalid.example/a', '//server/share/a', str(self.workspace / 'outside'), str(self.output)]:
            self.rows[0]['image_path'] = value; self.save()
            with patch.object(module, '_stream_sha') as streamed:
                with self.assertRaises(ValueError): self.inspect()
                streamed.assert_not_called()

    def test_cli_cp949_utf8_new_evidence_and_protected_output(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_raster_content.py'), '--data-root', str(self.root), '--expected-manifest-sha256', self.pin, '--max-local-bytes', '32', *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'content.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['actual_local_bytes_read'], 32)
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(cli('--output', self.source).returncode, 1)
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / 'no.json'
            self.assertEqual(cli('--output', path).returncode, 1)
            self.assertFalse(path.exists())
        self.manifest.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
