"""Tiny local rasters and GeoJSON for corner-only source/province diagnostics."""
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

import numpy as np
import rasterio
import pyproj
from affine import Affine
from shapely.geometry import box, mapping
from backend.app.data import recovery_source_footprints as module

ROOT=Path(__file__).resolve().parents[1]


class SourceFootprintTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.workspace=Path(self.temp.name)
        self.root=self.workspace/'data';self.output=self.root/'first-group-training-esri-v1';self.output.mkdir(parents=True)
        self.manifest=self.output/'annual-window-report.json';self.source=self.output/'source.tif';self.boundary=self.output/'boundary.geojson'
        self.transform=Affine(.25,0,105,0,-.25,-5);self.write_source(self.source)
        self.document={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'province_id':'banten'},'geometry':mapping(box(104,-7,107,-4))}]}
        self.rows=[{'province':'banten','source_window':{'path':str(self.source),'sha256':self.sha(self.source),'boundary_path':str(self.boundary),'boundary_sha256':''}}]
        self.save()
    def tearDown(self):self.temp.cleanup()
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def write_source(self,path,transform=None,crs='EPSG:4326'):
        with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=2,dtype='uint16',crs=crs,transform=self.transform if transform is None else transform) as dataset:dataset.write(np.ones((2,4,4),dtype='uint16'))
    def save(self):
        self.boundary.write_text(json.dumps(self.document),encoding='utf-8')
        for row in self.rows:
            if 'boundary_sha256' in row.get('source_window',{}):row['source_window']['boundary_sha256']=self.sha(self.boundary)
        self.save_manifest()
    def save_manifest(self):self.manifest.write_text(json.dumps({'scenes':self.rows}),encoding='utf-8');self.pin=self.sha(self.manifest)
    def inspect(self,**kwargs):return module.inspect_recovery_source_footprints(self.root,self.pin,**kwargs)

    def test_four_pixel_edge_corners_and_declared_province_relation_no_approvals(self):
        result=self.inspect(max_source_headers=1,max_relations=1)
        self.assertEqual(result['footprint_validation'],'CORNER_DIAGNOSTICS_COMPLETED')
        footprint=result['source_footprints'][0]['footprint']
        self.assertEqual(footprint['pixel_edge_corners'],[[0,0],[4,0],[4,4],[0,4]])
        self.assertEqual(footprint['longitude_latitude_corners'],[[105,-5],[106,-5],[106,-6],[105,-6]])
        self.assertEqual(result['relations'][0]['status'],'POSITIVE_AREA_OVERLAP')
        self.assertEqual(result['relations'][0]['intersection_area_square_degrees'],1)
        self.assertEqual(result['status'],'BLOCKED')
        for key in ['curved_edges_densified','exact_raster_footprint_verified','pixel_arrays_read','source_content_sha_revalidated','pixel_inside_ratio_computed','geodesic_area_computed','source_to_source_intersections_checked','training_split_leakage_resolved','original_geometry_reprojected_or_written','automatic_geometry_repair_performed','official_adm1_verified','boundary_authorization_verified','geometric_independence_checked','ready_for_training','scientific_accuracy_validated','settlement_authorized','automatic_resume_allowed']:
            self.assertIs(result[key],False)

    def test_rotation_skew_corners_are_not_axis_aligned_bbox(self):
        transform=Affine(.25,.05,105,.03,-.25,-5);self.write_source(self.source,transform);self.rows[0]['source_window']['sha256']=self.sha(self.source);self.save_manifest()
        footprint=self.inspect()['source_footprints'][0]['footprint']
        self.assertEqual(footprint['native_crs_corners'],[list(transform@point) for point in [(0,0),(4,0),(4,4),(0,4)]])
        self.assertNotEqual(footprint['longitude_latitude_corners'][0][1],footprint['longitude_latitude_corners'][1][1])

    def test_projected_utm_transform_always_xy_errcheck_and_offline_restored(self):
        forward=pyproj.Transformer.from_crs('EPSG:4326','EPSG:32748',always_xy=True)
        x,y=forward.transform(105,-6);self.write_source(self.source,Affine(100,0,x,0,-100,y),'EPSG:32748')
        self.rows[0]['source_window']['sha256']=self.sha(self.source);self.save_manifest()
        real=pyproj.Transformer.from_crs;calls=[]
        class Guard:
            def __init__(self,transformer):self.transformer=transformer
            @property
            def is_network_enabled(self):return self.transformer.is_network_enabled
            def transform(self,*args,**kwargs):
                self_outer.assertIs(pyproj.network.is_network_enabled(),False)
                self_outer.assertIs(kwargs.get('errcheck'),True)
                return self.transformer.transform(*args,**kwargs)
        self_outer=self
        def from_crs(*args,**kwargs):
            self.assertIs(pyproj.network.is_network_enabled(),False);calls.append(kwargs.copy());return Guard(real(*args,**kwargs))
        previous=pyproj.network.is_network_enabled()
        try:
            pyproj.network.set_network_enabled(True)
            with patch.object(pyproj.Transformer,'from_crs',side_effect=from_crs):result=self.inspect()
            self.assertIs(pyproj.network.is_network_enabled(),True)
            self.assertTrue(result['projection_runtime']['network_state_restored'])
            self.assertEqual(result['source_footprints'][0]['footprint_status'],'CORNER_ONLY_FOOTPRINT_VALID')
            self.assertTrue(all(call=={'always_xy':True,'allow_ballpark':False,'only_best':True} for call in calls))
        finally:pyproj.network.set_network_enabled(previous)

    def test_projection_exception_restores_prior_network_and_reports_unknown(self):
        previous=pyproj.network.is_network_enabled()
        try:
            pyproj.network.set_network_enabled(True)
            with patch.object(pyproj.Transformer,'from_crs',side_effect=RuntimeError('synthetic projection error')):result=self.inspect()
            self.assertIs(pyproj.network.is_network_enabled(),True)
            self.assertEqual(result['source_footprints'][0]['footprint_status'],'UNKNOWN_PROJECTION_OR_ENGINE_ERROR')
            self.assertEqual(result['relations'][0]['status'],'UNKNOWN_SOURCE_FOOTPRINT')
        finally:pyproj.network.set_network_enabled(previous)

    def test_antimeridian_nan_out_of_range_and_invalid_geometry_are_unknown(self):
        class Fake:
            is_network_enabled=False
            def __init__(self,values):self.values=values
            def transform(self,*args,**kwargs):return self.values
        for coordinates,expected in [(([179,-179,-179,179],[-5,-5,-6,-6]),'UNKNOWN_UNSUPPORTED_LONGITUDE_WRAP'),(([float('nan')]*4,[-5]*4),'UNKNOWN_INVALID_LON_LAT_CORNERS'),(([181]*4,[-5]*4),'UNKNOWN_INVALID_LON_LAT_CORNERS'),(([105]*4,[-5]*4),'UNKNOWN_INVALID_DERIVED_GEOMETRY')]:
            with patch.object(pyproj.Transformer,'from_crs',return_value=Fake(coordinates)):result=self.inspect()
            self.assertEqual(result['source_footprints'][0]['footprint_status'],expected)
            self.assertEqual(result['relations'][0]['status'],'UNKNOWN_SOURCE_FOOTPRINT')

    def test_cache_headers_unique_relations_and_missing_boundary_no_fallback(self):
        self.rows.append(copy.deepcopy(self.rows[0]));self.save_manifest()
        real_header,real_read,real_pair=module._read_header,module._read_bounded,module._pair_relation
        seen=[]
        def read(path,*args):seen.append(path);return real_read(path,*args)
        with patch.object(module,'_read_header',wraps=real_header) as opened,patch.object(module,'_pair_relation',wraps=real_pair) as compared,patch.object(module,'_read_bounded',side_effect=read):result=self.inspect()
        self.assertEqual(opened.call_count,1);self.assertEqual(compared.call_count,1);self.assertEqual(seen.count(self.boundary),1)
        self.assertEqual(result['planned_unique_relation_count'],1)
        self.assertEqual(result['relations'][0]['scene_indexes'],[0,1])
        for row in self.rows:
            row['source_window'].pop('boundary_path');row['source_window'].pop('boundary_sha256')
        self.save_manifest();seen=[]
        with patch.object(module,'_read_bounded',side_effect=read):result=self.inspect()
        self.assertNotIn(self.boundary,seen);self.assertEqual(result['source_header_attempt_count'],1)
        self.assertEqual(len(result['unknown_boundary_references']),2);self.assertEqual(result['relation_attempt_count'],0)
        self.assertEqual(result['coverage_status'],'INCOMPLETE_BOUNDARY_REFERENCES')

    def test_absent_boundary_on_second_source_still_checks_both_headers(self):
        other=self.output/'legacy.tif';self.write_source(other)
        self.rows.append({'province':'banten','source_window':{'path':str(other),'sha256':self.sha(other)}});self.save_manifest()
        result=self.inspect(max_source_headers=2,max_relations=1)
        self.assertEqual(result['source_header_attempt_count'],2);self.assertEqual(result['relation_attempt_count'],1)
        self.assertEqual(result['footprint_validation'],'KNOWN_CORNER_DIAGNOSTICS_PARTIAL')

    def test_contact_disjoint_and_missing_declared_province_no_fallback(self):
        for geometry,status in [(box(106,-6,107,-5),'BOUNDARY_CONTACT'),(box(107,-6,108,-5),'DISJOINT')]:
            self.document['features'][0]['geometry']=mapping(geometry);self.save()
            self.assertEqual(self.inspect()['relations'][0]['status'],status)
        self.rows[0]['province']='not-found';self.save_manifest()
        self.assertEqual(self.inspect()['relations'][0]['status'],'UNKNOWN_BOUNDARY_PROVINCE_GEOMETRY')

    def test_all_preflight_reference_conflicts_missing_and_caps_block_headers(self):
        original=copy.deepcopy(self.rows)
        variants=[lambda:self.rows[0]['source_window'].__setitem__('sha256',False),lambda:self.rows[0]['source_window'].pop('boundary_sha256'),lambda:self.rows[0]['source_window'].__setitem__('boundary_path',None)]
        for mutate in variants:
            self.rows=copy.deepcopy(original);mutate();self.save_manifest()
            with patch.object(module,'_read_header') as opened:result=self.inspect();opened.assert_not_called()
            self.assertEqual(result['footprint_validation'],'NOT_STARTED_PLAN_REJECTED')
        self.rows=copy.deepcopy(original);self.rows.append(copy.deepcopy(self.rows[0]));self.rows[1]['source_window']['sha256']='0'*64;self.save_manifest()
        with patch.object(module,'_read_header') as opened:result=self.inspect();opened.assert_not_called()
        self.assertIn('CANONICAL_EXPECTED_SHA_CONFLICT',{x['code'] for x in result['issues']})
        self.rows=copy.deepcopy(original)
        other=self.output/'other.tif';self.write_source(other);row=copy.deepcopy(self.rows[0]);row['source_window'].update(path=str(other),sha256=self.sha(other));self.rows.append(row);self.save_manifest()
        for kwargs in [{'max_source_headers':1},{'max_relations':1},{'max_source_headers':True},{'max_relations':10001}]:
            with patch.object(module,'_read_header') as opened:
                with self.assertRaises(ValueError):self.inspect(**kwargs)
                opened.assert_not_called()
        other.unlink()
        with patch.object(module,'_read_header') as opened:result=self.inspect();opened.assert_not_called()
        self.assertIn('DECLARED_FILE_MISSING',{x['code'] for x in result['issues']})

    def test_image_sha_is_format_only_and_invalid_header_or_boundary_topology_unknown(self):
        self.rows[0]['source_window']['sha256']='0'*64;self.save_manifest()
        result=self.inspect();self.assertFalse(result['source_content_sha_revalidated'])
        self.assertEqual(result['source_footprints'][0]['footprint_status'],'CORNER_ONLY_FOOTPRINT_VALID')
        self.write_source(self.source,crs=None)
        result=self.inspect();self.assertEqual(result['source_footprints'][0]['footprint_status'],'UNKNOWN_SOURCE_HEADER')
        self.write_source(self.source)
        self.document['features'][0]['geometry']={'type':'Polygon','coordinates':[[[104,-7],[107,-4],[104,-4],[107,-7],[104,-7]]]};self.save()
        result=self.inspect();self.assertEqual(result['relations'][0]['status'],'UNKNOWN_BOUNDARY_PROVINCE_GEOMETRY')

    def test_boundary_diagnostic_failure_keeps_header_independent_but_relation_unknown(self):
        original_rows, original_doc = copy.deepcopy(self.rows), copy.deepcopy(self.document)
        for case in ('sha', 'structure', 'province'):
            self.rows, self.document = copy.deepcopy(original_rows), copy.deepcopy(original_doc)
            if case == 'sha':
                self.rows[0]['source_window']['boundary_sha256'] = '0' * 64; self.save_manifest()
            elif case == 'structure':
                self.document['features'][0]['geometry'] = {'type': 'Point', 'coordinates': [105,-6]}; self.save()
            else:
                self.rows[0]['province'] = 'not-found'; self.save_manifest()
            result = self.inspect()
            self.assertEqual(result['source_header_attempt_count'],1)
            self.assertEqual(result['source_footprints'][0]['footprint_status'],'CORNER_ONLY_FOOTPRINT_VALID')
            self.assertEqual(result['relations'][0]['status'],'UNKNOWN_BOUNDARY_PROVINCE_GEOMETRY')
            self.assertEqual(result['footprint_validation'],'ISSUES_FOUND')

    def test_runtime_network_restoration_mismatch_is_an_issue_not_completion(self):
        first = {'available':True,'pyproj_version':'test','proj_version':'test','network_enabled_at_entry':False}
        last = {'available':True,'pyproj_version':'test','proj_version':'test','network_enabled_at_entry':True}
        with patch.object(module,'_projection_runtime',side_effect=[first,last]): result=self.inspect()
        self.assertIs(result['projection_runtime']['network_state_restored'],False)
        self.assertIn('PROJECTION_NETWORK_RESTORATION_UNVERIFIED',{issue['code'] for issue in result['issues']})
        self.assertEqual(result['footprint_validation'],'ISSUES_FOUND')

    def test_pixel_full_sha_repair_traps_and_source_bytes_sidecars_preserved(self):
        self.source.with_suffix('.tif.aux.xml').write_text('<PAMDataset><SRS>EPSG:3857</SRS></PAMDataset>',encoding='utf-8')
        before={p:p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        real_open=rasterio.open;real_bytes=Path.read_bytes
        class Guard:
            def __init__(self,dataset):self.dataset=dataset
            def __enter__(self):self.dataset.__enter__();return self
            def __exit__(self,*args):return self.dataset.__exit__(*args)
            def __getattr__(self,name):
                if name in ('read','read_masks','statistics','tags'):raise AssertionError('pixels forbidden')
                return getattr(self.dataset,name)
        def opened(path,**kwargs):return Guard(real_open(path,**kwargs))
        def bytes_read(path):
            if path==self.source:raise AssertionError('full image SHA forbidden')
            return real_bytes(path)
        import shapely
        with patch.object(rasterio,'open',side_effect=opened),patch.object(Path,'read_bytes',new=bytes_read),patch.object(shapely,'buffer',side_effect=AssertionError('repair forbidden')),patch.object(shapely,'make_valid',side_effect=AssertionError('repair forbidden')):self.assertEqual(self.inspect()['footprint_validation'],'CORNER_DIAGNOSTICS_COMPLETED')
        self.assertEqual(before,{p:p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_projection_or_geometry_engine_unavailable_and_pair_exception_are_unknown(self):
        with patch.object(module,'_projection_runtime',return_value={'available':False,'pyproj_version':'UNKNOWN','proj_version':'UNKNOWN','network_enabled_at_entry':'UNKNOWN'}):result=self.inspect()
        self.assertTrue(result['relations'][0]['status'].startswith('UNKNOWN'))
        with patch.object(module,'_geometry_runtime',return_value=({'available':False,'shapely_version':'UNKNOWN','geos_version':'UNKNOWN'},None,None)):result=self.inspect()
        self.assertEqual(result['relations'][0]['status'],'UNKNOWN_SOURCE_FOOTPRINT')
        with patch.object(module,'_pair_relation',return_value={'status':'UNKNOWN_ENGINE_ERROR'}):result=self.inspect()
        self.assertEqual(result['relations'][0]['status'],'UNKNOWN_ENGINE_ERROR')

    def test_strict_json_pin_paths_and_asset_mutation_alias_fail_closed(self):
        for pin in [True,'A'*64,'0'*64]:
            with self.assertRaises(ValueError):module.inspect_recovery_source_footprints(self.root,pin)
        for path in ['https://invalid.example/a','//server/share/a',str(self.workspace/'outside'),str(self.output)]:
            original=copy.deepcopy(self.rows);self.rows[0]['source_window']['path']=path;self.save_manifest()
            with self.assertRaises(ValueError):self.inspect()
            self.rows=original
        self.save_manifest()
        real=module._read_header
        def mutate(path):
            header=real(path)
            with self.source.open('ab') as stream:stream.write(b'X')
            return header
        with patch.object(module,'_read_header',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed'):self.inspect()
        self.write_source(self.source);self.save_manifest()
        real_resolve=module._confined;calls=0
        def retarget(root,path):
            nonlocal calls
            if Path(path)==self.source:
                calls+=1
                if calls>=2:return self.output/'other'
            return real_resolve(root,path)
        with patch.object(module,'_confined',side_effect=retarget):
            with self.assertRaisesRegex(ValueError,'changed'):self.inspect()
        self.boundary.write_bytes('{"quote":"\\\"","nested":[]}'.encode('utf-16'));self.rows[0]['source_window']['boundary_sha256']=self.sha(self.boundary);self.save_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_cli_cp949_utf8_new_evidence_and_output_protection(self):
        def cli(*args):return subprocess.run([sys.executable,str(ROOT/'scripts/inspect_recovery_source_footprints.py'),'--data-root',str(self.root),'--expected-manifest-sha256',self.pin,'--max-source-headers','1','--max-relations','1',*map(str,args)],capture_output=True,text=True,encoding='cp949',env={**os.environ,'PYTHONIOENCODING':'cp949'})
        result=cli();self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii())
        output=self.workspace/'footprints.json';self.assertEqual(cli('--output',output).returncode,0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['source_header_attempt_count'],1)
        before=output.read_bytes();self.assertEqual(cli('--output',output).returncode,1);self.assertEqual(output.read_bytes(),before)
        self.assertEqual(cli('--output',self.source).returncode,1)
        with tempfile.TemporaryDirectory() as external:
            path=Path(external)/'no.json';self.assertEqual(cli('--output',path).returncode,1);self.assertFalse(path.exists())
        self.manifest.write_text('{}',encoding='utf-8');result=cli();self.assertEqual(result.returncode,1);self.assertTrue(result.stderr.isascii())


if __name__=='__main__':unittest.main()
