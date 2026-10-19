"""Unit tests verifying LCLUC CODEX data pipeline inventory, class definitions, and file integrity."""
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
FIRST_GROUP_6 = {'banten', 'west_java', 'east_java', 'south_sulawesi', 'gorontalo', 'southeast_sulawesi'}
WORLDCOVER_CODES = {0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}
ESRI_CODES = {0, 1, 2, 4, 5, 7, 8, 9, 11}


def compute_sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


class TestLCLUCClassDefinitions(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / 'data/lcluc_class_definitions_v1.0.json'
        self.assertTrue(self.path.exists(), f"Missing {self.path}")
        self.data = json.loads(self.path.read_text(encoding='utf-8'))

    def test_schema_and_legend_version(self):
        self.assertEqual(self.data.get('schema_version'), '1.0')
        self.assertEqual(self.data.get('legend_version'), '1.0')

    def test_nine_classes_specification(self):
        classes = self.data.get('classes', [])
        self.assertEqual(len(classes), 9)
        expected_keys = [
            'water', 'trees', 'grass', 'flooded_vegetation',
            'crops', 'shrub_and_scrub', 'built_area', 'bare_ground', 'snow_and_ice'
        ]
        for idx, item in enumerate(classes):
            self.assertEqual(item['class_id'], idx)
            self.assertEqual(item['key'], expected_keys[idx])
            self.assertTrue(bool(item['name_ko']))
            self.assertTrue(bool(item['name_en']))
            self.assertTrue(bool(item['definition']))
            self.assertTrue(item['color'].startswith('#'))
            self.assertEqual(item['legend_version'], '1.0')
            self.assertEqual(item['nodata_code'], 255)

    def test_nodata_definition(self):
        nodata = self.data.get('nodata')
        self.assertIsNotNone(nodata)
        self.assertEqual(nodata['value_uint8'], 255)
        self.assertTrue(nodata['transparent'])

    def test_crosswalk_mappings_and_limitations(self):
        crosswalks = self.data.get('crosswalks', {})
        self.assertIn('esa_worldcover_10m', crosswalks)
        self.assertIn('esri_io_10m', crosswalks)

        wc = crosswalks['esa_worldcover_10m']
        wc_codes = {m['source_code'] for m in wc['mappings']}
        self.assertEqual(wc_codes, {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100})
        self.assertTrue(len(wc['limitations']) >= 3)

        esri = crosswalks['esri_io_10m']
        esri_codes = {m['source_code'] for m in esri['mappings']}
        self.assertEqual(esri_codes, {1, 2, 4, 5, 7, 8, 9, 11})
        self.assertTrue(len(esri['limitations']) >= 2)


class TestLCLUCDataInventory(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / 'docs/lcluc-map/annual-data-inventory.json'
        self.assertTrue(self.path.exists(), f"Missing {self.path}")
        self.data = json.loads(self.path.read_text(encoding='utf-8'))

    def test_scope_and_rejected_provinces(self):
        scope_provinces = set(self.data['scope']['first_group_6_provinces'])
        self.assertEqual(scope_provinces, FIRST_GROUP_6)

        rejected = self.data.get('rejected_entries', [])
        rejected_ids = [r['scene_id'] for r in rejected]
        self.assertIn('central_java_candidate-2021', rejected_ids)

    def test_first_group_2021_files_exist_and_hashes_match(self):
        fg2021 = self.data['datasets']['first_group_2021_worldcover']
        self.assertEqual(fg2021['total_scenes'], 6)
        scenes = fg2021['scenes']
        self.assertEqual(len(scenes), 6)

        provinces_found = set()
        for scene in scenes:
            prov = scene['province']
            provinces_found.add(prov)
            self.assertIn(prov, FIRST_GROUP_6)
            self.assertEqual(scene['year'], 2021)

            for role, finfo in scene['files'].items():
                p = ROOT / finfo['relative_path']
                self.assertTrue(p.exists(), f"File does not exist: {p}")
                self.assertEqual(p.stat().st_size, finfo['bytes'])
                actual_sha = compute_sha256(p)
                self.assertEqual(actual_sha, finfo['sha256'], f"SHA mismatch on {p}")
                self.assertEqual(finfo['width'], 256)
                self.assertEqual(finfo['height'], 256)
                self.assertIsNotNone(finfo['crs'])
                self.assertEqual(len(finfo['bounds_native']), 4)
                self.assertEqual(len(finfo['bounds_wgs84']), 4)

                # If label, verify class values are valid WorldCover codes
                if role == 'label-worldcover':
                    self.assertTrue(set(finfo['unique_values']).issubset(WORLDCOVER_CODES),
                                    f"Invalid class values in {p}: {finfo['unique_values']}")

        self.assertEqual(provinces_found, FIRST_GROUP_6)

    def test_baseline_2021_candidates_files_exist(self):
        base2021 = self.data['datasets']['baseline_2021_candidates']
        self.assertEqual(base2021['total_scenes'], 2)
        for scene in base2021['scenes']:
            self.assertIn(scene['province'], FIRST_GROUP_6)
            for role, finfo in scene['files'].items():
                p = ROOT / finfo['relative_path']
                self.assertTrue(p.exists(), f"File does not exist: {p}")
                self.assertEqual(p.stat().st_size, finfo['bytes'])
                self.assertEqual(compute_sha256(p), finfo['sha256'])

    def test_esri_v1_training_patches_inventory(self):
        esri_ds = self.data['datasets']['first_group_training_esri_v1']
        self.assertEqual(esri_ds['total_patches'], 1779)
        patches_by_year = esri_ds['patches_by_year_and_province']
        self.assertEqual(set(map(int, patches_by_year.keys())), {2020, 2021, 2022, 2023, 2024, 2025})

        samples = esri_ds['representative_sampled_patches']
        self.assertTrue(len(samples) >= 30)

        for s in samples:
            self.assertIn(s['province'], FIRST_GROUP_6)
            for role, finfo in s['files'].items():
                p = ROOT / finfo['relative_path']
                self.assertTrue(p.exists(), f"Sample file does not exist: {p}")
                self.assertEqual(p.stat().st_size, finfo['bytes'])
                self.assertEqual(compute_sha256(p), finfo['sha256'])
                self.assertEqual(finfo['width'], 256)
                self.assertEqual(finfo['height'], 256)

                if role == 'label':
                    self.assertTrue(set(finfo['unique_values']).issubset(ESRI_CODES),
                                    f"Invalid Esri class values in {p}: {finfo['unique_values']}")


class TestAuditDocumentation(unittest.TestCase):
    def test_audit_doc_exists_and_contains_key_sections(self):
        doc_path = ROOT / 'docs/lcluc-map/current-state-audit.md'
        self.assertTrue(doc_path.exists(), f"Missing {doc_path}")
        text = doc_path.read_text(encoding='utf-8')
        self.assertIn('First Group 6개 대상 주', text)
        self.assertIn('Central Java', text)
        self.assertIn('VERIFIED_REAL', text)
        self.assertIn('NoData', text)
        self.assertIn('Nearest Neighbor', text)
        self.assertIn('data/first-group-training-esri-v1', text)


if __name__ == '__main__':
    unittest.main()
