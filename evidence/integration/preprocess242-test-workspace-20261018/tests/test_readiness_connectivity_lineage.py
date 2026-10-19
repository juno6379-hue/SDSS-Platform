"""Tiny pinned JSON fixtures only; no real report/raster/assessment execution."""
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
from backend.app.data import readiness_connectivity_lineage as module
from backend.app.data.readiness_connectivity_witness import diagnose_readiness_connectivity,PROVINCES,FIXED_PROVINCE_SPLITS
from backend.app.ml.readiness_connectivity_adapter import capture_readiness_connectivity

ROOT=Path(__file__).resolve().parents[1]


class ReadinessConnectivityLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.workspace=Path(self.temp.name);self.root=self.workspace/'data';self.manifest=self.root/'first-group-training-esri-v1/annual-window-report.json';self.manifest.parent.mkdir(parents=True);self.report=self.root/'first-group/readiness-connectivity-20261017.json';self.report.parent.mkdir()
        self.raw=[{'province':'banten','source_group':'b/group','scene_id':'shared','image_path':'missing-b1.tif','patch_sha256':{'image':'a'*64}},{'province':'banten','source_group':'b/group','scene_id':'shared','image_path':'missing-b2.tif','patch_sha256':{'image':'b'*64}},{'province':'west_java','source_group':'w/group','scene_id':'shared','image_path':'missing-w.tif','patch_sha256':{'image':'c'*64}}]
        self.scenes=[{'province':r['province'],'source_group':r['source_group'],'scene_id':r['scene_id'],'bounds_wgs84':(i*3,0,i*3+1,1),'eligible_patches':0 if i==2 else 1} for i,r in enumerate(self.raw)]
        self.save()
    def tearDown(self):self.temp.cleanup()
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(self):
        self.manifest.write_text(json.dumps({'scenes':self.raw}),encoding='utf-8')
        policy={'required_provinces':list(PROVINCES),'province_splits':dict(FIXED_PROVINCE_SPLITS)}
        projected=[{'scene_index':i,'province':r['province'],'source_group':module._token(r['source_group'],group=True),'scene_id':module._token(r['scene_id']),'bounds_wgs84':list(r['bounds_wgs84'])} for i,r in enumerate(self.scenes)]
        witness=diagnose_readiness_connectivity(projected,FIXED_PROVINCE_SPLITS)
        refs=[{'path':str(self.manifest.relative_to(self.root)),'sha256':self.sha(self.manifest)}]
        capture=capture_readiness_connectivity(self.scenes,policy,witness['province_components'],refs)
        counts={'train':0,'val':0,'test':0}
        for r in self.scenes:counts[FIXED_PROVINCE_SPLITS[r['province']]]+=r['eligible_patches']
        self.fresh={'schema_version':1,'status':'blocked','ready_for_training':False,'scientific_accuracy_validated':False,'policy':policy,'group_splits':dict(FIXED_PROVINCE_SPLITS),'province_groups':witness['province_components'],'input_manifests':refs,'patch_counts_by_split':counts,'connectivity_diagnostics':capture}
        self.write_report()
    def write_report(self):self.report.write_text(json.dumps(self.fresh),encoding='utf-8')
    def inspect(self,token='shared',**kwargs):return module.inspect_readiness_connectivity_lineage(self.root,self.sha(self.report),self.sha(self.manifest),token,**kwargs)
    def test_all_members_ambiguous_candidates_and_zero_patch_without_source_io(self):
        before=self.manifest.read_bytes(),self.report.read_bytes()
        with patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No assess')),patch('backend.app.data.readiness_connectivity_witness.diagnose_readiness_connectivity',side_effect=AssertionError('No helper')):
            r=self.inspect()
        self.assertEqual(r['report_active_token_member_count'],3);self.assertEqual(r['raw_active_token_member_count'],3);self.assertEqual(r['candidate_link_count_total'],5);self.assertEqual(r['unique_candidate_raw_row_count'],3)
        self.assertEqual(r['binding_status_counts_all_report_literal_members'],{'AMBIGUOUS_MATCH_SET':2,'UNIQUE_METADATA_CANDIDATE':1});self.assertEqual(r['report_members'][2]['eligible_patches'],0)
        self.assertFalse(r['exact_row_binding_verified']);self.assertFalse(r['raw_row_order_used_as_identity']);self.assertEqual(before,(self.manifest.read_bytes(),self.report.read_bytes()))
        self.assertTrue(all(not c['source_file_read_or_hashed'] for c in r['candidate_rows']))
    def test_same_order_counts_never_choose_same_index_from_ambiguous_set(self):
        r=self.inspect();self.assertEqual(r['report_members'][0]['candidate_row_indices'],[0,1]);self.assertEqual(r['report_members'][1]['candidate_row_indices'],[0,1]);self.assertFalse(r['report_members'][0]['exact_row_binding_verified'])
    def test_fallback_missing_vs_explicit_null_and_falsy_group_skips_both_roles(self):
        self.raw=[{'aoi':'banten','scene_id':'shared','image_path':'x'}, {'province':'west_java','source_group':None,'scene_id':'shared','image_path':'y'}]
        self.scenes=[{'province':'banten','source_group':'shared','scene_id':'shared','bounds_wgs84':(0,0,1,1),'eligible_patches':1},{'province':'west_java','source_group':None,'scene_id':'shared','bounds_wgs84':(3,0,4,1),'eligible_patches':0}];self.save();r=self.inspect()
        self.assertEqual(r['raw_active_token_member_count'],1);self.assertEqual(r['raw_skipped_literal_member_count'],1);self.assertEqual(r['report_members'][0]['active_token_roles'],['source_group','scene_id']);self.assertEqual(r['report_members'][1]['active_token_roles'],[])
        self.assertEqual(r['report_members'][1]['candidate_status'],'UNIQUE_METADATA_CANDIDATE')
    def test_cross_role_namespace_scalar_str_and_province_id_fallback(self):
        self.raw=[{'province_id':'banten','source_group':123,'scene_id':None},{'aoi':'west_java','source_group':'different','scene_id':123}]
        self.scenes=[{'province':'banten','source_group':123,'scene_id':None,'bounds_wgs84':(0,0,1,1),'eligible_patches':1},{'province':'west_java','source_group':'different','scene_id':123,'bounds_wgs84':(3,0,4,1),'eligible_patches':0}];self.save();r=self.inspect('123')
        self.assertEqual(r['raw_active_token_member_count'],2);self.assertEqual(r['report_members'][0]['active_token_roles'],['source_group']);self.assertEqual(r['report_members'][1]['active_token_roles'],['scene_id'])
    def test_raw_province_none_does_not_fallback_unknown_not_absence(self):
        self.raw[0].update(province=None,aoi='banten');self.save();r=self.inspect();self.assertEqual(r['raw_unknown_row_count'],1);self.assertFalse(r['raw_metadata_membership_complete']);self.assertEqual(r['lineage_status'],'RAW_METADATA_INCOMPLETE')
    def test_no_token_raw_only_and_report_member_missing_match(self):
        self.assertEqual(self.inspect('absent')['lineage_status'],'TOKEN_NOT_FOUND')
        self.raw.append({'province':'banten','source_group':'raw-only','scene_id':'raw-only'});self.save();self.assertEqual(self.inspect('raw-only')['lineage_status'],'RAW_ONLY_MEMBERSHIP')
        self.raw=self.raw[2:];self.save();r=self.inspect();self.assertEqual(r['lineage_status'],'REPORT_MEMBER_NO_RAW_MATCH');self.assertEqual(r['binding_status_counts_all_report_literal_members']['NO_MATCH'],2)
    def test_output_caps_preserve_whole_membership_and_candidate_link_counts(self):
        r=self.inspect(max_candidates=1,max_members=1);self.assertEqual(r['report_active_token_member_count'],3);self.assertEqual(r['candidate_link_count_total'],5);self.assertEqual(r['unique_candidate_raw_row_count'],3);self.assertEqual(len(r['report_members']),1);self.assertEqual(r['candidate_link_count_stored'],1);self.assertTrue(r['output_truncated']);self.assertTrue(r['report_members'][0]['candidate_links_truncated'])
    def test_large_repeated_key_counts_do_not_materialize_all_candidate_pairs(self):
        self.raw=[copy.deepcopy(self.raw[0]) for _ in range(1000)];self.scenes=[{**self.scenes[0],'eligible_patches':1} for _ in range(50)];self.save();r=self.inspect(max_candidates=2)
        self.assertEqual(r['candidate_link_count_total'],50000);self.assertEqual(r['candidate_link_count_stored'],2);self.assertEqual(r['unique_candidate_raw_row_count'],1000);self.assertEqual(len(r['candidate_rows']),2)
    def test_typed_counter_index_order_policy_and_partial_capture_rejected(self):
        original=copy.deepcopy(self.fresh)
        for mutate in [lambda d:d.update(schema_version=True),lambda d:d['connectivity_diagnostics'].update(scene_count=True),lambda d:d['connectivity_diagnostics']['projected_scene_metadata'][1].update(scene_index=0),lambda d:d['connectivity_diagnostics']['scene_mapping'][0].update(eligible_position=True),lambda d:d['policy']['province_splits'].update(banten='train'),lambda d:d['connectivity_diagnostics'].update(capture_status='NOT_CAPTURED_BUDGET'),lambda d:d['connectivity_diagnostics']['witness'].update(witness_edge_count_stored=False),lambda d:d['connectivity_diagnostics']['witness'].update(execution_authorized=True),lambda d:d['connectivity_diagnostics'].update(proposed_refund_bytes=True),lambda d:d['connectivity_diagnostics']['witness']['limits'].update(max_scenes=True),lambda d:d['connectivity_diagnostics']['limits'].update(max_bbox_pairs=1),lambda d:d['connectivity_diagnostics']['witness'].update(token_occurrences_processed=False)]:
            self.fresh=copy.deepcopy(original);mutate(self.fresh);self.write_report()
            with self.assertRaises(ValueError):self.inspect()
    def test_report_manifest_binding_sha_path_or_ref_alias_mismatch(self):
        original=copy.deepcopy(self.fresh)
        for value in ['../outside.json','https://example.invalid/report.json','different.json']:
            self.fresh=copy.deepcopy(original);self.fresh['input_manifests'][0]['path']=value;self.fresh['connectivity_diagnostics']['manifest_input_references']=copy.deepcopy(self.fresh['input_manifests']);self.write_report()
            with self.assertRaises(ValueError):self.inspect()
        self.fresh=copy.deepcopy(original);self.fresh['input_manifests'][0]['sha256']='0'*64;self.write_report()
        with self.assertRaises(ValueError):self.inspect()
    def test_strict_json_utf8_depth_duplicate_nonfinite_pin_and_string_caps(self):
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*40+b'0'+b']'*40,json.dumps({'a':'"'}).encode('utf-16')]:
            self.report.write_bytes(raw)
            with self.assertRaises((ValueError,UnicodeError)):self.inspect()
        self.write_report()
        with self.assertRaises(ValueError):module.inspect_readiness_connectivity_lineage(self.root,'0'*64,self.sha(self.manifest),'shared')
        for token in [None,1,'x'*4097]:
            with self.assertRaises(ValueError):self.inspect(token)
        for key in ['max_candidates','max_members']:
            with self.assertRaises(ValueError):self.inspect(**{key:True})
    def test_both_file_size_preflight_before_any_content_and_stale_changes(self):
        with patch.object(module,'REPORT_BYTES',1),patch.object(module,'_read_bounded',side_effect=AssertionError('No content IO')),self.assertRaises(ValueError):self.inspect()
        original=module._read_bounded;calls=0
        def change(*args):
            nonlocal calls
            raw=original(*args);calls+=1
            if calls==2:self.manifest.write_bytes(self.manifest.read_bytes()+b' ')
            return raw
        with patch.object(module,'_read_bounded',side_effect=change),self.assertRaises(ValueError):self.inspect()
    def test_logical_target_retarget_or_outside_report_rejected(self):
        original=module._confined;count=0
        def retarget(root,path):
            nonlocal count
            value=original(root,path)
            if Path(path)==self.report:
                count+=1
                if count>1:return self.root/'retargeted.json'
            return value
        with patch.object(module,'_confined',side_effect=retarget),self.assertRaises(ValueError):self.inspect()
        with self.assertRaises(ValueError):self.inspect(report_path=self.workspace/'outside-report.json')
    def test_declared_candidate_hash_and_paths_are_claims_missing_invalid_explicit(self):
        self.raw[0].update(image_path='https://not-opened.invalid/image.tif',patch_sha256={'image':False});self.save();r=self.inspect();c=r['candidate_rows'][0]
        self.assertEqual(c['image_path_declared'],'https://not-opened.invalid/image.tif');self.assertEqual(c['declared_patch_image_sha256_status'],'MISSING_OR_INVALID');self.assertFalse(c['source_file_read_or_hashed'])
    def test_cli_output_windows_aliases_and_preserved_logical_report_argument(self):
        import scripts.inspect_readiness_connectivity_lineage as cli
        for value in [str(self.workspace/'file.json:stream'),str(self.workspace/'CON.json'),str(self.workspace/'trailing.'),'C:\\tmp\\CON.txt']:
            with self.assertRaises(ValueError):cli._output_path(value,self.root,[self.report,self.manifest])
        alias=self.root/'logical-alias'/'report.json'
        argv=['inspect_readiness_connectivity_lineage.py','--data-root',str(self.root),'--report',str(alias),'--expected-report-sha256',self.sha(self.report),'--expected-manifest-sha256',self.sha(self.manifest),'--token','shared']
        minimal={k:None for k in ['status','lineage_status','report_active_token_member_count','raw_active_token_member_count','candidate_link_count_total','unique_candidate_raw_row_count','output_truncated','exact_row_binding_verified']}
        import io
        with patch.object(sys,'argv',argv),patch.object(cli,'inspect_readiness_connectivity_lineage',return_value=minimal) as inspect,patch.object(sys,'stdout',io.StringIO()):self.assertEqual(cli.main(),0)
        self.assertEqual(inspect.call_args.kwargs['report_path'],alias.absolute())
    def test_cli_cp949_ascii_summary_utf8_evidence_and_existing_alias_protection(self):
        output=self.workspace/'결과–lineage.json';command=[sys.executable,str(ROOT/'scripts/inspect_readiness_connectivity_lineage.py'),'--data-root',str(self.root),'--expected-report-sha256',self.sha(self.report),'--expected-manifest-sha256',self.sha(self.manifest),'--token','shared','--output',str(output)]
        env={**os.environ,'PYTHONIOENCODING':'cp949'};result=subprocess.run(command,capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['candidate_link_count_total'],5)
        before=output.read_bytes();again=subprocess.run(command,capture_output=True,env=env);self.assertEqual(again.returncode,1);self.assertEqual(before,output.read_bytes());self.assertTrue(again.stderr.isascii())
        command[-1]=str(self.report);before=self.report.read_bytes();again=subprocess.run(command,capture_output=True,env=env);self.assertEqual(again.returncode,1);self.assertEqual(before,self.report.read_bytes())


    def complete_identity(self):
        for index,(scene,row) in enumerate(zip(self.scenes,self.raw)):
            row['image_path']=str(self.root/f'images/source-{index}.tif')
            scene['image_path']=f'images/source-{index}.tif';scene['image_sha256']=row['patch_sha256']['image']
        self.save()
    def test_identity_complete_declared_pair_refines_without_changing_broad_candidates(self):
        self.complete_identity();r=self.inspect();refined=r['source_identity_refinement']
        self.assertEqual(r['candidate_link_count_total'],5);self.assertEqual(refined['candidate_link_count_total'],3);self.assertEqual(refined['unique_candidate_raw_row_count'],3)
        self.assertEqual([m['refined_match_status'] for m in refined['members']],['UNIQUE_DECLARED_METADATA_CANDIDATE']*3);self.assertEqual(refined['members'][2]['eligible_patches'],0)
        self.assertTrue(all(not m['exact_row_binding_verified'] for m in refined['members']));self.assertFalse(refined['original_file_or_product_authenticity_verified'])
    def test_identity_duplicate_declarations_remain_ambiguous_and_counts_unique(self):
        self.complete_identity();self.raw[1]['image_path']=self.raw[0]['image_path'];self.raw[1]['patch_sha256']=copy.deepcopy(self.raw[0]['patch_sha256']);self.scenes[1]['image_path']=self.scenes[0]['image_path'];self.scenes[1]['image_sha256']=self.scenes[0]['image_sha256'];self.save()
        r=self.inspect();refined=r['source_identity_refinement'];self.assertEqual(refined['candidate_link_count_total'],5);self.assertEqual(refined['unique_candidate_raw_row_count'],3);self.assertEqual(refined['members'][0]['refined_match_status'],'AMBIGUOUS_DECLARED_METADATA_MATCH_SET')
    def test_identity_absence_partial_invalid_and_unsupported_path_preserve_candidates(self):
        baseline=self.inspect();self.fresh['connectivity_diagnostics'].pop('source_identity');self.write_report();legacy=self.inspect();self.assertNotIn('source_identity_refinement',legacy)
        baseline.pop('source_identity_refinement');baseline['inputs']['report'].pop('sha256');legacy['inputs']['report'].pop('sha256');self.assertEqual(baseline,legacy)
        for field,value in [('image_path','images/partial.tif'),('image_sha256',False)]:
            self.scenes[0][field]=value;self.save();refined=self.inspect()['source_identity_refinement'];self.assertEqual(refined['candidate_link_count_total'],5)
        self.complete_identity();self.scenes[0]['image_path']='../outside.tif';self.save();r=self.inspect();self.assertEqual(r['source_identity_refinement']['members'][0]['refinement_status'],'NOT_REFINED_UNSUPPORTED_LEXICAL_PATH');self.assertEqual(r['source_identity_refinement']['members'][0]['refined_candidate_count'],2)
    def test_identity_raw_incomparable_declarations_keep_whole_original_match_set(self):
        self.complete_identity();self.raw[0]['image_path']='https://not-read.invalid/a.tif';self.save();r=self.inspect();refined=r['source_identity_refinement'];self.assertEqual(refined['members'][0]['refinement_status'],'NOT_REFINED_RAW_DECLARATIONS_INCOMPLETE');self.assertEqual(refined['members'][0]['candidate_row_indices'],[0,1]);self.assertEqual(refined['candidate_link_count_total'],5)
        self.raw[0]['province']=None;self.save();self.assertEqual(self.inspect()['source_identity_refinement']['members'][0]['refinement_status'],'NOT_REFINED_RAW_METADATA_INCOMPLETE')
    def test_identity_version_flags_order_status_and_field_state_tamper_fail_closed(self):
        self.complete_identity();original=copy.deepcopy(self.fresh)
        mutations=[lambda x:x.update(identity_schema_version=True),lambda x:x.update(identity_schema_version=2),lambda x:x.update(source_authenticity_verified=True),lambda x:x.update(scene_count=True),lambda x:x.update(complete_declared_scene_count=False),lambda x:x.update(coverage_status='UNKNOWN_NOT_PROVIDED'),lambda x:x['scene_identities'][1].update(scene_index=0),lambda x:x['scene_identities'][0].update(identity_status='UNKNOWN_NOT_PROVIDED'),lambda x:x['scene_identities'][0].update(image_sha256_declared='A'*64),lambda x:x['scene_identities'][0].update(image_path_status='ABSENT'),lambda x:x.update(extra=True)]
        for mutate in mutations:
            self.fresh=copy.deepcopy(original);mutate(self.fresh['connectivity_diagnostics']['source_identity']);self.write_report()
            with self.assertRaises(ValueError):self.inspect()
    def test_identity_not_captured_error_preserves_unknown_broad_set(self):
        with patch('backend.app.ml.readiness_connectivity_adapter._source_identity_metadata',side_effect=RuntimeError('fixture')):self.save()
        r=self.inspect();refined=r['source_identity_refinement'];self.assertEqual(refined['candidate_link_count_total'],5);self.assertTrue(all(m['refinement_status']=='NOT_REFINED_IDENTITY_NOT_CAPTURED' for m in refined['members']))
    def test_lexical_path_protocol_no_filesystem_and_platform_boundaries(self):
        with patch.object(Path,'resolve',side_effect=AssertionError('No resolve')),patch.object(Path,'stat',side_effect=AssertionError('No stat')),patch('builtins.open',side_effect=AssertionError('No open')):
            root='E:\\DATA';left=module._lexical_identity_path('region/image.tif',root);right=module._lexical_identity_path('e:\\data\\REGION\\IMAGE.TIF',root);self.assertEqual(left,right)
            for value in ['E:\\data-other\\image.tif','C:\\DATA\\image.tif','E:relative.tif','\\rooted.tif','../outside.tif','https://x/image.tif','\\\\server\\image.tif','folder/file:stream','CON.tif','trailing.tif.','bad?.tif','bad*.tif','bad|x.tif','folder/']:
                self.assertIsNone(module._lexical_identity_path(value,root),value)
            self.assertNotEqual(module._lexical_identity_path('A.tif','/data'),module._lexical_identity_path('a.tif','/data'));self.assertIsNone(module._lexical_identity_path('/data-other/x.tif','/data'))
    def test_identity_refinement_budget_cache_and_declared_mismatch_zero(self):
        self.complete_identity();self.scenes[0]['image_sha256']='f'*64;self.save();r=self.inspect(max_candidates=1);refined=r['source_identity_refinement'];self.assertEqual(refined['members'][0]['refined_match_status'],'NO_DECLARED_METADATA_MATCH');self.assertEqual(refined['candidate_link_count_total'],2);self.assertTrue(refined['output_truncated']);self.assertLessEqual(refined['candidate_link_count_stored'],1)
        self.raw=[copy.deepcopy(self.raw[0]) for _ in range(1000)];self.scenes=[copy.deepcopy(self.scenes[0]) for _ in range(50)];self.scenes[0]['image_sha256']=self.raw[0]['patch_sha256']['image']
        for item in self.scenes:item['image_sha256']=self.raw[0]['patch_sha256']['image']
        self.save();r=self.inspect(max_candidates=2);refined=r['source_identity_refinement'];self.assertEqual(refined['candidate_link_count_total'],50000);self.assertEqual(refined['unique_candidate_raw_row_count'],1000);self.assertEqual(refined['candidate_link_count_stored'],2)


if __name__=='__main__':unittest.main()
