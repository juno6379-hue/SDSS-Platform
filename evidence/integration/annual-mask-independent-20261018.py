"""Independent annual spatial+binary-mask composition; actual Temp fixtures only."""
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
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from app.dataset_registry import canonical_manifest, register_version, version_key
from app.ml import annual_quality_mask_diagnostics as module
spec = importlib.util.spec_from_file_location('independent_annual_spatial_fixture', ROOT / 'evidence/integration/registry-spatial-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/annual_quality_mask_diagnostics.py'
FROZEN = 'c7dcf589ead5abd94365cf816314f5a2936e029ce9c23bdac12dd2d63afe6abe'
TEST_FROZEN = '0bba28e14244f6dc2d753bab6bc14ee3b1e7e0f6639016b40f1ef71ac5d11f38'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified',
    'minimum_validity_policy_verified', 'registry_aoi_verified', 'source_authority_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.fixture, self.store, self.root = self.base.fixture, self.base.store, self.base.root
        self.rows = copy.deepcopy(self.base.rows)
        for i, row in enumerate(self.rows):
            directory = self.root / f'scene-{i}'
            mask = directory / 'mask.tif'; mask.write_bytes(self.mask_bytes(np.indices((16, 16)).sum(axis=0).astype('uint8') % 2))
            mask_ref = dict(id=f'annual-mask-{i}', version='v1', sha256=sha(mask.read_bytes()))
            report = directory / 'quality.json'
            body = dict(schema_version=1, scope='LCLUC_QUALITY_MASK_EVIDENCE', image_ref=row['image_ref'], mask_ref=mask_ref, quality_status='RAW')
            report.write_text(json.dumps(body), encoding='utf-8')
            report_ref = dict(id=f'annual-quality-{i}', version='v1', sha256=sha(report.read_bytes()))
            image_key = version_key(row['image_ref']['id'], row['image_ref']['version'])
            image = self.store.get('dataset_versions', image_key)
            image['manifest']['quality_report_ref'] = report.relative_to(self.root).as_posix(); self.save(image)
            for ref, path, kind in ((mask_ref, mask, 'raster'), (report_ref, report, 'document')):
                manifest = copy.deepcopy(image['manifest'])
                manifest.update(dataset_id=ref['id'], version=ref['version'], sha256=ref['sha256'], data_type=kind,
                    artifact_uri=path.relative_to(self.root).as_posix(), lineage=[])
                manifest['source'] = dict(institution='synthetic fixture', product='mask evidence fixture', license='test only')
                if kind == 'raster': manifest['source']['mask_semantics'] = dict(schema_version=1, kind='binary_validity', valid_value=1, invalid_value=0)
                else: manifest['lineage'] = [dict(row['image_ref'], role='quality_input_image'), dict(mask_ref, role='quality_input_mask')]
                register_version(self.store, manifest)
            row.update(quality_report_ref=report_ref, mask_ref=mask_ref)

    def mask_bytes(self, values):
        with MemoryFile() as memory:
            with memory.open(driver='GTiff', width=16, height=16, count=1, dtype='uint8', crs='EPSG:32748',
                    transform=from_origin(500000, 9000000, 10, 10)) as dataset:
                dataset.write(values, 1)
            return memory.read()

    def save(self, record):
        record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
        self.store.put('dataset_versions', record)

    def update_mask(self, index, values):
        row = self.rows[index]; mask = self.root / f'scene-{index}' / 'mask.tif'
        mask.write_bytes(self.mask_bytes(values)); row['mask_ref']['sha256'] = sha(mask.read_bytes())
        record = self.store.get('dataset_versions', version_key(row['mask_ref']['id'], row['mask_ref']['version']))
        record['manifest']['sha256'] = row['mask_ref']['sha256']; self.save(record)
        report = self.root / f'scene-{index}' / 'quality.json'
        body = json.loads(report.read_text()); body['mask_ref'] = row['mask_ref']
        report.write_text(json.dumps(body), encoding='utf-8'); row['quality_report_ref']['sha256'] = sha(report.read_bytes())
        record = self.store.get('dataset_versions', version_key(row['quality_report_ref']['id'], row['quality_report_ref']['version']))
        record['manifest']['sha256'] = row['quality_report_ref']['sha256']
        record['manifest']['lineage'][1]['sha256'] = row['mask_ref']['sha256']; self.save(record)

    def read(self, rows=None, transform_record=None, on_get=None):
        before = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        get, actual_read = self.store.get, rasterio.io.DatasetReader.read
        calls = []; pixels = []
        def observed(kind, key):
            calls.append((kind, key))
            if on_get: on_get(kind, key)
            record = get(kind, key)
            return transform_record(kind, key, record) if transform_record else record
        def read_pixels(dataset, *args, **kwargs):
            pixels.append((dataset.count, args, kwargs))
            self.assertEqual(dataset.count, 1)
            self.assertEqual((args, kwargs), ((1,), dict(masked=False)))
            return actual_read(dataset, *args, **kwargs)
        with patch.object(self.store, 'get', observed), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(torch, 'load', wraps=torch.load) as model_load, \
             patch.object(rasterio.io.DatasetReader, 'read', read_pixels), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('intrinsic mask pixels')):
            result = module.inspect_annual_quality_mask_diagnostics(self.store, self.fixture.model_ref,
                self.fixture.report_sha, self.rows if rows is None else rows)
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'annual_spatial_observation',
            'mask_observations', 'spatial_observation_calls', 'mask_observation_calls', 'checked_rows',
            'artifact_bytes_verified', 'mask_values_verified', 'registry_manifest_join_verified', *FLAGS})
        self.assertEqual(result['scope'], 'ANNUAL_REGISTERED_QUALITY_MASK_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls, pixels, model_load.call_count

    def test_actual_two_and_six_years_model_once_1_plus_6n_gets_mask_reads_n(self):
        for count in (2, 6):
            result, calls, pixels, loads = self.read(self.rows[:count])
            self.assertEqual(result['status'], 'ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED')
            self.assertEqual((len(calls), len(pixels), loads), (1 + 6 * count, count, 1))
            self.assertEqual(result['spatial_observation_calls'], 1)
            self.assertEqual((result['mask_observation_calls'], result['checked_rows']), (count, count))
            for row in result['mask_observations']:
                self.assertEqual(set(row), {'year', 'status', 'mask_observation', 'registry_manifest_join_verified', 'issue'})
                self.assertEqual(row['mask_observation']['counts'], dict(valid_pixels=128, invalid_pixels=128, total_pixels=256))
                self.assertIs(row['registry_manifest_join_verified'], True)
            self.assertIs(result['artifact_bytes_verified'], True)
            self.assertIs(result['annual_spatial_observation']['registry_aoi_verified'], False)

    def test_invalid_sixth_row_ref_schema_or_order_is_pre_model_and_store(self):
        variants = []
        for change in (lambda r: r.pop('mask_ref'), lambda r: r['mask_ref'].update(version='latest'),
                       lambda r: r.update(year=True), lambda r: r.update(mask_ref=r['image_ref'])):
            rows = copy.deepcopy(self.rows); change(rows[5]); variants.append(rows)
        for rows in variants:
            result, calls, pixels, loads = self.read(rows)
            self.assertEqual(result['status'], 'INVALID_INPUT')
            self.assertEqual((calls, pixels, loads), ([], [], 0))

    def test_middle_mask_failure_failfast_after_full_130_and_partial_counts(self):
        values = np.ones((16, 16), dtype='uint8'); values[0, 0] = 255
        self.update_mask(1, values)
        result, calls, pixels, loads = self.read()
        self.assertEqual(result['status'], 'MASK_BLOCKED')
        self.assertEqual(result['annual_spatial_observation']['status'], 'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
        self.assertEqual((len(calls), len(pixels), loads), (25, 2, 1))
        self.assertEqual([r['status'] for r in result['mask_observations']], ['MATCHED_UNVERIFIED', 'BLOCKED'] + ['NOT_CHECKED'] * 4)
        self.assertEqual(result['checked_rows'], 2)
        self.assertIsNone(result['mask_observations'][1]['mask_observation']['counts'])
        self.assertIs(result['registry_manifest_join_verified'], False)

    def test_changed_registry_image_manifest_same_file_sha_is_join_blocked(self):
        row = self.rows[1]; key = version_key(row['image_ref']['id'], row['image_ref']['version']); seen = 0
        def changed(kind, identifier, record):
            nonlocal seen
            if kind == 'dataset_versions' and identifier == key:
                seen += 1
                if seen == 2:
                    record['manifest']['source']['institution'] = 'changed metadata same image bytes'
                    record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
            return record
        result, calls, pixels, loads = self.read(transform_record=changed)
        self.assertEqual(result['status'], 'MASK_BLOCKED')
        self.assertEqual(result['issue'], dict(code='REGISTRY_IMAGE_MANIFEST_CHANGED', field='image_manifest', year=2021))
        self.assertEqual((len(calls), len(pixels), loads), (25, 2, 1))
        blocked = result['mask_observations'][1]
        self.assertEqual(blocked['mask_observation']['status'], 'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
        self.assertEqual(blocked['mask_observation']['counts']['valid_pixels'], 128)
        self.assertIs(blocked['registry_manifest_join_verified'], False)
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_normalization_numeric_string_blocks_130_before_any_mask_values(self):
        row = self.rows[0]; path = self.root / 'scene-0' / 'evidence.json'
        evidence = json.loads(path.read_text()); evidence['scale'] = '0.0001'
        path.write_text(json.dumps(evidence), encoding='utf-8'); row['evidence_ref']['sha256'] = sha(path.read_bytes())
        record = self.store.get('dataset_versions', version_key(row['evidence_ref']['id'], row['evidence_ref']['version']))
        record['manifest']['sha256'] = row['evidence_ref']['sha256']; self.save(record)
        result, calls, pixels, loads = self.read()
        self.assertEqual(result['status'], 'ANNUAL_SPATIAL_BLOCKED')
        self.assertEqual((len(pixels), loads), (0, 1))
        self.assertEqual(result['mask_observation_calls'], 0)
        self.assertEqual({r['status'] for r in result['mask_observations']}, {'NOT_CHECKED'})

    def test_all_zero_not_quality_approval_and_input_snapshot_is_preserved(self):
        self.update_mask(0, np.zeros((16, 16), dtype='uint8'))
        rows = copy.deepcopy(self.rows[:2])
        def mutate(kind, key):
            if kind == 'models':
                rows[1]['mask_ref']['sha256'] = '0' * 64
                rows[1]['year'] = 2199
        result, _, pixels, _ = self.read(rows, on_get=mutate)
        self.assertEqual(result['status'], 'ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertEqual([r['year'] for r in result['mask_observations']], [2020, 2021])
        self.assertEqual(result['mask_observations'][0]['mask_observation']['counts'], dict(valid_pixels=0, invalid_pixels=256, total_pixels=256))
        self.assertIs(result['minimum_validity_policy_verified'], False)

    def test_quality_pin_conflict_and_model_pin_failure_do_not_claim_aggregate(self):
        rows = copy.deepcopy(self.rows[:2]); rows[0]['quality_report_ref']['sha256'] = '0' * 64
        result, calls, pixels, loads = self.read(rows)
        self.assertEqual(result['status'], 'MASK_BLOCKED')
        self.assertEqual(result['issue']['code'], 'REGISTRY_REFERENCE_CONFLICT')
        self.assertEqual(pixels, [])
        checkpoint = self.fixture.model_dir / 'best.pt'; checkpoint.write_bytes(checkpoint.read_bytes() + b'changed')
        result, calls, pixels, loads = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'ANNUAL_SPATIAL_BLOCKED')
        self.assertEqual((len(calls), len(pixels), loads), (1, 0, 0))
        self.assertEqual(result['mask_observation_calls'], 0)


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = 'c8ce70a082705fe270806515efbea94a9f4ed07c'
    checks = []
    for name in ('backend/app/ml/registry_spatial_normalization.py', 'backend/app/ml/registered_binary_mask_values.py',
                 'backend/app/ml/registered_quality_mask_files.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    test_sha = sha((ROOT / 'tests/test_annual_quality_mask_diagnostics.py').read_bytes())
    payload = dict(scope='SYNTHETIC_TEMP_ANNUAL_SPATIAL_AND_BINARY_MASK_JOIN', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), test_sha256=test_sha,
        frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN, frozen_test_matches=test_sha == TEST_FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_checkpoint_reads_or_writes=0, image_pixel_reads=0, intrinsic_mask_reads=0,
        training_inference_calls=0, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Readonly130 then per-row133 sequentially; image manifest SHA join detects this intervening metadata change, not a global atomic snapshot or complete TOCTOU elimination.',
          'NOT_CHECKED mask rows may already have completed all130 image reads. Nested133 counts may remain historical success when the outer manifest join fails.',
          'All-zero masks can pass diagnostics; no actual annual data completeness, QA/semantic truth/minimum coverage, independent accuracy, model or execution approval.',
          'Internal unwired helper; inherited Store/Torch/GDAL resource and authority limits remain. No API/UI/frontend/build/browser/full-backend rerun. Prior1184 is history; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/annual-mask-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] and payload['frozen_test_matches'] else 1)
