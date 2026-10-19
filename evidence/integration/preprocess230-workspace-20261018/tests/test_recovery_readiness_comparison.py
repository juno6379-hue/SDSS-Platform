"""Tiny pinned JSON fixtures only: never open real images or rerun readiness."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from backend.app.data import recovery_readiness_comparison as module

ROOT=Path(__file__).resolve().parents[1]


class ReadinessComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.workspace=Path(self.temp.name)
        self.root=self.workspace/'data';self.output=self.root/'first-group-training-esri-v1';self.output.mkdir(parents=True)
        self.manifest=self.output/'annual-window-report.json';self.saved_path=self.root/'first-group/readiness-resume-20261017.json';self.saved_path.parent.mkdir()
        self.corner_path=self.workspace/'모서리–report.json'
        self.policy_map,self.policy=module._fixed_policy()
        self.paths=[self.output/f'nonexistent-source-{i}.tif' for i in range(3)]
        self.rows=[{'province':p,'source_window':{'path':str(path),'sha256':str(i)*64}} for i,(p,path) in enumerate(zip(['south_sulawesi','banten','west_java'],self.paths))]
        self.write(self.manifest,{'scenes':self.rows})
        self.saved={'schema_version':1,'policy':{'province_splits':self.policy_map},'input_manifests':[{'path':str(self.manifest.relative_to(self.root)),'sha256':self.sha(self.manifest)}],
          'status':'blocked','ready_for_training':False,'scientific_accuracy_validated':False,'patch_counts_by_split':{'train':1,'val':0,'test':1},'prepared_payload':None,
          'blockers':[{'code':'SHARED_SOURCE_CROSSES_FIXED_SPLIT','province':'west_java','detail':'stored component; no token/bbox witness'},*({'code':'REFERENCE_CLASS_IMBALANCE','detail':str(i)} for i in range(3)),{'code':'CLASS_COVERAGE','detail':'val/class7: 209 pixels'}],
          'province_groups':{'west_java':'banten','banten':'banten'},'group_splits':self.policy_map}
        self.corner={'schema_version':1,'kind':'RECOVERY_PHYSICAL_SOURCE_FIXED_SPLIT_CORNER_DIAGNOSTIC','mode':'READ_ONLY','status':'BLOCKED','candidate_validation':'CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED','manifest':{'path':str(self.manifest),'sha256':self.sha(self.manifest)},'fixed_split_policy':self.policy,
          'scope_rows':'ALL_PHYSICAL_MANIFEST_SCENES','aggregate_physical_row_count':3,'physical_row_counts_by_fixed_split':{'train':1,'val':1,'test':1},'boundary_status':'BOUNDARY_NOT_USED',
          'planned_source_header_count':3,'source_header_attempt_count':3,'max_source_headers':3,'pair_plan_evaluated':True,'planned_cross_split_pair_count':3,'pair_diagnostic_record_count':3,'intersection_attempt_count':3,'max_pairs':3,'within_split_pair_count_out_of_scope':0,'within_split_pair_status':'OUT_OF_SCOPE',
          'shared_source_cross_split_findings':[],'positive_area_overlap_candidate_count':0,'positive_area_overlap_candidates':[],'issues':[],
          'footprint_method':'FOUR_PIXEL_EDGE_CORNERS_STRAIGHT_SEGMENTS','area_units':'square_degrees_planar_diagnostic','exactly_once_applied':'UNKNOWN','proposed_refund_bytes':0,'network_requests':0,'source_files_written':0,
          'geometry_runtime':{'available':True,'shapely_version':'synthetic','geos_version':'synthetic'},'projection_runtime':{'available':True,'pyproj_version':'synthetic','proj_version':'synthetic','network_enabled_at_entry':False,'network_enabled_at_exit':False,'network_state_restored':True},'source_footprints':[],'pair_results':[]}
        for k in ['eligibility_recomputed','quality_status_used_as_filter','readiness_gate_revalidated','curved_edges_densified','exact_raster_footprint_verified','source_content_sha_revalidated','pixel_arrays_read','eligible_subset_leakage_assessed','training_split_leakage_resolved','geometric_independence_verified','original_geometry_reprojected_or_written','automatic_geometry_repair_performed','ready_for_training','training_executed','scientific_accuracy_validated','settlement_authorized','execution_authorized','automatic_resume_allowed']:self.corner[k]=False
        splits=['train','val','test']
        for i,(row,path,split) in enumerate(zip(self.rows,self.paths,splits)):
            self.corner['source_footprints'].append({'path':str(path),'recorded_sha256':row['source_window']['sha256'],'recorded_sha_revalidated':False,'provinces':[row['province']],'fixed_splits':[split],'scene_indexes':[i],'rows_by_split':{split:[i]},'header':{'status':'VALID_HEADER','driver':'GTiff','width':4,'height':4,'count':1,'crs_wkt':'synthetic CRS','transform':[1.0,0.0,100.0,0.0,-1.0,0.0],'dtypes':['uint8']},'footprint_status':'CORNER_ONLY_FOOTPRINT_VALID','footprint':{'status':'CORNER_ONLY_FOOTPRINT_VALID','always_xy':True,'transform_errcheck':True,'projection_network_enabled_during_transform':False,'pixel_edge_corners':[[0,0],[4,0],[4,4],[0,4]],'native_crs_corners':[[100.0,0.0],[104.0,0.0],[104.0,-4.0],[100.0,-4.0]],'longitude_latitude_corners':[[100.0,0.0],[104.0,0.0],[104.0,-4.0],[100.0,-4.0]],'geometry':{'type':'Polygon','coordinates':[[[100.0,0.0],[104.0,0.0],[104.0,-4.0],[100.0,-4.0],[100.0,0.0]]]},'topology':{'status':'VALID_TOPOLOGY','is_empty':False,'is_valid':True,'finite_positive_area':True,'area_square_degrees_planar':16.0}}})
        for i in range(3):
            for j in range(i+1,3):
                self.corner['pair_results'].append({'left_source_path':str(self.paths[i]),'right_source_path':str(self.paths[j]),'left_fixed_splits':[splits[i]],'right_fixed_splits':[splits[j]],'cross_split_combinations':[{'left':splits[i],'right':splits[j]}],'status':'DISJOINT','intersection_empty':True,'intersects':False,'disjoint':True,'touches':False,'equal':False,'left_contains_right':False,'right_contains_left':False,'intersection_area_square_degrees':0.0})
        self.save()
    def tearDown(self):self.temp.cleanup()
    def write(self,path,value):path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self):self.write(self.saved_path,self.saved);self.write(self.corner_path,self.corner)
    def inspect(self):return module.inspect_recovery_readiness_comparison(self.root,self.sha(self.manifest),self.sha(self.saved_path),self.corner_path,self.sha(self.corner_path))
    def test_complete_snapshots_distinct_scopes_blockers_preserved_no_raster_io(self):
        before=[p.read_bytes() for p in [self.manifest,self.saved_path,self.corner_path]]
        with patch('backend.app.ml.readiness.assess',side_effect=AssertionError('no gate rerun')),patch('backend.app.data.recovery_raster_headers._read_header',side_effect=AssertionError('no headers')):
            result=self.inspect()
        self.assertEqual(result['issues'],[]);self.assertTrue(result['stored_corner_all_cross_pairs_disjoint'])
        self.assertEqual(result['saved_readiness_blockers'],self.saved['blockers']);self.assertEqual(result['saved_readiness_blocker_count'],5)
        self.assertEqual(result['shared_source_token_or_bbox_branch_cause'],'UNKNOWN_NOT_PERSISTED');self.assertEqual(result['eligible_scene_witness_status'],'UNKNOWN_NOT_PERSISTED')
        self.assertEqual(result['saved_province_groups'],self.saved['province_groups']);self.assertIs(result['saved_component_mapping_is_branch_witness'],False)
        self.assertEqual(result['physical_minus_saved_eligible_by_split'],{'train':0,'val':1,'test':0})
        self.assertEqual(result['status'],'BLOCKED');self.assertIs(result['ready_for_training'],False)
        self.assertEqual(before,[p.read_bytes() for p in [self.manifest,self.saved_path,self.corner_path]])
    def test_partial_unknown_or_issues_never_all_disjoint(self):
        for change in [lambda c:c.update(intersection_attempt_count=2),lambda c:c['pair_results'][0].update(status='NOT_CHECKED_INVALID_CORNER_FOOTPRINT'),lambda c:c.update(issues=[{'code':'INVALID'}]),lambda c:c['source_footprints'][0].update(footprint_status='UNKNOWN')]:
            with self.subTest(change=change):
                original=copy.deepcopy(self.corner);change(self.corner);self.save();r=self.inspect();self.assertFalse(r['stored_corner_all_cross_pairs_disjoint']);self.assertTrue(r['issues']);self.corner=original
    def test_missing_duplicate_or_wrong_pair_canonical_set(self):
        for mode in ['missing','duplicate','reverse']:
            original=copy.deepcopy(self.corner)
            if mode=='missing':self.corner['pair_results'].pop()
            elif mode=='duplicate':self.corner['pair_results'][1]=copy.deepcopy(self.corner['pair_results'][0])
            else:
                p=self.corner['pair_results'][0];p['left_source_path'],p['right_source_path']=p['right_source_path'],p['left_source_path']
            self.save();self.assertFalse(self.inspect()['stored_corner_all_cross_pairs_disjoint']);self.corner=original
    def test_bool_integer_confusion_counts_flags_and_area_rejected(self):
        for key in ['schema_version','aggregate_physical_row_count','intersection_attempt_count','source_files_written']:
            old=self.corner[key];self.corner[key]=bool(old);self.save();self.assertTrue(self.inspect()['issues']);self.corner[key]=old
        self.corner['pair_results'][0]['intersection_area_square_degrees']=False;self.save();self.assertTrue(self.inspect()['issues'])
    def test_policy_code_or_manifest_bindings_mismatch(self):
        for change in [lambda c:c['fixed_split_policy'].update(implementation_sha256='0'*64),lambda c:c['manifest'].update(sha256='0'*64),lambda c:c.update(scope_rows='ELIGIBLE_ONLY')]:
            original=copy.deepcopy(self.corner);change(self.corner);self.save();self.assertTrue(self.inspect()['issues']);self.corner=original
        self.saved['input_manifests'].append(copy.deepcopy(self.saved['input_manifests'][0]));self.save();self.assertTrue(self.inspect()['issues'])
    def test_positive_contact_and_tiny_area_preserved_not_all_disjoint(self):
        p=self.corner['pair_results'][0];p.update(status='POSITIVE_AREA_OVERLAP',intersection_empty=False,intersects=True,disjoint=False,intersection_area_square_degrees=1e-300)
        self.corner['positive_area_overlap_candidate_count']=1;self.corner['positive_area_overlap_candidates']=[copy.deepcopy(p)];self.save();r=self.inspect();self.assertEqual(r['issues'],[]);self.assertFalse(r['stored_corner_all_cross_pairs_disjoint']);self.assertFalse(r['stored_corner_no_cross_split_candidates'])
        p.update(status='BOUNDARY_CONTACT',touches=True,intersection_area_square_degrees=0.0);self.corner.update(positive_area_overlap_candidate_count=0,positive_area_overlap_candidates=[]);self.save();r=self.inspect();self.assertEqual(r['issues'],[]);self.assertFalse(r['stored_corner_all_cross_pairs_disjoint'])
    def test_positive_equal_contains_saved_flag_contradiction_is_issue(self):
        p=self.corner['pair_results'][0];p.update(status='POSITIVE_AREA_OVERLAP',intersection_empty=False,intersects=True,disjoint=False,intersection_area_square_degrees=1.0,equal=True)
        self.corner['positive_area_overlap_candidate_count']=1;self.corner['positive_area_overlap_candidates']=[copy.deepcopy(p)];self.save();self.assertTrue(self.inspect()['issues'])
        p.update(left_contains_right=True,right_contains_left=True);self.corner['positive_area_overlap_candidates']=[copy.deepcopy(p)];self.save();self.assertEqual(self.inspect()['issues'],[])
    def test_contradictory_flags_network_or_authorization_no_success(self):
        for change in [lambda c:c['pair_results'][0].update(touches=True),lambda c:c['projection_runtime'].update(network_state_restored=False),lambda c:c.update(training_executed=True),lambda c:c['source_footprints'][0]['footprint'].update(always_xy=False)]:
            original=copy.deepcopy(self.corner);change(self.corner);self.save();self.assertTrue(self.inspect()['issues']);self.corner=original
    def test_readiness_missing_witness_is_not_inferred_from_text_or_component(self):
        self.saved['blockers'][0]['detail']='token cause or bbox cause cannot be proven';self.saved['prepared_payload']={'scenes':[]};self.save();r=self.inspect();self.assertEqual(r['eligible_scene_witness_status'],'PRESENT_NOT_ANALYZED');self.assertEqual(r['shared_source_token_or_bbox_branch_cause'],'UNKNOWN_NOT_PERSISTED')
    def test_invalid_manifest_ref_province_conflict_and_remote_no_raster_io(self):
        for mutate in [lambda r:r[0].update(province='unknown'),lambda r:r[0]['source_window'].update(path='https://example.invalid/a.tif'),lambda r:r[0]['source_window'].update(sha256=False)]:
            rows=copy.deepcopy(self.rows);mutate(rows);self.write(self.manifest,{'scenes':rows})
            with self.assertRaises(ValueError):self.inspect()
    def test_strict_json_pin_depth_and_encoding_fail_closed(self):
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',json.dumps({'a':1}).encode('utf-16'), ('['*40+'0'+']'*40).encode()]:
            self.corner_path.write_bytes(raw)
            with self.assertRaises((ValueError,UnicodeError)):self.inspect()
        self.save()
        with self.assertRaises(ValueError):module.inspect_recovery_readiness_comparison(self.root,'0'*64,self.sha(self.saved_path),self.corner_path,self.sha(self.corner_path))
    def test_limits_and_stale_input_or_logical_target(self):
        with patch.object(module,'REPORT_BYTES',1),self.assertRaises(ValueError):self.inspect()
        old=module._read_bounded;calls=0
        def changed(*args):
            nonlocal calls
            raw=old(*args);calls+=1
            if calls==3:self.saved_path.write_bytes(self.saved_path.read_bytes()+b' ')
            return raw
        with patch.object(module,'_read_bounded',side_effect=changed),self.assertRaises(ValueError):self.inspect()
        self.save();old=module._confined;count=0
        def retarget(base,path):
            nonlocal count
            result=old(base,path)
            if Path(path)==self.corner_path:
                count+=1
                if count>1:return self.workspace/'retarget.json'
            return result
        with patch.object(module,'_confined',side_effect=retarget),self.assertRaises(ValueError):self.inspect()
    def test_evidence_confinement_and_eligible_count_validation(self):
        path=self.root/'corner.json';path.write_bytes(self.corner_path.read_bytes())
        with self.assertRaises(ValueError):module.inspect_recovery_readiness_comparison(self.root,self.sha(self.manifest),self.sha(self.saved_path),path,self.sha(path))
        self.saved['patch_counts_by_split']['val']=True;self.save();self.assertTrue(self.inspect()['issues'])
    def test_huge_integer_area_is_issue_without_overflow(self):
        self.corner['pair_results'][0]['intersection_area_square_degrees']=10**400;self.save()
        self.assertTrue(self.inspect()['issues'])
    def test_runtime_and_stored_header_footprint_schema_required(self):
        for change in [lambda c:c['geometry_runtime'].update(available=False),lambda c:c['source_footprints'][0]['header'].pop('transform'),lambda c:c['source_footprints'][0]['header'].update(dtypes=[]),lambda c:c['source_footprints'][0]['footprint'].pop('native_crs_corners'),lambda c:c['source_footprints'][0]['footprint']['geometry'].update(coordinates=[])]:
            original=copy.deepcopy(self.corner);change(self.corner);self.save();self.assertTrue(self.inspect()['issues']);self.corner=original
    def test_source_duplicate_expected_sha_conflict_and_typed_counts(self):
        rows=copy.deepcopy(self.rows);rows.append(copy.deepcopy(rows[0]));rows[-1]['source_window']['sha256']='f'*64;self.write(self.manifest,{'scenes':rows})
        with self.assertRaises(ValueError):self.inspect()
        self.write(self.manifest,{'scenes':self.rows});self.saved['patch_counts_by_split']['val']=3;self.save();self.assertTrue(self.inspect()['issues'])
    def test_cli_cp949_new_utf8_output_and_existing_alias_rejected(self):
        output=self.workspace/'결과–new.json';command=[sys.executable,str(ROOT/'scripts/inspect_recovery_readiness_comparison.py'),'--data-root',str(self.root),'--expected-manifest-sha256',self.sha(self.manifest),'--expected-readiness-sha256',self.sha(self.saved_path),'--corner-report',str(self.corner_path.relative_to(ROOT)),'--expected-corner-sha256',self.sha(self.corner_path),'--output',str(output)]
        env={**os.environ,'PYTHONIOENCODING':'cp949'};result=subprocess.run(command,capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['issues'],[])
        result=subprocess.run(command,capture_output=True,env=env);self.assertEqual(result.returncode,1);self.assertTrue(result.stderr.isascii())
        command[-1]=str(self.corner_path);before=self.corner_path.read_bytes();result=subprocess.run(command,capture_output=True,env=env);self.assertEqual(result.returncode,1);self.assertEqual(before,self.corner_path.read_bytes())


if __name__=='__main__':unittest.main()
