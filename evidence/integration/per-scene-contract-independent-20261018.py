"""Independent synthetic metadata checks; no Store, raster, API or execution."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import time
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'backend/app/ml/per_scene_normalization_contract.py'
EXPECTED_SHA = 'b2f1f79c5b9773d9588d4e9b560f9df12ed94d2c1e5301b638cc9c432090f8ea'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
spec = importlib.util.spec_from_file_location('independent_per_scene', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
inspect = module.inspect_per_scene_normalization_contract
FLAGS = ('execution_authorized', 'artifact_bytes_verified', 'source_authority_verified',
         'scientific_accuracy_validated', 'workflow_supported')


def fixture():
    bands = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
    return [
        dict(normalization_mode='per_scene_product_metadata', bands=[1, 2, 3, 4, 5, 6], band_names=bands[:]),
        dict(scene_id='위성 제품 α', image_sha256='a' * 64, band_names=bands[:]),
        dict(scale=0.0001, offset=-0.1, evidence_path=r'Z:\없는 경로\증거.json', evidence_sha256='b' * 64),
        dict(status='verified_product_metadata', product_id='위성 제품 α', band_names=bands[:],
             scale=[0.0001] * 6, offset=[-0.1] * 6, source_url='opaque:공식 여부 미확인',
             source_metadata_path='../../not-resolved.json', source_metadata_sha256='c' * 64)]


class Independent(unittest.TestCase):
    def check(self, args, status, code=None, field=None):
        result = inspect(*args)
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', *FLAGS})
        self.assertIs(type(result['schema_version']), int)
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['scope'], 'PER_SCENE_NORMALIZATION_DECLARATIONS_ONLY')
        self.assertEqual(result['status'], status)
        self.assertEqual(result['issue'], None if code is None else {'code': code, 'field': field})
        for flag in FLAGS:
            self.assertIs(result[flag], False)
        return result

    def test_global_1_to_16_is_outside_observer_not_execution_rejection(self):
        for count in range(1, 17):
            self.check([dict(normalization_mode='global', bands=list(range(1, count + 1))), object(), object(), object()], 'OUT_OF_SCOPE')
        self.check([{}, object(), object(), object()], 'OUT_OF_SCOPE')
        self.check([dict(normalization_mode='future_mode'), object(), object(), object()], 'OUT_OF_SCOPE')

    def test_consistency_scalar_vector_math_six_channels(self):
        args = fixture()
        self.check(args, 'DECLARATIONS_CONSISTENT_UNVERIFIED')
        args[2]['scale'] = [1, 2, 3, 4, 5, 6]
        args[3]['scale'] = [1., 2., 3., 4., 5., 6.]
        args[2]['offset'] = [0, -1, -2, -3, -4, -5]
        args[3]['offset'] = [0., -1., -2., -3., -4., -5.]
        self.check(args, 'DECLARATIONS_CONSISTENT_UNVERIFIED')
        for i in range(6):
            self.assertEqual(17 * args[2]['scale'][i] + args[2]['offset'][i],
                             17 * args[3]['scale'][i] + args[3]['offset'][i])
        args[3]['scale'][5] += 1e-9
        self.check(args, 'DECLARATION_MISMATCH', 'FIELD_MISMATCH', 'normalization.scale')

    def test_missing_versus_null_all_required_fields(self):
        for i, original in enumerate(fixture()):
            for key in original:
                if i == 0 and key == 'normalization_mode':
                    continue
                args = fixture(); del args[i][key]
                parent = ('checkpoint_manifest', 'source_scene', 'normalization', 'evidence')[i]
                self.check(args, 'INCOMPLETE', 'MISSING_FIELD', parent + '.' + key)
                args = fixture(); args[i][key] = None
                self.check(args, 'INVALID', 'INVALID_FIELD', parent + '.' + key)

    def test_numeric_strictness_and_bounds(self):
        for i in (2, 3):
            for key in ('scale', 'offset'):
                for value in (True, False, '0.0001', float('nan'), float('inf'), -float('inf'), 2 ** 53,
                              [1] * 5, [1] * 7, [1, 1, 1, 1, 1, True], (1,) * 6):
                    args = fixture(); args[i][key] = value
                    self.check(args, 'INVALID', 'INVALID_FIELD', ('normalization' if i == 2 else 'evidence') + '.' + key)
            for value in (0, -1, [1, 1, 1, 1, 1, 0]):
                args = fixture(); args[i]['scale'] = value
                self.check(args, 'INVALID', 'INVALID_FIELD', ('normalization' if i == 2 else 'evidence') + '.scale')

    def test_unicode_paths_hashes_and_oversize(self):
        self.check(fixture(), 'DECLARATIONS_CONSISTENT_UNVERIFIED')
        for i, key, maximum in ((1, 'scene_id', 128), (2, 'evidence_path', 512),
                                (3, 'source_url', 2048), (3, 'source_metadata_path', 512)):
            for value in ('x' * (maximum + 1), '', ' ', 'x\x00', 'x\x85', '\ud800'):
                args = fixture(); args[i][key] = value
                parent = ('checkpoint_manifest', 'source_scene', 'normalization', 'evidence')[i]
                self.check(args, 'INVALID', 'INVALID_FIELD', parent + '.' + key)
        for i, key in ((1, 'image_sha256'), (2, 'evidence_sha256'), (3, 'source_metadata_sha256')):
            args = fixture(); args[i][key] = 'A' * 64
            self.check(args, 'INVALID', 'INVALID_FIELD', ('checkpoint_manifest', 'source_scene', 'normalization', 'evidence')[i] + '.' + key)
        for i in range(4):
            args = fixture(); args[i].update({f'extra{n}': None for n in range(129)})
            self.check(args, 'INVALID', 'INPUT_LIMIT', ('checkpoint_manifest', 'source_scene', 'normalization', 'evidence')[i])

    def test_mismatch_priority_and_ordered_band_contract(self):
        for i, key, value, field in ((0, 'bands', [6, 5, 4, 3, 2, 1], 'checkpoint_manifest.bands'),
            (0, 'band_names', ['B03', 'B02', 'B04', 'B08', 'B11', 'B12'], 'checkpoint_manifest.band_names'),
            (1, 'band_names', ['x'] * 6, 'source_scene.band_names'),
            (3, 'status', 'VERIFIED_PRODUCT_METADATA', 'evidence.status'),
            (3, 'product_id', 'other', 'evidence.product_id'),
            (3, 'band_names', ['x'] * 6, 'evidence.band_names'),
            (3, 'offset', -0.2, 'normalization.offset')):
            args = fixture(); args[i][key] = value
            self.check(args, 'DECLARATION_MISMATCH', 'FIELD_MISMATCH', field)
        args = fixture(); args[0]['bands'][0] = True
        self.check(args, 'INVALID', 'INVALID_FIELD', 'checkpoint_manifest.bands')

    def test_pure_no_io_immutable_and_detached_output(self):
        args = fixture(); before = copy.deepcopy(args)
        class Opaque:
            def __iter__(self): raise AssertionError('extra traversed')
            def __str__(self): raise AssertionError('extra stringified')
        for item in args: item['opaque_extra'] = Opaque()
        with patch('builtins.open', side_effect=AssertionError('file access')), \
             patch.object(pathlib.Path, 'open', side_effect=AssertionError('path access')), \
             patch('subprocess.run', side_effect=AssertionError('process access')):
            first = self.check(args, 'DECLARATIONS_CONSISTENT_UNVERIFIED')
            second = self.check(args, 'DECLARATIONS_CONSISTENT_UNVERIFIED')
        for i, item in enumerate(args):
            self.assertEqual({k:v for k,v in item.items() if k != 'opaque_extra'}, before[i])
        first['execution_authorized'] = True
        self.assertIs(second['execution_authorized'], False)


if __name__ == '__main__':
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Independent)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    baseline = '9a79c3db77e3a94936ab74597939b5bf5630e2c3'
    old_paths = ['backend/app/lcluc_workflow.py', 'backend/app/ml/service.py', 'backend/app/ml/normalization.py',
                 'backend/app/main.py', 'frontend/src/LclucWorkflowPanel.tsx',
                 'frontend/src/lclucWorkflowAdapter.ts', 'frontend/src/ModelReview.tsx', 'frontend/src/api.ts']
    comparisons = []
    for path in old_paths:
        original = subprocess.check_output(['git', 'show', baseline + ':' + path], cwd=ROOT)
        actual = (ROOT / path).read_bytes()
        comparisons.append(dict(path=path, baseline_sha256=hashlib.sha256(original).hexdigest(),
                                current_sha256=hashlib.sha256(actual).hexdigest(), unchanged=original == actual))
    diff = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    record = dict(scope='INDEPENDENT_SYNTHETIC_METADATA_ONLY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), seconds=time.perf_counter()-start,
        passed=result.wasSuccessful() and all(x['unchanged'] for x in comparisons) and not diff,
        helper_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), baseline_commit=baseline,
        original_source_byte_checks=comparisons, tracked_source_differences=diff,
        actual_file_verification=False, raster_reads=0, Store_calls=0, API_calls=0, inference_calls=0,
        training_calls=0, UI_changes=0, browser_runs=0, full_frontend_or_build_runs=0,
        limitation='Only supplied declaration compatibility; opaque paths/URLs and SHA syntax are not file, authority, calibration, mask, readiness or scientific verification. Existing global1..16 execution unchanged. No API/UI caller is wired. Existing1184 backend history is not a new run; do not sum overlapping suites.')
    (ROOT / 'evidence/integration/per-scene-contract-independent-20261018.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    raise SystemExit(0 if record['passed'] else 1)
