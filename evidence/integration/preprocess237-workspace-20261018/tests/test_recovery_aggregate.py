"""Synthetic aggregate reference/scene linkage, scope and read-only safety tests."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.app.data import recovery_aggregate as module

ROOT = Path(__file__).resolve().parents[1]


class AggregateRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.source = self.output / 'sources/batch-a/annual-window-report.json'
        self.source.parent.mkdir(parents=True)
        self.ledger_path = self.root / 'first-group-training-budget/global-ledger.json'
        self.ledger_path.parent.mkdir()
        self.aggregate_path = self.output / 'annual-window-report.json'
        self.raw_image = self.source.parent / 'window/image.tif'
        self.report = {'scenes': [{'status': 'rgb_window_downloaded', 'image_path': str(self.raw_image), 'scene_id': 'scene-a'}]}
        self.aggregate = {'source_manifests': [str(self.source)], 'scenes': [
            {'patch_id': 'batch-a-r0-c0', 'image_path': str(self.output / 'patches/batch-a/r00-c00/image.tif'), 'scene_id': 'scene-a', 'source_window': {'path': str(self.raw_image)}},
            {'patch_id': 'batch-a-r0-c1', 'image_path': str(self.output / 'patches/batch-a/r00-c01/image.tif'), 'scene_id': 'scene-a', 'source_window': {'path': str(self.raw_image)}}]}
        self.ledger = {'batches': {'batch-a': {'status': 'settled', 'report_path': str(self.source)}}}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        for path, doc in [(self.source, self.report), (self.aggregate_path, self.aggregate), (self.ledger_path, self.ledger)]:
            path.write_text(json.dumps(doc), encoding='utf-8')

    def inspect(self):
        return module.inspect_recovery_aggregate(self.root)

    def codes(self):
        return {item['code'] for item in self.inspect()['issues']}

    def test_two_patches_per_source_are_valid_metadata_but_never_exactly_once_proof(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = self.inspect()
        self.assertEqual(report['metadata_consistency'], 'CONSISTENT_METADATA')
        self.assertEqual([x['status'] for x in report['scene_source_links']], ['UNIQUE_METADATA_MATCH'] * 2)
        self.assertEqual(report['exactly_once_applied'], 'UNKNOWN')
        self.assertEqual(report['status'], 'BLOCKED')
        for key in ['settlement_authorized', 'execution_authorized', 'automatic_resume_allowed', 'source_file_hashes_verified', 'scene_year_province_checked', 'crop_window_identity_checked']:
            self.assertIs(report[key], False)
        self.assertEqual(report['raster_files_read'], 0)
        self.assertEqual(report['proposed_refund_bytes'], 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_canonical_duplicate_report_reference_detected_without_duplicate_match_invention(self):
        self.aggregate['source_manifests'].append(str(self.source.parent / '../batch-a/annual-window-report.json'))
        self.save()
        report = self.inspect()
        self.assertEqual(len(report['duplicate_source_references']), 1)
        self.assertEqual(report['scene_source_links'][0]['status'], 'UNIQUE_METADATA_MATCH')

    def test_missing_invalid_and_wrong_type_reference_diagnosed(self):
        self.aggregate['source_manifests'] += [False, str(self.source.parent / 'missing.json')]
        self.source.write_text('{"scenes":[],"scenes":[]}', encoding='utf-8')
        self.aggregate_path.write_text(json.dumps(self.aggregate), encoding='utf-8')
        self.assertTrue({'SOURCE_REFERENCE_INVALID', 'SOURCE_REPORT_INVALID', 'SOURCE_REPORT_MISSING'} <= self.codes())

    def test_nonfinite_duplicate_json_and_boolean_scene_container_invalid(self):
        for raw in ['{"scenes":NaN}', '{"x":1e999}', '{"scenes":true}', '{"scenes":[],"scenes":[]}']:
            self.source.write_text(raw, encoding='utf-8')
            self.assertTrue({'SOURCE_REPORT_INVALID', 'SOURCE_REPORT_SCENES_INVALID'} & self.codes())

    def test_other_experiment_ledger_does_not_produce_missing_reference_false_positive(self):
        other = self.root / 'different-experiment/sources/old/annual-window-report.json'
        self.ledger['batches']['old'] = {'status': 'settled', 'report_path': str(other)}
        self.save()
        report = self.inspect()
        self.assertEqual(report['metadata_consistency'], 'CONSISTENT_METADATA')
        self.assertEqual(report['ledger_report_reconciliation'][1]['scope'], 'OUT_OF_SCOPE')

    def test_settled_current_source_absent_from_refs_and_missing_file_are_separate(self):
        self.aggregate['source_manifests'] = []; self.save()
        self.assertIn('SETTLED_REPORT_NOT_REFERENCED', self.codes())
        self.source.unlink()
        self.assertIn('LEDGER_SOURCE_REPORT_MISSING', self.codes())

    def test_pending_report_reference_detected_with_or_without_ledger_report_path(self):
        self.ledger['batches']['batch-a']['status'] = 'pending'; self.save()
        self.assertIn('PENDING_BATCH_REPORT_REFERENCED', self.codes())
        del self.ledger['batches']['batch-a']['report_path']; self.save()
        self.assertIn('PENDING_BATCH_REPORT_REFERENCED', self.codes())

    def test_current_reference_without_ledger_binding_or_multiple_bindings_is_explicit(self):
        self.ledger['batches'] = {}; self.save()
        self.assertIn('SOURCE_REFERENCE_LEDGER_UNKNOWN', self.codes())
        self.ledger['batches'] = {'batch-a': {'status': 'settled', 'report_path': str(self.source)}, 'other-key': {'status': 'settled', 'report_path': str(self.source)}}
        self.save()
        self.assertIn('SOURCE_REFERENCE_LEDGER_AMBIGUOUS', self.codes())

    def test_current_scope_ledger_status_must_be_pending_or_settled(self):
        for status in [True, 1, 'complete', None]:
            self.ledger['batches']['batch-a']['status'] = status
            self.save()
            self.assertIn('LEDGER_BATCH_STATUS_INVALID', self.codes())
            self.assertEqual(self.inspect()['metadata_consistency'], 'ISSUES_FOUND')

    def test_duplicate_patch_id_and_canonical_image_path_detected(self):
        self.aggregate['scenes'][1]['patch_id'] = self.aggregate['scenes'][0]['patch_id']
        self.aggregate['scenes'][1]['image_path'] = str(self.output / 'patches/batch-a/r00-c00/../r00-c00/image.tif')
        self.save()
        self.assertTrue({'DUPLICATE_PATCH_ID', 'DUPLICATE_PATCH_IMAGE_PATH'} <= self.codes())

    def test_source_identity_missing_mismatch_and_ambiguity_diagnosed(self):
        self.aggregate['scenes'][0]['scene_id'] = 'other'; self.save()
        self.assertIn('SCENE_SOURCE_MISSING_MATCH', self.codes())
        self.aggregate['scenes'][0].pop('source_window'); self.save()
        self.assertIn('SCENE_SOURCE_IDENTITY_MISSING', self.codes())
        self.report['scenes'].append(copy.deepcopy(self.report['scenes'][0])); self.save()
        self.assertIn('SCENE_SOURCE_AMBIGUOUS_MATCH', self.codes())

    def test_report_with_no_materializable_rows_can_have_zero_patches(self):
        self.report['scenes'] = [{'status': 'error'}]
        self.aggregate['scenes'] = []; self.save()
        self.assertEqual(self.inspect()['metadata_consistency'], 'CONSISTENT_METADATA')

    def test_root_escape_remote_path_and_nonobject_scene_rejected(self):
        self.aggregate['source_manifests'] = [str(self.workspace / 'outside.json')]; self.save()
        with self.assertRaises(ValueError): self.inspect()
        self.aggregate['source_manifests'] = ['//server/share/report.json']; self.save()
        with self.assertRaises(ValueError): self.inspect()
        self.aggregate['source_manifests'] = [str(self.source)]
        self.aggregate['scenes'] = [False]; self.save()
        self.assertIn('AGGREGATE_SCENE_INVALID', self.codes())

    def test_source_file_change_between_repeated_reads_rejected(self):
        real = module._fingerprint
        calls = 0
        def change(path):
            nonlocal calls
            if path == self.source:
                calls += 1
                if calls == 2: self.source.write_text('{"scenes":[]}', encoding='utf-8')
            return real(path)
        with patch.object(module, '_fingerprint', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_missing_report_appearing_and_logical_target_retarget_rejected(self):
        self.source.unlink()
        real = module._fingerprint
        calls = 0
        def appear(path):
            nonlocal calls
            if path == self.source:
                calls += 1
                if calls == 2: self.source.write_text('{}', encoding='utf-8')
            return real(path)
        with patch.object(module, '_fingerprint', side_effect=appear):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.save()
        real_resolve = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.aggregate_path:
                calls += 1
                if calls >= 2: return self.output / 'other.json'
            return real_resolve(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'target changed'): self.inspect()

    def test_cli_cp949_new_evidence_input_preserved_and_output_restrictions(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_aggregate.py'), '--data-root', str(self.root), *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'evidence.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'BLOCKED')
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(before, output.read_bytes())
        self.assertEqual(cli('--output', self.aggregate_path).returncode, 1)
        with tempfile.TemporaryDirectory() as external:
            path = Path(external) / 'not-created.json'
            self.assertEqual(cli('--output', path).returncode, 1)
            self.assertFalse(path.exists())
        self.aggregate_path.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
