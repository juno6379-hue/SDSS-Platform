import unittest
import tempfile
import json
import hashlib
from pathlib import Path
from app.collection_priority_status import collection_targets, candidate_quality, bare_target_review, PROVINCES
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


class BareTargetReviewTests(unittest.TestCase):
    def publish(self, root, edit=None):
        folder = root / 'first-group-training-priority'
        folder.mkdir(exist_ok=True)
        summary = {'schema_version': 1, 'status': 'LOCAL_TARGET_REVIEW_FINISHED',
            'recorded_at': '2026-10-18T12:00:00+09:00', 'current_manifest_sha256': 'a' * 64,
            'execution_supported': False, 'actual_quality_verified': False, 'scientific_accuracy_validated': False,
            'candidate_total': 12, 'summary_by_province': [{'province': p, 'candidates': 2, 'support_clear': 1, 'overlap': 1, 'local_invalid': 0} for p in PROVINCES]}
        report = {'ui_summary': summary}
        if edit:
            edit(report)
        target = folder / 'review.json'
        target.write_text(json.dumps(report), encoding='utf-8')
        receipt = {'schema_version': 1, 'report': {'path': 'first-group-training-priority/review.json', 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}}
        pointer = folder / 'latest-bare-review.json'
        pointer.write_text(json.dumps(receipt), encoding='utf-8')
        return pointer, target, receipt

    def test_pinned_local_review_is_not_remote_quality_and_stale_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publish(root)
            result = bare_target_review(root, 'b' * 64)
            self.assertTrue(result['available'])
            self.assertFalse(result['source_matches_current_manifest'])
            self.assertFalse(result['actual_quality_verified'])
            self.assertEqual(result['candidate_total'], 12)
            self.assertTrue(bare_target_review(root, 'a' * 64)['source_matches_current_manifest'])
            policy = collection_targets({'scenes': [row()]}, 'a' * 64, result)
            self.assertEqual(policy['balance_policy']['priority_provinces'], ['southeast_sulawesi', 'gorontalo'])
            self.assertTrue(policy['balance_policy']['minimum_floor_not_equal_quota'])
            self.assertEqual(policy['bare_target_review'], result)

    def test_searched_scope_defaults_and_restricted_scope_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publish(root)
            self.assertEqual(bare_target_review(root, 'a' * 64)['searched_provinces'], list(PROVINCES))
            def restricted(report):
                summary = report['ui_summary']
                summary['searched_provinces'] = ['gorontalo', 'west_java']
                for item in summary['summary_by_province']:
                    if item['province'] not in summary['searched_provinces']:
                        item.update(candidates=0, support_clear=0, overlap=0)
                summary['candidate_total'] = 4
            self.publish(root, restricted)
            result = bare_target_review(root, 'a' * 64)
            self.assertTrue(result['available'])
            self.assertEqual(result['searched_provinces'], ['gorontalo', 'west_java'])
            self.assertEqual(result['candidate_total'], 4)
            for field in ('execution_supported', 'actual_quality_verified', 'scientific_accuracy_validated'):
                self.assertIs(result[field], False)

    def test_invalid_scope_and_outside_candidates_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for scope in ([], ['gorontalo', 'gorontalo'], ['unknown'], [''], None, 'gorontalo', [True], [['gorontalo']]):
                with self.subTest(scope=scope):
                    self.publish(root, lambda r: r['ui_summary'].update(searched_provinces=scope))
                    self.assertFalse(bare_target_review(root, 'a' * 64)['available'])
            self.publish(root, lambda r: r['ui_summary'].update(searched_provinces=['gorontalo', 'west_java']))
            self.assertFalse(bare_target_review(root, 'a' * 64)['available'])

    def test_absence_invalid_receipt_hash_path_and_size_do_not_become_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(bare_target_review(root, 'a' * 64), {'available': False, 'status': 'NOT_PUBLISHED'})
            for bad in ['../outside.json', '/outside.json', 'data:private.json', 'first-group-training-priority/../review.json', 'first-group-training-priority\\review.json']:
                pointer, target, receipt = self.publish(root)
                receipt['report']['path'] = bad
                pointer.write_text(json.dumps(receipt), encoding='utf-8')
                self.assertFalse(bare_target_review(root, 'a' * 64)['available'])
            pointer, target, receipt = self.publish(root)
            target.write_text('{}', encoding='utf-8')
            self.assertFalse(bare_target_review(root, 'a' * 64)['available'])
            pointer.write_bytes(b' ' * 65537)
            self.assertEqual(bare_target_review(root, None)['status'], 'INVALID_RECEIPT')
            pointer, target, receipt = self.publish(root)
            target.write_bytes(b' ' * (2 * 1024 * 1024 + 1))
            self.assertFalse(bare_target_review(root, None)['available'])

    def test_linked_receipt_and_report_are_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publish(root)
            with patch.object(Path, 'is_symlink', return_value=True):
                self.assertEqual(bare_target_review(root, 'a' * 64)['status'], 'INVALID_RECEIPT')
            original = Path.is_symlink
            def report_link(path):
                return path.name == 'review.json' or original(path)
            with patch.object(Path, 'is_symlink', report_link):
                self.assertEqual(bare_target_review(root, 'a' * 64)['status'], 'INVALID_OR_BLOCKED_REPORT')

    def test_partial_and_contaminated_review_blocks_whole_summary(self):
        changes = [lambda r: r.pop('ui_summary'), lambda r: r['ui_summary'].update(execution_supported=True),
            lambda r: r['ui_summary'].update(actual_quality_verified=True),
            lambda r: r['ui_summary'].update(status='REVIEW_BLOCKED'),
            lambda r: r['ui_summary'].update(recorded_at='2026-10-18'),
            lambda r: r['ui_summary'].update(candidate_total=13),
            lambda r: r['ui_summary']['summary_by_province'].pop(),
            lambda r: r['ui_summary']['summary_by_province'][0].update(support_clear=True),
            lambda r: r['ui_summary']['summary_by_province'][0].update(candidates=3),
            lambda r: r['ui_summary']['summary_by_province'][0].update(province='unknown'),
            lambda r: r['ui_summary']['summary_by_province'][1].update(province=PROVINCES[0])]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for change in changes:
                with self.subTest(change=change):
                    self.publish(root, change)
                    result = bare_target_review(root, 'a' * 64)
                    self.assertFalse(result['available'])
                    self.assertNotIn('candidate_total', result)


if __name__ == '__main__':
    unittest.main()
