"""Synthetic local GTiff header tests; generated rasters only, no external access."""
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
from backend.app.data import recovery_raster_headers as module

ROOT = Path(__file__).resolve().parents[1]


class RasterHeaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.source = self.output / 'source.tif'
        self.manifest = self.output / 'annual-window-report.json'
        self.transform = Affine(10, 0, 500000, 0, -10, 9000000)
        self.write_raster(self.source, 512, 512, self.transform)
        self.rows = []
        for y in (0, 256):
            for x in (0, 256):
                path = self.output / f'patch-{x}-{y}.tif'
                self.write_raster(path, 256, 256, self.transform @ Affine.translation(x, y))
                self.rows.append({'image_path': str(path), 'source_window': {'path': str(self.source)}, 'window_in_source': [x, y, 256, 256]})
        self.save()

    def tearDown(self): self.temp.cleanup()

    def save(self): self.manifest.write_text(json.dumps({'scenes': self.rows}), encoding='utf-8')

    def write_raster(self, path, width, height, transform, crs='EPSG:32748', count=2, dtype='float32', **options):
        with rasterio.open(path, 'w', driver='GTiff', width=width, height=height, count=count, dtype=dtype, crs=crs, transform=transform, **options) as ds:
            ds.write(np.ones((count, height, width), dtype=dtype))

    def inspect(self): return module.inspect_recovery_raster_headers(self.root)

    def codes(self): return {item['code'] for item in self.inspect()['issues']}

    def first_patch(self): return Path(self.rows[0]['image_path'])

    def test_real_two_by_two_patch_headers_match_without_pixels_or_content_hash(self):
        result = self.inspect()
        self.assertEqual(result['header_consistency'], 'CONSISTENT_HEADERS')
        self.assertEqual(result['unique_raster_path_count'], 5)
        self.assertEqual([r['status'] for r in result['scene_checks']], ['HEADER_CONTRACT_MATCH'] * 4)
        self.assertEqual(result['status'], 'BLOCKED')
        for key in ['pixel_arrays_read', 'raster_content_sha_computed', 'label_quality_checked', 'same_content_different_file_checked', 'geometric_independence_checked', 'ready_for_training', 'scientific_accuracy_validated', 'settlement_authorized', 'automatic_resume_allowed']:
            self.assertIs(result[key], False)
        self.assertEqual(result['exactly_once_applied'], 'UNKNOWN')

    def test_rotated_skew_source_window_transform_is_supported(self):
        transform = Affine(10, 2, 500000, 1, -10, 9000000)
        self.write_raster(self.source, 512, 512, transform)
        for row in self.rows:
            x, y = row['window_in_source'][:2]
            self.write_raster(Path(row['image_path']), 256, 256, transform @ Affine.translation(x, y))
        self.assertEqual(self.inspect()['header_consistency'], 'CONSISTENT_HEADERS')

    def test_explicit_transform_tolerance_accepts_small_error_rejects_larger_error(self):
        self.write_raster(self.first_patch(), 256, 256, Affine(10, 0, 500000 + 1e-8, 0, -10, 9000000))
        self.assertNotIn('PATCH_TRANSFORM_MISMATCH', self.codes())
        self.write_raster(self.first_patch(), 256, 256, Affine(10, 0, 500000 + .01, 0, -10, 9000000))
        self.assertIn('PATCH_TRANSFORM_MISMATCH', self.codes())

    def test_bounds_grid_types_and_extent_are_checked(self):
        for crop, code in [([512, 0, 256, 256], 'CROP_OUTSIDE_SOURCE_BOUNDS'), ([False, 0, 256, 256], 'CROP_COORDINATES_INVALID'), ([0.0, 0, 256, 256], 'CROP_COORDINATES_INVALID'), ([1, 0, 256, 256], 'CROP_COORDINATES_INVALID'), ([-256, 0, 256, 256], 'CROP_COORDINATES_INVALID'), ([0, 0, 128, 256], 'CROP_COORDINATES_INVALID')]:
            self.rows[0]['window_in_source'] = crop; self.save()
            self.assertIn(code, self.codes())

    def test_extreme_integer_offset_is_bounded_issue_without_float_overflow(self):
        self.rows[0]['window_in_source'] = [256 * 10 ** 400, 0, 256, 256]
        self.save()
        self.assertIn('CROP_OUTSIDE_SOURCE_BOUNDS', self.codes())

    def test_dimensions_band_count_dtypes_and_crs_mismatches_detected(self):
        for options, code in [({'width': 128}, 'PATCH_DIMENSIONS_MISMATCH'), ({'count': 1}, 'PATCH_BAND_COUNT_MISMATCH'), ({'dtype': 'uint16'}, 'PATCH_DTYPES_MISMATCH'), ({'crs': 'EPSG:4326'}, 'PATCH_CRS_MISMATCH')]:
            kwargs = {'width': 256, 'height': 256, 'transform': self.transform, **options}
            self.write_raster(self.first_patch(), **kwargs)
            self.assertIn(code, self.codes())

    def test_missing_crs_singular_and_nonfinite_affine_invalid(self):
        self.write_raster(self.first_patch(), 256, 256, self.transform, crs=None)
        self.assertIn('PATCH_HEADER_INVALID', self.codes())
        self.write_raster(self.first_patch(), 256, 256, Affine(1, 2, 5, 2, 4, 6))
        self.assertIn('PATCH_HEADER_INVALID', self.codes())
        self.assertFalse(module._valid_transform([float('nan'), 0, 0, 0, -1, 0]))
        self.assertFalse(module._valid_transform([1, 0, 0, 0, float('inf'), 0]))
        self.write_raster(self.first_patch(), 256, 256, Affine(float('nan'), 0, 5, 0, -1, 6))
        self.assertIn('PATCH_HEADER_INVALID', self.codes())

    def test_missing_and_vrt_rejected_before_gdal_open(self):
        self.first_patch().unlink()
        self.assertIn('PATCH_HEADER_MISSING', self.codes())
        self.first_patch().write_text('<VRTDataset rasterXSize="256" rasterYSize="256"><VRTRasterBand><SimpleSource><SourceFilename>https://invalid.example/no.tif</SourceFilename></SimpleSource></VRTRasterBand></VRTDataset>', encoding='utf-8')
        real = module.rasterio.open
        called = []
        def opened(path, *args, **kwargs):
            called.append(Path(path))
            return real(path, *args, **kwargs)
        with patch.object(module.rasterio, 'open', side_effect=opened):
            self.assertIn('PATCH_HEADER_UNSUPPORTED', self.codes())
        self.assertNotIn(self.first_patch(), called)

    def test_bigtiff_header_supported_and_bad_tiff_invalid(self):
        self.write_raster(self.first_patch(), 256, 256, self.transform, BIGTIFF='YES')
        self.assertEqual(self.inspect()['header_consistency'], 'CONSISTENT_HEADERS')
        self.first_patch().write_bytes(b'II+\x00\x04\x00\x00\x00')
        self.assertIn('PATCH_HEADER_INVALID', self.codes())
        self.first_patch().write_bytes(b'II*\x00BAD!')
        self.assertIn('PATCH_HEADER_INVALID', self.codes())

    def test_big_endian_classic_and_bigtiff_signatures_are_supported(self):
        for bigtiff, signature in [('NO', b'MM\x00*'), ('YES', b'MM\x00+')]:
            self.write_raster(self.first_patch(), 256, 256, self.transform, BIGTIFF=bigtiff, ENDIANNESS='BIG')
            with self.first_patch().open('rb') as stream:
                self.assertEqual(stream.read(4), signature)
            self.assertEqual(self.inspect()['header_consistency'], 'CONSISTENT_HEADERS')

    def test_actual_driver_must_be_gtiff_even_after_magic_precheck(self):
        class UnexpectedDriver:
            driver = 'VRT'
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with patch.object(module.rasterio, 'open', return_value=UnexpectedDriver()):
            self.assertEqual(module._read_header(self.source), {'status': 'UNSUPPORTED', 'reason': 'DRIVER_NOT_GTIFF'})

    def test_open_is_gtiff_readonly_safe_env_and_read_method_never_called(self):
        real_open, real_env = module.rasterio.open, module.rasterio.Env
        calls, environments = [], []
        class Guard:
            def __init__(self, dataset): self.dataset = dataset
            def __enter__(self): self.dataset.__enter__(); return self
            def __exit__(self, *args): return self.dataset.__exit__(*args)
            def __getattr__(self, name):
                if name in ('read', 'read_masks', 'statistics', 'stats', 'tags'):
                    raise AssertionError('Pixels/statistics must not be requested')
                return getattr(self.dataset, name)
        def opened(path, **kwargs):
            calls.append(kwargs.copy())
            return Guard(real_open(path, **kwargs))
        def env(**kwargs): environments.append(kwargs.copy()); return real_env(**kwargs)
        with patch.object(module.rasterio, 'open', side_effect=opened), patch.object(module.rasterio, 'Env', side_effect=env):
            self.assertEqual(self.inspect()['header_consistency'], 'CONSISTENT_HEADERS')
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(c == {'mode': 'r', 'driver': 'GTiff', 'GEOREF_SOURCES': 'INTERNAL'} for c in calls))
        self.assertTrue(all(e == module.SAFE_GDAL_OPTIONS for e in environments))

    def test_header_cache_stat_recheck_and_source_bytes_sidecars_preserved(self):
        aux = self.source.with_suffix('.tif.aux.xml')
        aux.write_text('<PAMDataset><SRS>EPSG:4326</SRS></PAMDataset>', encoding='utf-8')
        self.source.with_suffix('.tfw').write_text('1\n0\n0\n-1\n0\n0\n', encoding='ascii')
        before = {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        real = module._read_header
        with patch.object(module, '_read_header', wraps=real) as opened:
            self.assertEqual(self.inspect()['header_consistency'], 'CONSISTENT_HEADERS')
            self.assertEqual(opened.call_count, 5)
        self.assertEqual(before, {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_raster_stat_change_and_missing_appearing_fail_closed(self):
        real = module._stamp
        calls = 0
        def changed(path):
            nonlocal calls
            if path == self.source:
                calls += 1
                if calls == 2:
                    with self.source.open('ab') as stream: stream.write(b'X')
            return real(path)
        with patch.object(module, '_stamp', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.first_patch().unlink()
        calls = 0
        def appear(path):
            nonlocal calls
            if path == self.first_patch():
                calls += 1
                if calls == 2: path.write_bytes(b'fake')
            return real(path)
        with patch.object(module, '_stamp', side_effect=appear):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_logical_retarget_aggregate_stale_and_strict_json(self):
        real = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.source:
                calls += 1
                if calls == 2: return self.output / 'elsewhere.tif'
            return real(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'target changed'): self.inspect()
        real_header = module._read_header
        def mutate(path):
            self.manifest.write_text('{}', encoding='utf-8')
            return real_header(path)
        with patch.object(module, '_read_header', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        for raw in ['{"scenes":[],"scenes":[]}', '{"scenes":NaN}', '{"x":1e999}']:
            self.manifest.write_text(raw, encoding='utf-8')
            with self.assertRaises(ValueError): self.inspect()

    def test_remote_root_escape_and_nonfile_paths_rejected(self):
        for target in ['https://invalid.example/a.tif', '//server/share/a.tif', str(self.workspace / 'outside.tif'), str(self.output)]:
            self.rows[0]['image_path'] = target; self.save()
            with self.assertRaises(ValueError): self.inspect()

    def test_cli_cp949_new_utf8_evidence_and_protected_output(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_raster_headers.py'), '--data-root', str(self.root), *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'headers.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'BLOCKED')
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(cli('--output', self.source).returncode, 1)
        self.rows[0]['image_path'] = 'https://invalid.example/a.tif'; self.save()
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
