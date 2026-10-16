"""수집 실패가 기존 성공 재고를 숨기지 않는지 확인한다."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from app.collection_status import collection_status


class CollectionStatusTests(unittest.TestCase):
    def write(self, root, relative, value):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_empty_inventory_is_unknown_and_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collection_status(Path(directory))
            self.assertEqual(len(result['cells']), 36)
            self.assertEqual(result['summary']['available_image_cells'], 0)
            self.assertFalse(result['summary']['learning_ready'])
            self.assertIsNone(result['latest_run'])
            self.assertTrue(all(row['collection_status'] == 'unknown' for row in result['cells']))

    def test_later_failure_does_not_overwrite_success_and_hides_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'image.tif').write_bytes(b'actual fixture')
            (root / 'label.tif').write_bytes(b'label fixture')
            self.write(root, 'first-group-2021/annual-window-report.json', {'scenes': [
                {'aoi': 'banten', 'year': '2021', 'status': 'rgb_window_downloaded',
                 'image_path': 'image.tif', 'label_path': 'label.tif', 'bands': ['B02', 'B03', 'B04']}]})
            failure = self.write(root, 'first-group-annual/chunk-01/annual-window-report.json', {'scenes': [
                {'aoi': 'banten', 'year': '2021', 'status': 'rate_limited',
                 'error': {'http_status': 429, 'category': 'http', 'sanitized_message': 'sensitive fixture'}}]})
            self.write(root, 'first-group-annual/run-result.json', {'status': 'finished', 'manifests': [str(failure)],
                'reserved_or_transferred_bytes_including_prior': 100, 'maximum_total_bytes': 200})
            result = collection_status(root)
            row = next(row for row in result['cells'] if row['province'] == 'banten' and row['year'] == 2021)
            self.assertTrue(row['image_available'])
            self.assertTrue(row['label_available'])
            self.assertEqual(row['latest_attempt_status'], 'rate_limited')
            self.assertEqual(row['collection_status'], 'rgb_window_downloaded')
            self.assertEqual(result['latest_run']['rate_limited_cells'], 1)
            self.assertNotIn('sensitive fixture', json.dumps(result))

    def test_external_paths_and_missing_files_are_not_available(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            outside = Path(external) / 'image.tif'
            outside.write_bytes(b'outside')
            self.write(root, 'first-group-test/annual-window-report.json', {'scenes': [
                {'aoi': 'west_java', 'year': 2021, 'image_path': str(outside), 'label_path': 'missing.tif'}]})
            result = collection_status(root)
            self.assertEqual(result['summary']['available_image_cells'], 0)

    def test_quality_requires_matching_audit_report_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'image.tif').write_bytes(b'fixture')
            report = self.write(root, 'first-group-2021/annual-window-report.json', {'scenes': [
                {'aoi': 'east_java', 'year': 2021, 'image_path': 'image.tif'}]})
            audit = {'inputs': [{'path': str(report), 'sha256': hashlib.sha256(report.read_bytes()).hexdigest()}],
                     'inventory': [{'province': 'east_java', 'year': 2021, 'manifest_path': str(report), 'eligible_patch_count': 1, 'label_year': 2021}]}
            self.write(root, 'first-group/quality-audit-2021.json', audit)
            self.assertEqual(collection_status(root)['summary']['quality_eligible_cells'], 1)
            report.write_text('{"scenes":[]}', encoding='utf-8')
            self.assertEqual(collection_status(root)['summary']['quality_eligible_cells'], 0)

    def test_incomplete_json_is_unknown_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'first-group-run/annual-window-report.json'
            path.parent.mkdir()
            path.write_text('{', encoding='utf-8')
            result = collection_status(root)
            self.assertEqual(result['summary']['available_image_cells'], 0)
            self.assertEqual(result['unreadable_reports'], ['annual-window-report.json'])

    def test_ready_report_becomes_stale_when_input_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / 'manifest.json'
            manifest.write_text('{}', encoding='utf-8')
            image = root / 'image.tif'
            image.write_bytes(b'original')
            entry = lambda path: {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            self.write(root, 'first-group/training-readiness.json', {'schema_version': 1,
                'status': 'ready_for_weak_label_experiment', 'ready_for_training': True,
                'input_manifests': [entry(manifest)], 'verified_files': [entry(image)]})
            self.assertTrue(collection_status(root)['summary']['learning_ready'])
            image.write_bytes(b'modified')
            result = collection_status(root)
            self.assertFalse(result['summary']['learning_ready'])
            self.assertEqual(result['training_readiness']['integrity_status'], 'stale_or_missing')

    def test_probe_rate_limit_does_not_invent_failed_scene_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'first-group-recovery32/run-result.json', {'status': 'stopped_rate_limit',
                'manifests': [], 'error': {'http_status': 429, 'category': 'http_response'}})
            run = collection_status(root)['latest_run']
            self.assertTrue(run['rate_limit_active'])
            self.assertEqual(run['rate_limited_cells'], 0)
            self.assertEqual(run['complete_windows'], 0)


if __name__ == '__main__':
    unittest.main()
