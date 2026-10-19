"""Tiny GeoJSON tests for bounded declared boundary structure/province diagnostics."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.app.data import recovery_boundary as module

ROOT = Path(__file__).resolve().parents[1]


class BoundaryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.manifest = self.output / 'annual-window-report.json'
        self.boundary = self.output / 'boundary.geojson'
        self.ring = [[105, -6], [106, -6], [106, -5], [105, -6]]
        self.document = {'type': 'FeatureCollection', 'features': [self.feature()]}
        self.rows = [{'province': 'banten', 'source_window': {'boundary_path': str(self.boundary), 'boundary_sha256': ''}}]
        self.save()

    def tearDown(self): self.temp.cleanup()
    def feature(self): return {'type': 'Feature', 'properties': {'province_id': 'banten'}, 'geometry': {'type': 'Polygon', 'coordinates': [copy.deepcopy(self.ring)]}}
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self, raw=None):
        self.boundary.write_text(json.dumps(self.document) if raw is None else raw, encoding='utf-8')
        sha = self.sha(self.boundary)
        for row in self.rows:
            if type(row) is dict and type(row.get('source_window')) is dict and 'boundary_sha256' in row['source_window']: row['source_window']['boundary_sha256'] = sha
        self.save_manifest()
    def save_manifest(self):
        self.manifest.write_text(json.dumps({'scenes': self.rows}), encoding='utf-8'); self.pin = self.sha(self.manifest)
    def inspect(self, **kwargs): return module.inspect_recovery_boundary(self.root, self.pin, **kwargs)
    def codes(self): return {item['code'] for item in self.inspect()['issues']}

    def test_valid_polygon_and_shared_reference_bytes_once_unknown_approvals_false(self):
        self.rows.append(copy.deepcopy(self.rows[0])); self.save_manifest()
        before = {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        real = module._read_bounded
        calls = []
        def read(path, *args): calls.append(path); return real(path, *args)
        with patch.object(module, '_read_bounded', side_effect=read): result = self.inspect()
        self.assertEqual(calls.count(self.boundary), 1)
        self.assertEqual(result['boundary_validation'], 'STRUCTURE_MATCH')
        self.assertEqual(result['actual_boundary_bytes_read'], self.boundary.stat().st_size)
        self.assertEqual(result['feature_count'], 1)
        self.assertEqual(result['vertex_count'], 4)
        self.assertEqual([x['status'] for x in result['region_links']], ['UNIQUE_PROVINCE_MATCH'] * 2)
        self.assertEqual(result['status'], 'BLOCKED')
        for key in ['topology_validated', 'self_intersection_checked', 'official_adm1_verified', 'boundary_authorization_verified', 'pixel_inside_coverage_checked', 'geometric_independence_checked', 'ready_for_training', 'scientific_accuracy_validated', 'settlement_authorized', 'automatic_resume_allowed']:
            self.assertIs(result[key], False)
        self.assertEqual(before, {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_multipolygon_and_legacy_absent_refs_partial_known_structure(self):
        self.document['features'][0]['geometry'] = {'type': 'MultiPolygon', 'coordinates': [[self.ring], [self.ring]]}
        self.rows.append({'province': 'legacy', 'source_window': {}}); self.save()
        result = self.inspect()
        self.assertEqual(result['boundary_validation'], 'KNOWN_STRUCTURE_MATCH_PARTIAL')
        self.assertEqual(len(result['unknown_references']), 1)
        self.assertEqual(result['region_links'][0]['status'], 'UNIQUE_PROVINCE_MATCH')
        self.assertEqual(result['vertex_count'], 8)

    def test_all_absent_refs_never_claim_boundary_structure_match(self):
        self.rows = [{'province': 'banten', 'source_window': {}}]; self.save_manifest()
        result = self.inspect()
        self.assertEqual(result['boundary_validation'], 'NO_RECORDED_REFERENCES')
        self.assertEqual(result['actual_boundary_bytes_read'], 0)

    def test_partial_null_boolean_invalid_hash_province_and_conflict_plan_read_zero(self):
        original = copy.deepcopy(self.rows)
        changes = [lambda: self.rows[0]['source_window'].pop('boundary_sha256'), lambda: self.rows[0]['source_window'].__setitem__('boundary_path', None), lambda: self.rows[0]['source_window'].__setitem__('boundary_sha256', False), lambda: self.rows[0].__setitem__('province', '   '), lambda: self.rows[0].__setitem__('source_window', True)]
        real = module._read_bounded
        for change in changes:
            self.rows = copy.deepcopy(original); change(); self.save_manifest()
            seen = []
            def read(path, *args): seen.append(path); return real(path, *args)
            with patch.object(module, '_read_bounded', side_effect=read): result = self.inspect()
            self.assertEqual(result['boundary_validation'], 'NOT_STARTED_PLAN_REJECTED')
            self.assertNotIn(self.boundary, seen)
        self.rows = copy.deepcopy(original); self.rows.append(copy.deepcopy(original[0])); self.rows[1]['source_window']['boundary_sha256'] = '0' * 64; self.save_manifest()
        self.assertIn('BOUNDARY_SHA_CANONICAL_CONFLICT', self.codes())

    def test_missing_explicit_file_different_from_absent_ref(self):
        self.boundary.unlink()
        result = self.inspect()
        self.assertEqual(result['boundary_validation'], 'NOT_STARTED_PLAN_REJECTED')
        self.assertIn('BOUNDARY_FILE_MISSING', {x['code'] for x in result['issues']})
        self.assertEqual(result['unknown_references'], [])

    def test_byte_file_feature_vertex_and_depth_limits(self):
        for kwargs in [{'max_local_bytes': self.boundary.stat().st_size - 1}, {'max_vertices': 3}, {'max_json_depth': 3}]:
            with self.assertRaises(ValueError): self.inspect(**kwargs)
        for kwargs in [{'max_features': False}, {'max_boundary_files': 0}, {'max_json_depth': 33}, {'unknown_limit': 1}]:
            with self.assertRaises(ValueError): self.inspect(**kwargs)
        self.assertEqual(self.inspect(max_local_bytes=self.boundary.stat().st_size)['boundary_validation'], 'STRUCTURE_MATCH')
        self.document['features'].append(copy.deepcopy(self.document['features'][0])); self.save()
        with self.assertRaisesRegex(ValueError, 'feature limit'): self.inspect(max_features=1)
        other = self.output / 'other.geojson'; other.write_bytes(self.boundary.read_bytes())
        self.rows.append({'province': 'banten', 'source_window': {'boundary_path': str(other), 'boundary_sha256': self.sha(other)}}); self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'file-count'): self.inspect(max_boundary_files=1)

    def test_depth_scan_handles_escaped_quotes_and_brackets_inside_strings(self):
        self.document['note'] = 'brackets [ { ] } and quote " escaped \\ tail'
        self.save()
        self.assertEqual(self.inspect()['boundary_validation'], 'STRUCTURE_MATCH')
        module._check_depth(b'{"text":"[[[[\\\"[[["}', 2)
        self.save('{"type":"FeatureCollection","features":' + '[' * 40 + ']' * 40 + '}')
        with self.assertRaisesRegex(ValueError, 'depth'): self.inspect()

    def test_utf16_utf32_bom_nul_and_escaped_quote_depth_attacks_fail_before_json_parse(self):
        text = '{"note":"escaped \\\" quote","nested":' + '[' * 80 + '0' + ']' * 80 + '}'
        for encoding in ['utf-16', 'utf-16-le', 'utf-16-be', 'utf-32', 'utf-32-le', 'utf-32-be', 'utf-8-sig']:
            self.boundary.write_bytes(text.encode(encoding))
            self.rows[0]['source_window']['boundary_sha256'] = self.sha(self.boundary)
            self.save_manifest()
            with self.subTest(encoding=encoding):
                with self.assertRaises(ValueError): self.inspect()
        with self.assertRaises(ValueError): module._check_depth(b'{"note":"x\x00y"}', 32)
        with self.assertRaisesRegex(ValueError, 'depth'): module._check_depth(text.encode('utf-8'), 32)
        deep = 0
        for _ in range(80): deep = [deep]
        manifest_text = json.dumps({'scenes': self.rows, 'escaped_quote': '"', 'nested': deep})
        real = module._read_bounded
        for encoding in ['utf-16', 'utf-32']:
            self.manifest.write_bytes(manifest_text.encode(encoding)); self.pin = self.sha(self.manifest)
            seen = []
            def read(path, *args): seen.append(path); return real(path, *args)
            with patch.object(module, '_read_bounded', side_effect=read):
                with self.assertRaises(ValueError): self.inspect()
            self.assertNotIn(self.boundary, seen)

    def test_invalid_feature_collection_geometry_empty_ring_and_open_ring(self):
        variants = [lambda: self.document.__setitem__('type', 'Feature'), lambda: self.document.__setitem__('features', []), lambda: self.document['features'][0]['geometry'].__setitem__('type', 'Point'), lambda: self.document['features'][0]['geometry'].__setitem__('coordinates', []), lambda: self.document['features'][0]['geometry'].__setitem__('coordinates', [[[1, 2], [3, 4]]]), lambda: self.document['features'][0]['geometry'].__setitem__('coordinates', [[[1, 2], [2, 2], [2, 3], [1, 3]]])]
        original = copy.deepcopy(self.document)
        for mutate in variants:
            self.document = copy.deepcopy(original); mutate(); self.save()
            self.assertEqual(self.inspect()['boundary_validation'], 'ISSUES_FOUND')

    def test_short_invalid_rings_still_consume_total_vertex_budget(self):
        self.document['features'][0]['geometry']['coordinates'] = [self.ring[:3], self.ring[:3]]
        self.save()
        with self.assertRaisesRegex(ValueError, 'vertex limit'): self.inspect(max_vertices=3)
        result = self.inspect()
        self.assertEqual(result['vertex_count'], 6)
        self.assertIn('RING_INVALID', {x['code'] for x in result['issues']})

    def test_coordinate_boolean_nonfinite_hugeint_range_and_dimension(self):
        for point in [[True, -6], [float('nan'), -6], [1e309, -6], [10 ** 400, -6], [181, -6], [105, -91], [105, -6, 0]]:
            self.document['features'][0]['geometry']['coordinates'] = [[point, [106, -6], [106, -5], point]]
            self.save()
            if any(type(v) is float and not __import__('math').isfinite(v) for v in point):
                with self.assertRaises(ValueError): self.inspect()
            else: self.assertEqual(self.inspect()['boundary_validation'], 'ISSUES_FOUND')

    def test_province_missing_blank_duplicate_and_mismatch_never_use_last_feature(self):
        for province in [None, '', '  ', True]:
            self.document['features'][0]['properties']['province_id'] = province; self.save()
            self.assertIn('PROVINCE_ID_MISSING_OR_INVALID', self.codes())
        self.document['features'][0]['properties']['province_id'] = 'banten'
        self.document['features'].append(copy.deepcopy(self.document['features'][0])); self.save()
        result = self.inspect()
        self.assertIn('DUPLICATE_PROVINCE_ID', {x['code'] for x in result['issues']})
        self.assertEqual(result['region_links'][0]['status'], 'AMBIGUOUS_PROVINCE')
        self.document['features'] = [self.feature()]
        self.rows[0]['province'] = 'other'; self.save()
        self.assertEqual(self.inspect()['region_links'][0]['status'], 'MISSING_PROVINCE')

    def test_self_intersection_is_not_checked_and_explicit_crs_not_assumed(self):
        self.document['features'][0]['geometry']['coordinates'] = [[[105, -6], [106, -5], [105, -5], [106, -6], [105, -6]]]
        self.save()
        result = self.inspect()
        self.assertEqual(result['boundary_validation'], 'STRUCTURE_MATCH')
        self.assertFalse(result['self_intersection_checked'])
        self.document['crs'] = {'type': 'name', 'properties': {'name': 'EPSG:3857'}}; self.save()
        self.assertIn('EXPLICIT_CRS_DECLARATION_NOT_SUPPORTED', self.codes())

    def test_pinned_and_boundary_sha_mismatch_strict_json(self):
        for pin in [None, True, 'A' * 64, '0' * 64]:
            with self.assertRaises(ValueError): module.inspect_recovery_boundary(self.root, pin)
        self.rows[0]['source_window']['boundary_sha256'] = '0' * 64; self.save_manifest()
        self.assertIn('BOUNDARY_SHA_MISMATCH', self.codes())
        for raw in ['{"type":"FeatureCollection","features":[],"features":[]}', '{"x":NaN}', '{"x":1e999}']:
            self.save(raw)
            with self.assertRaises(ValueError): self.inspect()

    def test_root_remote_nonfile_and_read_mutation_alias_and_missing_appearing(self):
        original = copy.deepcopy(self.rows)
        for path in ['https://invalid.example/boundary', '//server/share/a', str(self.workspace / 'outside'), str(self.output)]:
            self.rows = copy.deepcopy(original); self.rows[0]['source_window']['boundary_path'] = path; self.save_manifest()
            with self.assertRaises(ValueError): self.inspect()
        self.rows = original; self.save()
        real = module._read_bounded
        def mutate(path, *args):
            result = real(path, *args)
            if path == self.boundary: self.boundary.write_text('{}', encoding='utf-8')
            return result
        with patch.object(module, '_read_bounded', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.save()
        real_resolve = module._confined
        calls = 0
        def retarget(root, path):
            nonlocal calls
            if Path(path) == self.boundary:
                calls += 1
                if calls >= 2: return self.output / 'other'
            return real_resolve(root, path)
        with patch.object(module, '_confined', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()
        self.boundary.unlink()
        real_stat = module._file_stamp
        calls = 0
        def appears(path):
            nonlocal calls
            if path == self.boundary:
                calls += 1
                if calls == 2: self.boundary.write_bytes(b'{}')
            return real_stat(path)
        with patch.object(module, '_file_stamp', side_effect=appears):
            with self.assertRaisesRegex(ValueError, 'changed'): self.inspect()

    def test_cli_cp949_utf8_existing_input_and_external_output_protection(self):
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/inspect_recovery_boundary.py'), '--data-root', str(self.root), '--expected-manifest-sha256', self.pin, *map(str, args)], capture_output=True, text=True, encoding='cp949', env={**os.environ, 'PYTHONIOENCODING': 'cp949'})
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        output = self.workspace / 'boundary-result.json'
        self.assertEqual(cli('--output', output).returncode, 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['declared_reference_rows'], 1)
        before = output.read_bytes()
        self.assertEqual(cli('--output', output).returncode, 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(cli('--output', self.boundary).returncode, 1)
        with tempfile.TemporaryDirectory() as external:
            path = Path(external) / 'no.json'
            self.assertEqual(cli('--output', path).returncode, 1)
            self.assertFalse(path.exists())
        self.manifest.write_text('{}', encoding='utf-8')
        failure = cli()
        self.assertEqual(failure.returncode, 1)
        self.assertTrue(failure.stderr.isascii())


if __name__ == '__main__': unittest.main()
