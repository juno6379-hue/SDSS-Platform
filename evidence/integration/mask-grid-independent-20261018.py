"""Independent actual image/mask GTiff header diagnostic after131 bindings."""
import ast
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
from rasterio.transform import Affine, from_origin
from app.dataset_registry import canonical_manifest, version_key
from app.ml import registered_quality_mask_grid as module
spec = importlib.util.spec_from_file_location('independent_quality_fixture', ROOT / 'evidence/integration/quality-mask-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/registered_quality_mask_grid.py'
FROZEN = 'd4827f901496607e9bd33e9d4bb9446f19de176592b3a903405fe243e4ee6ec3'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('quality_report_verified', 'quality_mask_verified', 'pixel_values_verified', 'mask_semantics_verified',
    'registry_aoi_verified', 'source_authority_verified', 'scientific_accuracy_validated', 'execution_authorized',
    'state_dict_verified', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp()
        self.addCleanup(self.base.tearDown)
        self.store, self.root = self.base.store, self.base.root
        self.names = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
        self.base.mutate(0, lambda m: m['source'].update(band_names=self.names[:]))
        self.asset(0); self.asset(2)

    def asset(self, index, raw=None, **options):
        if raw is None:
            profile = dict(driver='GTiff', width=16, height=16, count=6 if index == 0 else 1,
                dtype='uint16' if index == 0 else 'uint8', crs='EPSG:32748', transform=from_origin(500000, 9000000, 10, 10))
            names = options.pop('names', tuple(self.names) if index == 0 else None)
            profile.update(options)
            with MemoryFile() as memory:
                with memory.open(**profile) as dataset:
                    if names is not None: dataset.descriptions = names
                    # Arbitrary fixture values255; the diagnostic never reads them.
                    dataset.write(np.full((profile['count'], profile['height'], profile['width']), 255, dtype=profile['dtype']))
                raw = memory.read()
        path = self.base.image if index == 0 else self.base.mask
        path.write_bytes(raw); ref = self.base.refs[index]; ref['sha256'] = sha(raw)
        self.base.mutate(index, lambda m: m.update(sha256=ref['sha256']))
        self.base.mutate(1, lambda m: m['lineage'][0 if index == 0 else 1].update(sha256=ref['sha256']))
        self.base.body['image_ref' if index == 0 else 'mask_ref'] = dict(ref)
        self.base.report_bytes()

    def read(self, refs=None, transform_record=None):
        before = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        get, opened = self.store.get, Path.open; calls = []; assets = []
        def get_record(kind, key):
            calls.append((kind, key)); record = get(kind, key)
            return transform_record(kind, key, record) if transform_record else record
        def open_file(path, *args, **kwargs):
            if path in (self.base.image, self.base.mask): assets.append(path.name)
            return opened(path, *args, **kwargs)
        with patch.object(self.store, 'get', get_record), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(Path, 'open', open_file), \
             patch.object(rasterio.io.DatasetReader, 'read', side_effect=AssertionError('pixel read')), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('mask read')):
            result = module.inspect_registered_quality_mask_grid(self.store, *(self.base.refs if refs is None else refs))
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'quality_mask_observation',
            'image_header', 'mask_header', 'image_mask_headers_verified', 'image_mask_grid_verified',
            'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'REGISTERED_QUALITY_MASK_GRID_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls, assets

    def test_actual_six_band_image_one_uint8_mask_three_gets_two_reads_each_no_values(self):
        result, calls, assets = self.read()
        self.assertEqual(result['status'], 'REGISTERED_QUALITY_MASK_GRID_MATCHED_UNVERIFIED')
        self.assertEqual(len(calls), 3)
        self.assertEqual((assets.count('image.bin'), assets.count('mask.bin')), (2, 2))
        for flag in ('image_mask_headers_verified', 'image_mask_grid_verified', 'artifact_bytes_verified'):
            self.assertIs(result[flag], True)
        self.assertEqual(result['image_header']['band_names'], self.names)
        self.assertEqual((result['mask_header']['count'], result['mask_header']['dtype']), (1, 'uint8'))
        self.assertEqual(result['image_header']['bounds'], result['mask_header']['bounds'])
        self.assertIs(result['quality_mask_observation']['raster_header_verified'], False)
        self.assertIs(result['mask_semantics_verified'], False)

    def test_mask_offset_crs_shape_and_affine_grid_mismatches(self):
        for options in (dict(transform=from_origin(500010, 9000000, 10, 10)), dict(crs='EPSG:32749'), dict(width=17)):
            self.asset(2, **options); result, _, _ = self.read()
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertEqual(result['issue'], dict(code='IMAGE_MASK_GRID_MISMATCH', field='grid'))
            self.assertIsNotNone(result['image_header']); self.assertIsNotNone(result['mask_header'])
            self.assertIs(result['quality_mask_observation']['artifact_bytes_verified'], True)
            self.assertIs(result['artifact_bytes_verified'], False)

    def test_mask_count_dtype_rotation_and_size_reject(self):
        for options in (dict(count=2), dict(dtype='uint16'), dict(width=1025),
                        dict(transform=Affine(10, 1, 500000, 0, -10, 9000000))):
            self.asset(2, **options); result, _, _ = self.read()
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertEqual(result['issue']['code'], 'MASK_HEADER_INVALID')
            self.assertIs(result['quality_mask_observation']['artifact_bytes_verified'], True)

    def test_mask_opaque_and_vrt_never_reach_second_memoryfile(self):
        for raw in (b'opaque mask bytes', b'<VRTDataset rasterXSize="16" rasterYSize="16"/>'):
            self.asset(2, raw=raw)
            with patch.object(rasterio.io, 'MemoryFile', wraps=MemoryFile) as opened:
                result, _, _ = self.read()
            self.assertEqual(result['issue'], dict(code='MASK_FORMAT_UNSUPPORTED', field='mask'))
            self.assertEqual(opened.call_count, 1)  # actual image only; mask magic rejects
            self.assertIs(result['quality_mask_observation']['artifact_bytes_verified'], True)

    def test_missing_source_bands_never_guessed_after_131_bytes(self):
        self.base.mutate(0, lambda m: m['source'].pop('band_names'))
        with patch.object(module, '_header', side_effect=AssertionError('image header forbidden')) as image, \
             patch.object(module, '_mask_header', side_effect=AssertionError('mask header forbidden')) as mask:
            result, _, assets = self.read()
        self.assertEqual(result['issue']['code'], 'RASTER_BAND_SIGNATURE_INVALID')
        image.assert_not_called(); mask.assert_not_called()
        self.assertEqual((assets.count('image.bin'), assets.count('mask.bin')), (1, 1))
        self.assertIs(result['quality_mask_observation']['artifact_bytes_verified'], True)

    def test_131_failure_never_opens_headers_and_role_error_mapping_is_preserved(self):
        self.base.report_bytes(b'{"x":NaN}')
        with patch.object(module, '_header', side_effect=AssertionError('image header forbidden')) as image, \
             patch.object(module, '_mask_header', side_effect=AssertionError('mask header forbidden')) as mask:
            result, _, assets = self.read()
        self.assertEqual(result['issue'], dict(code='EVIDENCE_JSON_INVALID', field='quality_report'))
        self.assertEqual(assets, []); image.assert_not_called(); mask.assert_not_called()

    def test_change_between_131_and_header_snapshot_fails_same_sha_recheck(self):
        original = module.read_registered_quality_mask_files
        for target, role in ((self.base.image, 'image'), (self.base.mask, 'mask')):
            raw = target.read_bytes()
            def changed(*args):
                result = original(*args)
                target.write_bytes(raw + b'changed after131 bytes')
                return result
            db = self.store.db.read_bytes()
            with patch.object(module, 'read_registered_quality_mask_files', changed):
                result = module.inspect_registered_quality_mask_grid(self.store, *self.base.refs)
            self.assertEqual(result['issue'], dict(code='SHA256_MISMATCH', field=role))
            self.assertIs(result['quality_mask_observation']['artifact_bytes_verified'], True)
            self.assertIs(result['artifact_bytes_verified'], False)
            self.assertEqual(db, self.store.db.read_bytes())
            target.write_bytes(raw)

    def test_same_get_canonical_copy_supplies_header_names_and_invalid_input_zero_get(self):
        ref = self.base.image_ref; key = version_key(ref['id'], ref['version'])
        def changed(kind, identifier, record):
            if kind == 'dataset_versions' and identifier == key:
                record['manifest']['source'].pop('band_names')
                record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
            return record
        result, calls, _ = self.read(transform_record=changed)
        self.assertEqual(result['issue']['code'], 'RASTER_BAND_SIGNATURE_INVALID')
        self.assertEqual(calls.count(('dataset_versions', key)), 1)
        refs = [self.base.image_ref, self.base.report_ref, self.base.image_ref]
        result, calls, _ = self.read(refs)
        self.assertEqual(result['issue'], dict(code='INVALID_INPUT', field='references'))
        self.assertEqual(calls, [])
        tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
        methods = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(methods & {'read', 'read_masks', 'sample', 'statistics', 'dataset_mask'})


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = 'e994e834b7630f979d037bb52bf366f19a502a87'
    checks = []
    for name in ('backend/app/ml/registered_quality_mask_files.py', 'backend/app/ml/registry_raster_grid_normalization.py',
                 'backend/app/ml/per_scene_normalization_files.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_ACTUAL_IMAGE_MASK_GTIFF_METADATA_ONLY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_reads_or_writes=0, inference_training_pixel_mask_reads=0,
        UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Actual mask header1band uint8 and matching strict image grid do not verify mask values/conventions, cloud/nodata meaning, QA approval or scientific accuracy.',
          'Three get calls only, but image/mask each intentionally read twice and SHA checked; partial headers and131 byte success are historical observations, not complete132 success.',
          'Same-get canonical copies and later snapshot checks do not guarantee atomic Store/files or CPU/RSS/time/GDAL isolation.',
          'New standalone reader not connected to130/Workflow/API/UI. No frontend/build/browser/full-backend rerun. Prior1184 is historical; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/mask-grid-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
