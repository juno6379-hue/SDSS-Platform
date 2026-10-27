"""권위 registry, Swipe preflight, PNG 투명도와 SHA 고정을 검증한다."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from app.landcover_tiles import inventory, palette_for, render_tile, series_index, tile


class LandcoverTileTests(unittest.TestCase):
    def raster(self, path, values, nodata=0, bounds=None):
        half = 20037508.342789244
        path.parent.mkdir(parents=True, exist_ok=True)
        bounds = bounds or (-half, -half, half, half)
        with rasterio.open(path, 'w', driver='GTiff', width=2, height=2, count=1, dtype='uint8',
                           crs='EPSG:3857', transform=from_bounds(*bounds, 2, 2), nodata=nodata) as target:
            target.write(np.asarray(values, dtype='uint8'), 1)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def authority(self, root, rows, **extra):
        report = root / 'first-group-training-esri-v1' / 'annual-window-report.json'
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({'synthetic': True, 'learning_ready': False, 'scenes': rows, **extra}), encoding='utf-8')
        return report

    def row(self, root, year, name=None, bounds=None, aoi='fixture/00/r0-c0'):
        name = name or str(year)
        group = root / 'first-group-training-esri-v1' / 'sources' / name
        window = group / f'window-{name}'
        label = window / 'label.tif'
        quality = window / 'quality.tif'
        image = window / 'image.tif'
        self.raster(label, [[1, 2], [5, int(year) % 8 + 1]], bounds=bounds)
        self.raster(quality, [[1, 1], [1, 1]], bounds=bounds)
        self.raster(image, [[1, 1], [1, 1]], bounds=bounds)
        source_group = f'fixture/source-{name}'
        source_row = {'year': year, 'aoi': aoi, 'province': 'fixture', 'label_source': 'esri_io',
                      'label_path': str(label), 'quality_mask_path': str(quality),
                      'quality_mask': 'fixture-mask-v1', 'source_group': source_group,
                      'taxonomy_signature': 'fixture-schema-v1', 'label_dataset_version': f'fixture-{year}'}
        (group / 'annual-window-report.json').write_text(json.dumps({'scenes': [source_row]}), encoding='utf-8')
        return {'year': year, 'aoi': 'fixture', 'province': 'fixture', 'label_source': 'esri_io',
                'quality_status': 'quality_eligible', 'source_group': source_group,
                'spatial_location_id': aoi, 'taxonomy_signature': 'fixture-schema-v1',
                'source_window': {'path': str(image), 'sha256': self.sha(image)},
                '_fixture_label_path': str(label)}

    def test_authority_only_existing_years_and_reference_statistics_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [self.row(root, year) for year in (2020, 2021, 2023)]
            self.authority(root, rows)
            decoy = root / 'first-group-newer' / 'annual-window-report.json'
            decoy.parent.mkdir()
            decoy.write_text(json.dumps({'scenes': [self.row(root, 2025, 'decoy')]}), encoding='utf-8')

            public, layers = inventory(root)

            self.assertEqual(public['authority']['report'], 'first-group-training-esri-v1/annual-window-report.json')
            self.assertEqual(public['registry_status'], 'REGISTERED')
            self.assertEqual(public['change_statistics_status'], 'BLOCKED_NO_MODEL_PREDICTION')
            self.assertEqual(len(public['series']), 1)
            group = public['series'][0]
            self.assertFalse(group['independent_ground_truth'])
            self.assertFalse(group['model_prediction'])
            self.assertEqual([item['year'] for item in group['years']], [2020, 2021, 2023])
            self.assertTrue(all(item['reference_kind'] == 'weak_label_agreement' for item in group['years']))
            self.assertTrue(all(item['independent_ground_truth'] is False for item in group['years']))
            self.assertTrue(all(item['model_prediction'] is False for item in group['years']))
            self.assertEqual(group['missing_years'], [2022, 2024, 2025])
            self.assertEqual(len(layers), 3)
            comparison = next(item for item in public['comparisons'] if item['left_year'] == 2020 and item['right_year'] == 2021)
            self.assertTrue(comparison['visual_comparison_allowed'])
            self.assertFalse(comparison['change_statistics_allowed'])
            self.assertEqual(comparison['change_statistics_status'], 'BLOCKED_REFERENCE_LAYERS_NOT_MODEL_PREDICTIONS')
            self.assertTrue(comparison['comparison_id'].startswith('cmp-'))

    def test_duplicate_group_year_is_removed_instead_of_silent_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.authority(root, [self.row(root, 2020, 'first'), self.row(root, 2020, 'second')])

            public, layers = inventory(root)

            self.assertEqual(public['registry_status'], 'BLOCKED')
            self.assertEqual([issue['code'] for issue in public['issues']], ['DUPLICATE_GROUP_YEAR'])
            self.assertEqual(public['series'][0]['years'], [])
            self.assertEqual(public['series'][0]['blocked_years'], [{'year': 2020, 'reason': 'DUPLICATE_GROUP_YEAR'}])
            self.assertEqual(layers, {})

    def test_grid_mismatch_blocks_swipe_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = self.row(root, 2020, 'left', bounds=(-10, -10, 10, 10))
            right = self.row(root, 2021, 'right', bounds=(-20, -10, 0, 10))
            self.authority(root, [left, right])

            public, _ = inventory(root)
            comparison = public['comparisons'][0]

            self.assertFalse(comparison['visual_comparison_allowed'])
            self.assertEqual(comparison['preflight_status'], 'BLOCKED')
            self.assertIn('affine', comparison['mismatched_contract_fields'])
            self.assertIn('bounds', comparison['mismatched_contract_fields'])

    def test_label_and_quality_mask_grid_mismatch_blocks_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row(root, 2020)
            quality = Path(row['_fixture_label_path']).with_name('quality.tif')
            self.raster(quality, [[1, 1], [1, 1]], bounds=(-20, -10, 0, 10))
            self.authority(root, [row])

            public, layers = inventory(root)

            self.assertEqual(public['registry_status'], 'BLOCKED')
            self.assertEqual(public['series'], [])
            self.assertEqual(layers, {})
            self.assertIn('QUALITY_MASK_GRID_MISMATCH', public['issues'][0]['detail'])

    def test_nonbinary_quality_mask_blocks_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row(root, 2020)
            quality = Path(row['_fixture_label_path']).with_name('quality.tif')
            self.raster(quality, [[1, 2], [1, 0]])
            self.authority(root, [row])

            public, layers = inventory(root)

            self.assertEqual(public['registry_status'], 'BLOCKED')
            self.assertEqual(layers, {})
            self.assertIn('QUALITY_MASK_NOT_BINARY_0_1', public['issues'][0]['detail'])

    def test_tile_rejects_same_size_same_mtime_sha_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row(root, 2020)
            self.authority(root, [row])
            public, _ = series_index(root, refresh=True)
            layer_id = public['series'][0]['years'][0]['layer_id']
            path = Path(row['_fixture_label_path'])
            stamp = path.stat()
            raw = bytearray(path.read_bytes())
            raw[-1] ^= 1
            path.write_bytes(raw)
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))

            with self.assertRaisesRegex(KeyError, 'SHA256'):
                tile(root, layer_id, 0, 0, 0)

    def test_tile_rejects_quality_mask_same_size_same_mtime_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row(root, 2020)
            self.authority(root, [row])
            public, _ = series_index(root, refresh=True)
            layer_id = public['series'][0]['years'][0]['layer_id']
            path = Path(row['_fixture_label_path']).with_name('quality.tif')
            stamp = path.stat()
            raw = bytearray(path.read_bytes())
            raw[-1] ^= 1
            path.write_bytes(raw)
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))

            with self.assertRaisesRegex(KeyError, '마스크 SHA256'):
                tile(root, layer_id, 0, 0, 0)

    def test_quality_mask_hides_invalid_classified_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row(root, 2020)
            quality = Path(row['_fixture_label_path']).with_name('quality.tif')
            self.raster(quality, [[1, 0], [1, 1]])
            self.authority(root, [row])
            public, _ = series_index(root, refresh=True)
            layer_id = public['series'][0]['years'][0]['layer_id']

            raw = tile(root, layer_id, 0, 0, 0)
            with MemoryFile(raw) as memory, memory.open() as image:
                rgba = image.read()

            self.assertEqual(int(rgba[3, 64, 64]), 255)
            self.assertEqual(int(rgba[3, 64, 192]), 0)

    def test_esri_cloud_and_nodata_are_transparent_but_water_is_blue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'esri.tif'
            self.raster(path, [[1, 0], [10, 2]])
            raw = render_tile(str(path), path.stat().st_mtime_ns, path.stat().st_size,
                              json.dumps(palette_for('esri_io')), 0, 0, 0)
            with MemoryFile(raw) as memory, memory.open() as image:
                rgba = image.read()
            self.assertEqual(rgba[:, 64, 64].tolist(), [65, 155, 223, 255])
            self.assertEqual(int(rgba[3, 64, 192]), 0)
            self.assertEqual(int(rgba[3, 192, 64]), 0)
            self.assertEqual(rgba[:, 192, 192].tolist(), [57, 125, 73, 255])

    def test_model_class_zero_is_water_and_ignore255_is_transparent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.tif'
            self.raster(path, [[0, 255], [1, 2]], nodata=255)
            raw = render_tile(str(path), path.stat().st_mtime_ns, path.stat().st_size,
                              json.dumps(palette_for('model_prediction')), 0, 0, 0)
            with MemoryFile(raw) as memory, memory.open() as image:
                rgba = image.read()
            self.assertEqual(rgba[:, 64, 64].tolist(), [65, 155, 223, 255])
            self.assertEqual(int(rgba[3, 64, 192]), 0)

    def test_unknown_layer_and_invalid_xyz_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KeyError):
                tile(Path(directory), 'not-a-local-layer', 0, 0, 0)
            with self.assertRaises(ValueError):
                tile(Path(directory), 'none', 0, 1, 0)

    def test_external_reference_path_is_not_exposed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            label = Path(external) / 'outside.tif'
            quality = Path(external) / 'quality.tif'
            self.raster(label, [[1, 2], [5, 7]])
            self.raster(quality, [[1, 1], [1, 1]])
            group = root / 'first-group-training-esri-v1' / 'sources' / 'outside-source'
            window = group / 'window'
            image = window / 'image.tif'
            self.raster(image, [[1, 1], [1, 1]])
            group.mkdir(parents=True, exist_ok=True)
            group.joinpath('annual-window-report.json').write_text(json.dumps({'scenes': [{
                'year': 2020, 'province': 'fixture', 'aoi': 'outside', 'label_source': 'esri_io',
                'label_path': str(label), 'quality_mask_path': str(quality), 'source_group': 'fixture/outside',
                'quality_mask': 'fixture-mask-v1', 'taxonomy_signature': 'fixture-schema-v1'}]}))
            row = {'year': 2020, 'province': 'fixture', 'label_source': 'esri_io',
                   'quality_status': 'quality_eligible', 'source_group': 'fixture/outside',
                   'taxonomy_signature': 'fixture-schema-v1', 'source_window': {'path': str(image)}}
            self.authority(root, [row])
            public, _ = inventory(root)
            self.assertEqual(public['series'], [])
            self.assertEqual(public['issues'][0]['code'], 'AUTHORITY_SOURCE_IDENTITY_NOT_FOUND')


if __name__ == '__main__':
    unittest.main()
