"""Synthetic within-file boundary pair plans, exact positive intersections and guards."""
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
from shapely.geometry import box, mapping, shape
from backend.app.data import recovery_boundary_relations as module

ROOT = Path(__file__).resolve().parents[1]


class BoundaryRelationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'evidence')
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / 'data'
        self.output = self.root / 'first-group-training-esri-v1'
        self.output.mkdir(parents=True)
        self.manifest = self.output / 'annual-window-report.json'
        self.boundary = self.output / 'boundary.geojson'
        self.document = {'type': 'FeatureCollection', 'features': [self.feature(f'p{index}', box(index * 2, 0, index * 2 + 1, 1)) for index in range(6)]}
        self.rows = [{'province': 'p0', 'source_window': {'boundary_path': str(self.boundary), 'boundary_sha256': ''}}]
        self.save()
    def tearDown(self): self.temp.cleanup()
    def feature(self, province, geometry): return {'type': 'Feature', 'properties': {'province_id': province}, 'geometry': mapping(geometry)}
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self, raw=None):
        self.boundary.write_text(json.dumps(self.document) if raw is None else raw, encoding='utf-8')
        for row in self.rows:
            if row.get('source_window', {}).get('boundary_path') == str(self.boundary) and 'boundary_sha256' in row['source_window']: row['source_window']['boundary_sha256'] = self.sha(self.boundary)
        self.save_manifest()
    def save_manifest(self):
        self.manifest.write_text(json.dumps({'scenes': self.rows}), encoding='utf-8'); self.pin = self.sha(self.manifest)
    def inspect(self, **kwargs): return module.inspect_recovery_boundary_relations(self.root, self.pin, **kwargs)

    def test_all_unordered_pairs_once_geometry_cache_and_same_raw_read(self):
        real_read, real_pair = module._read_bounded, module._pair_relation
        runtime, real_shape, explain = module._geometry_runtime()
        reads, shape_calls = [], []
        def read(path, *args): reads.append(path); return real_read(path, *args)
        def constructed(geometry): shape_calls.append(geometry); return real_shape(geometry)
        with patch.object(module, '_read_bounded', side_effect=read), patch.object(module, '_pair_relation', wraps=real_pair) as pairs, patch.object(module, '_geometry_runtime', return_value=(runtime, constructed, explain)):
            result = self.inspect(max_pairs=15)
        self.assertEqual(reads.count(self.boundary), 1)
        self.assertEqual(reads.count(self.manifest), 2)
        self.assertEqual(len(shape_calls), 6)
        self.assertEqual(pairs.call_count, 15)
        self.assertEqual(result['planned_pair_count'], 15)
        self.assertEqual(result['pair_attempt_count'], 15)
        self.assertEqual({p['status'] for p in result['pair_results']}, {'DISJOINT'})
        self.assertEqual({(p['left_feature_index'],p['right_feature_index']) for p in result['pair_results']}, {(i,j) for i in range(6) for j in range(i+1,6)})
        self.assertEqual(result['pair_validation'], 'RELATIONS_DIAGNOSED')
        self.assertEqual(result['area_units'], 'square_degrees_planar_diagnostic')
        self.assertEqual(result['status'], 'BLOCKED')
        for key in ['administrative_boundary_error_determined','automatic_geometry_repair_performed','geometry_reprojected','official_adm1_verified','boundary_authorization_verified','pixel_inside_coverage_checked','geometric_independence_checked','ready_for_training','scientific_accuracy_validated','settlement_authorized','automatic_resume_allowed']:
            self.assertIs(result[key], False)

    def test_pair_budget_full_preflight_invalid_types_and_hard_cap_do_no_pair_work(self):
        for budget in [14, 0, True, 15.0, 8129]:
            with patch.object(module, '_pair_relation') as pair, patch.object(module, '_construct_checked_geometry') as construct:
                with self.assertRaises(ValueError): self.inspect(max_pairs=budget)
                pair.assert_not_called(); construct.assert_not_called()

    def test_point_and_edge_contacts_are_not_empty_intersections(self):
        for right in [box(1,0,2,1), box(1,1,2,2)]:
            result = module._pair_relation(box(0,0,1,1), right)
            self.assertEqual(result['status'], 'BOUNDARY_CONTACT')
            self.assertFalse(result['intersection_empty']); self.assertTrue(result['touches'])
            self.assertTrue(result['intersects']); self.assertFalse(result['disjoint'])
            self.assertEqual(result['intersection_area_square_degrees'], 0)

    def test_overlap_containment_equality_and_arbitrarily_small_positive_area(self):
        cases = [(box(0,0,2,2), box(1,1,3,3)), (box(0,0,2,2), box(.5,.5,1,1)), (box(0,0,2,2), box(0,0,2,2)), (box(0,0,1,1), box(1-1e-12,0,2,1))]
        for left, right in cases:
            relation = module._pair_relation(left, right)
            self.assertEqual(relation['status'], 'POSITIVE_AREA_OVERLAP')
            self.assertGreater(relation['intersection_area_square_degrees'], 0)
        contained = module._pair_relation(*cases[1]); self.assertTrue(contained['left_contains_right'])
        self.assertFalse(cases[1][0].overlaps(cases[1][1]))
        equal = module._pair_relation(*cases[2]); self.assertTrue(equal['equal'])
        self.assertTrue(equal['left_contains_right']); self.assertTrue(equal['right_contains_left'])
        self.assertLess(module._pair_relation(*cases[3])['intersection_area_square_degrees'], 1e-10)

    def test_intersection_called_once_per_pair_and_overlap_is_finding_not_admin_error(self):
        counts = []
        class Proxy:
            def __init__(self, geometry): self.geometry = geometry
            def intersection(self, other): counts.append(1); return self.geometry.intersection(other.geometry)
            def touches(self, other): return self.geometry.touches(other.geometry)
            def equals(self, other): return self.geometry.equals(other.geometry)
            def contains(self, other): return self.geometry.contains(other.geometry)
        relation = module._pair_relation(Proxy(box(0,0,2,2)), Proxy(box(0,0,1,1)))
        self.assertEqual(len(counts), 1); self.assertEqual(relation['status'], 'POSITIVE_AREA_OVERLAP')
        self.document['features'] = [self.feature('p0',box(0,0,2,2)),self.feature('p1',box(0,0,1,1))]; self.save()
        result = self.inspect(max_pairs=1)
        self.assertEqual(result['positive_area_overlap_pair_count'],1)
        self.assertEqual(result['pair_validation'],'RELATIONS_DIAGNOSED')
        self.assertEqual(result['issues'],[])
        self.assertFalse(result['administrative_boundary_error_determined'])

    def test_negative_nonfinite_empty_positive_and_inconsistent_engine_values_unknown(self):
        class Fake:
            def __init__(self, empty, area, touches=False): self.empty,self.area,self.touch=empty,area,touches
            def intersection(self, other): return types.SimpleNamespace(is_empty=self.empty,area=self.area)
            def touches(self, other): return self.touch
        for fake in [Fake(False,-1),Fake(False,float('nan')),Fake(False,float('inf')),Fake(True,1),Fake(False,0,False),Fake(False,1,True)]:
            self.assertTrue(module._pair_relation(fake,fake)['status'].startswith('UNKNOWN'))
        class Failing:
            def intersection(self,other): raise RuntimeError('synthetic pair error')
        self.assertEqual(module._pair_relation(Failing(),Failing())['status'],'UNKNOWN_ENGINE_ERROR')
        with patch.object(module,'_pair_relation',return_value={'status':'UNKNOWN_ENGINE_ERROR','intersection_area_square_degrees':None}):
            result=self.inspect(max_pairs=15)
            self.assertEqual(result['pair_validation'],'RELATION_ISSUES_FOUND')
            self.assertEqual(result['pair_attempt_count'],15)

    def test_invalid_topology_prevents_all_pairs_and_geometry_error_not_pass(self):
        self.document['features'][1]['geometry']={'type':'Polygon','coordinates':[[[2,0],[3,1],[2,1],[3,0],[2,0]]]};self.save()
        with patch.object(module,'_pair_relation') as pair:
            result=self.inspect(max_pairs=15)
            self.assertEqual(result['pair_validation'],'NOT_CHECKED_TOPOLOGY_ISSUES');pair.assert_not_called()
        runtime={'available':True,'shapely_version':'test','geos_version':'test'}
        def fail(geometry): raise RuntimeError('shape failure')
        with patch.object(module,'_geometry_runtime',return_value=(runtime,fail,lambda g:'unused')),patch.object(module,'_pair_relation') as pair:
            result=self.inspect(max_pairs=15)
            self.assertEqual(result['pair_validation'],'NOT_CHECKED_TOPOLOGY_ISSUES');pair.assert_not_called()

    def test_input_plan_sha_structure_region_issues_prevent_pairs(self):
        original_rows,original_doc=copy.deepcopy(self.rows),copy.deepcopy(self.document)
        variants=[lambda:self.rows[0]['source_window'].pop('boundary_sha256'),lambda:self.rows[0]['source_window'].__setitem__('boundary_sha256','0'*64),lambda:self.document['features'][0]['geometry'].__setitem__('coordinates',[]),lambda:self.rows[0].__setitem__('province','missing')]
        for mutate in variants:
            self.rows,self.document=copy.deepcopy(original_rows),copy.deepcopy(original_doc);mutate()
            if 'boundary_sha256' not in self.rows[0]['source_window'] or self.rows[0]['source_window'].get('boundary_sha256')=='0'*64:self.save_manifest()
            else:self.save()
            with patch.object(module,'_pair_relation') as pair:
                result=self.inspect(max_pairs=15)
                self.assertTrue(result['pair_validation'].startswith(('NOT_STARTED','NOT_CHECKED')));pair.assert_not_called()

    def test_legacy_unknown_no_references_and_single_feature_have_distinct_nonexecution(self):
        self.rows.append({'province':'p0','source_window':{}});self.save_manifest()
        self.assertEqual(self.inspect(max_pairs=15)['pair_validation'],'KNOWN_RELATIONS_DIAGNOSED_PARTIAL')
        self.document['features']=self.document['features'][:1];self.save()
        result=self.inspect(max_pairs=1)
        self.assertEqual(result['pair_validation'],'NO_PAIR_CANDIDATES');self.assertEqual(result['pair_attempt_count'],0)
        self.rows=[self.rows[1]];self.save_manifest()
        result=self.inspect(max_pairs=1)
        self.assertEqual(result['pair_validation'],'NO_RECORDED_REFERENCES');self.assertFalse(result['cross_feature_pair_diagnostics_performed'])

    def test_different_boundary_files_are_explicitly_out_of_scope(self):
        self.document['features']=self.document['features'][:1];self.save()
        other=self.output/'other.geojson'
        other.write_text(json.dumps({'type':'FeatureCollection','features':[self.feature('other',box(0,0,1,1))]}),encoding='utf-8')
        self.rows.append({'province':'other','source_window':{'boundary_path':str(other),'boundary_sha256':self.sha(other)}});self.save_manifest()
        result=self.inspect(max_pairs=1)
        self.assertEqual(result['pair_validation'],'NO_PAIR_CANDIDATES')
        self.assertEqual(result['cross_file_pair_count_out_of_scope'],1)
        self.assertEqual(result['cross_file_pairs_status'],'OUT_OF_SCOPE')
        self.assertEqual(result['pair_attempt_count'],0)

    def test_engine_absence_and_missing_versions_do_not_invent_success(self):
        with patch.object(module,'_geometry_runtime',return_value=({'available':False,'shapely_version':'UNKNOWN','geos_version':'UNKNOWN'},None,None)):
            result=self.inspect(max_pairs=15)
            self.assertEqual(result['pair_validation'],'NOT_CHECKED_ENGINE_UNAVAILABLE')
            self.assertEqual(result['pair_attempt_count'],0)

    def test_no_repair_reproject_public_reread_or_source_changes(self):
        from shapely.geometry.base import BaseGeometry
        from backend.app.data import recovery_boundary,recovery_boundary_topology
        before={p:p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        with patch.object(shapely,'buffer',side_effect=AssertionError('repair forbidden')),patch.object(shapely,'make_valid',side_effect=AssertionError('repair forbidden')),patch.object(BaseGeometry,'buffer',side_effect=AssertionError('repair forbidden')),patch.object(recovery_boundary,'inspect_recovery_boundary',side_effect=AssertionError('public reread forbidden')),patch.object(recovery_boundary_topology,'inspect_recovery_boundary_topology',side_effect=AssertionError('public reread forbidden')):
            self.assertEqual(self.inspect(max_pairs=15)['pair_validation'],'RELATIONS_DIAGNOSED')
        self.assertEqual(before,{p:p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_limits_strict_encoding_pin_and_path_fail_before_pair_work(self):
        for kwargs in [{'max_vertices':2},{'max_features':5},{'max_local_bytes':self.boundary.stat().st_size-1},{'max_json_depth':3}]:
            with patch.object(module,'_pair_relation') as pair:
                with self.assertRaises(ValueError):self.inspect(max_pairs=15,**kwargs)
                pair.assert_not_called()
        for pin in [True,'A'*64,'0'*64]:
            with self.assertRaises(ValueError):module.inspect_recovery_boundary_relations(self.root,pin,max_pairs=15)
        self.boundary.write_bytes(('{"quote":"\\\"","nested":'+'['*80+'0'+']'*80+'}').encode('utf-16'));self.rows[0]['source_window']['boundary_sha256']=self.sha(self.boundary);self.save_manifest()
        with self.assertRaises(ValueError):self.inspect(max_pairs=15)
        self.save()
        self.rows[0]['source_window']['boundary_path']='https://invalid.example/a';self.save_manifest()
        with self.assertRaises(ValueError):self.inspect(max_pairs=15)

    def test_file_and_manifest_mutation_and_logical_retarget_fail_closed(self):
        real=module._read_bounded
        def mutate(path,*args):
            raw=real(path,*args)
            if path==self.boundary:self.boundary.write_text('{}',encoding='utf-8')
            return raw
        with patch.object(module,'_read_bounded',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed'):self.inspect(max_pairs=15)
        self.save()
        real_resolve=module._confined;calls=0
        def retarget(root,path):
            nonlocal calls
            if Path(path)==self.boundary:
                calls+=1
                if calls>=2:return self.output/'other'
            return real_resolve(root,path)
        with patch.object(module,'_confined',side_effect=retarget):
            with self.assertRaisesRegex(ValueError,'changed'):self.inspect(max_pairs=15)

    def test_cli_cp949_utf8_new_evidence_and_output_protection(self):
        def cli(*args):return subprocess.run([sys.executable,str(ROOT/'scripts/inspect_recovery_boundary_relations.py'),'--data-root',str(self.root),'--expected-manifest-sha256',self.pin,'--max-pairs','15',*map(str,args)],capture_output=True,text=True,encoding='cp949',env={**os.environ,'PYTHONIOENCODING':'cp949'})
        result=cli();self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii())
        output=self.workspace/'relations.json';self.assertEqual(cli('--output',output).returncode,0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['pair_attempt_count'],15)
        before=output.read_bytes();self.assertEqual(cli('--output',output).returncode,1);self.assertEqual(output.read_bytes(),before)
        self.assertEqual(cli('--output',self.boundary).returncode,1)
        with tempfile.TemporaryDirectory() as external:
            path=Path(external)/'no.json';self.assertEqual(cli('--output',path).returncode,1);self.assertFalse(path.exists())
        self.manifest.write_text('{}',encoding='utf-8');result=cli();self.assertEqual(result.returncode,1);self.assertTrue(result.stderr.isascii())


if __name__=='__main__':unittest.main()
