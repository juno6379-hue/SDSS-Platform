"""작은 합성 저장통계만 사용하며 픽셀/QA/수집/학습을 실행하지 않는다."""
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
from backend.app.ml import bare_class_requirements as module
from backend.app.ml.readiness import balance_diagnostics

ROOT=Path(__file__).resolve().parents[1]


class BareClassRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.workspace=Path(self.temp.name);self.root=self.workspace/'data';self.path=self.root/module.REPORT_RELATIVE;self.path.parent.mkdir(parents=True)
        policy={'province_splits':dict(module.FIXED_PROVINCE_SPLITS),'patch_size':256,'required_classes':[0,1,2,4,6,7],'min_class_pixels_per_split':256,'min_class_patches_per_split':5,'min_class_pixels_per_patch':256,'min_required_class_ratio':.005,'max_reference_class_dominance':.9,'label_source':'esri_io'}
        self.report={'schema_version':1,'status':'blocked','ready_for_training':False,'scientific_accuracy_validated':False,'policy':policy,'input_signature':{'class_names':['water','trees','grass','flooded','crops','unused','built','bare','snow'],'label_source':'esri_io'},'input_manifests':[{'path':'candidate.json','sha256':'a'*64}],'blockers':[{'code':'REFERENCE_CLASS_IMBALANCE'}]*3+[{'code':'CLASS_COVERAGE'}],
          'patch_counts_by_split':{'train':628,'val':217,'test':250},'class_counts_by_split':{'train':[3284571,23384879,3847244,218,7043179,0,2587604,1418,0],'val':[104961,5321808,143324,741,2339876,0,6078324,209,0],'test':[126922,6243038,1528013,12967,1942451,0,6398524,1025,0]},
          'class_patch_counts_by_split':{'train':[138,520,285,0,268,0,285,0,0],'val':[76,183,103,1,171,0,193,0,0],'test':[38,193,174,7,124,0,184,0,0]}}
        self.balance();self.save()
    def tearDown(self):self.temp.cleanup()
    def balance(self):self.report['reference_balance_by_split']={s:balance_diagnostics(self.report['class_counts_by_split'][s],self.report['class_patch_counts_by_split'][s],self.report['policy']) for s in ['train','val','test']}
    def save(self):self.path.write_text(json.dumps(self.report),encoding='utf-8');self.pin=hashlib.sha256(self.path.read_bytes()).hexdigest()
    def build(self,report=None):return module.build_bare_class_requirements(report or self.report,{'path':str(self.path),'sha256':self.pin})
    def test_separate_pixel_patch_ratio_dominance_conditions(self):
        result=self.build();splits=result['by_split'];self.assertEqual(result['eligible_patch_count'],1095);self.assertEqual(result['fixed_province_splits'],module.FIXED_PROVINCE_SPLITS)
        self.assertEqual([splits[s]['split_pixel_shortfall'] for s in splits],[0,47,0]);self.assertEqual([splits[s]['contributing_patch_shortfall'] for s in splits],[5,5,5])
        self.assertEqual([splits[s]['reference_class_pixel_total'] for s in splits],[40149113,13989243,16252940]);self.assertTrue(all(not row['bare_ratio_threshold_met'] for row in splits.values()));self.assertTrue(all(row['dominance_threshold_met'] for row in splits.values()))
        self.assertTrue(all(row['stored_reference_balance_failures']==['class7_pixel_ratio','class7_patch_representation'] for row in splits.values()));self.assertTrue(all(result[k] is False for k in module.FALSE_FIELDS))
    def test_pure_projection_no_io_assess_or_input_mutation(self):
        before=copy.deepcopy(self.report)
        with patch('pathlib.Path.open',side_effect=AssertionError('No IO')),patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No QA')):result=self.build()
        self.assertEqual(before,self.report);self.assertEqual(result['pin_validation'],'CALLER_DECLARED_REFERENCE_ONLY');self.assertFalse(result['source_manifest_currently_verified'])
    def test_zero_denominator_stored_zero_ratios_output_unavailable(self):
        for s in ['train','val','test']:self.report['patch_counts_by_split'][s]=0;self.report['class_counts_by_split'][s]=[0]*9;self.report['class_patch_counts_by_split'][s]=[0]*9
        self.balance();result=self.build()
        for row in result['by_split'].values():self.assertIsNone(row['bare_ratio']);self.assertIsNone(row['bare_ratio_shortfall']);self.assertIsNone(row['dominant_class_ratio']);self.assertFalse(row['bare_ratio_threshold_met']);self.assertFalse(row['dominance_threshold_met'])
    def test_contribution_patches_can_share_one_patch_across_classes(self):
        for s in ['train','val','test']:
            self.report['patch_counts_by_split'][s]=1;self.report['class_counts_by_split'][s]=[256,0,0,0,0,0,0,256,0];self.report['class_patch_counts_by_split'][s]=[1,0,0,0,0,0,0,1,0]
        self.balance();r=self.build();self.assertEqual(r['by_split']['train']['contributing_patch_shortfall'],4);self.assertEqual(r['by_split']['train']['bare_ratio'],.5)
    def test_per_class_contribution_minimum_and_pixel_total_bound(self):
        for change in [lambda r:r['class_patch_counts_by_split']['train'].__setitem__(7,6),lambda r:r['class_patch_counts_by_split']['val'].__setitem__(0,218),lambda r:r['class_counts_by_split']['val'].__setitem__(0,217*65536),lambda r:r['class_counts_by_split']['train'].__setitem__(7,10**400)]:
            r=copy.deepcopy(self.report);change(r)
            with self.assertRaises(ValueError):self.build(r)
    def test_typed_counts_policy_nonfinite_and_class_scope_rejected(self):
        changes=[lambda r:r['class_counts_by_split']['val'].__setitem__(7,True),lambda r:r['class_counts_by_split']['val'].__setitem__(7,209.0),lambda r:r['policy'].update(min_class_pixels_per_split=True),lambda r:r['policy'].update(min_class_patches_per_split=5.0),lambda r:r['policy'].update(min_required_class_ratio=float('nan')),lambda r:r['policy'].update(max_reference_class_dominance=10**400),lambda r:r['policy'].update(required_classes=[7,7]),lambda r:r['policy'].update(required_classes=[9,7]),lambda r:r['input_signature']['class_names'].__setitem__(7,'unknown')]
        for change in changes:
            r=copy.deepcopy(self.report);change(r)
            with self.assertRaises(ValueError):self.build(r)
    def test_current_candidate_policy_scope_does_not_accept_relaxation(self):
        for key,value in [('required_classes',[7]),('min_required_class_ratio',0),('min_required_class_ratio',.0049),('max_reference_class_dominance',1),('min_class_pixels_per_split',65537),('min_class_patches_per_split',4),('min_class_pixels_per_patch',255)]:
            report=copy.deepcopy(self.report);report['policy'][key]=value
            with self.assertRaises(ValueError):self.build(report)
    def test_stored_balance_whole_typed_tamper_rejected(self):
        for change in [lambda r:r['reference_balance_by_split']['val'].update(passed=True),lambda r:r['reference_balance_by_split']['train']['class_ratios'].__setitem__(7,0.005),lambda r:r['reference_balance_by_split']['test'].update(failures=[]),lambda r:r['reference_balance_by_split']['val']['class_patch_counts'].__setitem__(7,False)]:
            r=copy.deepcopy(self.report);change(r)
            with self.assertRaises(ValueError):self.build(r)
    def test_pixel_floor_alone_never_satisfies_ratio_or_patch_condition(self):
        self.report['class_counts_by_split']['val'][7]=256;self.balance();r=self.build()['by_split']['val'];self.assertEqual(r['split_pixel_shortfall'],0);self.assertEqual(r['contributing_patch_shortfall'],5);self.assertFalse(r['bare_ratio_threshold_met']);self.assertFalse(r['all_bare_conditions_met'])
    def test_reader_only_one_fixed_json_and_byte_preservation(self):
        before=self.path.read_bytes();original=Path.open;opened=[]
        def guard(path,*args,**kwargs):self.assertEqual(path.resolve(),self.path.resolve());opened.append(path);return original(path,*args,**kwargs)
        with patch('pathlib.Path.open',guard):r=module.inspect_bare_class_requirements(self.root,self.pin)
        self.assertEqual(len(opened),2);self.assertEqual(self.path.read_bytes(),before);self.assertEqual(r['pin_validation'],'PINNED_REPORT_BYTES_AND_STABILITY_VERIFIED')
    def test_pin_formats_size_preflight_and_strict_json(self):
        for pin in [None,True,'A'*64,'0'*64]:
            with self.assertRaises(ValueError):module.inspect_bare_class_requirements(self.root,pin)
        with patch.object(module,'REPORT_CAP',1),patch('pathlib.Path.open',side_effect=AssertionError('No content')),self.assertRaises(ValueError):module.inspect_bare_class_requirements(self.root,self.pin)
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'['*33+b'0'+b']'*33,json.dumps({'q':'"'}).encode('utf-16')]:
            self.path.write_bytes(raw);pin=hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):module.inspect_bare_class_requirements(self.root,pin)
    def test_stale_logical_target_and_remote_source_reference_rejected(self):
        original=module.BoundedJSONIO.read;calls=0
        def changed(io,*args):
            nonlocal calls
            r=original(io,*args);calls+=1
            if calls==1:self.path.write_bytes(self.path.read_bytes()+b' ')
            return r
        with patch.object(module.BoundedJSONIO,'read',changed),self.assertRaises(ValueError):module.inspect_bare_class_requirements(self.root,self.pin)
        self.report['input_manifests'][0]['path']='https://unread.invalid/data.json';self.save()
        with self.assertRaises(ValueError):module.inspect_bare_class_requirements(self.root,self.pin)
    def test_cli_cp949_fresh_evidence_output_and_existing_input_preserved(self):
        output=self.workspace/'결과–bare.json';command=[sys.executable,str(ROOT/'scripts/inspect_bare_class_requirements.py'),'--data-root',str(self.root),'--expected-report-sha256',self.pin,'--output',str(output)]
        env={**os.environ,'PYTHONPATH':str(ROOT/'.runtime'),'PYTHONIOENCODING':'cp949'};result=subprocess.run(command,capture_output=True,env=env);self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['by_split']['val']['split_pixel_shortfall'],47)
        before=output.read_bytes();again=subprocess.run(command,capture_output=True,env=env);self.assertEqual(again.returncode,1);self.assertTrue(again.stderr.isascii());self.assertEqual(output.read_bytes(),before)
    def test_output_alias_windows_devices_and_output_cap(self):
        from scripts import inspect_bare_class_requirements as cli
        for path in [self.path,self.workspace/'CON.json',self.workspace/'file.json:stream',self.workspace/'trailing.']:
            with self.assertRaises(ValueError):cli._output_path(path,self.root,[self.path])
        command=[sys.executable,str(ROOT/'scripts/inspect_bare_class_requirements.py'),'--data-root',str(self.root),'--expected-report-sha256',self.pin,'--output',str(self.workspace/'new.json')]
        # A small output cap fails measurement before output creation.
        import io
        with patch.object(sys,'argv',command[1:]),patch.object(cli,'OUTPUT_CAP',1),patch.object(sys,'stderr',io.StringIO()):self.assertEqual(cli.main(),1)
        self.assertFalse((self.workspace/'new.json').exists())

if __name__=='__main__':unittest.main()
