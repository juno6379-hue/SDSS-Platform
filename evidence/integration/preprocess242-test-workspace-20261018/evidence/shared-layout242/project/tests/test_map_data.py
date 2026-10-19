"""지도 표시의 좌표·잘림·빈 변화와 원본 면적 통계를 구분한다."""
import json
from pathlib import Path
import tempfile
import unittest
from app.map_data import map_data


class MapDataTests(unittest.TestCase):
    def test_empty_change_does_not_invent_bounds(self):
        result = map_data({'geometry': {'type': 'FeatureCollection', 'features': []}, 'changed_area_m2': 0}, Path('.'))
        self.assertIsNone(result['bbox'])
        self.assertEqual(result['feature_count'], 0)
        self.assertFalse(result['validation']['independent_accuracy_validated'])

    def test_wgs84_bounds_and_truncation_preserve_full_raster_statistics(self):
        feature = {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[106,-7],[107,-7],[107,-6],[106,-7]]]}, 'properties': {}}
        result = map_data({'geometry': {'type': 'FeatureCollection', 'features': [feature]}, 'vector_truncated': True, 'changed_area_m2': 1000000}, Path('.'))
        self.assertEqual(result['bbox'], [106,-7,107,-6])
        self.assertTrue(result['truncated'])
        self.assertEqual(result['changed_area_m2'], 1000000)

    def test_geojson_path_must_stay_inside_data_root(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            path = Path(other) / 'external.geojson'
            path.write_text(json.dumps({'type': 'FeatureCollection', 'features': []}), encoding='utf-8')
            with self.assertRaises(ValueError):
                map_data({'geojson_path': str(path)}, Path(directory))

    def test_projected_coordinates_are_not_treated_as_longitude(self):
        feature = {'geometry': {'type': 'Polygon', 'coordinates': [[[624160,9287010],[625160,9287010],[625160,9288010],[624160,9287010]]]}}
        with self.assertRaises(ValueError):
            map_data({'geometry': {'type': 'FeatureCollection', 'features': [feature]}}, Path('.'))
