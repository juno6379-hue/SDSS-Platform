"""Synthetic assess on/off equality and optional all-scene capture; no real data."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import rasterio
import test_ml_readiness as fixtures
from backend.app.ml import readiness
from backend.app.ml import readiness_connectivity_adapter as adapter
from backend.app.ml.dataset import file_digest


class ReadinessConnectivityAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReadinessTests('test_explicit_test_gate_passes_and_all_files_are_hash_bound');self.fixture.setUp()
        self.root=self.fixture.root;self.rows=self.fixture.rows;self.manifest=self.fixture.manifest
        for row,province in zip(self.rows,['south_sulawesi','banten','west_java']):row['aoi']=province
        self.fixture.save()
        self.policy={**self.fixture.policy,'required_provinces':readiness.FIRST_GROUP.copy(),'province_splits':readiness.default_policy()['province_splits']}
    def tearDown(self):self.fixture.tearDown()
    def run_gate(self,flag=None,policy=None):
        kwargs={'test_mode':True}
        if flag is not None:kwargs['connectivity_diagnostics']=flag
        return readiness.assess([self.manifest],self.root,policy or self.policy,**kwargs)
    def unchanged(self,off,on):
        self.assertIn('connectivity_diagnostics',on);remaining={k:v for k,v in on.items() if k!='connectivity_diagnostics'}
        self.assertEqual(json.dumps(off,sort_keys=True,allow_nan=False),json.dumps(remaining,sort_keys=True,allow_nan=False))
    def rename_id(self,index,value):
        row=self.rows[index];row['scene_id']=value;ep=self.root/row['normalization']['evidence_path'];e=json.loads(ep.read_text(encoding='utf-8'));e['product_id']=value;ep.write_text(json.dumps(e),encoding='utf-8');row['normalization']['evidence_sha256']=file_digest(ep)
    def test_default_off_has_identical_keys_and_never_calls_adapter(self):
        with patch.object(adapter,'capture_readiness_connectivity',side_effect=AssertionError('Default must not call')):
            default=self.run_gate();off=self.run_gate(False)
        self.assertEqual(default,off);self.assertNotIn('connectivity_diagnostics',default)
    def test_true_capture_only_adds_field_and_components_match(self):
        off=self.run_gate(False);on=self.run_gate(True);self.unchanged(off,on);d=on['connectivity_diagnostics']
        self.assertEqual(d['capture_status'],'CAPTURED_COMPONENTS_MATCH');self.assertTrue(d['gate_components_match']);self.assertEqual(d['scene_count'],3);self.assertEqual(d['manifest_input_references'],off['input_manifests']);self.assertEqual(d['witness']['province_components'],off['province_groups'])
        self.assertEqual([r['scene_index'] for r in d['scene_mapping']],[0,1,2]);self.assertEqual(d['scope'],'ALL_APPENDED_ASSESS_SCENES_INCLUDING_ZERO_PATCH')
    def test_zero_patch_scene_remains_critical_token_conflict_bridge(self):
        self.rows[0]['source_group']='bridge';self.rows[1]['source_group']='bridge';self.rows[1]['province_inside_fraction']=0.0;self.fixture.save()
        off=self.run_gate(False);on=self.run_gate(True);self.unchanged(off,on);d=on['connectivity_diagnostics']
        self.assertEqual(off['province_patch_counts']['banten'],0);self.assertEqual(d['scene_count'],3);self.assertEqual(d['supplied_eligible_patch_sum'],2)
        self.assertTrue(d['scene_mapping'][1]['included_despite_zero_eligible_patches']);self.assertEqual(d['witness']['scene_count'],3);self.assertTrue(d['witness']['fixed_split_conflicts']);self.assertIn('SHARED_SOURCE_CROSSES_FIXED_SPLIT',[b['code'] for b in off['blockers']])
        self.assertTrue(any(e['kind']=='TOKEN_SHARED_NAMESPACE' and e['left']['scene_index']==1 for e in d['witness']['witness_edges']))
    def test_numeric_and_none_scene_id_str_semantics_preserved(self):
        self.rename_id(0,None);self.rename_id(1,None);self.rows[0]['source_group']=123;self.rows[1]['source_group']='123';self.fixture.save()
        off=self.run_gate(False);on=self.run_gate(True);self.unchanged(off,on);d=on['connectivity_diagnostics'];self.assertEqual(d['capture_status'],'CAPTURED_COMPONENTS_MATCH')
        projected=d['projected_scene_metadata'];self.assertEqual(projected[0]['scene_id'],'None');self.assertEqual(projected[0]['source_group'],'123');self.assertEqual(d['scene_mapping'][0]['scene_id_original_type'],'NoneType')
        self.assertTrue(any(e['token']=='None' for e in d['witness']['witness_edges']))
    def test_falsy_group_skips_both_tokens_without_losing_bbox(self):
        self.rows[0]['source_group']=0;self.fixture.save();off=self.run_gate(False);on=self.run_gate(True);self.unchanged(off,on);d=on['connectivity_diagnostics']
        self.assertEqual(d['projected_scene_metadata'][0]['source_group'],'');self.assertEqual(d['witness']['token_occurrences_processed'],4);self.assertEqual(d['witness']['issues'][0]['code'],'SOURCE_GROUP_MISSING');self.assertTrue(d['gate_components_match'])
    def test_custom_test_policy_not_captured_but_ready_gate_unchanged(self):
        for row,province in zip(self.rows,['a','b','c']):row['aoi']=province
        self.fixture.save();off=self.run_gate(False,self.fixture.policy);on=self.run_gate(True,self.fixture.policy);self.unchanged(off,on)
        self.assertTrue(off['ready_for_training']);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'NOT_CAPTURED_UNSUPPORTED_POLICY');self.assertFalse(on['connectivity_diagnostics']['ready_for_training'])
    def test_helper_exception_does_not_change_gate_or_add_blocker(self):
        off=self.run_gate(False)
        with patch.object(adapter,'diagnose_readiness_connectivity',side_effect=RuntimeError('capture failed')):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'FAILED_DIAGNOSTIC')
    def test_adapter_boundary_exception_and_import_exception_preserve_gate(self):
        off=self.run_gate(False)
        with patch.object(adapter,'capture_readiness_connectivity',side_effect=RuntimeError('outer capture failure')):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'FAILED_ADAPTER_BOUNDARY')
        original=__import__
        def fail_import(name,*args,**kwargs):
            if name=='readiness_connectivity_adapter':raise ImportError('synthetic import failure')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=fail_import):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'FAILED_ADAPTER_BOUNDARY')
    def test_unsupported_metadata_not_captured_without_filtering_scene(self):
        self.rows[0]['source_group']={'not':'scalar'};self.fixture.save();off=self.run_gate(False);on=self.run_gate(True);self.unchanged(off,on)
        self.assertEqual(on['connectivity_diagnostics']['capture_status'],'NOT_CAPTURED_UNSUPPORTED_METADATA');self.assertEqual(on['connectivity_diagnostics']['scene_count'],3);self.assertIsNone(on['connectivity_diagnostics']['witness'])
    def test_unsupported_bounds_and_budget_preserve_gate(self):
        off=self.run_gate(False)
        capture=adapter.capture_readiness_connectivity
        def budget(*args):return capture(*args,limits={'max_scenes':2,'max_bbox_pairs':1,'max_witness_edges':1})
        with patch.object(adapter,'capture_readiness_connectivity',side_effect=budget):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'NOT_CAPTURED_BUDGET')
        original=adapter.diagnose_readiness_connectivity
        def unsupported(rows,*args,**kwargs):
            changed=copy.deepcopy(rows);changed[0]['bounds_wgs84']=[float('inf'),0,1,1];return original(changed,*args,**kwargs)
        with patch.object(adapter,'diagnose_readiness_connectivity',side_effect=unsupported):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'NOT_CAPTURED_UNSUPPORTED_METADATA')
    def test_component_mismatch_is_diagnostic_only(self):
        off=self.run_gate(False);original=adapter.diagnose_readiness_connectivity
        def mismatch(*args,**kwargs):
            r=original(*args,**kwargs);r['province_components']['west_java']='banten';return r
        with patch.object(adapter,'diagnose_readiness_connectivity',side_effect=mismatch):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'CAPTURED_COMPONENT_MISMATCH');self.assertFalse(on['connectivity_diagnostics']['gate_components_match'])
    def test_mutate_then_raise_capture_cannot_modify_ready_gate_inputs_or_payload(self):
        for row,province in zip(self.rows,['a','b','c']):row['aoi']=province
        self.fixture.save();off=self.run_gate(False,self.fixture.policy)
        def mutate(scenes,policy,groups,inputs):
            scenes[0]['eligible_patches']=999;scenes[0]['source_group']='tamper';policy['required_years'].append(1999);groups.clear();inputs.clear();raise RuntimeError('mutated detached copies')
        with patch.object(adapter,'capture_readiness_connectivity',side_effect=mutate):on=self.run_gate(True,self.fixture.policy)
        self.unchanged(off,on);self.assertTrue(on['ready_for_training']);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'FAILED_ADAPTER_BOUNDARY')
    def test_helper_mutate_policy_then_raise_cannot_change_gate_or_pure_adapter_input(self):
        off=self.run_gate(False)
        def mutate(scenes,mapping,**kwargs):mapping.clear();scenes.clear();raise RuntimeError('synthetic bad helper')
        with patch.object(adapter,'diagnose_readiness_connectivity',side_effect=mutate):on=self.run_gate(True)
        self.unchanged(off,on);self.assertEqual(on['connectivity_diagnostics']['capture_status'],'FAILED_DIAGNOSTIC')
        policy=copy.deepcopy(self.policy);scenes=[{'province':'south_sulawesi','source_group':'x','scene_id':'x','bounds_wgs84':(0,0,1,1),'eligible_patches':0}];before=copy.deepcopy(scenes)
        with patch.object(adapter,'diagnose_readiness_connectivity',side_effect=mutate):adapter.capture_readiness_connectivity(scenes,policy,{},[])
        self.assertEqual(policy,self.policy);self.assertEqual(scenes,before)
    def test_required_province_order_unsupported_preserves_original_gate_event_order(self):
        policy={**self.policy,'required_provinces':list(reversed(readiness.FIRST_GROUP))};off=self.run_gate(False,policy);on=self.run_gate(True,policy);self.unchanged(off,on)
        self.assertEqual(on['connectivity_diagnostics']['capture_status'],'NOT_CAPTURED_UNSUPPORTED_POLICY')
    def test_no_additional_data_file_pixel_hash_or_text_calls(self):
        counters=[]
        for flag in [False,True]:
            with patch.object(readiness,'read',wraps=readiness.read) as pixels,patch.object(readiness,'file_digest',wraps=readiness.file_digest) as hashes,patch.object(Path,'read_text',autospec=True,side_effect=Path.read_text) as texts:
                self.run_gate(flag);counters.append((pixels.call_args_list,hashes.call_args_list,texts.call_args_list))
        self.assertEqual(counters[0],counters[1])
    def test_exact_bool_flag_rejected_before_any_file_processing(self):
        for value in [0,1,'true',None,[],np.bool_(True)]:
            with patch.object(readiness,'file_digest',side_effect=AssertionError('No file work')),self.assertRaises(ValueError):readiness.assess([self.manifest],self.root,self.policy,test_mode=True,connectivity_diagnostics=value)
    def test_pure_adapter_input_invariance_zero_witness_and_safe_failure_flags(self):
        scenes=[{'province':'south_sulawesi','source_group':'x','scene_id':'x','bounds_wgs84':(0,0,1,1),'eligible_patches':0},{'province':'banten','source_group':'x','scene_id':None,'bounds_wgs84':(3,0,4,1),'eligible_patches':1}]
        groups={p:p for p in readiness.FIRST_GROUP};groups['south_sulawesi']='banten';before=copy.deepcopy(scenes);policy=copy.deepcopy(self.policy)
        with patch('builtins.open',side_effect=AssertionError('No adapter IO')):d=adapter.capture_readiness_connectivity(scenes,policy,groups,[],limits={'max_scenes':2,'max_bbox_pairs':1,'max_witness_edges':0})
        self.assertEqual(d['capture_status'],'CAPTURED_COMPONENTS_MATCH');self.assertTrue(d['witness']['witness_edges_truncated']);self.assertTrue(d['witness']['union_complete']);self.assertEqual(scenes,before);self.assertEqual(policy,self.policy)
        for key in ['eligibility_recomputed','historical_readiness_cause_reconstructed','ready_for_training','scientific_accuracy_validated','training_executed','gate_result_modified','settlement_authorized','execution_authorized','automatic_resume_allowed','provenance_verified','executing_code_verified']:self.assertIs(d[key],False)


    def test_optional_source_identity_from_already_assessed_metadata_keeps_gate(self):
        off=self.run_gate(False);on=self.run_gate(True);self.unchanged(off,on)
        identity=on['connectivity_diagnostics']['source_identity']
        self.assertEqual(identity['identity_schema_version'],1);self.assertEqual(identity['coverage_status'],'COMPLETE_DECLARED_METADATA');self.assertEqual(identity['scene_count'],3)
        hashes={r['path']:r['sha256'] for r in off['verified_files'] if r['kind']=='input_image'}
        for index,item in enumerate(identity['scene_identities']):
            self.assertEqual(item['scene_index'],index);self.assertEqual(item['eligible_position'],index);self.assertEqual(item['image_path_declared'],self.rows[index]['image_path']);self.assertEqual(item['image_sha256_declared'],hashes[self.rows[index]['image_path']]);self.assertEqual(item['identity_status'],'DECLARED_PATH_AND_SHA256')
        self.assertEqual(on['connectivity_diagnostics']['schema_version'],1);self.assertEqual(set(on['connectivity_diagnostics']['projected_scene_metadata'][0]),{'scene_index','province','source_group','scene_id','bounds_wgs84'})
    def test_source_identity_absent_partial_null_invalid_do_not_change_capture_or_witness(self):
        scenes=[{'province':'banten','source_group':'x','scene_id':'x','bounds_wgs84':(0,0,1,1),'eligible_patches':0}]
        groups={p:p for p in readiness.FIRST_GROUP};baseline=adapter.capture_readiness_connectivity(scenes,self.policy,groups,[])
        self.assertEqual(baseline['source_identity']['coverage_status'],'UNKNOWN_NOT_PROVIDED')
        variants=[({'image_path':'relative/image.tif'},'PARTIAL_DECLARATION'),({'image_path':None,'image_sha256':None},'INVALID_DECLARATION'),({'image_path':False,'image_sha256':False},'INVALID_DECLARATION'),({'image_path':'','image_sha256':'x'},'INVALID_DECLARATION'),({'image_path':'x'*4097,'image_sha256':'A'*64},'INVALID_DECLARATION')]
        for additions,status in variants:
            with self.subTest(status=status):
                modified=[{**scenes[0],**additions}];r=adapter.capture_readiness_connectivity(modified,self.policy,groups,[])
                self.assertEqual(r['capture_status'],baseline['capture_status']);self.assertEqual(r['witness'],baseline['witness']);self.assertEqual(r['source_identity']['scene_identities'][0]['identity_status'],status)
    def test_source_identity_path_invalid_unicode_controls_and_sha_format_are_safe_json(self):
        base={'province':'banten','source_group':'x','scene_id':'x','bounds_wgs84':(0,0,1,1),'eligible_patches':0};groups={p:p for p in readiness.FIRST_GROUP}
        for value,status in [('a\x00b','INVALID_CONTROL_CHARACTER'),('a\nb','INVALID_CONTROL_CHARACTER'),('\ud800','INVALID_UNICODE'),('   ','EMPTY_DECLARATION'),([], 'INVALID_TYPE')]:
            scenes=[{**base,'image_path':value,'image_sha256':'a'*64}];r=adapter.capture_readiness_connectivity(scenes,self.policy,groups,[]);item=r['source_identity']['scene_identities'][0]
            self.assertIsNone(item['image_path_declared']);self.assertEqual(item['image_path_status'],status);json.dumps(r,ensure_ascii=False,allow_nan=False).encode('utf-8')
        for value,status in [('a'*63,'INVALID_LENGTH'),('A'*64,'INVALID_SHA256_FORMAT'),(None,'NULL_DECLARATION'),(1,'INVALID_TYPE')]:
            r=adapter.capture_readiness_connectivity([{**base,'image_path':'x','image_sha256':value}],self.policy,groups,[]);self.assertEqual(r['source_identity']['scene_identities'][0]['image_sha256_status'],status)
    def test_source_identity_no_io_literal_paths_order_zero_and_input_unchanged(self):
        scenes=[{'province':'banten','source_group':'x','scene_id':'x','bounds_wgs84':(0,0,1,1),'eligible_patches':0,'image_path':'../raw/./one.tif','image_sha256':'a'*64},{'province':'west_java','source_group':'x','scene_id':'two','bounds_wgs84':(3,0,4,1),'eligible_patches':0,'image_path':'https://not-accessed.invalid/two.tif','image_sha256':'b'*64}]
        before=copy.deepcopy(scenes);groups={p:p for p in readiness.FIRST_GROUP};groups['west_java']='banten'
        with patch.object(Path,'resolve',side_effect=AssertionError('No path resolution')),patch.object(Path,'stat',side_effect=AssertionError('No stat')),patch('builtins.open',side_effect=AssertionError('No IO')),patch.object(readiness,'file_digest',side_effect=AssertionError('No hash')):
            result=adapter.capture_readiness_connectivity(scenes,self.policy,groups,[])
        self.assertEqual(result['capture_status'],'CAPTURED_COMPONENTS_MATCH');identity=result['source_identity'];self.assertEqual([x['image_path_declared'] for x in identity['scene_identities']],[x['image_path'] for x in scenes]);self.assertEqual([m['eligible_patches'] for m in result['scene_mapping']],[0,0]);self.assertEqual(scenes,before)
        for key in ['path_normalized_or_resolved','source_files_read_or_hashed','source_authenticity_verified','exact_original_row_binding_verified','ready_for_training','scientific_accuracy_validated']:self.assertIs(identity[key],False)
    def test_source_identity_builder_error_does_not_change_existing_capture(self):
        normal=self.run_gate(True)
        with patch.object(adapter,'_source_identity_metadata',side_effect=RuntimeError('identity failure')):failed=self.run_gate(True)
        identity=failed['connectivity_diagnostics']['source_identity'];self.assertEqual(identity['identity_capture_status'],'NOT_CAPTURED_ERROR');self.assertFalse(identity['source_authenticity_verified'])
        for result in [normal,failed]:result['connectivity_diagnostics'].pop('source_identity');result.pop('assessed_at',None)
        self.assertEqual(json.dumps(normal,sort_keys=True),json.dumps(failed,sort_keys=True))
    def test_existing_lineage_reader_accepts_optional_identity_and_legacy_absence(self):
        import test_readiness_connectivity_lineage as lineage_fixtures
        fixture=lineage_fixtures.ReadinessConnectivityLineageTests('test_all_members_ambiguous_candidates_and_zero_patch_without_source_io');fixture.setUp()
        try:
            fixture.scenes[0].update(image_path='unread/image.tif',image_sha256='a'*64);fixture.save();new=fixture.inspect()
            self.assertIn('source_identity',fixture.fresh['connectivity_diagnostics']);fixture.fresh['connectivity_diagnostics'].pop('source_identity');fixture.write_report();legacy=fixture.inspect()
            refinement=new.pop('source_identity_refinement')
            self.assertNotIn('source_identity_refinement',legacy)
            self.assertEqual(refinement['status'],'DECLARED_METADATA_ONLY');self.assertFalse(refinement['exact_row_binding_verified'])
            for result in [new,legacy]:result['inputs']['report'].pop('sha256')
            self.assertEqual(new,legacy);self.assertEqual(new['candidate_link_count_total'],5)
        finally:fixture.tearDown()


if __name__=='__main__':unittest.main()
