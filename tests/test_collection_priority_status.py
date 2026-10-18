import unittest
import tempfile
import json
import hashlib
from pathlib import Path
from app.collection_priority_status import collection_targets, candidate_quality
from unittest.mock import patch
from app.collection_status import collection_status


def row(province='banten', year=2024, split='val', scene='same', eligible=True, bare=256):
    return dict(province=province, year=year, split=split, scene_id=scene,
                quality_status='quality_eligible' if eligible else 'quality_insufficient',
                sample_class_coverage={'8': bare, '2': 1024})


class CollectionPriorityStatusTests(unittest.TestCase):
    def test_stale_global_readiness_does_not_hash_its_obsolete_raster_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / 'first-group-training-esri-v1/annual-window-report.json'
            current.parent.mkdir()
            current.write_text('{"scenes": []}', encoding='utf-8')
            old = root / 'old.json'
            old.write_text('{}', encoding='utf-8')
            report = root / 'first-group/training-readiness.json'
            report.parent.mkdir()
            report.write_text(json.dumps({'input_manifests': [{'path': 'old.json', 'sha256': hashlib.sha256(old.read_bytes()).hexdigest()}],
                                          'verified_files': [{'path': 'old.json', 'sha256': hashlib.sha256(old.read_bytes()).hexdigest()}]}), encoding='utf-8')
            with patch('app.collection_status.same_hash', side_effect=AssertionError('obsolete raster hashing')):
                result = collection_status(root)
            self.assertFalse(result['training_readiness']['manifest_matches_current'])
            self.assertFalse(result['training_readiness']['evidence_matched'])
            self.assertFalse(result['summary']['learning_ready'])

    def test_candidate_receipt_requires_pinned_cohort_and_qa_agreement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'first-group-training-priority'
            folder.mkdir()
            contents = ['snapshot', 'candidate', json.dumps({'patch_counts_by_split': {'train': 2, 'val': 1, 'test': 1}, 'blockers': ['bare']})]
            files = []
            for index, text in enumerate(contents):
                path = root / f'input{index}.json'
                path.write_text(text, encoding='utf-8')
                files.append({'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            receipt = {'files': files, 'by_split': {'train': 2, 'val': 1, 'test': 1}, 'blocker_count': 1,
                       'source_manifest_sha256': files[0]['sha256'], 'recorded_at': 'test', 'scene_split_conflicts': []}
            pointer = folder / 'latest-candidate.json'
            pointer.write_text(json.dumps(receipt), encoding='utf-8')
            check = lambda p, h: hashlib.sha256(p.read_bytes()).hexdigest() == h
            result = candidate_quality(root, 'new-collection', check)
            self.assertTrue(result['available'])
            self.assertFalse(result['source_matches_current_manifest'])
            self.assertFalse(result['ready_for_training'])
            receipt['by_split']['train'] = 3
            pointer.write_text(json.dumps(receipt), encoding='utf-8')
            self.assertFalse(candidate_quality(root, None, check)['available'])
            receipt['by_split']['train'] = 2
            pointer.write_text(json.dumps(receipt), encoding='utf-8')
            (root / files[1]['path']).write_text('tamper', encoding='utf-8')
            self.assertFalse(candidate_quality(root, None, check)['available'])

    def test_counts_include_ineligible_only_in_physical_inventory(self):
        result = collection_targets({'scenes': [row(), row(eligible=False)]}, 'pinned')
        self.assertEqual((result['physical_total'], result['eligible_total'], result['ineligible_total']), (2, 1, 1))
        self.assertEqual(result['cell_gap_total'], 36 * 28 - 1)
        self.assertFalse(result['learning_ready'])
        self.assertFalse(result['native_raster_reverified'])

    def test_surplus_in_one_cell_does_not_cover_another_gap(self):
        result = collection_targets({'scenes': [row()] * 30}, 'pinned')
        self.assertEqual(result['cell_gap_total'], 35 * 28)
        self.assertEqual(result['eligible_target_gap'], 1170)

    def test_scene_conflict_and_bare_contribution_are_separate(self):
        result = collection_targets({'scenes': [row(bare=255), row('west_java', split='test')]}, 'pinned')
        quality = result['class_quality']
        self.assertEqual(quality['scene_split_conflicts'], ['same'])
        self.assertEqual(quality['bare_by_split']['val']['contributing_patches'], 0)
        self.assertEqual(quality['bare_by_split']['test']['contributing_patches'], 1)
        self.assertAlmostEqual(quality['bare_by_split']['val']['ratio'], 255 / 1279)

    def test_untrusted_or_missing_manifest_remains_unknown(self):
        for scenes in ([], [row(split='train')], [row(year=2026)], [dict(row(), sample_class_coverage={'8': float('nan')})]):
            with self.subTest(scenes=scenes):
                self.assertFalse(collection_targets({'scenes': scenes}, 'pin')['available'])
        self.assertFalse(collection_targets({'scenes': [row()]}, None)['available'])


if __name__ == '__main__':
    unittest.main()
