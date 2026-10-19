"""Small synthetic boundary topology tests; no real boundary data or repairs."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import shapely
from backend.app.data import recovery_boundary_topology as module

ROOT = Path(__file__).resolve().parents[1]


class BoundaryTopologyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.boundary = self.output / 'boundary.geojson'
        self.manifest = self.output / 'annual-window-report.json'
        self.ring = [[105, -6], [106, -6], [106, -5], [105, -5], [105, -6]]
        self.feature = {'type': 'Feature', 'properties': {'province_id': 'banten'}, 'geometry': {'type': 'Polygon', 'coordinates': [copy.deepcopy(self.ring)]}}
        self.document = {'type': 'FeatureCollection', 'features': [copy.deepcopy(self.feature)]}
        self.rows = [{'province': 'banten', 'source_window': {'boundary_path': str(self.boundary), 'boundary_sha256': ''}}]
        self.save()
    def tearDown(self): self.temp.cleanup()
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self, raw=None):
        self.boundary.write_text(json.dumps(self.document) if raw is None else raw, encoding='utf-8')
        for row in self.rows:
            if 'boundary_sha256' in row.get('source_window', {}): row['source_window']['boundary_sha256'] = self.sha(self.boundary)
        self.save_manifest()
    def save_manifest(self):
        self.manifest.write_text(json.dumps({'scenes': self.rows}), encoding='utf-8'); self.pin = self.sha(self.manifest)
    def inspect(self, **kwargs): return module.inspect_recovery_boundary_topology(self.root, self.pin, **kwargs)

    def test_valid_polygon_runtime_planar_area_and_shared_file_single_raw_read(self):
        self.rows.append(copy.deepcopy(self.rows[0])); self.save_manifest()
        real = module._read_bounded
        seen = []
        def read(path, *args): seen.append(path); return real(path, *args)
        with patch.object(module, '_read_bounded', side_effect=read): result = self.inspect()
        self.assertEqual(seen.count(self.boundary), 1)
        self.assertEqual(seen.count(self.manifest), 2)
        self.assertEqual(result['topology_validation'], 'TOPOLOGY_VALID')
        self.assertEqual(result['topology_engine_attempt_count'], 1)
        self.assertEqual(result['topology_feature_checks'][0]['area_square_degrees_planar'], 1)
        self.assertEqual(result['area_units'], 'square_degrees_planar_diagnostic')
        self.assertEqual(result['geometry_runtime']['shapely_version'], shapely.__version__)
        self.assertNotEqual(result['geometry_runtime']['geos_version'], 'UNKNOWN')
        self.assertEqual(result['status'], 'BLOCKED')
        for key in ['automatic_geometry_repair_performed', 'geometry_reprojected', 'cross_feature_overlap_checked', 'official_adm1_verified', 'boundary_authorization_verified', 'pixel_inside_coverage_checked', 'geometric_independence_checked', 'ready_for_training', 'scientific_accuracy_validated', 'settlement_authorized', 'automatic_resume_allowed']:
            self.assertIs(result[key], False)

    def test_self_intersection_outside_hole_overlapping_multipolygon_and_degenerate(self):
        variants = [
            {'type': 'Polygon', 'coordinates': [[[105,-6],[106,-5],[105,-5],[106,-6],[105,-6]]]},
            {'type': 'Polygon', 'coordinates': [self.ring, [[110,-6],[110.1,-6],[110.1,-5.9],[110,-5.9],[110,-6]]]},
            {'type': 'MultiPolygon', 'coordinates': [[self.ring], [self.ring]]},
            {'type': 'Polygon', 'coordinates': [[[105,-6],[105.5,-6],[106,-6],[105,-6]]]}]
        for geometry in variants:
            self.document['features'][0]['geometry'] = geometry; self.save()
            result = self.inspect()
            self.assertEqual(result['topology_validation'], 'TOPOLOGY_ISSUES_FOUND')
            self.assertEqual(result['files'][0]['status'], 'STRUCTURE_MATCH')
            self.assertEqual(result['topology_feature_checks'][0]['status'], 'INVALID_TOPOLOGY')
            self.assertIs(result['topology_feature_checks'][0]['is_valid'], False)
            self.assertNotEqual(result['topology_feature_checks'][0]['validity_reason'], 'Valid Geometry')

    def test_valid_hole_and_separate_multipolygon_are_valid(self):
        hole = [[105.2,-5.8],[105.2,-5.6],[105.4,-5.6],[105.4,-5.8],[105.2,-5.8]]
        self.document['features'][0]['geometry']['coordinates'].append(hole); self.save()
        result = self.inspect()
        self.assertEqual(result['topology_validation'], 'TOPOLOGY_VALID')
        self.assertAlmostEqual(result['topology_feature_checks'][0]['area_square_degrees_planar'], .96)
        other = [[107,-6],[108,-6],[108,-5],[107,-5],[107,-6]]
        self.document['features'][0]['geometry'] = {'type': 'MultiPolygon', 'coordinates': [[self.ring], [other]]}; self.save()
        self.assertEqual(self.inspect()['topology_validation'], 'TOPOLOGY_VALID')

    def test_separate_valid_features_overlap_is_explicitly_not_checked(self):
        other = copy.deepcopy(self.document['features'][0]); other['properties']['province_id'] = 'other'
        self.document['features'].append(other); self.save()
        result = self.inspect()
        self.assertEqual(result['topology_validation'], 'TOPOLOGY_VALID')
        self.assertEqual(result['topology_engine_attempt_count'], 2)
        self.assertIs(result['cross_feature_overlap_checked'], False)

    def test_legacy_unknown_and_no_recorded_refs_do_not_invent_feature_checks(self):
        self.rows.append({'province': 'banten', 'source_window': {}}); self.save_manifest()
        result = self.inspect()
        self.assertEqual(result['topology_validation'], 'KNOWN_TOPOLOGY_VALID_PARTIAL')
        self.assertEqual(result['topology_engine_attempt_count'], 1)
        self.assertEqual(len(result['unknown_references']), 1)
        self.rows = [self.rows[1]]; self.save_manifest()
        with patch.object(module, '_feature_topology') as checked:
            result = self.inspect()
            self.assertEqual(result['topology_validation'], 'NO_RECORDED_REFERENCES')
            checked.assert_not_called()

    def test_plan_sha_structure_and_region_issues_never_call_topology(self):
        original_rows, original_document = copy.deepcopy(self.rows), copy.deepcopy(self.document)
        variants = [lambda: self.rows[0]['source_window'].pop('boundary_sha256'),
                    lambda: self.rows[0]['source_window'].__setitem__('boundary_sha256', '0' * 64),
                    lambda: self.document['features'][0]['geometry'].__setitem__('coordinates', []),
                    lambda: self.document['features'].append(copy.deepcopy(self.document['features'][0])),
                    lambda: self.rows[0].__setitem__('province', 'not-found')]
        for mutate in variants:
            self.rows, self.document = copy.deepcopy(original_rows), copy.deepcopy(original_document)
            mutate()
            if self.rows[0]['source_window'].get('boundary_sha256') == '0' * 64: self.save_manifest()
            elif 'boundary_sha256' not in self.rows[0]['source_window']: self.save_manifest()
            else: self.save()
            with patch.object(module, '_feature_topology') as checked:
                result = self.inspect()
                self.assertTrue(result['topology_validation'].startswith(('NOT_STARTED', 'NOT_CHECKED')))
                checked.assert_not_called()

    def test_feature_vertex_byte_depth_limits_block_geometry_engine(self):
        for kwargs in [{'max_vertices': 4}, {'max_local_bytes': self.boundary.stat().st_size - 1}, {'max_json_depth': 3}]:
            with patch.object(module, '_feature_topology') as checked:
                with self.assertRaises(ValueError): self.inspect(**kwargs)
                checked.assert_not_called()
        self.document['features'].append(copy.deepcopy(self.document['features'][0])); self.save()
        with patch.object(module, '_feature_topology') as checked:
            with self.assertRaises(ValueError): self.inspect(max_features=1)
            checked.assert_not_called()

    def test_engine_error_unavailability_and_nonfinite_or_empty_geometry_are_unknown_or_invalid(self):
        runtime = {'available': True, 'shapely_version': 'test', 'geos_version': 'test'}
        def fail(geometry): raise RuntimeError('synthetic engine error')
        with patch.object(module, '_geometry_runtime', return_value=(runtime, fail, lambda g: 'unused')):
            result = self.inspect()
            self.assertEqual(result['topology_feature_checks'][0]['status'], 'UNKNOWN_ENGINE_ERROR')
            self.assertEqual(result['topology_validation'], 'TOPOLOGY_ISSUES_FOUND')
        with patch.object(module, '_geometry_runtime', return_value=({'available': False, 'shapely_version': 'UNKNOWN', 'geos_version': 'UNKNOWN'}, None, None)):
            self.assertEqual(self.inspect()['topology_validation'], 'NOT_CHECKED_ENGINE_UNAVAILABLE')
        for fake in [types.SimpleNamespace(is_empty=True, is_valid=True, area=0), types.SimpleNamespace(is_empty=False, is_valid=True, area=float('nan'))]:
            result = module._feature_topology(self.feature, lambda geometry: fake, lambda geometry: 'Valid Geometry')
            self.assertEqual(result['status'], 'INVALID_TOPOLOGY')
            if not fake.is_empty: self.assertIsNone(result['area_square_degrees_planar'])

    def test_missing_runtime_version_fields_preserve_unknown_without_crashing(self):
        with patch.object(shapely, '__version__', None), patch.object(shapely, 'geos_version_string', None), patch.dict(sys.modules, {'shapely.geos': types.SimpleNamespace(geos_version_string=None)}):
            runtime, shape, explain = module._geometry_runtime()
        self.assertTrue(runtime['available'])
        self.assertEqual(runtime['shapely_version'], 'UNKNOWN')
        self.assertEqual(runtime['geos_version'], 'UNKNOWN')
        self.assertTrue(callable(shape)); self.assertTrue(callable(explain))

    def test_no_repair_reproject_source_writes_and_old_public_inspector_not_called(self):
        from shapely.geometry.base import BaseGeometry
        from backend.app.data import recovery_boundary
        before = {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        with patch.object(shapely, 'buffer', side_effect=AssertionError('repair forbidden')), patch.object(shapely, 'make_valid', side_effect=AssertionError('repair forbidden')), patch.object(BaseGeometry, 'buffer', side_effect=AssertionError('repair forbidden')), patch.object(recovery_boundary, 'inspect_recovery_boundary', side_effect=AssertionError('public reread forbidden')):
            self.assertEqual(self.inspect()['topology_validation'], 'TOPOLOGY_VALID')
        self.assertEqual(before, {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_utf16_escaped_quote_depth_and_strict_json_fail_before_engine(self):
        for encoding in ['utf-16', 'utf-32']:
            text = '{"escaped_quote":"\\\"","nested":' + '[' * 80 + '0' + ']' * 80 + '}'
            self.boundary.write_bytes(text.encode(encoding)); self.rows[0]['source_window']['boundary_sha256'] = self.sha(self.boundary); self.save_manifest()
            with patch.object(module, '_feature_topology') as checked:
                with self.assertRaises(ValueError): self.inspect()
                checked.assert_not_called()
        for raw in ['{"features":[],"features":[]}', '{"x":NaN}', '{"x":1e999}']:
            self.save(raw)
            with self.assertRaises(ValueError): self.inspect()

    def test_path_pins_and_change_guards_preserved(self):
        for pin in [True, 'A' * 64, '0' * 64]:
            with self.assertRaises(ValueError): module.inspect_recovery_boundary_topology(self.root, pin)
        original = copy.deepcopy(self.rows)
        for path in ['https://invalid.example/a', '//server/share/a', str(self.workspace / 'outside'), str(self.output)]:
            self.rows = copy.deepcopy(original); self.rows[0]['source_window']['boundary_path'] = path; self.save_manifest()
            with self.assertRaises(ValueError): self.inspect()
        self.rows = original; self.save()
        real = module._read_bounded
        def mutate(path, *args):
            raw = real(path, *args)
            if path == self.boundary: self.boundary.write_text('{}', encoding='utf-8')
            return raw
        with patch.object(module, '_read_bounded', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.save()
        real_resolve = module._confined; calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.boundary:
                calls += 1
                if calls >= 2: return self.output / 'elsewhere'
            return real_resolve(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_cli_cp949_utf8_new_evidence_and_output_protection(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_boundary_topology.py'), '--data-root', str(self.root), '--expected-manifest-sha256', self.pin, *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr); self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'topology.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['topology_validation'], 'TOPOLOGY_VALID')
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1); self.assertEqual(output.read_bytes(), before)
        self.assertEqual(cli('--output', self.boundary).returncode, 1)
        with tempfile.TemporaryDirectory() as external:
            path = Path(external) / 'no.json'
            self.assertEqual(cli('--output', path).returncode, 1); self.assertFalse(path.exists())
        self.manifest.write_text('{}', encoding='utf-8')
        result = cli(); self.assertEqual(result.returncode, 1); self.assertTrue(result.stderr.isascii())


if __name__ == '__main__': unittest.main()
