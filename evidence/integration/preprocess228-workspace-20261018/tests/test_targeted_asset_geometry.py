import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from app.data.targeted_asset_geometry import inspect_targeted_asset_geometry


class TargetedAssetGeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'data').mkdir()
        self.raster('image.tif', from_origin(500000, 9300000, 10, 10), 'EPSG:32748', 512)
        self.raster('label.tif', from_origin(499000, 9301000, 20, 20), 'EPSG:32748', 512)
        bbox = list(transform_bounds('EPSG:32748', 'EPSG:4326', 501000, 9297000, 503000, 9299000, densify_pts=100))
        self.request = {'schema_version': 1, 'kind': 'TARGETED_ASSET_GEOMETRY_REQUEST',
                        'target_year': 2025, 'image_year': 2025, 'label_year': 2025,
                        'target_bbox_wgs84': bbox, 'image_ref': self.ref('image.tif'), 'label_ref': self.ref('label.tif')}

    def tearDown(self):
        self.temp.cleanup()

    def raster(self, name, affine, crs, side=256, driver='GTiff'):
        with rasterio.open(self.root/'data'/name, 'w', driver=driver, count=1, dtype='uint8',
                           width=side, height=side, transform=affine, crs=crs) as ds:
            ds.write(np.ones((side, side), dtype='uint8'), 1)

    def ref(self, name):
        return {'path': 'data/'+name, 'sha256': hashlib.sha256((self.root/'data'/name).read_bytes()).hexdigest()}

    def run_request(self, request=None):
        return inspect_targeted_asset_geometry(self.root, self.request if request is None else request)

    def test_actual_projected_different_resolution_and_input_files_unchanged(self):
        before = {p: p.read_bytes() for p in (self.root/'data').iterdir()}
        request = copy.deepcopy(self.request)
        out = self.run_request()
        self.assertEqual(out['status'], 'LOCAL_COVERAGE_OBSERVED_EXECUTION_BLOCKED', out)
        self.assertEqual([a['transform'][0] for a in out['assets']], [10, 20])
        self.assertTrue(all(a['sampled_native_envelope_contained'] for a in out['assets']))
        self.assertTrue(all(not a['complete_projection_coverage_proven'] for a in out['assets']))
        for key in ('same_grid_asserted', 'execution_supported', 'pending_footprints_verified',
                    'support_assets_verified', 'source_scene_split_verified', 'quality_verified',
                    'temporal_truth_verified', 'training_ready'):
            self.assertFalse(out[key])
        self.assertEqual(request, self.request)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.root/'data').iterdir()})

    def test_center_inside_but_full_bbox_outside_rejected(self):
        self.request['target_bbox_wgs84'] = list(transform_bounds('EPSG:32748', 'EPSG:4326',
                                                                 499900, 9297000, 503000, 9299000))
        out = self.run_request()
        self.assertEqual(out['issue'], 'IMAGE_COVERAGE_SHORTFALL')
        self.assertEqual(out['assets'], [])

    def test_image_inside_label_outside_even_with_successful_scl_not_used(self):
        self.raster('label.tif', from_origin(510000, 9300000, 10, 10), 'EPSG:32748')
        self.request['label_ref'] = self.ref('label.tif')
        out = self.run_request()
        self.assertEqual(out['issue'], 'LABEL_COVERAGE_SHORTFALL')
        self.assertFalse(out['local_bytes_verified'])
        self.assertEqual(out['assets'], [])

    def test_exact_geographic_boundary_is_accepted(self):
        for name in ('image.tif', 'label.tif'):
            self.raster(name, from_origin(105, -6, .001, .001), 'EPSG:4326')
        self.request.update(image_ref=self.ref('image.tif'), label_ref=self.ref('label.tif'),
                            target_bbox_wgs84=[105, -6.256, 105.256, -6])
        self.assertTrue(self.run_request()['local_bytes_verified'])

    def test_different_actual_crs_checked_independently(self):
        self.raster('label.tif', from_origin(104, -5, .01, .01), 'EPSG:4326', 512)
        self.request['label_ref'] = self.ref('label.tif')
        out = self.run_request()
        self.assertTrue(out['local_bytes_verified'], out)
        self.assertEqual([a['crs'] for a in out['assets']], ['EPSG:32748', 'EPSG:4326'])
        self.assertFalse(out['same_grid_asserted'])

    def test_changed_sha_and_post_observation_mutation_are_blocked(self):
        with (self.root/'data/image.tif').open('ab') as stream:
            stream.write(b'changed')
        self.assertEqual(self.run_request()['issue'], 'FILE_PIN_MISMATCH')
        self.request['image_ref'] = self.ref('image.tif')
        from app.data import targeted_asset_geometry as module
        original = module._observe
        calls = 0
        def mutate(*args):
            nonlocal calls
            row = original(*args)
            calls += 1
            if calls == 2:
                with (self.root/'data/image.tif').open('ab') as stream:
                    stream.write(b'concurrent change')
            return row
        with patch.object(module, '_observe', side_effect=mutate):
            out = self.run_request()
        self.assertEqual(out['issue'], 'FILE_PIN_MISMATCH')
        self.assertEqual(out['assets'], [])

    def test_invalid_request_and_year_precede_file_reads(self):
        cases = []
        for key, value in [('schema_version', True), ('label_year', True), ('label_year', 2024),
                           ('target_bbox_wgs84', [True, 0, 1, 1]), ('target_bbox_wgs84', [170, 0, -170, 1]),
                           ('target_bbox_wgs84', [0, 0, float('nan'), 1])]:
            row = copy.deepcopy(self.request); row[key] = value; cases.append(row)
        row = copy.deepcopy(self.request); row['catalog_bbox'] = [0, 0, 1, 1]; cases.append(row)
        row = copy.deepcopy(self.request); row['loop'] = row; cases.append(row)
        with patch('app.data.targeted_asset_geometry._pinned', side_effect=AssertionError('I/O forbidden')) as reader:
            for row in cases:
                self.assertEqual(self.run_request(row)['status'], 'BLOCKED')
            reader.assert_not_called()

    def test_catalog_hint_cannot_override_actual_grid(self):
        self.raster('image.tif', from_origin(510000, 9300000, 10, 10), 'EPSG:32748')
        self.request['image_ref'] = self.ref('image.tif')
        self.assertEqual(self.run_request()['issue'], 'IMAGE_COVERAGE_SHORTFALL')

    def test_malformed_tiff_and_projected_boundary_fail_closed(self):
        (self.root/'data/broken.tif').write_bytes(b'II*\x00PRIVATE_INVALID_GDAL_BYTES')
        original = copy.deepcopy(self.request)
        self.request['image_ref'] = self.ref('broken.tif')
        out = self.run_request()
        self.assertEqual(out['status'], 'BLOCKED')
        self.assertEqual(out['assets'], [])
        self.assertNotIn('PRIVATE', str(out))
        self.assertNotIn(str(self.root), str(out))
        self.request = original
        # Explicit fault injection: transformed sampled envelope exactly on the
        # projected outer edge is conservatively rejected by outward ULP padding.
        with patch('rasterio.warp.transform_bounds', return_value=(500000, 9294880, 505120, 9300000)):
            out = self.run_request()
        self.assertEqual(out['issue'], 'IMAGE_COVERAGE_SHORTFALL')

    def test_vrt_and_rotated_grid_and_path_escape_rejected(self):
        (self.root/'data/fake.tif').write_text('<VRTDataset><SourceFilename>/secret</SourceFilename></VRTDataset>')
        self.request['image_ref'] = self.ref('fake.tif')
        self.assertEqual(self.run_request()['issue'], 'RASTER_INVALID')
        from affine import Affine
        self.raster('rotated.tif', Affine(10, 1, 500000, 0, -10, 9300000), 'EPSG:32748')
        self.request['image_ref'] = self.ref('rotated.tif')
        self.assertEqual(self.run_request()['issue'], 'RASTER_GRID_INVALID')
        self.request['image_ref']['path'] = '../outside-private-file.tif'
        out = self.run_request()
        self.assertEqual(out['status'], 'BLOCKED')
        self.assertNotIn('outside-private', str(out))


if __name__ == '__main__':
    unittest.main()
