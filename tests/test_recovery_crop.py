"""Synthetic crop metadata provenance and safety checks, no raster files required."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.app.data import recovery_crop as module

ROOT = Path(__file__).resolve().parents[1]


class RecoveryCropTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.source = self.output / 'sources/batch-a/annual-window-report.json'
        self.source.parent.mkdir(parents=True)
        self.aggregate_path = self.output / 'annual-window-report.json'
        self.image = self.source.parent / 'raw/image.tif'
        self.report = {'scenes': [{'status': 'rgb_window_downloaded', 'image_path': str(self.image), 'scene_id': 'scene-a', 'year': '2023', 'province': 'banten', 'aoi': 'banten-grid'}]}
        self.aggregate = {'source_manifests': [str(self.source)], 'scenes': [
            {'scene_id': 'scene-a', 'source_window': {'path': str(self.image)}, 'year': '2023', 'province': 'banten', 'aoi': 'banten', 'window_in_source': [0, 0, 256, 256]},
            {'scene_id': 'scene-a', 'source_window': {'path': str(self.image)}, 'year': '2023', 'province': 'banten', 'window_in_source': [256, 0, 256, 256]}]}
        self.save()

    def tearDown(self): self.temp.cleanup()

    def save(self):
        self.source.write_text(json.dumps(self.report), encoding='utf-8')
        self.aggregate_path.write_text(json.dumps(self.aggregate), encoding='utf-8')

    def inspect(self): return module.inspect_recovery_crop(self.root)

    def codes(self): return {issue['code'] for issue in self.inspect()['issues']}

    def test_distinct_crops_same_source_valid_metadata_with_exact_typed_year_province(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.inspect()
        self.assertEqual(result['metadata_consistency'], 'CONSISTENT_METADATA')
        self.assertEqual(result['scene_checks'][0]['year_binding'], 'EXACT_TYPED_MATCH')
        self.assertEqual(result['scene_checks'][0]['province_binding'], 'EXACT_TYPED_MATCH')
        self.assertEqual(result['duplicate_source_crops'], [])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['exactly_once_applied'], 'UNKNOWN')
        self.assertEqual(result['raster_files_read'], 0)
        for key in ['settlement_authorized', 'execution_authorized', 'automatic_resume_allowed', 'ready_for_training', 'training_executed', 'scientific_accuracy_validated', 'raster_bounds_checked', 'geometric_overlap_checked', 'different_file_same_sha_checked']:
            self.assertIs(result[key], False)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_same_source_scene_and_coordinates_detected_even_with_alias_path(self):
        self.aggregate['scenes'][1]['window_in_source'] = [0, 0, 256, 256]
        self.aggregate['scenes'][1]['source_window']['path'] = str(self.image.parent / '../raw/image.tif')
        self.save()
        self.assertIn('DUPLICATE_SOURCE_CROP', self.codes())
        self.assertEqual(self.inspect()['duplicate_source_crops'][0]['scene_indexes'], [0, 1])

    def test_crop_requires_exact_int_nonnegative_grid_and_256_extent(self):
        for crop in [[False, 0, 256, 256], [0.0, 0, 256, 256], [-256, 0, 256, 256], [1, 0, 256, 256], [0, 0, 255, 256], [0, 0, True, 256], [0, 0, 256], '0,0,256,256', None]:
            self.aggregate['scenes'][0]['window_in_source'] = crop
            self.save()
            with self.subTest(crop=crop): self.assertIn('CROP_COORDINATES_INVALID', self.codes())

    def test_year_and_province_mismatch_and_type_mismatch_are_detected(self):
        for field, value, code in [('year', '2022', 'YEAR_BINDING_MISMATCH'), ('year', 2023, 'YEAR_BINDING_MISMATCH'), ('year', True, 'YEAR_FIELD_INVALID'), ('year', 2023.0, 'YEAR_FIELD_INVALID'), ('province', 'west_java', 'PROVINCE_BINDING_MISMATCH'), ('province', False, 'PROVINCE_FIELD_INVALID')]:
            self.aggregate['scenes'][0] = copy.deepcopy(self.aggregate['scenes'][1])
            self.aggregate['scenes'][0]['window_in_source'] = [0, 0, 256, 256]
            self.aggregate['scenes'][0][field] = value
            self.save()
            with self.subTest(field=field, value=value): self.assertIn(code, self.codes())

    def test_equal_but_out_of_contract_years_are_invalid_without_coercing_rows(self):
        for value in [-1, 0, 99999, 2014, 2027, '1900', '2027', ' 2023', '２０２３']:
            self.report['scenes'][0]['year'] = value
            for row in self.aggregate['scenes']: row['year'] = value
            self.save()
            with self.subTest(value=value):
                self.assertIn('YEAR_FIELD_INVALID', self.codes())
                self.assertEqual(self.inspect()['scene_checks'][0]['year_binding'], 'INVALID')

    def test_whitespace_only_province_is_invalid_and_values_are_not_normalized(self):
        self.report['scenes'][0]['province'] = '   '
        for row in self.aggregate['scenes']: row['province'] = '   '
        self.save()
        self.assertIn('PROVINCE_FIELD_INVALID', self.codes())
        self.report['scenes'][0]['province'] = 'banten'
        self.aggregate['scenes'][0]['province'] = ' banten'
        self.save()
        self.assertIn('PROVINCE_BINDING_MISMATCH', self.codes())

    def test_matching_integer_year_is_valid_and_missing_fields_remain_unknown(self):
        self.report['scenes'][0]['year'] = 2023
        for row in self.aggregate['scenes']: row['year'] = 2023
        self.save()
        self.assertEqual(self.inspect()['scene_checks'][0]['year_binding'], 'EXACT_TYPED_MATCH')
        self.report['scenes'][0].pop('province'); self.save()
        result = self.inspect()['scene_checks'][0]
        self.assertEqual(result['province_binding'], 'UNKNOWN')
        self.assertIn('PROVINCE_BINDING_UNKNOWN_MISSING', self.codes())

    def test_missing_and_ambiguous_source_rows_never_invent_context_match(self):
        self.aggregate['scenes'][0]['scene_id'] = 'absent'; self.save()
        self.assertEqual(self.inspect()['scene_checks'][0]['source_link'], 'MISSING_MATCH')
        self.report['scenes'].append(copy.deepcopy(self.report['scenes'][0])); self.save()
        self.assertEqual(self.inspect()['scene_checks'][1]['source_link'], 'AMBIGUOUS_MATCH')
        self.assertEqual(self.inspect()['scene_checks'][1]['year_binding'], 'UNKNOWN')

    def test_duplicate_reference_does_not_invent_ambiguous_row_and_empty_report_is_normal(self):
        self.aggregate['source_manifests'].append(str(self.source)); self.save()
        self.assertEqual(self.inspect()['scene_checks'][0]['source_link'], 'UNIQUE_METADATA_MATCH')
        self.report['scenes'] = [{'status': 'failed'}]
        self.aggregate['scenes'] = []; self.save()
        self.assertEqual(self.inspect()['metadata_consistency'], 'CONSISTENT_METADATA')

    def test_strict_json_invalid_source_and_missing_report_are_diagnosed(self):
        for raw in ['{"scenes":[],"scenes":[]}', '{"x":NaN}', '{"x":1e999}', '[]']:
            self.source.write_text(raw, encoding='utf-8')
            self.assertIn('SOURCE_REPORT_MISSING_OR_INVALID', self.codes())
        self.source.unlink()
        self.assertIn('SOURCE_REPORT_MISSING_OR_INVALID', self.codes())

    def test_root_escape_remote_and_wrong_type_scene_are_safe(self):
        self.aggregate['scenes'][0]['source_window']['path'] = str(self.workspace / 'outside.tif'); self.save()
        with self.assertRaises(ValueError): self.inspect()
        self.aggregate['scenes'][0]['source_window']['path'] = '//server/share/image.tif'; self.save()
        with self.assertRaises(ValueError): self.inspect()
        self.aggregate['scenes'] = [False]; self.save()
        self.assertIn('AGGREGATE_SCENE_INVALID', self.codes())

    def test_input_change_and_missing_appearing_are_rejected(self):
        real = module._fingerprint
        calls = 0
        def changing(path):
            nonlocal calls
            if path == self.source:
                calls += 1
                if calls == 2: self.source.write_text('{}', encoding='utf-8')
            return real(path)
        with patch.object(module, '_fingerprint', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.source.unlink()
        calls = 0
        with patch.object(module, '_fingerprint', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_logical_alias_retarget_rejected_without_symlink_privilege(self):
        real = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.aggregate_path:
                calls += 1
                if calls == 2: return self.output / 'other.json'
            return real(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'target changed'): self.inspect()

    def test_cli_cp949_stdout_utf8_evidence_and_output_restrictions(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_crop.py'), '--data-root', str(self.root), *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'report.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'BLOCKED')
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(before, output.read_bytes())
        self.assertEqual(cli('--output', self.aggregate_path).returncode, 1)
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / 'no.json'
            self.assertEqual(cli('--output', path).returncode, 1)
            self.assertFalse(path.exists())
        self.aggregate_path.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
