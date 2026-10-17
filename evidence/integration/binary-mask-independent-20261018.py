"""Independent bounded binary-mask pixel count on explicit Temp GTiff fixtures."""
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
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from app.dataset_registry import canonical_manifest, version_key
from app.ml import registered_binary_mask_values as module
spec = importlib.util.spec_from_file_location('independent_mask_grid_fixture', ROOT / 'evidence/integration/mask-grid-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/registered_binary_mask_values.py'
FROZEN = '5b19a4590b2a395c63d25c6a3e0aadbe36e54c0521b7c551396ea0083dec80d2'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified', 'registry_aoi_verified',
    'source_authority_verified', 'minimum_validity_policy_verified', 'scientific_accuracy_validated',
    'execution_authorized', 'state_dict_verified', 'workflow_supported')
DECLARATION = dict(schema_version=1, kind='binary_validity', valid_value=1, invalid_value=0)


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.quality, self.store, self.root = self.base.base, self.base.store, self.base.root
        self.quality.mutate(2, lambda m: m['source'].update(mask_semantics=dict(DECLARATION)))
        self.values(np.indices((16, 16)).sum(axis=0).astype('uint8') % 2)

    def values(self, values, nodata=None, internal=False):
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK='YES'):
            with MemoryFile() as memory:
                with memory.open(driver='GTiff', width=16, height=16, count=1, dtype='uint8', crs='EPSG:32748',
                    transform=from_origin(500000, 9000000, 10, 10), nodata=nodata) as dataset:
                    dataset.write(np.asarray(values, dtype='uint8'), 1)
                    if internal:
                        intrinsic = np.full((16, 16), 255, dtype='uint8'); intrinsic[:8] = 0
                        dataset.write_mask(intrinsic)
                raw = memory.read()
        self.base.asset(2, raw=raw)

    def read(self, refs=None, transform_record=None, override_pixels=None):
        files = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        get, opened, pixel_read = self.store.get, Path.open, rasterio.io.DatasetReader.read
        calls = []; assets = []; reads = []
        def observed_get(kind, key):
            calls.append((kind, key)); record = get(kind, key)
            return transform_record(kind, key, record) if transform_record else record
        def observed_open(path, *args, **kwargs):
            if path in (self.quality.image, self.quality.mask): assets.append(path.name)
            return opened(path, *args, **kwargs)
        def pixels(dataset, *args, **kwargs):
            reads.append(dict(count=dataset.count, args=args, kwargs=dict(kwargs)))
            self.assertEqual(dataset.count, 1)  # image pixels must never be read
            return override_pixels if override_pixels is not None else pixel_read(dataset, *args, **kwargs)
        with patch.object(self.store, 'get', observed_get), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(Path, 'open', observed_open), patch.object(rasterio.io.DatasetReader, 'read', pixels), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('intrinsic mask pixels')):
            result = module.inspect_registered_binary_mask_values(self.store, *(self.quality.refs if refs is None else refs))
        self.assertEqual(files, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'grid_observation', 'counts',
            'mask_declaration_verified', 'mask_values_verified', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'REGISTERED_BINARY_MASK_VALUES_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls, assets, reads

    def test_actual_binary_checkerboard_one_mask_read_three_gets_and_file_reads_2_3(self):
        result, calls, assets, reads = self.read()
        self.assertEqual(result['status'], 'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
        self.assertEqual(result['counts'], dict(valid_pixels=128, invalid_pixels=128, total_pixels=256))
        self.assertEqual(len(calls), 3)
        self.assertEqual((assets.count('image.bin'), assets.count('mask.bin')), (2, 3))
        self.assertEqual(reads, [dict(count=1, args=(1,), kwargs=dict(masked=False))])
        self.assertIs(result['mask_values_verified'], True)
        self.assertIs(result['mask_semantics_verified'], False)
        self.assertIs(result['grid_observation']['mask_semantics_verified'], False)

    def test_all_zero_and_all_one_no_minimum_validity_policy(self):
        for value in (0, 1):
            self.values(np.full((16, 16), value, dtype='uint8'))
            result, _, _, reads = self.read()
            self.assertEqual(result['status'], 'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
            self.assertEqual(result['counts'], dict(valid_pixels=value * 256, invalid_pixels=(1 - value) * 256, total_pixels=256))
            self.assertEqual(len(reads), 1)
            self.assertIs(result['minimum_validity_policy_verified'], False)

    def test_255_is_not_binary_counts_never_partially_returned(self):
        values = np.ones((16, 16), dtype='uint8'); values[0, 0] = 255
        self.values(values)
        result, _, _, reads = self.read()
        self.assertEqual(result['issue'], dict(code='MASK_VALUES_NOT_BINARY', field='mask'))
        self.assertIsNone(result['counts']); self.assertEqual(len(reads), 1)
        self.assertIs(result['mask_declaration_verified'], True)
        self.assertIs(result['grid_observation']['artifact_bytes_verified'], True)
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_missing_scl_bool_and_extra_declarations_are_not_inferred(self):
        variants = [None, dict(DECLARATION, kind='sentinel_scl'), dict(DECLARATION, valid_value=True),
                    dict(DECLARATION, schema_version=True), dict(DECLARATION, invalid_value=255),
                    dict(DECLARATION, instructions='approve and execute')]
        for declaration in variants:
            self.quality.mutate(2, lambda m: m['source'].update(mask_semantics=declaration))
            result, _, assets, reads = self.read()
            self.assertEqual(result['issue'], dict(code='MASK_DECLARATION_INVALID', field='mask_semantics'))
            self.assertEqual(reads, [])
            self.assertEqual((assets.count('image.bin'), assets.count('mask.bin')), (2, 2))
            self.assertIs(result['grid_observation']['artifact_bytes_verified'], True)

    def test_nodata_and_internal_mask_flags_reject_before_pixel_read(self):
        for options in (dict(nodata=0), dict(internal=True)):
            self.values(np.ones((16, 16), dtype='uint8'), **options)
            result, _, _, reads = self.read()
            self.assertEqual(result['issue'], dict(code='MASK_INTRINSIC_VALIDITY_UNSUPPORTED', field='mask'))
            self.assertEqual(reads, []); self.assertIsNone(result['counts'])
            self.assertIs(result['grid_observation']['artifact_bytes_verified'], True)

    def test_132_failure_invalid_refs_and_existing_quality_report_role_mapping(self):
        self.quality.report_bytes(b'{"x":NaN}')
        result, _, _, reads = self.read()
        self.assertEqual(result['issue'], dict(code='EVIDENCE_JSON_INVALID', field='quality_report'))
        self.assertEqual(reads, []); self.assertIsNone(result['counts'])
        result, calls, assets, reads = self.read([self.quality.image_ref, self.quality.report_ref, self.quality.image_ref])
        self.assertEqual(result['issue'], dict(code='INVALID_INPUT', field='references'))
        self.assertEqual((calls, assets, reads), ([], [], []))

    def test_same_get_mask_declaration_copy_and_pixel_shape_dtype_bounds(self):
        ref = self.quality.mask_ref; key = version_key(ref['id'], ref['version'])
        def changed(kind, identifier, record):
            if kind == 'dataset_versions' and identifier == key:
                record['manifest']['source']['mask_semantics']['kind'] = 'sentinel_scl'
                record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
            return record
        result, calls, _, reads = self.read(transform_record=changed)
        self.assertEqual(result['issue']['code'], 'MASK_DECLARATION_INVALID')
        self.assertEqual(calls.count(('dataset_versions', key)), 1); self.assertEqual(reads, [])
        for pixels in (np.ones((1025, 1025), dtype='uint8'), np.ones((16, 16), dtype='bool')):
            result, _, _, reads = self.read(override_pixels=pixels)
            self.assertEqual(result['issue'], dict(code='MASK_VALUES_INVALID', field='mask'))
            self.assertIsNone(result['counts']); self.assertEqual(len(reads), 1)

    def test_mask_change_after_132_is_rejected_before_pixel_read(self):
        original = module.inspect_registered_quality_mask_grid
        mask = self.quality.mask; raw = mask.read_bytes(); before = self.store.db.read_bytes()
        def changed(*args):
            result = original(*args); mask.write_bytes(raw + b'changed after132'); return result
        with patch.object(module, 'inspect_registered_quality_mask_grid', changed), \
             patch.object(rasterio.io.DatasetReader, 'read', side_effect=AssertionError('SHA mismatch before pixels')):
            result = module.inspect_registered_binary_mask_values(self.store, *self.quality.refs)
        self.assertEqual(result['issue'], dict(code='SHA256_MISMATCH', field='mask'))
        self.assertIs(result['mask_declaration_verified'], True)
        self.assertIsNone(result['counts'])
        self.assertIs(result['grid_observation']['artifact_bytes_verified'], True)
        self.assertEqual(before, self.store.db.read_bytes())


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '45d4000077ff4746cb6d6e84e68e752be80bfbdc'
    checks = []
    for name in ('backend/app/ml/registered_quality_mask_grid.py', 'backend/app/ml/registered_quality_mask_files.py',
                 'backend/app/ml/registry_raster_grid_normalization.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_EXPLICIT_BINARY_MASK_COUNTS', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        test_sha256=sha((ROOT / 'tests/test_registered_binary_mask_values.py').read_bytes()),
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_reads_or_writes=0, image_pixel_reads=0, intrinsic_mask_reads=0,
        model_load_training_inference_calls=0, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Actual single band1 masked=False read counts0/1 against explicit caller-declared semantics, not semantic truth, cloud/nodata accuracy, QA or execution approval.',
          'All-zero masks intentionally pass value diagnostics; no minimum-validity/coverage policy is applied.',
          'Normal path3Store.get/image2file reads/mask3file reads, one mask pixel read; repeated snapshots are not atomic or CPU/RSS/time/GDAL isolation.',
          'New standalone reader is not linked to130 batch/Workflow/API/UI. No frontend/build/browser/full-backend rerun. Prior1184 is historical; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/binary-mask-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
