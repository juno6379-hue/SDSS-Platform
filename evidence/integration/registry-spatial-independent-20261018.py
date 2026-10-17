"""Independent Registry bbox vs sampled GTiff-envelope diagnostic checks."""
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
import pyproj.network
import rasterio
from rasterio.warp import transform, transform_bounds
from app.dataset_registry import canonical_manifest, version_key
from app.ml import registry_raster_grid_normalization as raster_layer
from app.ml import registry_spatial_normalization as module
spec = importlib.util.spec_from_file_location('independent_raster_fixture', ROOT / 'evidence/integration/raster-grid-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/registry_spatial_normalization.py'
FROZEN = '3044f176093c462eb2a407cc4a3b7310ae115b8700c0f71735f05c245ac5c108'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('registry_aoi_verified', 'physical_coverage_verified', 'quality_report_verified', 'quality_mask_verified',
    'pixel_values_verified', 'source_authority_verified', 'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.fixture, self.store, self.rows, self.root = self.base.fixture, self.base.store, self.base.rows, self.base.root
        for i in range(6): self.spatial(i, [100, -20, 110, 0])

    def spatial(self, index, bbox, crs='EPSG:4326'):
        ref = self.rows[index]['image_ref']; key = version_key(ref['id'], ref['version'])
        record = self.store.get('dataset_versions', key)
        record['manifest']['spatial'] = dict(bbox=bbox, crs=crs)
        record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
        self.store.put('dataset_versions', record)

    def envelope(self):
        # Independent direct PROJ calculation on known fixture coordinates;
        # fixture/header IO is not repeated by130.
        return list(transform_bounds('EPSG:32748', 'OGC:CRS84', 500000, 8999840, 500160, 9000000, densify_pts=21))

    def read(self, rows=None, transform_record=None):
        files = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        network_before = pyproj.network.is_network_enabled()
        calls = []; images = []; get = self.store.get; path_open = Path.open
        image_paths = {self.root / f'scene-{i}' / 'image.bin' for i in range(6)}
        def observed_get(kind, key):
            calls.append((kind, key)); record = get(kind, key)
            return transform_record(kind, key, record) if transform_record else record
        def observed_open(path, *args, **kwargs):
            if path in image_paths: images.append(path)
            return path_open(path, *args, **kwargs)
        with patch.object(self.store, 'get', observed_get), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(Path, 'open', observed_open), \
             patch.object(raster_layer, '_header', wraps=raster_layer._header) as headers, \
             patch.object(rasterio.io.DatasetReader, 'read', side_effect=AssertionError('pixels')), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('masks')):
            result = module.inspect_registry_spatial_normalization(self.store, self.fixture.model_ref,
                self.fixture.report_sha, self.rows if rows is None else rows)
        self.assertEqual(files, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(network_before, pyproj.network.is_network_enabled())
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'raster_batch_observation',
            'spatial_observations', 'registry_bbox_contains_raster_envelope_verified', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'PINNED_YEARS_REGISTRY_ENVELOPE_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls, images, headers.call_count

    def test_actual_two_and_six_rows_no_extra_store_get_or_image_open(self):
        for count in (2, 6):
            result, calls, images, headers = self.read(self.rows[:count])
            self.assertEqual(result['status'], 'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
            self.assertEqual(len(calls), 1 + 3 * count)
            self.assertEqual(len(set(calls)), len(calls))
            self.assertEqual(len(images), 2 * count)  # inherited129 header +125 SHA read
            self.assertEqual(headers, count)
            self.assertIs(result['registry_bbox_contains_raster_envelope_verified'], True)
            self.assertIs(result['artifact_bytes_verified'], True)
            self.assertIs(result['raster_batch_observation']['registry_aoi_verified'], False)
            self.assertEqual([r['status'] for r in result['spatial_observations']], ['MATCHED_UNVERIFIED'] * count)

    def test_lon_lat_axis_epsg4326_crs84_and_independent_dense_edge_math(self):
        self.spatial(1, [100, -20, 110, 0], 'OGC:CRS84')
        result, _, _, _ = self.read(self.rows[:2])
        actual = result['spatial_observations'][0]['raster_wgs84_envelope']
        points = []
        for i in range(101):
            f = i / 100
            points.extend([(500000 + 160 * f, 8999840), (500000 + 160 * f, 9000000),
                           (500000, 8999840 + 160 * f), (500160, 8999840 + 160 * f)])
        lon, lat = transform('EPSG:32748', 'OGC:CRS84', [p[0] for p in points], [p[1] for p in points])
        expected = [min(lon), min(lat), max(lon), max(lat)]
        for a, b in zip(actual, expected): self.assertAlmostEqual(a, b, delta=1e-9)
        self.assertAlmostEqual(actual[0], 105, delta=1e-9)
        self.assertTrue(-10 < actual[1] < actual[3] < -8)
        self.assertEqual(result['spatial_observations'][0]['raster_wgs84_envelope'],
                         result['spatial_observations'][1]['raster_wgs84_envelope'])

    def test_epsilon_boundary_and_math_failfast_after_all_files_already_read(self):
        left, bottom, right, top = self.envelope(); t = 1e-7
        self.spatial(0, [left + t, bottom + t, right - t, top - t])
        self.assertEqual(self.read(self.rows[:2])[0]['status'], 'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
        self.spatial(0, [left + 2 * t, bottom, right, top])
        result, calls, images, headers = self.read()
        self.assertEqual(result['status'], 'SPATIAL_BLOCKED')
        self.assertEqual(result['issue']['code'], 'REGISTRY_BBOX_DOES_NOT_CONTAIN_ENVELOPE')
        self.assertEqual(result['raster_batch_observation']['status'], 'RASTER_GRID_MATCHED_UNVERIFIED')
        self.assertEqual((len(calls), len(images), headers), (19, 12, 6))
        self.assertEqual([r['status'] for r in result['spatial_observations']], ['BLOCKED'] + ['NOT_CHECKED'] * 5)
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_registry_crs_dateline_polar_and_broad_bbox_policies(self):
        for bbox, crs, code in (([500000, 8999840, 500160, 9000000], 'EPSG:32748', 'REGISTRY_SPATIAL_CRS_UNSUPPORTED'),
            ([-180, -20, 110, 0], 'EPSG:4326', 'SPATIAL_DATELINE_UNSUPPORTED'),
            ([-100, -20, 110, 0], 'OGC:CRS84', 'SPATIAL_DATELINE_UNSUPPORTED'),
            ([100, -85, 110, 0], 'EPSG:4326', 'SPATIAL_POLAR_UNSUPPORTED')):
            self.spatial(0, bbox, crs)
            result, _, _, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'SPATIAL_BLOCKED')
            self.assertEqual(result['issue']['code'], code)
        self.spatial(0, [100, -20, 110, 0])
        result, _, _, _ = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
        self.assertIs(result['physical_coverage_verified'], False)
        self.assertIs(result['registry_aoi_verified'], False)

    def test_captured_actual_get_copy_used_for_containment_without_reread(self):
        key = version_key(self.rows[0]['image_ref']['id'], self.rows[0]['image_ref']['version'])
        def changed(kind, identifier, record):
            if kind == 'dataset_versions' and identifier == key:
                record['manifest']['spatial']['bbox'] = [106, -20, 107, 0]  # excludes105E
                record['manifest'], record['manifest_sha256'] = canonical_manifest(record['manifest'])
            return record
        result, calls, images, headers = self.read(self.rows[:2], transform_record=changed)
        self.assertEqual(result['status'], 'SPATIAL_BLOCKED')
        self.assertEqual(result['spatial_observations'][0]['registry_bbox'], [106, -20, 107, 0])
        self.assertEqual(calls.count(('dataset_versions', key)), 1)
        self.assertEqual((len(calls), len(images), headers), (7, 4, 2))

    def test_upstream_header_failure_has_priority_and_skips_all_spatial_math(self):
        self.spatial(0, [500000, 8999840, 500160, 9000000], 'EPSG:32748')
        self.base.image(0, raw=b'opaque no raster header')
        with patch.object(module, '_envelope', side_effect=AssertionError('post math forbidden')):
            result, _, _, _ = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'RASTER_BLOCKED')
        self.assertEqual([r['status'] for r in result['spatial_observations']], ['NOT_CHECKED'] * 2)

    def test_transform_invalid_output_or_network_enabled_fail_closed_without_preference_mutation(self):
        for output, code in (((float('nan'), -10, 106, -9), 'SPATIAL_BOUNDS_INVALID'),
                             ((179, -10, -179, -9), 'SPATIAL_DATELINE_UNSUPPORTED'),
                             ((105, 84, 106, 85), 'SPATIAL_POLAR_UNSUPPORTED')):
            with patch('rasterio.warp.transform_bounds', return_value=output):
                result, _, _, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'SPATIAL_BLOCKED')
            self.assertEqual(result['issue']['code'], code)
        before = pyproj.network.is_network_enabled()
        with patch.object(pyproj.network, 'is_network_enabled', return_value=True), \
             patch('rasterio.warp.transform_bounds', side_effect=AssertionError('network-enabled math forbidden')):
            result, _, _, _ = self.read(self.rows[:2])
        self.assertEqual(result['issue']['code'], 'SPATIAL_TRANSFORM_UNAVAILABLE')
        self.assertEqual(before, pyproj.network.is_network_enabled())

    def test_invalid_global_model_failure_never_spatial_math_or_new_io(self):
        for mode in ('invalid', 'global', 'model'):
            rows = copy.deepcopy(self.rows[:2])
            if mode == 'invalid': rows[0]['year'] = True
            elif mode == 'global': self.fixture.manifest['normalization_mode'] = 'global'; self.fixture.bind_model()
            else:
                path = self.fixture.model_dir / 'best.pt'; path.write_bytes(path.read_bytes() + b'changed')
            with patch.object(module, '_envelope', side_effect=AssertionError('math forbidden')):
                result, calls, images, headers = self.read(rows)
            self.assertEqual(len(calls), 0 if mode == 'invalid' else 1)
            self.assertEqual((len(images), headers), (0, 0))
        tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
        methods = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(methods & {'open', 'read', 'read_masks', 'read_bytes', 'sample', 'statistics', 'dataset_mask'})


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '759eac034a0921f898aaf9b5e175421a222ec63f'
    checks = []
    for name in ('backend/app/ml/registry_raster_grid_normalization.py', 'backend/app/ml/registry_temporal_normalization.py',
                 'backend/app/ml/pinned_annual_normalization.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_REGISTRY_BBOX_VS_SAMPLED_WGS84_ENVELOPE', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_checkpoint_reads_or_writes=0, inference_training_pixel_mask_read_calls=0,
        UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Densify21 finite-sample envelope is not a guaranteed conservative bound or exact raster footprint.',
          'Registry lon/lat bbox containment within1e-7degree tolerance, not AOI truth, province-wide coverage, acquisition/source authority, QA or execution approval.',
          'Post-math NOT_CHECKED rows may already have completed every129 file/header read. Capture/base failures have different read histories.',
          'PROJ network preference is read only; full GDAL/network and CPU/RSS/time isolation, atomic snapshots and inherited Store/Torch limits are not guaranteed.',
          'Internal unwired observer; no API/UI/frontend/build/browser/full-backend rerun. Prior1184 history is not new. Do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/registry-spatial-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
