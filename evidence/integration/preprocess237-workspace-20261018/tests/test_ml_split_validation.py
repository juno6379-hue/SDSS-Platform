"""Adversarial metadata-only split-plan validation; temporary synthetic files only."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.ml.split_planning import digest, plan_split_repair, write_plan
from backend.app.ml.split_validation import validate_split_repair_plan

ROOT = Path(__file__).resolve().parents[1]


class SplitValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.json'
        self.saved = self.root / 'saved.json'
        self.candidate = self.root / 'candidate.json'
        self.policy = self.root / 'policy.json'
        self.splits = {'a': 'train', 'b': 'val', 'c': 'test'}
        self.rows = [{'province': p, 'year': 2021, 'scene_id': p,
                      'source_group': p, 'quality_status': 'quality_eligible'} for p in self.splits]
        self.rows[1]['source_group'] = 'c'
        self.source.write_text(json.dumps({'synthetic': True, 'scenes': self.rows}), encoding='utf-8')
        self.sha = digest(self.source)
        self.policy.write_text(json.dumps({'province_splits': self.splits}), encoding='utf-8')
        self.plan = plan_split_repair(self.source, self.sha, province_splits=self.splits)
        write_plan(self.plan, self.saved, derived_manifest=self.candidate)
        self.originals = {p: p.read_bytes() for p in self.root.iterdir()}

    def tearDown(self):
        self.temp.cleanup()

    def validate(self, **kwargs):
        return validate_split_repair_plan(self.saved, self.source, self.sha, province_splits=self.splits, **kwargs)

    def mutate_plan(self, fn):
        doc = copy.deepcopy(self.plan)
        fn(doc)
        self.saved.write_text(json.dumps(doc), encoding='utf-8')

    def cli(self, *args, io_encoding='utf-8'):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/validate_training_split_repair.py'),
            '--saved-plan', str(self.saved), '--manifest', str(self.source),
            '--expected-sha256', self.sha, '--plan', str(self.policy), *map(str, args)],
            capture_output=True, text=True, encoding=io_encoding, env={**os.environ, 'PYTHONIOENCODING': io_encoding})

    def test_metadata_plan_recomputed_without_claiming_candidate_check_or_training(self):
        report = self.validate()
        self.assertTrue(report['plan_integrity_valid'])
        self.assertEqual(report['candidate_validation']['status'], 'NOT_REQUESTED')
        self.assertIsNone(report['candidate_validation']['candidate_integrity_valid'])
        self.assertEqual(report['evidence_state'], 'TESTED_SYNTHETIC')
        self.assertEqual(report['excluded_rows'], 1)
        for key in ['ready_for_training', 'training_executed', 'scientific_accuracy_validated',
                    'raster_files_rehashed', 'spatial_overlap_rechecked', 'exact_class_counts_recomputed']:
            self.assertIs(report[key], False)
        self.assertEqual(self.originals, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_four_digit_string_years_preserve_source_rows_without_coercion(self):
        for row in self.rows:
            row['year'] = '2021'
        self.source.write_text(json.dumps({'synthetic': True, 'scenes': self.rows}), encoding='utf-8')
        self.sha = digest(self.source)
        self.plan = plan_split_repair(self.source, self.sha, province_splits=self.splits)
        self.saved.write_text(json.dumps(self.plan), encoding='utf-8')
        self.candidate.unlink()
        candidate_plan = self.root / 'candidate-plan.json'
        write_plan(self.plan, candidate_plan, derived_manifest=self.candidate)
        before = self.source.read_bytes()
        self.assertTrue(self.validate(candidate_path=self.candidate, candidate_sha256=digest(self.candidate))['candidate_validation']['candidate_integrity_valid'])
        self.assertEqual(before, self.source.read_bytes())
        self.assertIs(type(json.loads(self.candidate.read_text(encoding='utf-8'))['scenes'][0]['year']), str)

    def test_boolean_float_whitespace_and_invalid_string_years_are_rejected(self):
        for value in [True, 2021.0, ' 2021', '2021 ', '21', '20x1', '２０２１']:
            doc = {'synthetic': True, 'scenes': copy.deepcopy(self.rows)}
            doc['scenes'][0]['year'] = value
            self.source.write_text(json.dumps(doc), encoding='utf-8')
            self.sha = digest(self.source)
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'year'):
                    self.validate()

    def test_exact_candidate_metadata_match_is_separate_from_readiness(self):
        report = self.validate(candidate_path=self.candidate, candidate_sha256=digest(self.candidate))
        self.assertIs(report['candidate_validation']['candidate_integrity_valid'], True)
        self.assertFalse(report['ready_for_training'])

    def test_rehashed_tampered_plan_indices_policy_and_approval_rejected(self):
        for field, value in [('retained_row_indexes', [0, 1, 2]), ('ready_for_training', True),
                             ('status', 'READY'), ('policy', {'province_splits': self.splits})]:
            with self.subTest(field=field):
                self.mutate_plan(lambda d: d.__setitem__(field, value))
                with self.assertRaisesRegex(ValueError, 'recomputed'):
                    self.validate()

    def test_boolean_integer_and_float_integer_confusion_rejected(self):
        for value in [True, 1.0]:
            self.mutate_plan(lambda d: d.__setitem__('schema_version', value))
            with self.assertRaises(ValueError):
                self.validate()
        self.mutate_plan(lambda d: d['retained_row_indexes'].__setitem__(0, False))
        with self.assertRaises(ValueError):
            self.validate()

    def test_nonfinite_and_duplicate_keys_are_rejected(self):
        for text in [self.saved.read_text(encoding='utf-8').replace('"schema_version": 1', '"schema_version": NaN'),
                     '{"schema_version": 1, "schema_version": 1}', '{"value":1e999}']:
            self.saved.write_text(text, encoding='utf-8')
            with self.assertRaises(ValueError):
                self.validate()

    def test_stale_source_and_caller_sha_cannot_be_taken_from_plan(self):
        self.source.write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.validate()
        self.source.write_bytes(self.originals[self.source])
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            validate_split_repair_plan(self.saved, self.source, '0' * 64, province_splits=self.splits)

    def test_independent_caller_policy_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_split_repair_plan(self.saved, self.source, self.sha,
                province_splits={'a': 'val', 'b': 'train', 'c': 'test'})

    def test_readiness_binding_and_stale_readiness_are_checked(self):
        readiness = self.root / 'readiness.json'
        doc = {'input_manifests': [{'path': self.source.name, 'sha256': self.sha}],
            'patch_counts_by_split': {'train': 1, 'val': 1, 'test': 1},
            'policy': {'province_splits': self.splits, 'patch_size': 256, 'min_valid_fraction': .8},
            'class_counts_by_split': {s: [100] * 9 for s in self.splits.values()},
            'class_patch_counts_by_split': {s: [0] * 9 for s in self.splits.values()}}
        readiness.write_text(json.dumps(doc), encoding='utf-8')
        sha = digest(readiness)
        args = {'readiness_path': readiness, 'readiness_sha256': sha, 'data_root': self.root}
        self.plan = plan_split_repair(self.source, self.sha, province_splits=self.splits, **args)
        self.saved.write_text(json.dumps(self.plan), encoding='utf-8')
        self.assertTrue(self.validate(**args)['plan_integrity_valid'])
        readiness.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.validate(**args)

    def test_candidate_tampering_rows_lineage_flags_and_sha_rejected(self):
        original = json.loads(self.candidate.read_text(encoding='utf-8'))
        changes = [lambda d: d['scenes'].reverse(),
                   lambda d: d['lineage']['source_row_indexes'].append(1),
                   lambda d: d.__setitem__('executed', 0),
                   lambda d: d.__setitem__('learning_ready', True)]
        for change in changes:
            doc = copy.deepcopy(original)
            change(doc)
            self.candidate.write_text(json.dumps(doc), encoding='utf-8')
            with self.assertRaises(ValueError):
                self.validate(candidate_path=self.candidate, candidate_sha256=digest(self.candidate))
        self.candidate.write_text(json.dumps(original), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.validate(candidate_path=self.candidate, candidate_sha256='0' * 64)

    def test_missing_candidate_and_unpaired_parameters_never_succeed(self):
        for kwargs in [{'candidate_path': self.candidate}, {'candidate_sha256': '0' * 64},
                       {'readiness_path': self.root / 'missing.json'},
                       {'candidate_path': self.root / 'missing.json', 'candidate_sha256': '0' * 64}]:
            with self.assertRaises((ValueError, OSError)):
                self.validate(**kwargs)

    def test_change_during_recomputation_is_rejected(self):
        def changed(*args, **kwargs):
            self.source.write_text('{}', encoding='utf-8')
            return copy.deepcopy(self.plan)
        with patch('backend.app.ml.split_validation.plan_split_repair', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.validate()

    def test_cli_stdout_new_output_and_existing_input_paths_protected(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['plan_integrity_valid'])
        self.assertEqual(self.originals, {p: p.read_bytes() for p in self.root.iterdir()})
        output = self.root / 'evidence.json'
        result = self.cli('--output', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        for target in [output, self.saved, self.source, self.policy, self.candidate]:
            before = target.read_bytes()
            result = self.cli('--output', target)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(before, target.read_bytes())

    def test_cli_cp949_console_stdout_and_stderr_are_ascii_safe(self):
        output = self.root / 'console-evidence.json'
        result = self.cli('--output', output, io_encoding='cp949')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        self.assertTrue(json.loads(result.stdout)['plan_integrity_valid'])
        report = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(report['saved_plan']['path'], str(self.saved.resolve()))
        missing = self.root / 'missing-\u2013.json'
        result = self.cli('--saved-plan', missing, io_encoding='cp949')
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.isascii())
        self.assertIn('Split repair validation failed:', result.stderr)

    def test_cli_output_outside_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            output = Path(outside) / 'report.json'
            self.assertEqual(self.cli('--output', output).returncode, 1)
            self.assertFalse(output.exists())

    def test_cli_tampered_plan_does_not_create_evidence(self):
        self.mutate_plan(lambda d: d.__setitem__('training_executed', True))
        output = self.root / 'must-not-exist.json'
        self.assertEqual(self.cli('--output', output).returncode, 1)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
