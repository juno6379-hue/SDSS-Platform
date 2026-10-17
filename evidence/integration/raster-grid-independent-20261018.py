"""Independent actual GTiff metadata/grid fixtures; never operating raster IO."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.runtime'), str(ROOT / 'backend')]
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import Affine, from_origin
from app.dataset_registry import canonical_manifest, version_key
from app.ml import registry_raster_grid_normalization as module
spec = importlib.util.spec_from_file_location('independent_temporal_fixture', ROOT / 'evidence/integration/temporal-normalization-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/registry_raster_grid_normalization.py'
FROZEN = '17371e6a2a49a9845bf2a5d6b2cb0a777808400ac814b2d14e6347d7eb992501'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('registry_aoi_verified', 'quality_report_verified', 'quality_mask_verified', 'pixel_values_verified',
    'state_dict_verified', 'source_authority_verified', 'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported')
JUNCTION = dict(created=False, rejected=False, link_only_removed=False, target_preserved=False)


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.fixture = self.base.fixture
        self.store, self.rows, self.root = self.base.store, self.base.rows, self.fixture.root
        for index in range(6): self.image(index)

    def image(self, index, raw=None, **options):
        if raw is None:
            profile = dict(driver='GTiff', width=16, height=16, count=6, dtype='uint16', crs='EPSG:32748',
                           transform=from_origin(500000, 9000000, 10, 10))
            names = options.pop('names', tuple(self.fixture.names))
            profile.update(options)
            with MemoryFile() as memory:
                with memory.open(**profile) as dataset:
                    dataset.descriptions = names
                raw = memory.read()
        path = self.root / f'scene-{index}' / 'image.bin'; path.write_bytes(raw)
        ref = self.rows[index]['image_ref']; ref['sha256'] = sha(raw)
        record = self.store.get('dataset_versions', version_key(ref['id'], ref['version']))
        record['manifest']['sha256'] = ref['sha256']; self.save_record(record)
        ref = self.rows[index]['evidence_ref']
        record = self.store.get('dataset_versions', version_key(ref['id'], ref['version']))
        record['manifest']['lineage'][0]['sha256'] = sha(raw); self.save_record(record)

    def save_record(self, record):
        record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
        self.store.put('dataset_versions', record)

    def read(self, rows=None):
        before = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        calls = []; get = self.store.get
        def observed(kind, key): calls.append((kind, key)); return get(kind, key)
        with patch.object(self.store, 'get', observed), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(rasterio.io.DatasetReader, 'read', side_effect=AssertionError('pixel read')), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('mask read')):
            result = module.inspect_registry_raster_grid_normalization(self.store, self.fixture.model_ref,
                self.fixture.report_sha, self.rows if rows is None else rows)
        after = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'temporal_batch_observation',
            'header_observations', 'raster_header_verified', 'cross_scene_grid_verified', 'artifact_bytes_verified',
            'registry_temporal_year_verified', *FLAGS})
        self.assertEqual(result['scope'], 'PINNED_YEARS_RASTER_GRID_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls

    def test_actual_two_and_six_gtiffs_headers_grid_without_pixels_or_extra_get(self):
        for count in (2, 6):
            result, calls = self.read(self.rows[:count])
            self.assertEqual(result['status'], 'RASTER_GRID_MATCHED_UNVERIFIED')
            self.assertEqual(len(calls), 1 + 3 * count)
            self.assertEqual(len(set(calls)), len(calls))
            for flag in ('raster_header_verified', 'cross_scene_grid_verified', 'artifact_bytes_verified',
                         'registry_temporal_year_verified'): self.assertIs(result[flag], True)
            header = result['header_observations'][0]['header']
            self.assertEqual(set(header), {'width', 'height', 'count', 'crs_wkt', 'transform', 'bounds', 'band_names'})
            self.assertEqual(header['bounds'], [500000., 8999840., 500160., 9000000.])
            self.assertEqual(header['band_names'], self.fixture.names)
            nested = result['temporal_batch_observation']['batch_observation']
            self.assertEqual(nested['model_observation_calls'], 1)
            self.assertIs(nested['raster_header_verified'], False)
            self.assertIs(nested['temporal_year_verified'], False)

    def test_actual_crs_shift_and_shape_mismatch_failfast(self):
        for options in (dict(crs='EPSG:32749'), dict(transform=from_origin(500010, 9000000, 10, 10)), dict(width=17)):
            self.image(1, **options); result, calls = self.read()
            self.assertEqual(result['status'], 'RASTER_BLOCKED')
            self.assertEqual(result['issue'], dict(code='RASTER_GRID_MISMATCH', field='grid', year=2021))
            self.assertEqual(len(calls), 5)
            self.assertEqual([r['status'] for r in result['header_observations']], ['MATCHED_UNVERIFIED', 'BLOCKED'])
            self.assertIs(result['cross_scene_grid_verified'], False)
            self.image(1)

    def test_actual_missing_or_ordered_descriptions_are_not_guessed(self):
        for names in ((None,) * 6, tuple(reversed(self.fixture.names))):
            self.image(0, names=names); result, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'RASTER_BLOCKED')
            self.assertEqual(result['issue']['code'], 'RASTER_BAND_SIGNATURE_INVALID')

    def test_non_projected_foot_units_rotation_and_size_are_rejected(self):
        for options, field in ((dict(crs='EPSG:4326'), 'crs'), (dict(crs='EPSG:2227'), 'crs'),
                              (dict(transform=Affine(10, 1, 500000, 0, -10, 9000000)), 'transform'),
                              (dict(width=1025), 'shape')):
            self.image(0, **options); result, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'RASTER_BLOCKED')
            self.assertEqual(result['issue']['code'], 'RASTER_HEADER_INVALID')
            self.assertEqual(result['issue']['field'], field)

    def test_opaque_and_vrt_rejected_before_memoryfile(self):
        for raw in (b'not a raster', b'<VRTDataset rasterXSize="16" rasterYSize="16"><VRTRasterBand dataType="UInt16" band="1"/></VRTDataset>'):
            self.image(0, raw=raw)
            with patch.object(rasterio.io, 'MemoryFile', side_effect=AssertionError('must reject magic before GDAL')):
                result, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'RASTER_BLOCKED')
            self.assertEqual(result['issue']['code'], 'RASTER_FORMAT_UNSUPPORTED')

    def test_missing_decl_access_policy_precede_actual_header_io(self):
        ref = self.rows[0]['image_ref']; key = version_key(ref['id'], ref['version'])
        original = self.store.get('dataset_versions', key)
        for mutation, code in ((lambda m: m['source'].pop('band_names'), 'RASTER_BAND_SIGNATURE_INVALID'),
                               (lambda m: m.update(access_class='RESTRICTED'), 'ACCESS_DECLARATION_BLOCKED')):
            record = copy.deepcopy(original); mutation(record['manifest']); self.save_record(record)
            with patch.object(module, '_snapshot', side_effect=AssertionError('header file read forbidden')):
                result, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'RASTER_BLOCKED')
            self.assertEqual(result['issue']['code'], code)
            self.store.put('dataset_versions', original)

    def test_header_snapshot_then_byte_change_is_rejected_by_later_125(self):
        original = module._header
        path = self.root / 'scene-0' / 'image.bin'
        def change(raw, names):
            value = original(raw, names)
            path.write_bytes(path.read_bytes() + b'changed after header snapshot')
            return value
        # Deliberate test mutation makes a whole-tree no-write assertion unsuitable;
        # keep DB digest and explicit final failure checks separate.
        before = self.store.db.read_bytes()
        with patch.object(module, '_header', change):
            result = module.inspect_registry_raster_grid_normalization(self.store, self.fixture.model_ref,
                self.fixture.report_sha, self.rows[:2])
        self.assertEqual(before, self.store.db.read_bytes())
        self.assertEqual(result['status'], 'SCENE_BLOCKED')
        self.assertEqual(result['header_observations'][0]['status'], 'MATCHED_UNVERIFIED')
        self.assertIs(result['raster_header_verified'], False)
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_actual_junction_blocked_before_gdal_and_link_only_removed(self):
        if os.name != 'nt': self.skipTest('Windows actual junction only')
        link, target = self.root / 'junction', self.root / 'scene-0'
        created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(created.returncode, 0); JUNCTION['created'] = True
        ref = self.rows[0]['image_ref']; key = version_key(ref['id'], ref['version'])
        record = self.store.get('dataset_versions', key)
        record['manifest']['artifact_uri'] = 'junction/image.bin'; self.save_record(record)
        try:
            with patch.object(module, '_header', side_effect=AssertionError('reparse cannot reach GDAL')):
                result = module.inspect_registry_raster_grid_normalization(self.store, self.fixture.model_ref,
                    self.fixture.report_sha, self.rows[:2])
            self.assertEqual(result['status'], 'RASTER_BLOCKED')
            self.assertEqual(result['issue']['code'], 'PATH_INVALID'); JUNCTION['rejected'] = True
        finally:
            self.assertEqual(link.absolute().parent, self.root)
            self.assertEqual(link.name, 'junction')
            self.assertEqual(os.lstat(link).st_reparse_tag, 0xA0000003)
            os.rmdir(link)
            JUNCTION['link_only_removed'] = not link.exists()
            JUNCTION['target_preserved'] = (target / 'image.bin').is_file()

    def test_invalid_global_and_model_failure_header_zero_and_no_pixel_call_sites(self):
        for mode in ('invalid', 'global', 'model_failure'):
            rows = copy.deepcopy(self.rows[:2])
            if mode == 'invalid': rows[0]['year'] = True
            elif mode == 'global': self.fixture.manifest['normalization_mode'] = 'global'; self.fixture.bind_model()
            else:
                path = self.fixture.model_dir / 'best.pt'; path.write_bytes(path.read_bytes() + b'tamper')
            with patch.object(module, '_header', side_effect=AssertionError('header forbidden')):
                result, calls = self.read(rows)
            self.assertEqual(result['header_observations'], [])
            self.assertEqual(len(calls), 0 if mode == 'invalid' else 1)
        tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
        methods = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(methods & {'read', 'read_masks', 'sample', 'statistics', 'overviews', 'dataset_mask'})


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '97e712d4476eb00680469d40972c571172930f3f'
    checks = []
    for name in ('backend/app/ml/registry_temporal_normalization.py', 'backend/app/ml/pinned_annual_normalization.py',
                 'backend/app/ml/registered_per_scene_files.py', 'backend/app/ml/per_scene_normalization_files.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_ACTUAL_GTIFF_HEADERS_AND_STRICT_GRID_ONLY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        actual_windows_junction=JUNCTION, operating_Store_API_registration_checkpoint_reads_or_writes=0,
        inference_training_pixel_mask_read_calls=0, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Metadata-only GTiff interpretation and strict canonical WKT/shape/affine equality, not raster values, masks, actual AOI, physical acquisition, calibration or scientific accuracy.',
          'Snapshot before GDAL and later same-SHA recheck reduce this change gap, not global atomicity or all races. GDAL/Torch/Store parsing do not guarantee CPU/RSS/time isolation.',
          'Internal unwired observer; existing temporal/batch nested flags retain their narrower scopes. No API/UI/frontend/build/browser/full-backend rerun. Prior1184 is history; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/raster-grid-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
