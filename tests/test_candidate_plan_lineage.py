"""Tiny synthetic five-JSON fixtures only; no real data or source raster reads."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_readiness_connectivity_lineage as fixtures
from backend.app.ml import candidate_plan_lineage as module
from backend.app.ml.split_planning import plan_split_repair


class CandidatePlanLineageTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReadinessConnectivityLineageTests();self.f.setUp()
        for i,row in enumerate(self.f.raw):row.update(year='2021',quality_status='quality_insufficient' if i==2 else 'quality_eligible')
        self.f.complete_identity()
        self.f.fresh.update(blockers=[{'code':'CLASS_COVERAGE','class':7,'pixels':209}],class_counts_by_split={s:[209]*9 for s in ('train','val','test')},class_patch_counts_by_split={s:[0]*9 for s in ('train','val','test')})
        self.f.fresh['policy'].update(patch_size=256,min_valid_fraction=.8,min_patches=1,min_patches_per_split={s:0 for s in ('train','val','test')});self.f.write_report()
        self.old=self.f.root/'old.json';self.old.write_text(json.dumps({k:v for k,v in self.f.fresh.items() if k!='connectivity_diagnostics'}),encoding='utf-8')
        self.planpath=self.f.workspace/'plan.json';self.lineagepath=self.f.workspace/'lineage.json'
        self.plan=plan_split_repair(self.f.manifest,self.f.sha(self.f.manifest),province_splits=module.FIXED_PROVINCE_SPLITS,readiness_path=self.old,readiness_sha256=self.f.sha(self.old),data_root=self.f.root)
        self.planpath.write_text(json.dumps(self.plan),encoding='utf-8')
        self.lineage=self.f.inspect();self.lineagepath.write_text(json.dumps(self.lineage),encoding='utf-8')
        self.paths=dict(plan=self.planpath,source=self.f.manifest,old_readiness=self.old,new_report=self.f.report,lineage=self.lineagepath)
        self.pins={k:self.f.sha(v) for k,v in self.paths.items()};self.refs={k:{'path':str(v),'sha256':self.pins[k]} for k,v in self.paths.items()}
        self.docs=dict(plan=self.plan,source={'scenes':copy.deepcopy(self.f.raw)},old_readiness=json.loads(self.old.read_text()),new_report=self.f.fresh,lineage=self.lineage)
    def tearDown(self):self.f.tearDown()
    def build(self,docs=None,refs=None):return module.build_candidate_plan_lineage(docs or self.docs,refs or self.refs,data_root_literal=str(self.f.root),token='shared')
    def inspect(self):return module.inspect_candidate_plan_lineage(self.f.root,self.paths,self.pins,token='shared',evidence_root=self.f.workspace)
    def test_complete_reference_keeps_zero_patch_and_plan_only(self):
        before=copy.deepcopy(self.docs);r=self.build();self.assertEqual(before,self.docs)
        self.assertEqual(r['current_query']['report_member_count'],3);self.assertEqual(r['current_query']['zero_patch_member_count'],1)
        self.assertEqual(r['current_query']['excluded_declared_raw_candidate_count'],2);self.assertEqual(r['current_query']['retained_declared_raw_candidate_count'],1)
        self.assertEqual(r['projected_after']['eligible_total'],0);self.assertFalse(r['candidate_manifest_created']);self.assertFalse(r['exact_row_binding_verified']);self.assertEqual(r['full_planner_recomputation'],'NOT_PERFORMED')
    def test_pure_core_no_io_planner_assess_helper_registry(self):
        with patch('pathlib.Path.open',side_effect=AssertionError('No IO')),patch('backend.app.ml.split_planning.plan_split_repair',side_effect=AssertionError('No planner')),patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No assess')),patch('backend.app.data.readiness_connectivity_witness.diagnose_readiness_connectivity',side_effect=AssertionError('No helper')):self.build()
    def test_uint_partition_duplicate_missing_bool_and_float(self):
        for value in [[True,1],[0,0],[0.0,1],[],[0,9]]:
            docs=copy.deepcopy(self.docs);docs['plan']['excluded_row_indexes']=value
            with self.assertRaises(ValueError):self.build(docs)
    def test_selected_plan_counts_policy_or_declared_reference_tamper(self):
        changes=[lambda d:d['plan']['projected_after'].update(eligible_total=True),lambda d:d['plan']['policy']['keep_split_priority'].reverse(),lambda d:d['plan']['source_manifest'].update(sha256='0'*64),lambda d:d['lineage']['inputs']['report'].update(sha256='0'*64),lambda d:d['new_report']['input_manifests'][0].update(path='../outside')]
        for change in changes:
            docs=copy.deepcopy(self.docs);change(docs)
            with self.assertRaises(ValueError):self.build(docs)
    def test_old_new_gate_class_or_blocker_difference_rejected(self):
        for key,value in [('blockers',[]),('patch_counts_by_split',{'train':0,'val':True,'test':0}),('class_counts_by_split',{})]:
            docs=copy.deepcopy(self.docs);docs['new_report'][key]=value
            with self.assertRaises(ValueError):self.build(docs)
    def test_class_bounds_remain_conservative_and_tamper_rejected(self):
        self.assertEqual(self.build()['class_impact']['by_split']['val']['class_pixel_upper_bounds'][7],209)
        for key,value in [('exact_after_counts_computed',True),('bare_shortage_resolved',True)]:
            docs=copy.deepcopy(self.docs);docs['plan']['class_impact'][key]=value
            with self.assertRaises(ValueError):self.build(docs)
        docs=copy.deepcopy(self.docs);docs['plan']['class_impact']['by_split']['val']['class_pixel_upper_bounds'][7]=210
        with self.assertRaises(ValueError):self.build(docs)
    def test_report_identity_partial_unknown_or_reordered_fails_closed(self):
        for change in [lambda d:d['new_report']['connectivity_diagnostics']['source_identity']['scene_identities'][0].update(identity_status='UNKNOWN_NOT_PROVIDED'),lambda d:d['new_report']['connectivity_diagnostics']['scene_mapping'][0].update(eligible_position=2),lambda d:d['new_report']['connectivity_diagnostics']['source_identity'].update(identity_schema_version=True)]:
            docs=copy.deepcopy(self.docs);change(docs)
            with self.assertRaises(ValueError):self.build(docs)
    def test_lineage_truncated_false_authority_or_inconsistent_member_rejected(self):
        changes=[lambda d:d['lineage'].update(output_truncated=True),lambda d:d['lineage'].update(ready_for_training=True),lambda d:d['lineage']['report_members'][0].update(candidate_row_indices=[0]),lambda d:d['lineage']['source_identity_refinement']['members'][0].update(candidate_row_indices=[1])]
        for change in changes:
            docs=copy.deepcopy(self.docs);change(docs)
            with self.assertRaises(ValueError):self.build(docs)
    def test_declared_match_is_not_internal_scene_index_identity(self):
        # Reorder raw rows; projection order stays fixed. Rebuild saved lineage and plan metadata.
        self.f.raw.reverse();self.f.save();self.f.fresh.update(self.docs['new_report']);self.f.fresh['input_manifests'][0]['sha256']=self.f.sha(self.f.manifest);self.f.fresh['connectivity_diagnostics']['manifest_input_references']=copy.deepcopy(self.f.fresh['input_manifests']);self.f.write_report()
        docs=copy.deepcopy(self.docs);docs['source']['scenes']=self.f.raw;docs['lineage']=self.f.inspect();docs['new_report']=self.f.fresh
        refs=copy.deepcopy(self.refs);refs['source']['sha256']=self.f.sha(self.f.manifest);refs['new_report']['sha256']=self.f.sha(self.f.report)
        docs['old_readiness']['input_manifests']=copy.deepcopy(self.f.fresh['input_manifests']);docs['plan']['source_manifest']['sha256']=refs['source']['sha256'];docs['plan']['excluded_row_indexes']=[1,2];docs['plan']['retained_row_indexes']=[0]
        r=self.build(docs,refs);self.assertEqual(r['current_query']['member_plan_links'][0]['raw_manifest_candidate_row_index'],2);self.assertFalse(r['exact_row_binding_verified'])
    def test_capture_claims_version_and_remote_roots_rejected(self):
        for field,value in [('ready_for_training',True),('source_files_read',False),('proposed_refund_bytes',1),('execution_authorized',True)]:
            docs=copy.deepcopy(self.docs);docs['new_report']['connectivity_diagnostics'][field]=value
            with self.assertRaises(ValueError):self.build(docs)
        for version in [None,True,'split-repair-v1-INVALID','x'*4097]:
            docs=copy.deepcopy(self.docs);docs['plan']['derived_manifest_version']=version
            with self.assertRaises(ValueError):self.build(docs)
        for remote in ['https://example.invalid/data','//server/share','C:relative']:
            with patch.object(module,'_file_stamp',side_effect=AssertionError('No network/stat')),self.assertRaises(ValueError):module.inspect_candidate_plan_lineage(remote,self.paths,self.pins,token='shared',evidence_root=self.f.workspace)
    def test_ambiguous_declared_pair_and_unsupported_raw_path_not_promoted(self):
        for alter in [lambda d:d['source']['scenes'][1].update(image_path=d['source']['scenes'][0]['image_path'],patch_sha256=copy.deepcopy(d['source']['scenes'][0]['patch_sha256'])),lambda d:d['source']['scenes'][0].update(image_path='https://unopened.invalid/image.tif')]:
            docs=copy.deepcopy(self.docs);alter(docs)
            with self.assertRaises(ValueError):self.build(docs)
    def test_member_link_budget_checked_before_cartesian_materialization(self):
        with patch.object(module,'LINK_CAP',1),patch.object(module,'_refine_identity_members',side_effect=AssertionError('No refinement')),self.assertRaises(ValueError):self.build()
    def test_bounded_cli_core_pin_stability_and_input_bytes_preserved(self):
        before={k:p.read_bytes() for k,p in self.paths.items()};r=self.inspect();self.assertEqual(r['pin_validation'],'FIVE_INPUT_BYTE_SHA256_VERIFIED_WITH_STABILITY_RECHECK');self.assertEqual(before,{k:p.read_bytes() for k,p in self.paths.items()})
        self.pins['plan']='0'*64
        with self.assertRaises(ValueError):self.inspect()
    def test_preflight_size_confine_and_five_distinct_files(self):
        with patch.dict(module.BYTE_CAPS,{'source':1}),patch.object(module,'_read_bounded',side_effect=AssertionError('No content')),self.assertRaises(ValueError):self.inspect()
        self.paths['lineage']=self.paths['plan']
        with self.assertRaises(ValueError):self.inspect()
    def test_strict_json_depth_dupe_utf16_and_nonfinite(self):
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'['*33+b'0'+b']'*33,json.dumps({'a':'"'}).encode('utf-16')]:
            self.lineagepath.write_bytes(raw);self.pins['lineage']=self.f.sha(self.lineagepath)
            with self.assertRaises(ValueError):self.inspect()
    def test_logical_retarget_and_content_change_detected(self):
        original=module._read_bounded;calls=0
        def changing(*args):
            nonlocal calls
            raw=original(*args);calls+=1
            if calls==5:self.planpath.write_bytes(self.planpath.read_bytes()+b' ')
            return raw
        with patch.object(module,'_read_bounded',side_effect=changing),self.assertRaises(ValueError):self.inspect()
    def test_logical_target_recheck_without_content_change(self):
        original=module._confined;calls=0
        def retarget(scope,path):
            nonlocal calls
            calls+=1
            result=original(scope,path)
            return self.f.workspace/'retargeted.json' if calls>5 else result
        with patch.object(module,'_confined',side_effect=retarget),self.assertRaises(ValueError):self.inspect()
    def test_cli_cp949_new_only_output_and_input_alias(self):
        output=self.f.workspace/'결과–plan-reference.json'
        command=[sys.executable,str(fixtures.ROOT/'scripts/inspect_candidate_plan_lineage.py'),'--data-root',str(self.f.root),'--token','shared','--output',str(output)]
        for k in module.NAMES:command+=['--'+k.replace('_','-'),str(self.paths[k]),'--'+k.replace('_','-')+'-sha256',self.pins[k]]
        result=subprocess.run(command,capture_output=True,env={**os.environ,'PYTHONPATH':str(fixtures.ROOT/'.runtime'),'PYTHONIOENCODING':'cp949'})
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'],'PLAN_ONLY')
        before=output.read_bytes();again=subprocess.run(command,capture_output=True);self.assertEqual(again.returncode,1);self.assertEqual(output.read_bytes(),before)
    def test_cli_windows_alias_paths_rejected_without_writes(self):
        import scripts.inspect_candidate_plan_lineage as cli
        for value in [str(self.f.workspace/'CON.json'),str(self.f.workspace/'x.json:stream'),str(self.f.workspace/'trail.')]:
            with self.assertRaises(ValueError):cli._output_path(value,self.f.root,self.paths.values())

if __name__=='__main__':unittest.main()
