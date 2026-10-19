"""정합 감사가 실제 오류를 찾고 0/255를 혼동하지 않는지 확인한다."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.audit_raster_alignment import audit_manifest, audit_pair, audit_reports, audit_source_reprojection, backend_mapping, backend_esri_mapping, counts, digest, independent_map, WORLD_COVER_MAPPING, ESRI_MAPPING
from rasterio.warp import transform_geom


class RasterAlignmentAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.transform = from_origin(500000, 9300000, 10, 10)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, data, transform=None):
        if data.ndim == 2:
            data = data[None]
        with rasterio.open(path, 'w', driver='GTiff', width=data.shape[2], height=data.shape[1],
                           count=data.shape[0], dtype=data.dtype, nodata=0, crs='EPSG:32748',
                           transform=transform or self.transform) as output:
            output.write(data)

    def pair(self):
        image = self.root / 'image.tif'
        label = self.root / 'label.tif'
        self.write(image, np.full((3, 4, 4), 100, dtype='uint16'))
        raw = np.full((4, 4), 80, dtype='uint8')
        raw[0, 0] = 0
        self.write(label, raw)
        return image, label, raw

    def test_water_zero_is_not_ignore_255(self):
        image, label, _ = self.pair()
        result = audit_pair(image, label)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['mapped_class_counts'], {'0': 15, '255': 1})
        self.assertEqual(result['water_raw80_mapped0_count'], 15)

    def test_half_pixel_shift_fails_even_with_same_crs_shape_resolution(self):
        image, label, raw = self.pair()
        self.write(label, raw, from_origin(500005, 9300000, 10, 10))
        result = audit_pair(image, label)
        self.assertEqual(result['status'], 'fail')
        self.assertTrue(result['checks']['shape_equal'])
        self.assertTrue(result['checks']['resolution_equal'])
        self.assertFalse(result['checks']['exact_affine_equal'])
        self.assertFalse(result['checks']['pixel_centers_equal'])

    def test_fractional_interpolated_class_fails(self):
        image, label, raw = self.pair()
        raw = raw.astype('float32')
        raw[0, 1] = 39.5
        self.write(label, raw)
        result = audit_pair(image, label)
        self.assertFalse(result['checks']['raw_class_codes_legal'])

    def test_quality_exclusion_must_zero_label(self):
        image, label, _ = self.pair()
        quality = self.root / 'quality.tif'
        self.write(quality, np.zeros((4, 4), dtype='uint8'))
        result = audit_pair(image, label, quality)
        self.assertFalse(result['checks']['quality_excluded_label_zero'])
        self.assertEqual(result['status'], 'fail')

    def test_mapping_merges_are_explicit(self):
        original = np.array([0, *WORLD_COVER_MAPPING], dtype='uint8')
        self.assertEqual(independent_map(original).tolist(), [255, 1, 5, 2, 4, 6, 7, 8, 0, 3, 1, 2])
        self.assertEqual(counts(independent_map(original))['1'], 2)

    def test_npz_corruption_detected_even_if_class_histogram_equal(self):
        image, label, raw = self.pair()
        expected = independent_map(raw)
        scaled = np.full((3, 4, 4), 0.01, dtype='float32')
        scaled[:, 0, 0] = 0
        # 클라스 수는 같지만 위치가 뒤바뀐 오류를 만든다.
        corrupted = expected.copy()
        corrupted[0, 0], corrupted[0, 1] = corrupted[0, 1], corrupted[0, 0]
        np.savez(self.root / '0_0_0.npz', label=corrupted, image=scaled)
        manifest = {'patch_size': 4, 'bands': [1, 2, 3], 'scale': .0001, 'offset': 0,
                    'patches': [{'path': '0_0_0.npz', 'group': 'independent', 'split': 'test'}],
                    'provenance': [{'image_path': 'image.tif', 'label_path': 'label.tif', 'label_source': 'worldcover',
                                    'image_sha256': digest(image), 'label_sha256': digest(label)}]}
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        result = audit_manifest(path, self.root)
        self.assertEqual(result['status'], 'fail')
        patch = result['patches'][0]
        self.assertTrue(patch['class_counts_equal'])
        self.assertEqual(patch['label_pixel_mismatch'], 2)

    def test_current_backend_mapping_matches_independent_table(self):
        source = Path(__file__).resolve().parents[1] / 'backend/app/ml/dataset.py'
        self.assertEqual(backend_mapping(source), WORLD_COVER_MAPPING)
        self.assertEqual(backend_esri_mapping(source.with_name('raster.py')), ESRI_MAPPING)

    def source_case(self):
        image, label = self.root / 'image.tif', self.root / 'label.tif'
        quality = self.root / 'quality.tif'
        raw = self.root / 'raw-worldcover.tif'
        scl = self.root / 'raw-SCL.tif'
        coarse_transform = from_origin(500000, 9300000, 20, 20)
        self.write(image, np.full((6, 4, 4), 100, dtype='uint16'))
        raw_values = np.array([[10, 40], [80, 95]], dtype='uint8')
        self.write(raw, raw_values, coarse_transform)
        self.write(scl, np.array([[9, 4], [6, 4]], dtype='uint8'), coarse_transform)
        valid = np.ones((4, 4), dtype='uint8')
        valid[:2, :2] = 0
        self.write(quality, valid)
        expected = raw_values.repeat(2, axis=0).repeat(2, axis=1)
        expected[valid == 0] = 0
        self.write(label, expected)
        archive = {path.name: {'path': str(path), 'sha256': digest(path), 'resampling_applied': False,
                               'transform': list(coarse_transform)} for path in (raw, scl)}
        return image, label, quality, archive, expected

    def test_archived_nearest_reprojection_and_scl_quality_exact(self):
        image, label, quality, archive, _ = self.source_case()
        result = audit_source_reprojection(image, label, quality, archive, self.root)
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['raw_source_pixel_reprojection_reproduced'])
        self.assertEqual(result['pixel_mismatch'], 0)
        self.assertEqual(result['quality_reconstruction']['status'], 'pass')
        self.assertEqual(audit_pair(image, label, quality, expected_bands=6)['status'], 'pass')

    def test_source_reproduction_detects_legal_but_wrong_final_pixel(self):
        image, label, quality, archive, expected = self.source_case()
        expected[3, 3] = 40
        self.write(label, expected)
        result = audit_source_reprojection(image, label, quality, archive, self.root)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['pixel_mismatch'], 1)

    def test_saved_quality_corruption_detected_against_raw_scl(self):
        image, label, quality, archive, expected = self.source_case()
        corrupted = np.ones((4, 4), dtype='uint8')
        self.write(quality, corrupted)
        # 최종 라벨까지 같은 잘못된 마스크에 맞추어도 원본 SCL 재현이 오류를 찾는다.
        expected[:2, :2] = 10
        self.write(label, expected)
        result = audit_source_reprojection(image, label, quality, archive, self.root)
        self.assertEqual(result['pixel_mismatch'], 0)
        self.assertEqual(result['quality_reconstruction']['status'], 'fail')
        self.assertEqual(result['status'], 'fail')

    def test_archive_hash_mismatch_prevents_source_verification(self):
        image, label, quality, archive, _ = self.source_case()
        archive['raw-worldcover.tif']['sha256'] = '0' * 64
        result = audit_source_reprojection(image, label, quality, archive, self.root)
        self.assertEqual(result['status'], 'fail')
        self.assertFalse(result['raw_source_pixel_reprojection_reproduced'])

    def test_old_crop_missing_remains_unverified(self):
        image, label, _ = self.pair()
        result = audit_source_reprojection(image, label, None, {}, self.root)
        self.assertEqual(result['status'], 'unverified')
        self.assertFalse(result['raw_source_pixel_reprojection_reproduced'])

    def test_patch_offset_inside_larger_raw_window_reprojects_exactly(self):
        image, label, quality, archive, _ = self.source_case()
        # 실제 수집의 큰 원본 창→작은 패치처럼 원점을 이동해 전체 창의 우하단을 선택한다.
        full = np.full((8, 8), 10, dtype='uint8')
        full[4:, 4:] = 40
        full_scl = np.full((8, 8), 4, dtype='uint8')
        for name, values in [('raw-worldcover.tif', full), ('raw-SCL.tif', full_scl)]:
            self.write(self.root / name, values)
            archive[name].update(sha256=digest(self.root / name), transform=list(self.transform))
        offset = from_origin(500040, 9299960, 10, 10)
        self.write(image, np.full((6, 4, 4), 100, dtype='uint16'), offset)
        self.write(label, np.full((4, 4), 40, dtype='uint8'), offset)
        self.write(quality, np.ones((4, 4), dtype='uint8'), offset)
        result = audit_source_reprojection(image, label, quality, archive, self.root)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['pixel_mismatch'], 0)

    def test_other_label_source_is_explicitly_unverified(self):
        path = self.root / 'annual-window-report.json'
        path.write_text(json.dumps({'scenes': [{'aoi': 'sample', 'year': 2020,
            'image_path': 'image.tif', 'label_path': 'other.tif', 'label_source': 'unknown_source',
            'source_window': {'width': 1024}, 'window_in_source': {'col_off': 256}}]}), encoding='utf-8')
        row = audit_reports([path], self.root)[0]
        self.assertEqual(row['status'], 'unverified')
        self.assertEqual(row['window_in_source'], {'col_off': 256})

    def test_esri_cloud10_ignored_water1_preserved_and_mapping_independent(self):
        image, label, quality, archive, _ = self.source_case()
        raw = self.root / 'raw-esri_io.tif'
        raw_values = np.array([[10, 1], [11, 2]], dtype='uint8')
        self.write(raw, raw_values, from_origin(500000, 9300000, 20, 20))
        archive[raw.name] = {**archive.pop('raw-worldcover.tif'), 'path': str(raw), 'sha256': digest(raw)}
        expected = raw_values.repeat(2, axis=0).repeat(2, axis=1)
        expected[expected == 10] = 0
        self.write(label, expected)
        result = audit_source_reprojection(image, label, quality, archive, self.root, 'esri_io')
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(independent_map(np.array([0, 1, 2, 4, 5, 7, 8, 9, 10, 11]), 'esri_io').tolist(),
                         [255, 0, 1, 3, 4, 6, 7, 8, 255, 2])
        self.assertEqual(audit_pair(image, label, quality, 6, 'esri_io')['status'], 'pass')

    def test_hash_cache_invalidates_changed_file(self):
        path = self.root / 'hash.txt'
        path.write_text('first', encoding='utf-8')
        before = digest(path)
        self.assertEqual(before, digest(path))
        path.write_text('different-length', encoding='utf-8')
        self.assertNotEqual(before, digest(path))

    def test_spatial_patch_quality_reconstructs_polygon_and_label_cloud(self):
        image, label, quality, archive, _ = self.source_case()
        raw = self.root / 'raw-esri_io.tif'
        # SCL은 모두 맑지만 원본 라벨 구름과 주경계 밖은 패치 품질에서 제외된다.
        raw_values = np.array([[10, 1], [11, 2]], dtype='uint8')
        self.write(raw, raw_values, from_origin(500000, 9300000, 20, 20))
        archive[raw.name] = {**archive.pop('raw-worldcover.tif'), 'path': str(raw), 'sha256': digest(raw)}
        self.write(self.root / 'raw-SCL.tif', np.full((2, 2), 4, dtype='uint8'), from_origin(500000, 9300000, 20, 20))
        archive['raw-SCL.tif']['sha256'] = digest(self.root / 'raw-SCL.tif')
        valid = np.ones((4, 4), dtype='uint8'); valid[:2, :2] = 0; valid[:, 3] = 0
        self.write(quality, valid)
        expected = raw_values.repeat(2, axis=0).repeat(2, axis=1); expected[valid == 0] = 0
        self.write(label, expected)
        polygon = {'type': 'Polygon', 'coordinates': [[[500000, 9299960], [500030, 9299960],
            [500030, 9300000], [500000, 9300000], [500000, 9299960]]]}
        geographic = transform_geom('EPSG:32748', 'EPSG:4326', polygon)
        result = audit_source_reprojection(image, label, quality, archive, self.root, 'esri_io', geographic, True)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['quality_reconstruction']['pixel_mismatch'], 0)

    def test_later_year_without_same_year_label_is_missing_not_verified(self):
        path = self.root / 'annual-window-report.json'
        path.write_text(json.dumps({'scenes': [{'aoi': 'example', 'year': '2023', 'status': 'rgb_window_downloaded',
                                               'image_path': 'image.tif', 'label_status': 'reference_planned'}]}), encoding='utf-8')
        result = audit_reports([path], self.root)
        self.assertEqual(result[0]['status'], 'missing')
        self.assertNotIn('source_reconstruction', result[0])
        self.assertIn('같은 연차 참조 없음', result[0]['reference_note'])


if __name__ == '__main__':
    unittest.main()
