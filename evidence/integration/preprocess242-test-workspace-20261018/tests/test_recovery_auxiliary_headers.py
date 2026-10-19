"""Synthetic GTiff auxiliary generation contracts and pinned partial header coverage."""
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

import numpy as np
import rasterio
from affine import Affine
from backend.app.data import recovery_auxiliary_headers as module

ROOT = Path(__file__).resolve().parents[1]


class AuxiliaryHeaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.manifest = self.output / 'annual-window-report.json'
        self.source, self.image, self.label, self.quality, self.source_quality = [self.output / name for name in ('source.tif', 'image.tif', 'label.tif', 'quality.tif', 'source-quality.tif')]
        self.transform = Affine(10, 2, 500000, 1, -10, 9000000)
        self.write(self.source, width=512, height=512, count=2, dtype='float32')
        self.write(self.image, count=2, dtype='float32')
        self.write(self.label); self.write(self.quality)
        self.write(self.source_quality, width=512, height=512)
        self.rows = [{'image_path': str(self.image), 'label_path': str(self.label), 'quality_mask_path': str(self.quality), 'patch_sha256': {'image': self.sha(self.image), 'label': self.sha(self.label), 'quality': self.sha(self.quality)}, 'source_window': {'path': str(self.source), 'sha256': self.sha(self.source), 'quality_mask_path': str(self.source_quality), 'quality_mask_sha256': self.sha(self.source_quality), 'boundary_path': 'https://out-of-scope.invalid/boundary', 'boundary_sha256': False}}]
        self.save()

    def tearDown(self): self.temp.cleanup()
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self, raw=None):
        self.manifest.write_text(json.dumps({'scenes': self.rows}) if raw is None else raw, encoding='utf-8')
        self.pin = self.sha(self.manifest)
    def write(self, path, width=256, height=256, count=1, dtype='uint8', crs='EPSG:32748', nodata=0, transform=None, **options):
        with rasterio.open(path, 'w', driver='GTiff', width=width, height=height, count=count, dtype=dtype, crs=crs, nodata=nodata, transform=self.transform if transform is None else transform, **options) as dataset:
            dataset.write(np.ones((count, height, width), dtype=dtype))
    def inspect(self, **kwargs): return module.inspect_recovery_auxiliary_headers(self.root, self.pin, **kwargs)
    def codes(self): return {issue['code'] for issue in self.inspect()['issues']}

    def test_valid_auxiliary_headers_generated_contract_exact_alignment_and_no_approvals(self):
        result = self.inspect()
        self.assertEqual(result['header_validation'], 'HEADERS_MATCH')
        self.assertEqual(result['opened_unique_header_count'], 5)
        self.assertEqual(result['boundary_status'], 'OUT_OF_SCOPE')
        self.assertEqual([c['affine_exact_match'] for c in result['checks']], [True] * 3)
        for coverage in result['role_coverage'].values():
            self.assertEqual(coverage['matched_rows'], 1)
            self.assertEqual(coverage['exact_affine_rows'], 1)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['exactly_once_applied'], 'UNKNOWN')
        for key in ['readiness_full_gate_revalidated', 'pixel_arrays_read', 'raster_content_sha_revalidated', 'label_semantics_validated', 'quality_suitability_validated', 'boundary_authorization_verified', 'ready_for_training', 'scientific_accuracy_validated', 'settlement_authorized', 'automatic_resume_allowed']:
            self.assertIs(result[key], False)

    def test_legacy_source_quality_absent_is_unknown_while_patch_headers_checked(self):
        self.rows[0]['source_window'].pop('quality_mask_path')
        self.rows[0]['source_window'].pop('quality_mask_sha256')
        self.save()
        result = self.inspect()
        self.assertEqual(result['header_validation'], 'KNOWN_HEADERS_MATCH_PARTIAL')
        self.assertEqual(result['coverage_status'], 'INCOMPLETE_REFERENCES')
        self.assertEqual(result['opened_unique_header_count'], 4)
        self.assertEqual(result['role_coverage']['source_quality']['unknown_rows'], 1)
        self.assertEqual(result['role_coverage']['patch_label']['matched_rows'], 1)

    def test_explicit_partial_null_malformed_or_conflicting_refs_prevent_all_headers(self):
        original = copy.deepcopy(self.rows)
        changes = [lambda: self.rows[0]['source_window'].pop('quality_mask_sha256'), lambda: self.rows[0]['source_window'].__setitem__('quality_mask_path', None), lambda: self.rows[0]['patch_sha256'].__setitem__('label', True), lambda: self.rows[0]['patch_sha256'].__setitem__('image', 'A' * 64), lambda: self.rows[0].__setitem__('patch_sha256', False)]
        for mutate in changes:
            self.rows = copy.deepcopy(original); mutate(); self.save()
            with patch.object(module, '_read_auxiliary_header') as opened:
                self.assertEqual(self.inspect()['header_validation'], 'NOT_STARTED_PLAN_REJECTED')
                opened.assert_not_called()
        self.rows = copy.deepcopy(original)
        self.rows.append(copy.deepcopy(self.rows[0]))
        self.rows[1]['source_window']['sha256'] = '0' * 64
        self.save()
        with patch.object(module, '_read_auxiliary_header') as opened:
            self.assertIn('EXPECTED_SHA_CANONICAL_PATH_CONFLICT', self.codes())
            opened.assert_not_called()

    def test_missing_explicit_file_rejects_plan_and_unique_header_budget_is_bounded(self):
        for value in [4, 0, -1, True, 5.0, 10001]:
            with patch.object(module, '_read_auxiliary_header') as opened:
                with self.assertRaises(ValueError): self.inspect(max_unique_headers=value)
                opened.assert_not_called()
        self.assertEqual(self.inspect(max_unique_headers=5)['opened_unique_header_count'], 5)
        self.label.unlink()
        with patch.object(module, '_read_auxiliary_header') as opened:
            self.assertIn('FILE_MISSING', self.codes())
            opened.assert_not_called()

    def test_dimensions_crs_affine_count_dtype_and_actual_nodata_are_checked(self):
        for options, code in [({'width': 128}, 'DIMENSIONS_MISMATCH'), ({'count': 2}, 'AUXILIARY_COUNT_NOT_ONE'), ({'dtype': 'uint16'}, 'AUXILIARY_DTYPE_NOT_UINT8'), ({'nodata': None}, 'AUXILIARY_NODATA_NOT_ZERO'), ({'nodata': 255}, 'AUXILIARY_NODATA_NOT_ZERO'), ({'crs': 'EPSG:4326'}, 'CRS_MISMATCH'), ({'transform': Affine(10, 2, 500001, 1, -10, 9000000)}, 'AFFINE_MISMATCH')]:
            self.write(self.label, **options)
            self.assertIn(code, self.codes())

    def test_tolerance_match_is_separate_from_readiness_exact_affine(self):
        self.write(self.quality, transform=Affine(10, 2, 500000 + 1e-8, 1, -10, 9000000))
        result = self.inspect()
        check = next(c for c in result['checks'] if c['role'] == 'patch_quality')
        self.assertEqual(check['status'], 'HEADER_ALIGNMENT_MATCH')
        self.assertIs(check['affine_exact_match'], False)
        self.assertEqual(result['role_coverage']['patch_quality']['exact_affine_rows'], 0)
        self.assertFalse(result['readiness_full_gate_revalidated'])

    def test_source_quality_matches_source_image_not_patch_grid(self):
        self.write(self.source_quality, width=256, height=256)
        self.assertIn('DIMENSIONS_MISMATCH', self.codes())
        self.write(self.source_quality, width=512, height=512, nodata=None)
        self.assertIn('AUXILIARY_NODATA_NOT_ZERO', self.codes())

    def test_declared_paired_image_is_checked_even_when_source_quality_unknown(self):
        self.rows[0]['source_window'].pop('quality_mask_path'); self.rows[0]['source_window'].pop('quality_mask_sha256'); self.save()
        self.source.write_text('<VRTDataset/>', encoding='utf-8')
        self.assertIn('DECLARED_HEADER_UNSUPPORTED', self.codes())

    def test_shared_header_cache_safe_env_readonly_pixel_and_full_hash_traps(self):
        self.rows.append(copy.deepcopy(self.rows[0])); self.save()
        real_open, real_env, real_bytes = module.rasterio.open, module.rasterio.Env, Path.read_bytes
        calls, options = [], []
        class Guard:
            def __init__(self, dataset): self.dataset = dataset
            def __enter__(self): self.dataset.__enter__(); return self
            def __exit__(self, *args): return self.dataset.__exit__(*args)
            def __getattr__(self, name):
                if name in ('read', 'read_masks', 'statistics', 'stats', 'tags'): raise AssertionError('Pixel/statistics API forbidden')
                return getattr(self.dataset, name)
        def opened(path, **kwargs): calls.append(kwargs); return Guard(real_open(path, **kwargs))
        def env(**kwargs): options.append(kwargs); return real_env(**kwargs)
        def read_bytes(path):
            if path != self.manifest: raise AssertionError('Full auxiliary/image byte SHA forbidden')
            return real_bytes(path)
        with patch.object(module.rasterio, 'open', side_effect=opened), patch.object(module.rasterio, 'Env', side_effect=env), patch.object(Path, 'read_bytes', new=read_bytes):
            result = self.inspect()
        self.assertEqual(result['opened_unique_header_count'], 5)
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(call == {'mode': 'r', 'driver': 'GTiff', 'GEOREF_SOURCES': 'INTERNAL'} for call in calls))
        self.assertTrue(all(option == module.SAFE_GDAL_OPTIONS for option in options))

    def test_source_bytes_prefix_sidecar_and_inventory_unchanged(self):
        self.label.with_suffix('.tif.aux.xml').write_text('<PAMDataset><SRS>EPSG:4326</SRS></PAMDataset>', encoding='utf-8')
        self.label.with_suffix('.tfw').write_text('1\n0\n0\n-1\n0\n0\n', encoding='ascii')
        before = {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(self.inspect()['header_validation'], 'HEADERS_MATCH')
        self.assertEqual(before, {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_nontiff_vrt_invalid_crs_singular_and_bigtiff_endian_safety(self):
        self.label.write_text('<VRTDataset><SourceFilename>https://invalid.example/a</SourceFilename></VRTDataset>', encoding='utf-8')
        real = module.rasterio.open
        paths = []
        def opened(path, **kwargs): paths.append(Path(path)); return real(path, **kwargs)
        with patch.object(module.rasterio, 'open', side_effect=opened): self.assertIn('AUXILIARY_HEADER_UNSUPPORTED', self.codes())
        self.assertNotIn(self.label, paths)
        self.label.unlink()
        for options in [{'crs': None}, {'transform': Affine(1, 2, 5, 2, 4, 6)}, {'transform': Affine(float('nan'), 0, 5, 0, -1, 6)}]:
            self.write(self.label, **options)
            self.assertIn('AUXILIARY_HEADER_INVALID', self.codes())
        self.write(self.label, BIGTIFF='YES', ENDIANNESS='BIG')
        self.assertEqual(self.inspect()['header_validation'], 'HEADERS_MATCH')

    def test_pin_strict_json_path_boundaries_and_nonfile_prevent_headers(self):
        for value in [True, 'A' * 64, '0' * 64]:
            with self.assertRaises(ValueError): module.inspect_recovery_auxiliary_headers(self.root, value)
        for raw in ['{"scenes":[],"scenes":[]}', '{"scenes":NaN}', '{"x":1e999}', '{"scenes":[]}']:
            self.save(raw)
            with self.assertRaises(ValueError): self.inspect()
        for path in ['https://invalid.example/label', '//server/share/label', str(self.workspace / 'outside'), str(self.output)]:
            self.rows[0]['label_path'] = path; self.save()
            with patch.object(module, '_read_auxiliary_header') as opened:
                with self.assertRaises(ValueError): self.inspect()
                opened.assert_not_called()

    def test_stat_change_manifest_mutation_alias_retarget_and_missing_appearing(self):
        real_header = module._read_auxiliary_header
        def mutate(path):
            result = real_header(path)
            if path == self.label:
                with self.label.open('ab') as stream: stream.write(b'X')
            return result
        with patch.object(module, '_read_auxiliary_header', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.write(self.label); self.save()
        def manifest_change(path):
            result = real_header(path); self.manifest.write_text('{}', encoding='utf-8'); return result
        with patch.object(module, '_read_auxiliary_header', side_effect=manifest_change):
            with self.assertRaisesRegex(ValueError, 'manifest changed'): self.inspect()
        self.save()
        real = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.label:
                calls += 1
                if calls >= 2: return self.output / 'other'
            return real(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.label.unlink()
        real_stamp = module._stamp
        calls = 0
        def appears(path):
            nonlocal calls
            if path == self.label:
                calls += 1
                if calls == 2: self.label.write_bytes(b'appeared')
            return real_stamp(path)
        with patch.object(module, '_stamp', side_effect=appears):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_cli_cp949_utf8_evidence_and_input_existing_external_output_protection(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_auxiliary_headers.py'), '--data-root', str(self.root), '--expected-manifest-sha256', self.pin, '--max-unique-headers', '5', *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'headers.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['opened_unique_header_count'], 5)
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(cli('--output', self.label).returncode, 1)
        with tempfile.TemporaryDirectory() as external:
            path = Path(external) / 'no.json'
            self.assertEqual(cli('--output', path).returncode, 1)
            self.assertFalse(path.exists())
        self.manifest.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
