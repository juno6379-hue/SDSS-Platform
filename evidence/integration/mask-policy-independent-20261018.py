"""Independent actual annual fixtures plus explicitly mocked policy-count boundary."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.runtime'), str(ROOT / 'backend')]
import numpy as np
import rasterio
import torch
from app.ml import annual_mask_policy as module
spec = importlib.util.spec_from_file_location('independent_annual_mask_fixture', ROOT / 'evidence/integration/annual-mask-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/annual_mask_policy.py'
FROZEN = 'ebf3db476613101732c4b1db0b2c41e45148dc76ebbec078031668d286541b9c'
TEST_FROZEN = '78a42535d9506ddf93e268ae6ec366af80b4f73b8aaa7344da9b165996ea6b26'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified', 'registry_aoi_verified',
    'source_authority_verified', 'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def policy(num=1, den=2):
    return dict(schema_version=1, minimum_valid_numerator=num, minimum_valid_denominator=den, comparison='greater_than_or_equal')


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store, self.root, self.rows, self.fixture = self.base.store, self.base.root, self.base.rows, self.base.fixture

    def read(self, selected_policy, rows=None, on_get=None):
        before = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        get, actual_read = self.store.get, rasterio.io.DatasetReader.read
        calls = []; pixels = []
        def observed(kind, key):
            calls.append((kind, key))
            if on_get: on_get(kind, key)
            return get(kind, key)
        def read_pixels(dataset, *args, **kwargs):
            self.assertEqual(dataset.count, 1); pixels.append((args, kwargs))
            return actual_read(dataset, *args, **kwargs)
        with patch.object(self.store, 'get', observed), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(torch, 'load', wraps=torch.load) as model_load, \
             patch.object(rasterio.io.DatasetReader, 'read', read_pixels), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('intrinsic mask')):
            result = module.inspect_annual_mask_policy(self.store, self.fixture.model_ref, self.fixture.report_sha,
                self.rows if rows is None else rows, selected_policy)
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'parent_annual_observation',
            'policy', 'per_year_observations', 'annual_observation_calls', 'caller_policy_evaluated', 'caller_policy_met',
            'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'CALLER_EXPLICIT_ANNUAL_MASK_POLICY_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls, pixels, model_load.call_count

    def real_parent(self):
        result, _, _, _ = self.read(policy(), self.rows[:2])
        self.assertEqual(result['status'], 'CALLER_POLICY_MET_UNVERIFIED')
        return result['parent_annual_observation']

    def test_actual_two_and_six_years_policy_math_adds_no_io(self):
        for count in (2, 6):
            result, calls, pixels, loads = self.read(policy(), self.rows[:count])
            self.assertEqual(result['status'], 'CALLER_POLICY_MET_UNVERIFIED')
            self.assertEqual((len(calls), len(pixels), loads), (1 + 6 * count, count, 1))
            self.assertEqual(result['annual_observation_calls'], 1)
            self.assertIs(result['caller_policy_evaluated'], True)
            self.assertEqual({r['status'] for r in result['per_year_observations']}, {'MET'})
            for row in result['per_year_observations']:
                self.assertEqual(set(row), {'year', 'status', 'counts', 'policy_met'})
                self.assertEqual(row['counts'], dict(valid_pixels=128, invalid_pixels=128, total_pixels=256))

    def test_invalid_policy_and_sixth_row_are_pre_store_no_defaults(self):
        variants = [None, {}, policy(True, 2), policy(.5, 2), policy('1', 2), policy(1, 0),
                    policy(1, 1000001), policy(-1, 2), policy(3, 2), dict(policy(), comparison='greater_than'),
                    dict(policy(), schema_version=True), dict(policy(), extra='approve')]
        for value in variants:
            result, calls, pixels, loads = self.read(value)
            self.assertEqual(result['status'], 'INVALID_INPUT')
            self.assertEqual((calls, pixels, loads), ([], [], 0))
            self.assertEqual(result['annual_observation_calls'], 0)
        rows = copy.deepcopy(self.rows); rows[5]['mask_ref']['version'] = 'latest'
        self.assertEqual(self.read(policy(), rows)[0]['status'], 'INVALID_INPUT')

    def test_real_policy_not_met_evaluates_every_year_after_all_mask_io(self):
        result, calls, pixels, loads = self.read(policy(500001, 1000000))
        self.assertEqual(result['status'], 'CALLER_POLICY_NOT_MET')
        self.assertEqual((len(calls), len(pixels), loads), (37, 6, 1))
        self.assertIs(result['caller_policy_evaluated'], True)
        self.assertIs(result['caller_policy_met'], False)
        self.assertIs(result['artifact_bytes_verified'], False)
        self.assertEqual([r['status'] for r in result['per_year_observations']], ['NOT_MET'] * 6)
        self.assertEqual(result['issue']['year'], 2020)
        self.assertIs(result['parent_annual_observation']['artifact_bytes_verified'], True)

    def test_exact_integer_cross_product_boundary_uses_explicit_mocked_counts(self):
        parent = self.real_parent()
        for valid, expected in ((349525, False), (349526, True)):
            simulated = copy.deepcopy(parent)
            for row in simulated['mask_observations']:
                row['mask_observation']['counts'] = dict(valid_pixels=valid, invalid_pixels=1048576-valid, total_pixels=1048576)
            with patch.object(module, 'inspect_annual_quality_mask_diagnostics', return_value=simulated):
                result, calls, pixels, loads = self.read(policy(1, 3), self.rows[:2])
            self.assertEqual(result['caller_policy_met'], expected)
            self.assertEqual((calls, pixels, loads), ([], [], 0))
            self.assertIs(result['caller_policy_evaluated'], True)
            self.assertEqual(valid * 3 >= 1048576, expected)

    def test_mocked_nested_counts_must_all_validate_before_any_policy_row(self):
        parent = self.real_parent()
        invalid = [dict(valid_pixels=True, invalid_pixels=255, total_pixels=256),
            dict(valid_pixels=1., invalid_pixels=255, total_pixels=256), dict(valid_pixels=-1, invalid_pixels=257, total_pixels=256),
            dict(valid_pixels=128, invalid_pixels=127, total_pixels=256), dict(valid_pixels=0, invalid_pixels=0, total_pixels=0),
            dict(valid_pixels=1, invalid_pixels=1048576, total_pixels=1048577), dict(valid_pixels=128, invalid_pixels=128),
            dict(valid_pixels=128, invalid_pixels=128, total_pixels=256, extra=0)]
        for counts in invalid:
            simulated = copy.deepcopy(parent); simulated['mask_observations'][1]['mask_observation']['counts'] = counts
            with patch.object(module, 'inspect_annual_quality_mask_diagnostics', return_value=simulated):
                result, calls, pixels, loads = self.read(policy(0, 1), self.rows[:2])
            self.assertEqual(result['status'], 'POLICY_INPUT_BLOCKED')
            self.assertEqual(result['issue']['year'], 2021)
            self.assertEqual({r['status'] for r in result['per_year_observations']}, {'NOT_CHECKED'})
            self.assertIs(result['caller_policy_evaluated'], False)
            self.assertEqual((calls, pixels, loads), ([], [], 0))
        for mutate in (lambda p: p.update(artifact_bytes_verified=1),
                       lambda p: p['mask_observations'][1].update(registry_manifest_join_verified=1),
                       lambda p: p['mask_observations'][1]['mask_observation'].update(mask_values_verified=1)):
            simulated = copy.deepcopy(parent); mutate(simulated)
            with patch.object(module, 'inspect_annual_quality_mask_diagnostics', return_value=simulated):
                self.assertEqual(self.read(policy(), self.rows[:2])[0]['status'], 'POLICY_INPUT_BLOCKED')

    def test_real_all_zero_zero_threshold_and_caller_policy_snapshot(self):
        self.base.update_mask(0, np.zeros((16, 16), dtype='uint8'))
        selected_policy = policy(0, 1000000); rows = copy.deepcopy(self.rows[:2])
        def mutate(kind, key):
            if kind == 'models':
                selected_policy['minimum_valid_numerator'] = 1000000
                rows[1]['mask_ref']['sha256'] = '0' * 64
        result, _, pixels, _ = self.read(selected_policy, rows, on_get=mutate)
        self.assertEqual(result['status'], 'CALLER_POLICY_MET_UNVERIFIED')
        self.assertEqual(result['policy'], policy(0, 1000000))
        self.assertEqual(result['per_year_observations'][0]['counts']['valid_pixels'], 0)
        self.assertEqual(len(pixels), 2)
        self.assertIs(result['quality_mask_verified'], False)

    def test_upstream_mask_failure_keeps_policy_rows_unchecked(self):
        self.base.update_mask(0, np.full((16, 16), 255, dtype='uint8'))
        result, calls, pixels, loads = self.read(policy(0, 1), self.rows[:2])
        self.assertEqual(result['status'], 'ANNUAL_DIAGNOSTICS_BLOCKED')
        self.assertEqual(result['parent_annual_observation']['status'], 'MASK_BLOCKED')
        self.assertEqual(result['annual_observation_calls'], 1)
        self.assertEqual({r['status'] for r in result['per_year_observations']}, {'NOT_CHECKED'})
        self.assertIs(result['caller_policy_evaluated'], False)


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '9a14fc62f7dd5dda6b1df8b2b0b241a17a12f28d'
    checks = []
    for name in ('backend/app/ml/annual_quality_mask_diagnostics.py', 'backend/app/ml/registered_binary_mask_values.py',
                 'backend/app/ml/registry_spatial_normalization.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    test_sha = sha((ROOT / 'tests/test_annual_mask_policy.py').read_bytes())
    payload = dict(scope='SYNTHETIC_TEMP_CALLER_RATIONAL_POLICY_PLUS_MOCKED_COUNTS_BOUNDARY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), test_sha256=test_sha,
        frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN, frozen_test_matches=test_sha == TEST_FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_checkpoint_reads_or_writes=0, image_pixel_reads=0, intrinsic_mask_reads=0,
        training_inference_calls=0, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Actual2/6-year TempStore/GTiff/untrained checkpoint paths are separate from explicitly mocked nested count/flag boundary cases; no fabricated counts claimed as measured.',
          'Caller-explicit integer rational threshold and every-year comparison only, not agency QA policy approval, semantic truth, actual annual completeness, scientific/model/execution approval.',
          'Policy failure follows all successful134 mask reads. Policy NOT_CHECKED after invalid counts means no135 arithmetic, not no historical134 IO.',
          'No extra IO beyond134; sequential snapshot/resource/authority limits remain. Internal unwired helper, no API/UI/front/build/browser/full-backend rerun. Prior1184 is historical; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/mask-policy-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] and payload['frozen_test_matches'] else 1)
