"""Synthetic/mock CLI opt-in and new-file safety; no real readiness or training."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts import run_experiment as module

ROOT=Path(__file__).resolve().parents[1]


class ReadinessConnectivityCliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.root=Path(self.temp.name)
        self.manifest=self.root/'합성–inputs.json';self.manifest.write_text(json.dumps({'synthetic':True,'scenes':[]}),encoding='utf-8')
        self.output=self.root/'진단–new.json'
        self.result={'schema_version':1,'status':'blocked','ready_for_training':False,'blockers':[{'code':'TEST','detail':'합성 차단'}],'scientific_accuracy_validated':False,
          'patch_counts_by_split':{'train':2,'val':0,'test':1},'connectivity_diagnostics':{'capture_status':'CAPTURED_COMPONENTS_MATCH','scene_count':4,'supplied_eligible_patch_sum':3,'ready_for_training':False}}
    def tearDown(self):self.temp.cleanup()
    def run_mock(self,**kwargs):
        with patch.object(module,'assess',return_value=copy.deepcopy(self.result)) as assess,patch.object(module,'train_model',side_effect=AssertionError('Never train')):
            result=module.run([self.manifest],self.root,self.output,**kwargs)
        return result,assess
    def argv(self,*extra):return ['run_experiment.py','--manifest',str(self.manifest),'--data-root',str(self.root),'--readiness-output',str(self.output),*extra]
    def child(self,*extra):return subprocess.run([sys.executable,str(ROOT/'scripts/run_experiment.py'),*self.argv(*extra)[1:]],cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'cp949'},capture_output=True)
    def test_default_off_assess_call_shape_and_legacy_existing_output_write(self):
        self.output.write_text('existing legacy output',encoding='utf-8');result,assess=self.run_mock()
        assess.assert_called_once_with([self.manifest.resolve()],self.root.resolve(),None)
        self.assertEqual(json.loads(self.output.read_text(encoding='utf-8')),result)
    def test_true_flag_only_passed_when_opted_in_and_new_utf8_output(self):
        result,assess=self.run_mock(connectivity_diagnostics=True)
        assess.assert_called_once_with([self.manifest.resolve()],self.root.resolve(),None,connectivity_diagnostics=True)
        self.assertIn('합성 차단',self.output.read_text(encoding='utf-8'));self.assertEqual(result['connectivity_diagnostics']['scene_count'],4)
    def test_invalid_bool_before_assess_or_output(self):
        for value in [0,1,None,'true',[]]:
            with patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=value)
        self.assertFalse(self.output.exists())
    def test_existing_file_directory_broken_symlink_and_alias_rejected_before_assess(self):
        self.output.write_bytes(b'preserve')
        with patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=True)
        self.assertEqual(self.output.read_bytes(),b'preserve');directory=self.root/'directory';directory.mkdir()
        with patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([self.manifest],self.root,directory,connectivity_diagnostics=True)
        broken=self.root/'broken';original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda path:True if path==broken else original(path)),patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([self.manifest],self.root,broken,connectivity_diagnostics=True)
        missing=self.root/'missing-input.json'
        with patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([missing],self.root,missing,connectivity_diagnostics=True)
    def test_final_symlink_is_rejected_before_following_exists(self):
        original=Path.exists
        def exists(path):
            if path==self.output:raise AssertionError('Do not follow final symlink')
            return original(path)
        original_link=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda path:True if path==self.output else original_link(path)),patch.object(Path,'exists',exists),self.assertRaises(ValueError):module._diagnostic_output(self.root,self.output,[self.manifest])
    def test_windows_ads_device_and_normalization_aliases_rejected_before_assess(self):
        for filename in ['existing.json:diagnostic','file::$DATA','NUL','CON.txt','COM1.json','LPT¹.txt','CONOUT$','CON .txt','file.','file ']:
            with self.subTest(filename=filename),patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.root/filename,connectivity_diagnostics=True)
        for value in ['C:\\synthetic\\CON.json','C:\\synthetic\\file.json:stream','\\\\?\\C:\\synthetic\\new.json']:
            with self.subTest(value=value),self.assertRaises(ValueError):module._local_path(value)
        self.assertEqual(json.loads(self.manifest.read_text(encoding='utf-8')),{'synthetic':True,'scenes':[]})
    def test_outside_root_or_remote_diagnostic_path_precheck(self):
        for output in [self.root.parent/'outside-new.json',Path('https://example.invalid/out.json')]:
            with patch.object(module,'assess',side_effect=AssertionError('Must precheck')),self.assertRaises(ValueError):module.run([self.manifest],self.root,output,connectivity_diagnostics=True)
    def test_assess_created_output_race_preserves_winner(self):
        def raced(*args,**kwargs):self.output.write_bytes(b'winner');return copy.deepcopy(self.result)
        with patch.object(module,'assess',side_effect=raced),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=True)
        self.assertEqual(self.output.read_bytes(),b'winner')
    def test_xmode_final_race_does_not_overwrite_winner(self):
        original=Path.open
        def raced(path,mode='r',*args,**kwargs):
            if path==self.output and mode=='x':
                with original(path,'wb') as stream:stream.write(b'late-winner')
            return original(path,mode,*args,**kwargs)
        with patch.object(module,'assess',return_value=copy.deepcopy(self.result)),patch.object(Path,'open',raced),self.assertRaises(FileExistsError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=True)
        self.assertEqual(self.output.read_bytes(),b'late-winner')
    def test_parent_identity_or_logical_resolution_change_rejected(self):
        identity=module._directory_identity;calls=0
        def changed(path):
            nonlocal calls
            calls+=1;value=identity(path)
            return value if calls==1 else (value[0],value[1]+1)
        with patch.object(module,'assess',return_value=copy.deepcopy(self.result)),patch.object(module,'_directory_identity',side_effect=changed),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=True)
        self.assertFalse(self.output.exists())
        original=Path.resolve;count=0
        def retarget(path,*args,**kwargs):
            nonlocal count
            value=original(path,*args,**kwargs)
            if path==self.output.parent:
                count+=1
                # root.resolve first, then logical.parent.resolve preflight.
                if count>=3:return self.root/'retargeted-parent'
            return value
        with patch.object(module,'assess',return_value=copy.deepcopy(self.result)),patch.object(Path,'resolve',retarget),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=True)
        self.assertFalse(self.output.exists())
    def test_partial_new_file_is_retained_without_cleanup(self):
        def failure(result,stream,**kwargs):stream.write('partial-new-evidence');raise OSError('synthetic write error')
        with patch.object(module,'assess',return_value=copy.deepcopy(self.result)),patch.object(module.json,'dump',side_effect=failure),self.assertRaises(OSError):module.run([self.manifest],self.root,self.output,connectivity_diagnostics=True)
        self.assertEqual(self.output.read_text(encoding='utf-8'),'partial-new-evidence')
    def test_ready_without_execute_and_blocked_with_execute_never_train(self):
        for ready,execute in [(True,False),(False,True)]:
            result=copy.deepcopy(self.result);result['ready_for_training']=ready;result['status']='ready_for_weak_label_experiment' if ready else 'blocked'
            output=self.root/f'{ready}-{execute}.json'
            with patch.object(module,'assess',return_value=result),patch.object(module,'train_model',side_effect=AssertionError('Never train')),patch.object(module,'prepare_dataset',side_effect=AssertionError('Never prepare')):
                returned=module.run([self.manifest],self.root,output,execute=execute,connectivity_diagnostics=True)
            self.assertEqual(returned['ready_for_training'],ready);self.assertFalse(returned['connectivity_diagnostics']['ready_for_training'])
    def test_diagnostics_cannot_bypass_original_run_id_validation(self):
        result=copy.deepcopy(self.result);result['ready_for_training']=True
        with patch.object(module,'assess',return_value=result),patch.object(module,'train_model',side_effect=AssertionError('Never train')),self.assertRaises(ValueError):module.run([self.manifest],self.root,self.output,execute=True,run_id='invalid/id',connectivity_diagnostics=True)
    def test_summary_unknown_missing_and_invalid_counts_do_not_imply_success(self):
        self.assertEqual(module._connectivity_summary({})['connectivity_capture_status'],'NOT_REPORTED')
        for status in ['NEW_UNKNOWN',True,None]:
            value={'connectivity_diagnostics':{'capture_status':status,'scene_count':True,'supplied_eligible_patch_sum':-1},'patch_counts_by_split':{'train':True,'val':0,'test':1}}
            summary=module._connectivity_summary(value);self.assertEqual(summary['connectivity_capture_status'],'UNKNOWN_CAPTURE_STATUS');self.assertIsNone(summary['connectivity_scene_count']);self.assertIsNone(summary['eligible_patch_count']);self.assertFalse(summary['connectivity_is_training_authorization'])
    def test_main_off_summary_keyset_and_assess_run_call_shape_preserved(self):
        value=copy.deepcopy(self.result);value.pop('connectivity_diagnostics');stdout=io.StringIO()
        with patch.object(sys,'argv',self.argv()),patch.object(module,'run',return_value=value) as run,patch.object(sys,'stdout',stdout):self.assertEqual(module.main(),0)
        summary=json.loads(stdout.getvalue());self.assertEqual(set(summary),{'status','ready_for_training','blocker_count','scientific_accuracy_validated'});self.assertEqual(run.call_args.kwargs,{})
    def test_main_plan_alias_rejected_before_plan_read_or_assess(self):
        missing=self.root/'new-plan.json';argv=self.argv('--connectivity-diagnostics','--plan',str(missing));argv[argv.index('--readiness-output')+1]=str(missing)
        with patch.object(sys,'argv',argv),patch.object(Path,'read_text',side_effect=AssertionError('Must precheck plan alias')),patch.object(module,'assess',side_effect=AssertionError('Must precheck')),patch.object(sys,'stderr',io.StringIO()):self.assertEqual(module.main(),1)
        self.assertFalse(missing.exists())
    def test_cli_write_default_plan_conflict_and_missing_explicit_output(self):
        before=self.manifest.read_bytes();result=self.child('--connectivity-diagnostics','--write-default-plan',str(self.manifest))
        self.assertEqual(result.returncode,2);self.assertEqual(self.manifest.read_bytes(),before);self.assertFalse(self.output.exists())
        argv=self.argv('--connectivity-diagnostics');index=argv.index('--readiness-output');del argv[index:index+2]
        result=subprocess.run([sys.executable,str(ROOT/'scripts/run_experiment.py'),*argv[1:]],cwd=ROOT,capture_output=True)
        self.assertEqual(result.returncode,2);self.assertFalse(self.output.exists())
    def test_real_synthetic_cli_cp949_ascii_summary_and_new_utf8_file(self):
        result=self.child('--connectivity-diagnostics')
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());summary=json.loads(result.stdout)
        self.assertEqual(summary['status'],'blocked');self.assertEqual(summary['connectivity_capture_status'],'CAPTURED_COMPONENTS_MATCH');self.assertEqual(summary['connectivity_scene_count'],0);self.assertFalse(summary['connectivity_is_training_authorization'])
        saved=json.loads(self.output.read_text(encoding='utf-8'));self.assertIn('합성',saved['blockers'][0]['detail']);self.assertIn('connectivity_diagnostics',saved)
        before=self.output.read_bytes();again=self.child('--connectivity-diagnostics');self.assertEqual(again.returncode,1);self.assertTrue(again.stderr.isascii());self.assertEqual(self.output.read_bytes(),before)
    def test_real_synthetic_cli_blocked_execute_exit2_without_training(self):
        result=self.child('--connectivity-diagnostics','--execute','--run-id','synthetic_no_training')
        self.assertEqual(result.returncode,2,result.stderr);self.assertEqual(json.loads(result.stdout)['status'],'blocked');self.assertFalse((self.root/'results').exists())


if __name__=='__main__':unittest.main()
