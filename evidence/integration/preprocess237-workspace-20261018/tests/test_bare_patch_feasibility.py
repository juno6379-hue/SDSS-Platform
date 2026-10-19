"""Small aggregate fixtures and independent exhaustive integer allocations."""
import copy
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from backend.app.ml import bare_patch_feasibility as module
from scripts import inspect_bare_patch_feasibility as cli
import test_bare_class_requirements as fixtures


ROOT = Path(__file__).resolve().parents[1]


class BarePatchFeasibilityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BareClassRequirementsTests()
        self.fixture.setUp()
        self.report = self.fixture.report
        self.reference = {'path': str(self.fixture.path), 'sha256': self.fixture.pin}

    def tearDown(self):
        self.fixture.tearDown()

    def build(self):
        return module.build_bare_patch_feasibility(self.report, self.reference)

    def test_small_capacity_bounds_match_independent_exhaustive_allocations(self):
        for eligible in range(5):
            for capacity in range(1, 6):
                for threshold in range(1, capacity + 1):
                    possible = {}
                    for allocation in itertools.product(range(capacity + 1), repeat=eligible):
                        pixels = sum(allocation)
                        count = sum(value >= threshold for value in allocation)
                        possible.setdefault(pixels, set()).add(count)
                    for pixels, counts in possible.items():
                        self.assertEqual(module._contribution_bounds(eligible, pixels, threshold, capacity),
                                         (min(counts), max(counts)))

    def test_integer_boundaries_zero_threshold_capacity_and_full_patch(self):
        self.assertEqual(module._contribution_bounds(0, 0, 256, 65536), (0, 0))
        self.assertEqual(module._contribution_bounds(2, 510, 256, 65536), (0, 1))
        self.assertEqual(module._contribution_bounds(2, 511, 256, 65536), (1, 1))
        self.assertEqual(module._contribution_bounds(2, 65537, 65536, 65536), (0, 1))
        self.assertEqual(module._contribution_bounds(2, 131071, 65536, 65536), (1, 1))
        self.assertEqual(module._contribution_bounds(1, 65536, 256, 65536), (1, 1))

    def test_bounds_reject_bool_float_huge_counts_and_outside_capacity(self):
        for arguments in ((True, 0, 1, 1), (1, True, 1, 1), (1, 1, True, 1), (1, 1, 1, True),
                          (1.0, 0, 1, 1), (1, 0.0, 1, 1), (1, -1, 1, 1), (1, 2, 1, 1),
                          (0, 1, 1, 1), (1, 0, 0, 1), (1, 0, 2, 1),
                          (10**400, 0, 1, 1), (1, 10**400, 1, 1), (1, 0, 1, 10**400)):
            with self.assertRaises(ValueError): module._contribution_bounds(*arguments)

    def test_stored_aggregate_example_new_gap_is_not76_split_floor(self):
        result = self.build(); values = result['by_split']
        self.assertEqual([values[s]['minimum_contributing_patches_from_aggregate'] for s in values], [0, 0, 0])
        self.assertEqual([values[s]['maximum_contributing_patches_from_aggregate'] for s in values], [5, 0, 4])
        self.assertEqual([values[s]['necessary_total_bare_pixel_shortfall'] for s in values], [0, 1071, 255])
        self.assertEqual([values[s]['minimum_total_bare_pixels_necessary_for_required_count'] for s in values], [1280] * 3)
        self.assertEqual([result['stored_requirements']['by_split'][s]['split_pixel_shortfall'] for s in values], [0, 47, 0])
        self.assertIs(values['train']['aggregate_upper_bound_supports_required_count'], True)
        self.assertEqual(values['train']['observed_contributing_patches'], 0)
        self.assertIs(result['ready_for_training'], False)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(all(result[field] is False for field in module.FALSE_FIELDS))

    def test_original76_build_exactly_once_preserved_no_io_or_assess_mutation(self):
        expected = self.fixture.build(); before = copy.deepcopy((self.report, self.reference))
        with patch.object(module.requirements, 'build_bare_class_requirements', wraps=module.requirements.build_bare_class_requirements) as original, \
             patch.object(Path, 'open', side_effect=AssertionError('no I/O')), \
             patch('backend.app.ml.readiness.assess', side_effect=AssertionError('no QA')):
            result = self.build()
        original.assert_called_once_with(self.report, self.reference)
        self.assertEqual(result['stored_requirements'], expected)
        self.assertEqual((self.report, self.reference), before)
        self.assertEqual(result['stored_requirements']['pin_validation'], 'CALLER_DECLARED_REFERENCE_ONLY')

    def test_zero_eligible_and_insufficient_eligible_are_not_sufficient_gates(self):
        for eligible in (0, 1):
            for split in ('train', 'val', 'test'):
                self.report['patch_counts_by_split'][split] = eligible
                self.report['class_counts_by_split'][split] = [0] * 9
                self.report['class_patch_counts_by_split'][split] = [0] * 9
            self.fixture.balance(); result = self.build()
            for value in result['by_split'].values():
                self.assertIs(value['eligible_patch_capacity_supports_required_count'], False)
                self.assertIs(value['aggregate_upper_bound_supports_required_count'], False)
                self.assertEqual(value['minimum_contributing_patches_from_aggregate'], 0)
                self.assertEqual(value['maximum_contributing_patches_from_aggregate'], 0)
            self.assertEqual(result['status'], 'BLOCKED')

    def test_impossible_stored_patch_count_is_diagnostic_not_base_gate_rewrite(self):
        for split in ('train', 'val', 'test'):
            self.report['patch_counts_by_split'][split] = 1
            self.report['class_counts_by_split'][split] = [0] * 7 + [65536, 0]
            self.report['class_patch_counts_by_split'][split] = [0] * 9
        self.fixture.balance(); expected = self.fixture.build(); result = self.build()
        self.assertEqual(result['stored_requirements'], expected)
        self.assertIs(result['stored_contributing_counts_within_aggregate_bounds'], False)
        self.assertEqual(result['inconsistent_splits'], ['train', 'val', 'test'])
        for value in result['by_split'].values():
            self.assertEqual(value['minimum_contributing_patches_from_aggregate'], 1)
            self.assertIs(value['observed_count_within_aggregate_bounds'], False)
        self.assertEqual(result['stored_requirements']['status'], 'BLOCKED')

    def test_original76_strict_contract_still_rejects_invalid_report_or_reference(self):
        for mutate in (lambda report: report['policy'].update(min_class_pixels_per_patch=255),
                       lambda report: report['class_counts_by_split']['train'].__setitem__(7, True),
                       lambda report: report['reference_balance_by_split']['val'].update(passed=True),
                       lambda report: report.update(ready_for_training=True)):
            report = copy.deepcopy(self.report); mutate(report)
            with self.assertRaises(ValueError): module.build_bare_patch_feasibility(report, self.reference)
        with self.assertRaises(ValueError): module.build_bare_patch_feasibility(self.report, {'path': 'x', 'sha256': 'bad'})

    def test_reader_reuses76_once_only_fixed_report_twice_and_preserves_bytes(self):
        original_open = Path.open; opened = []; before = self.fixture.path.read_bytes()
        def guarded(path, *args, **kwargs):
            self.assertEqual(path.resolve(), self.fixture.path.resolve()); opened.append(path)
            return original_open(path, *args, **kwargs)
        with patch.object(module.requirements, 'inspect_bare_class_requirements', wraps=module.requirements.inspect_bare_class_requirements) as reader, \
             patch.object(Path, 'open', guarded), patch('backend.app.ml.readiness.assess', side_effect=AssertionError('no QA')):
            result = module.inspect_bare_patch_feasibility(self.fixture.root, self.fixture.pin)
        reader.assert_called_once_with(self.fixture.root, self.fixture.pin)
        self.assertEqual(len(opened), 2)
        self.assertEqual(self.fixture.path.read_bytes(), before)
        self.assertEqual(result['stored_requirements']['pin_validation'], 'PINNED_REPORT_BYTES_AND_STABILITY_VERIFIED')

    def test_reader_pin_stale_duplicate_nonfinite_and_remote_references_fail(self):
        with self.assertRaises(ValueError): module.inspect_bare_patch_feasibility(self.fixture.root, '0' * 64)
        original_read = module.requirements.BoundedJSONIO.read
        def changed(context, *args):
            result = original_read(context, *args)
            self.fixture.path.write_bytes(self.fixture.path.read_bytes() + b' ')
            return result
        with patch.object(module.requirements.BoundedJSONIO, 'read', changed), self.assertRaises(ValueError):
            module.inspect_bare_patch_feasibility(self.fixture.root, self.fixture.pin)
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[' * 33 + b'0' + b']' * 33):
            self.fixture.path.write_bytes(raw); pin = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError): module.inspect_bare_patch_feasibility(self.fixture.root, pin)
        self.report['input_manifests'][0]['path'] = 'https://example.invalid/candidate.json'; self.fixture.save()
        with self.assertRaises(ValueError): module.inspect_bare_patch_feasibility(self.fixture.root, self.fixture.pin)

    def test_cli_cp949_new_evidence_and_no_overwrite(self):
        output = self.fixture.workspace / '결과–patch.json'
        command = [sys.executable, str(ROOT / 'scripts/inspect_bare_patch_feasibility.py'),
            '--data-root', str(self.fixture.root), '--expected-report-sha256', self.fixture.pin, '--output', str(output)]
        env = {**os.environ, 'PYTHONPATH': str(ROOT / '.runtime'), 'PYTHONIOENCODING': 'cp949'}
        before = self.fixture.path.read_bytes(); result = subprocess.run(command, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        value = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(value['by_split']['val']['necessary_total_bare_pixel_shortfall'], 1071)
        saved = output.read_bytes(); again = subprocess.run(command, capture_output=True, env=env)
        self.assertEqual(again.returncode, 1)
        self.assertTrue(again.stderr.isascii())
        self.assertEqual(output.read_bytes(), saved)
        self.assertEqual(self.fixture.path.read_bytes(), before)

    def test_cli_alias_devices_and_output_cap_before_creation(self):
        for path in (self.fixture.path, self.fixture.workspace / 'CON.json',
                     self.fixture.workspace / 'file.json:stream', self.fixture.workspace / 'trailing.'):
            with self.assertRaises(ValueError): cli._output_path(path, self.fixture.root, [self.fixture.path])
        output = self.fixture.workspace / 'new.json'
        args = ['inspect_bare_patch_feasibility.py', '--data-root', str(self.fixture.root),
                '--expected-report-sha256', self.fixture.pin, '--output', str(output)]
        with patch.object(sys, 'argv', args), patch.object(cli, 'OUTPUT_CAP', 1), patch.object(sys, 'stderr', io.StringIO()):
            self.assertEqual(cli.main(), 1)
        self.assertFalse(output.exists())
