"""Synthetic physical-source fixed-split corner candidates; no real image data."""
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
from backend.app.data import recovery_source_split_overlap as module

ROOT=Path(__file__).resolve().parents[1]


class SourceSplitOverlapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.workspace=Path(self.temp.name)
        self.root=self.workspace/'data';self.output=self.root/'first-group-training-esri-v1';self.output.mkdir(parents=True)
        self.manifest=self.output/'annual-window-report.json'
        self.paths=[self.output/f'source-{i}.tif' for i in range(3)]
        for path,x in zip(self.paths,[105,105.5,110]):self.write_source(path,x)
        self.rows=[{'province':province,'split':split,'quality_status':'quality_insufficient','source_window':{'path':str(path),'sha256':self.sha(path),'boundary_path':'https://not-used.invalid/boundary','boundary_sha256':False}} for path,province,split in zip(self.paths,['south_sulawesi','banten','west_java'],['train','val','test'])]
        self.save()
    def tearDown(self):self.temp.cleanup()
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def write_source(self,path,x=105,crs='EPSG:4326'):
        with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=2,dtype='uint16',crs=crs,transform=Affine(.25,0,x,0,-.25,-5)) as ds:ds.write(np.ones((2,4,4),dtype='uint16'))
    def save(self,raw=None):self.manifest.write_text(json.dumps({'scenes':self.rows}) if raw is None else raw,encoding='utf-8');self.pin=self.sha(self.manifest)
    def inspect(self,**kwargs):return module.inspect_recovery_source_split_overlap(self.root,self.pin,**kwargs)

    def test_all_physical_rows_fixed_policy_provenance_and_cross_pairs(self):
        result=self.inspect(max_source_headers=3,max_pairs=3)
        self.assertEqual(result['candidate_validation'],'CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED')
        self.assertEqual(result['physical_row_counts_by_fixed_split'],{'train':1,'val':1,'test':1})
        self.assertEqual(result['scope_rows'],'ALL_PHYSICAL_MANIFEST_SCENES')
        self.assertEqual(result['planned_cross_split_pair_count'],3);self.assertEqual(result['intersection_attempt_count'],3)
        self.assertEqual(result['positive_area_overlap_candidate_count'],1)
        self.assertEqual(result['boundary_status'],'BOUNDARY_NOT_USED')
        policy=result['fixed_split_policy'];self.assertEqual(policy['province_splits'],module.readiness.default_policy()['province_splits'])
        self.assertEqual(policy['implementation_sha256'],self.sha(Path(module.readiness.__file__)))
        self.assertEqual(result['status'],'BLOCKED')
        for key in ['eligibility_recomputed','quality_status_used_as_filter','readiness_gate_revalidated','curved_edges_densified','exact_raster_footprint_verified','source_content_sha_revalidated','pixel_arrays_read','eligible_subset_leakage_assessed','training_split_leakage_resolved','geometric_independence_verified','original_geometry_reprojected_or_written','automatic_geometry_repair_performed','ready_for_training','scientific_accuracy_validated','settlement_authorized','automatic_resume_allowed']:
            self.assertIs(result[key],False)

    def test_shared_canonical_source_across_splits_is_direct_finding_even_zero_distinct_pairs(self):
        self.rows=[copy.deepcopy(self.rows[0]),copy.deepcopy(self.rows[1])]
        self.rows[1]['source_window'].update(path=str(self.paths[0]),sha256=self.sha(self.paths[0]));self.save()
        result=self.inspect(max_source_headers=1,max_pairs=1)
        self.assertEqual(result['candidate_validation'],'SHARED_SOURCE_FINDINGS_NO_DISTINCT_PAIRS')
        self.assertEqual(result['planned_cross_split_pair_count'],0);self.assertEqual(result['intersection_attempt_count'],0)
        self.assertEqual(len(result['shared_source_cross_split_findings']),1)
        self.assertEqual(result['shared_source_cross_split_findings'][0]['fixed_splits'],['train','val'])
        self.assertEqual(result['source_header_attempt_count'],1)

    def test_multisplit_and_singleton_with_common_split_still_plan_cross_pair(self):
        sources={Path('a'):{'splits':{'train','val'}},Path('b'):{'splits':{'train'}},Path('c'):{'splits':{'val'}},Path('d'):{'splits':{'test'}},Path('e'):{'splits':{'train'}}}
        pairs,within=module._cross_split_plan(sources,9)
        self.assertEqual(len(pairs),9);self.assertEqual(within,1)
        self.assertIn((Path('a'),Path('b')),pairs);self.assertNotIn((Path('b'),Path('e')),pairs)
        self.assertEqual(len(set(pairs)),9)

    def test_within_single_split_pairs_out_of_scope_and_multiple_provinces_same_split(self):
        self.rows=self.rows[:2];self.rows[1].update(province='gorontalo',split='train');self.save()
        result=self.inspect(max_source_headers=2,max_pairs=1)
        self.assertEqual(result['candidate_validation'],'NO_CROSS_SPLIT_PAIR_CANDIDATES')
        self.assertEqual(result['within_split_pair_count_out_of_scope'],1)
        self.assertEqual(result['intersection_attempt_count'],0)
        self.assertEqual(result['shared_source_cross_split_findings'],[])
        self.assertEqual(result['source_header_attempt_count'],2)

    def test_source_cache_alias_and_pair_once_no_boundary_read(self):
        self.rows.append(copy.deepcopy(self.rows[0]));self.rows[-1]['source_window']['path']=str(self.output/'../first-group-training-esri-v1/source-0.tif');self.save()
        real_header,real_pair,real_read=module._read_header,module._pair_relation,module._read_bounded
        seen=[]
        def read(path,*args):seen.append(path);return real_read(path,*args)
        with patch.object(module,'_read_header',wraps=real_header) as opened,patch.object(module,'_pair_relation',wraps=real_pair) as compared,patch.object(module,'_read_bounded',side_effect=read):result=self.inspect(max_source_headers=3,max_pairs=3)
        self.assertEqual(opened.call_count,3);self.assertEqual(compared.call_count,3)
        self.assertEqual(seen,[self.manifest,self.manifest])
        self.assertEqual(result['aggregate_physical_row_count'],4)

    def test_bad_province_row_split_source_reference_and_conflict_plan_header_zero(self):
        original=copy.deepcopy(self.rows)
        variants=[lambda:self.rows[0].__setitem__('province','unknown'),lambda:self.rows[0].pop('province'),lambda:self.rows[0].__setitem__('province',True),lambda:self.rows[0].__setitem__('split','test'),lambda:self.rows[0].__setitem__('split',False),lambda:self.rows[0]['source_window'].__setitem__('sha256',False),lambda:self.rows[0].__setitem__('source_window',True)]
        for mutate in variants:
            self.rows=copy.deepcopy(original);mutate();self.save()
            with patch.object(module,'_read_header') as opened,patch.object(module,'_pair_relation') as pair:
                result=self.inspect();opened.assert_not_called();pair.assert_not_called()
            self.assertEqual(result['candidate_validation'],'NOT_STARTED_PLAN_REJECTED')
        self.rows=copy.deepcopy(original);self.rows.append(copy.deepcopy(self.rows[0]));self.rows[-1]['source_window']['sha256']='0'*64;self.save()
        with patch.object(module,'_read_header') as opened:result=self.inspect();opened.assert_not_called()
        self.assertIn('CANONICAL_EXPECTED_SHA_CONFLICT',{x['code'] for x in result['issues']})

    def test_header_pair_budgets_before_any_header_or_pair_work(self):
        for kwargs in [{'max_source_headers':2},{'max_pairs':2},{'max_source_headers':True},{'max_pairs':0},{'max_pairs':10001}]:
            with patch.object(module,'_read_header') as opened,patch.object(module,'_pair_relation') as pair:
                with self.assertRaises(ValueError):self.inspect(**kwargs)
                opened.assert_not_called();pair.assert_not_called()

    def test_invalid_footprint_skips_only_related_pairs_and_records_not_checked(self):
        self.write_source(self.paths[0],crs=None)
        result=self.inspect(max_source_headers=3,max_pairs=3)
        statuses=[r['status'] for r in result['pair_results']]
        self.assertEqual(statuses.count('NOT_CHECKED_INVALID_CORNER_FOOTPRINT'),2)
        self.assertEqual(result['pair_diagnostic_record_count'],3)
        self.assertEqual(result['intersection_attempt_count'],1)
        self.assertEqual(result['candidate_validation'],'ISSUES_FOUND')

    def test_contact_containment_equality_tinypositive_and_unknown_pair_diagnostics(self):
        for offset,status in [(106,'BOUNDARY_CONTACT'),(105,'POSITIVE_AREA_OVERLAP'),(106-1e-12,'POSITIVE_AREA_OVERLAP')]:
            self.write_source(self.paths[1],x=offset)
            result=self.inspect(max_source_headers=3,max_pairs=3)
            relation=next(r for r in result['pair_results'] if r['left_source_path']==str(self.paths[0]) and r['right_source_path']==str(self.paths[1]))
            self.assertEqual(relation['status'],status)
            if offset==105:self.assertTrue(relation['equal'])
            if offset>105 and status=='POSITIVE_AREA_OVERLAP':self.assertGreater(relation['intersection_area_square_degrees'],0);self.assertLess(relation['intersection_area_square_degrees'],1e-10)
        with patch.object(module,'_pair_relation',return_value={'status':'UNKNOWN_ENGINE_ERROR','intersection_area_square_degrees':None}):result=self.inspect(max_source_headers=3,max_pairs=3)
        self.assertEqual(result['intersection_attempt_count'],3);self.assertEqual(result['candidate_validation'],'ISSUES_FOUND')

    def test_projection_network_restored_on_success_and_failure(self):
        previous=pyproj.network.is_network_enabled()
        try:
            pyproj.network.set_network_enabled(True)
            result=self.inspect(max_source_headers=3,max_pairs=3)
            self.assertIs(pyproj.network.is_network_enabled(),True);self.assertTrue(result['projection_runtime']['network_state_restored'])
            with patch.object(pyproj.Transformer,'from_crs',side_effect=RuntimeError('synthetic projection error')):result=self.inspect(max_source_headers=3,max_pairs=3)
            self.assertIs(pyproj.network.is_network_enabled(),True)
            self.assertEqual(result['intersection_attempt_count'],0)
            self.assertEqual({r['status'] for r in result['pair_results']},{'NOT_CHECKED_INVALID_CORNER_FOOTPRINT'})
        finally:pyproj.network.set_network_enabled(previous)

    def test_projection_engine_unavailable_and_wrap_unsupported_not_pass(self):
        with patch.object(module,'_geometry_runtime',return_value=({'available':False,'shapely_version':'UNKNOWN','geos_version':'UNKNOWN'},None,None)):result=self.inspect()
        self.assertEqual(result['intersection_attempt_count'],0)
        self.assertEqual({r['status'] for r in result['pair_results']},{'NOT_CHECKED_INVALID_CORNER_FOOTPRINT'})
        real=module._source_footprint
        def wrapped(header,*args):
            return ({'status':'UNKNOWN_UNSUPPORTED_LONGITUDE_WRAP'},None) if header['transform'][2]==105 else real(header,*args)
        with patch.object(module,'_source_footprint',side_effect=wrapped):result=self.inspect()
        self.assertEqual(sum(r['status']=='NOT_CHECKED_INVALID_CORNER_FOOTPRINT' for r in result['pair_results']),2)

    def test_policy_invalid_or_implementation_changed_fails_closed(self):
        with patch.object(module.readiness,'default_policy',return_value={'province_splits':{}}):
            with self.assertRaises(ValueError):self.inspect()
        local_policy=self.workspace/'policy.py';local_policy.write_text('# synthetic policy provenance',encoding='utf-8')
        real=module._read_header
        def mutate(path):
            header=real(path);local_policy.write_text('# changed',encoding='utf-8');return header
        with patch.object(module.readiness,'__file__',str(local_policy)),patch.object(module,'_read_header',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'policy implementation changed'):self.inspect()

    def test_no_pixels_full_source_sha_public_inspector_or_source_changes(self):
        from backend.app.data import recovery_source_footprints
        import shapely
        before={p:p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        real_bytes=Path.read_bytes;real_open=rasterio.open
        class Guard:
            def __init__(self,ds):self.ds=ds
            def __enter__(self):self.ds.__enter__();return self
            def __exit__(self,*args):return self.ds.__exit__(*args)
            def __getattr__(self,name):
                if name in ('read','read_masks','statistics','tags'):raise AssertionError('pixels forbidden')
                return getattr(self.ds,name)
        def opened(path,**kwargs):return Guard(real_open(path,**kwargs))
        def bytes_read(path):
            if path in self.paths:raise AssertionError('full source SHA forbidden')
            return real_bytes(path)
        with patch.object(rasterio,'open',side_effect=opened),patch.object(Path,'read_bytes',new=bytes_read),patch.object(recovery_source_footprints,'inspect_recovery_source_footprints',side_effect=AssertionError('public/boundary reread forbidden')),patch.object(shapely,'buffer',side_effect=AssertionError('repair forbidden')),patch.object(shapely,'make_valid',side_effect=AssertionError('repair forbidden')):result=self.inspect()
        self.assertEqual(result['candidate_validation'],'CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED')
        self.assertEqual(before,{p:p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_pin_encoding_missing_remote_and_mutation_alias_fail_closed(self):
        for pin in [True,'A'*64,'0'*64]:
            with self.assertRaises(ValueError):module.inspect_recovery_source_split_overlap(self.root,pin)
        original=copy.deepcopy(self.rows)
        for path in ['https://invalid.example/a','//server/share/a',str(self.workspace/'outside'),str(self.output)]:
            self.rows=copy.deepcopy(original);self.rows[0]['source_window']['path']=path;self.save()
            with self.assertRaises(ValueError):self.inspect()
        self.rows=original;self.save();real=module._read_header
        def mutate(path):
            header=real(path)
            with self.paths[0].open('ab') as stream:stream.write(b'X')
            return header
        with patch.object(module,'_read_header',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed'):self.inspect()
        self.write_source(self.paths[0]);self.save();real_resolve=module._confined;calls=0
        def retarget(root,path):
            nonlocal calls
            if Path(path)==self.paths[0]:
                calls+=1
                if calls>=2:return self.output/'other'
            return real_resolve(root,path)
        with patch.object(module,'_confined',side_effect=retarget):
            with self.assertRaisesRegex(ValueError,'changed'):self.inspect()
        self.paths[1].unlink();self.assertIn('SOURCE_FILE_MISSING',{x['code'] for x in self.inspect()['issues']})
        text=json.dumps({'scenes':self.rows});self.manifest.write_bytes(text.encode('utf-16'));self.pin=self.sha(self.manifest)
        with self.assertRaises(ValueError):self.inspect()

    def test_cli_cp949_utf8_new_evidence_and_output_protection(self):
        def cli(*args):return subprocess.run([sys.executable,str(ROOT/'scripts/inspect_recovery_source_split_overlap.py'),'--data-root',str(self.root),'--expected-manifest-sha256',self.pin,'--max-source-headers','3','--max-pairs','3',*map(str,args)],capture_output=True,text=True,encoding='cp949',env={**os.environ,'PYTHONIOENCODING':'cp949'})
        result=cli();self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii())
        output=self.workspace/'split-overlap.json';self.assertEqual(cli('--output',output).returncode,0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['planned_cross_split_pair_count'],3)
        before=output.read_bytes();self.assertEqual(cli('--output',output).returncode,1);self.assertEqual(output.read_bytes(),before)
        self.assertEqual(cli('--output',self.paths[0]).returncode,1)
        with tempfile.TemporaryDirectory() as external:
            path=Path(external)/'no.json';self.assertEqual(cli('--output',path).returncode,1);self.assertFalse(path.exists())
        self.manifest.write_text('{}',encoding='utf-8');result=cli();self.assertEqual(result.returncode,1);self.assertTrue(result.stderr.isascii())


if __name__=='__main__':unittest.main()
