"""4개 작은 합성 JSON+모의 run. 실제 후보 QA/영상/학습은 실행하지 않는다."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from backend.app.ml import candidate_readiness_qa as module
from backend.app.ml.readiness_connectivity_adapter import failure_capture
from scripts import run_experiment

ROOT=Path(__file__).resolve().parents[1]


class CandidateReadinessQATests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.data=Path(self.temp.name);self.paths={r:self.data/(r+'.json') for r in module.ROLES};self.out=self.data/'new-qa'
        self.policy={**module.default_policy(),'label_source':'esri_io'};self.signature={'band_names':self.policy['band_names'],'band_indices':list(range(1,7)),'patch_size':256,'normalization_mode':'per_scene_product_metadata','label_source':'esri_io','class_names':['c'+str(i) for i in range(9)]}
        self.old={'schema_version':1,'status':'blocked','ready_for_training':False,'scientific_accuracy_validated':False,'policy':copy.deepcopy(self.policy),'input_manifests':[{'path':'source.json','sha256':'1'*64}],'input_signature':copy.deepcopy(self.signature)}
        self.candidate={'schema_version':1,'version':'split-repair-v1-'+'a'*16,'status':'PLANNED_DERIVED_CANDIDATE','executed':False,'learning_ready':False,'synthetic':True,'lineage':{'source_manifest':{'path':str(self.data/'source.json'),'sha256':'1'*64},'selection_policy':{'province_splits':dict(module.FIXED_PROVINCE_SPLITS),'keep_split_priority':['test','val','train']},'source_row_indexes':[0]},'scenes':[{'province':'banten','year':'2021','quality_status':'quality_eligible'}]}
        self.write('candidate',self.candidate);self.write('policy',self.policy);self.write('old_readiness',self.old)
        self.stage={'schema_version':1,'kind':'DATA_CANDIDATE_STAGING_RECEIPT','status':'METADATA_STAGED_FOR_QA','next_step':'NEXT_QA_NOT_PERFORMED','qa_status':'NOT_PERFORMED','package_reference':{'path':str(self.data.parent/'package'),'receipt_sha256':'2'*64},'input_pins':{'source':'1'*64,'readiness':self.sha(self.paths['old_readiness']),'saved_plan':'3'*64},'verified_package_outputs':{'plan':{'name':'plan.json','sha256':'4'*64,'bytes':100},'candidate':{'name':'candidate.json','sha256':self.sha(self.paths['candidate']),'bytes':self.paths['candidate'].stat().st_size}},'staged_candidate':{'path':'candidate.json','sha256':self.sha(self.paths['candidate']),'bytes':self.paths['candidate'].stat().st_size},'derived_manifest_version':self.candidate['version'],'source_row_count':2,'candidate_row_count':1,'projected_after':{'eligible_patches_by_split':{'train':0,'val':1,'test':0},'eligible_total':1,'eligible_by_province_year':{'banten/2021':1}},'metadata_integrity_verified':True,'original_candidate_bytes_preserved':True,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN','completion_contract':'합성 staging receipt',**{k:False for k in module.STAGE_FALSE}}
        self.write('staging_receipt',self.stage);self.refresh()
    def tearDown(self):self.temp.cleanup()
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def write(self,r,value):self.paths[r].write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    def refresh(self):self.pins={r:self.sha(p) for r,p in self.paths.items()}
    def report(self,ready=False):
        refs=[{'path':'candidate.json','sha256':self.pins['candidate']}];capture=failure_capture();capture.update(capture_status='CAPTURED_COMPONENTS_MATCH',scene_count=1,supplied_eligible_patch_sum=1,manifest_input_references=copy.deepcopy(refs))
        return {'schema_version':1,'status':'ready_for_weak_label_experiment' if ready else 'blocked','ready_for_training':ready,'scientific_accuracy_validated':False,'policy':copy.deepcopy(self.policy),'blockers':[] if ready else [{'code':'CLASS_COVERAGE','detail':'합성 클래스 부족'}],'patch_counts_by_split':{'train':0,'val':1,'test':0},'input_manifests':refs,'verified_files':[{'path':'candidate.json','sha256':self.pins['candidate'],'kind':'collection_manifest'}],'input_signature':copy.deepcopy(self.signature),'connectivity_diagnostics':capture,'prepared_payload':{} if ready else None}
    def fake_run(self,*args,**kwargs):
        self.assertEqual(kwargs,{'execute':False,'resume':False,'connectivity_diagnostics':True});self.assertEqual(args[0],[self.paths['candidate'].resolve()]);self.assertEqual(args[1],self.data)
        result=self.report();Path(args[2]).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');return result
    def assess(self):return module.assess_staged_candidate(self.data,self.paths,self.pins,self.out)
    def test_blocked_qa_is_completed_false_authorization_and_input_preservation(self):
        before={p:p.read_bytes() for p in self.paths.values()}
        with patch.object(module,'run',side_effect=self.fake_run) as run:r=self.assess()
        self.assertEqual(run.call_count,1);self.assertEqual(r['status'],'QA_COMPLETED');self.assertEqual(r['observed_readiness_status'],'blocked');self.assertFalse(r['observed_gate_ready_for_training']);self.assertFalse(r['execution_authorized']);self.assertFalse(r['ready_for_training']);self.assertEqual(before,{p:p.read_bytes() for p in before});self.assertEqual(json.loads((self.out/'qa-receipt.json').read_text(encoding='utf-8')),r)
    def test_actual_run_with_mock_assess_ready_true_never_prepares_trains_or_infers(self):
        result=self.report(True)
        with patch.object(run_experiment,'assess',return_value=result) as assess,patch.object(run_experiment,'prepare_dataset',side_effect=AssertionError('No prepare')) as prepare,patch.object(run_experiment,'train_model',side_effect=AssertionError('No train')) as train,patch.object(run_experiment,'infer_raster',side_effect=AssertionError('No infer')) as infer:
            r=self.assess()
        self.assertTrue(r['observed_gate_ready_for_training']);self.assertFalse(r['training_executed']);self.assertFalse(r['ready_for_training']);self.assertFalse(prepare.called or train.called or infer.called);self.assertTrue(assess.call_args.kwargs['connectivity_diagnostics'])
    def test_four_external_pin_formats_and_mismatch_before_run(self):
        for role in module.ROLES:
            original=self.pins[role]
            for value in [None,True,'A'*64,'0'*64]:
                self.pins[role]=value
                with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
                self.assertFalse(self.out.exists())
            self.pins[role]=original
    def test_stage_schema_flags_lineage_count_and_old_source_binding(self):
        original=copy.deepcopy(self.stage)
        changes=[lambda s:s.update(extra=True),lambda s:s.update(qa_performed=0),lambda s:s['input_pins'].update(readiness='0'*64),lambda s:s['staged_candidate'].update(bytes=True),lambda s:s.update(candidate_row_count=True),lambda s:s['staged_candidate'].update(path='../escape.json')]
        for change in changes:
            value=copy.deepcopy(original);change(value);self.write('staging_receipt',value);self.refresh()
            with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
        self.write('staging_receipt',original);self.old['input_manifests'][0]['sha256']='5'*64;self.write('old_readiness',self.old);self.stage['input_pins']['readiness']=self.sha(self.paths['old_readiness']);self.write('staging_receipt',self.stage);self.refresh()
        with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
    def test_policy_whole_typed_same_and_all_floors_no_coercion(self):
        original=copy.deepcopy(self.policy)
        changes=[('min_patches',999),('min_patches',True),('min_valid_fraction',.79),('min_patches_per_train_province',49),('min_unique_train_locations',31),('max_patches',3001),('min_province_inside_fraction',.94),('patch_size',256.0),('seed',True),('required_classes',[0,1]),('required_years',[2021]),('scope_statement','변경'),('extra_test_mode',True)]
        for key,value in changes:
            policy=copy.deepcopy(original);policy[key]=value;old=copy.deepcopy(self.old);old['policy']=copy.deepcopy(policy);self.write('policy',policy);self.write('old_readiness',old);stage=copy.deepcopy(self.stage);stage['input_pins']['readiness']=self.sha(self.paths['old_readiness']);self.write('staging_receipt',stage);self.refresh()
            with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
            self.assertFalse(self.out.exists())
    def test_explicit_label_source_extra_key_supported_but_mismatch_rejected(self):
        with patch.object(module,'run',side_effect=self.fake_run):self.assess()
        self.assertEqual(json.loads(self.paths['policy'].read_text())['label_source'],'esri_io')
        self.out=self.data/'wrong-label';self.policy['label_source']='worldcover';self.old['policy']=copy.deepcopy(self.policy);self.write('policy',self.policy);self.write('old_readiness',self.old);self.stage['input_pins']['readiness']=self.sha(self.paths['old_readiness']);self.write('staging_receipt',self.stage);self.refresh()
        with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
    def test_policy_object_detached_from_runner_mutation(self):
        original=copy.deepcopy(self.policy)
        def detached(*args,**kwargs):
            result=self.fake_run(*args,**kwargs);args[3]['province_splits']['banten']='train';return result
        with patch.object(module,'run',side_effect=detached):self.assess()
        self.assertEqual(self.policy,original);self.assertEqual(json.loads(self.paths['policy'].read_text()),original)
    def test_report_status_signature_source_counts_capture_or_approval_tamper(self):
        changes=[lambda r:r.pop('status'),lambda r:r.update(ready_for_training=True),lambda r:r.update(scientific_accuracy_validated=True),lambda r:r.pop('input_signature'),lambda r:r['input_signature'].update(label_source='other'),lambda r:r['input_manifests'][0].update(sha256='0'*64),lambda r:r['patch_counts_by_split'].update(val=True),lambda r:r['connectivity_diagnostics'].update(execution_authorized=True),lambda r:r['connectivity_diagnostics'].update(manifest_input_references=[])]
        for i,change in enumerate(changes):
            self.out=self.data/('invalid-report-'+str(i))
            def changed(*args,change=change,**kwargs):
                result=self.report();change(result);Path(args[2]).write_text(json.dumps(result),encoding='utf-8');return result
            with patch.object(module,'run',side_effect=changed),self.assertRaises(ValueError):self.assess()
            self.assertTrue((self.out/'readiness.json').exists());self.assertFalse((self.out/'qa-receipt.json').exists())
    def test_report_return_file_mismatch_and_report_limit_prevent_completion(self):
        def changed(*args,**kwargs):result=self.fake_run(*args,**kwargs);Path(args[2]).write_text('{}',encoding='utf-8');return result
        with patch.object(module,'run',side_effect=changed),self.assertRaises(ValueError):self.assess()
        self.assertFalse((self.out/'qa-receipt.json').exists())
    def test_report_read_cap_and_qa_receipt_cap_are_completion_limits(self):
        original=module._context
        def smaller(role,cap):return original(role,1 if role=='saved_plan' and cap==16*1024**2 else cap)
        with patch.object(module,'_context',side_effect=smaller),patch.object(module,'run',side_effect=self.fake_run),self.assertRaises(ValueError):self.assess()
        self.assertTrue((self.out/'readiness.json').exists());self.assertFalse((self.out/'qa-receipt.json').exists())
        self.out=self.data/'large-receipt'
        def large(*args,**kwargs):
            result=self.report();result['blockers'][0]['detail']='x'*70000;Path(args[2]).write_text(json.dumps(result),encoding='utf-8');return result
        with patch.object(module,'run',side_effect=large),self.assertRaises(ValueError):self.assess()
        self.assertFalse((self.out/'qa-receipt.json').exists())
    def test_partial_final_receipt_is_preserved_and_invalid(self):
        original=module.BoundedJSONIO.write
        def fail(io,path,*args):
            if Path(path).name=='qa-receipt.json':Path(path).write_bytes(b'{');raise OSError('부분영수증')
            return original(io,path,*args)
        with patch.object(module.BoundedJSONIO,'write',fail),patch.object(module,'run',side_effect=self.fake_run),self.assertRaises(OSError):self.assess()
        self.assertEqual((self.out/'qa-receipt.json').read_bytes(),b'{')
        with self.assertRaises(ValueError):json.loads((self.out/'qa-receipt.json').read_bytes())
    def test_cli_cp949_subprocess_uses_mock_run_only(self):
        runner=self.data/'mock_cli.py'
        code="import sys,json\nfrom pathlib import Path\nsys.path.insert(0,"+repr(str(ROOT))+ ")\nfrom backend.app.ml import candidate_readiness_qa as guard\ndef fake(manifests,root,path,policy,**kwargs):\n assert kwargs=={'execute':False,'resume':False,'connectivity_diagnostics':True}\n result="+repr(self.report())+"\n Path(path).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')\n return result\nguard.run=fake\nfrom scripts.assess_staged_candidate import main\nraise SystemExit(main())\n"
        runner.write_text(code,encoding='utf-8');argv=[sys.executable,str(runner),'--data-root',str(self.data),'--output-dir',str(self.out)]
        for role in module.ROLES:argv+=['--'+role.replace('_','-'),str(self.paths[role]),'--'+role.replace('_','-')+'-sha256',self.pins[role]]
        env={**os.environ,'PYTHONPATH':str(ROOT/'.runtime'),'PYTHONIOENCODING':'cp949'};result=subprocess.run(argv,capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());before=(self.out/'readiness.json').read_bytes()
        again=subprocess.run(argv,capture_output=True,env=env);self.assertEqual(again.returncode,1);self.assertTrue(again.stderr.isascii());self.assertEqual((self.out/'readiness.json').read_bytes(),before)
    def test_source_input_change_after_qa_no_receipt_partial_report_preserved(self):
        def changed(*args,**kwargs):
            result=self.fake_run(*args,**kwargs);path=self.paths['candidate'];path.write_bytes(path.read_bytes()+b' ');return result
        with patch.object(module,'run',side_effect=changed),self.assertRaises(ValueError):self.assess()
        self.assertTrue((self.out/'readiness.json').exists());self.assertFalse((self.out/'qa-receipt.json').exists())
    def test_run_exception_preserves_partial_report_no_completion(self):
        def failed(*args,**kwargs):Path(args[2]).write_bytes(b'{');raise OSError('합성 실패')
        with patch.object(module,'run',side_effect=failed),self.assertRaises(OSError):self.assess()
        self.assertEqual((self.out/'readiness.json').read_bytes(),b'{');self.assertFalse((self.out/'qa-receipt.json').exists())
    def test_input_role_caps_strict_json_and_early_output_guard(self):
        for role in module.ROLES:
            with patch.dict(module.CAPS,{role:1}),patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
        self.paths['policy'].write_bytes(b'{"a":1,"a":2}');self.refresh()
        with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises(ValueError):self.assess()
    def test_scopes_aliases_existing_and_missing_parent_refused(self):
        for out in [self.data,self.data.parent/'outside',self.data/'missing'/'new',self.data/'CON.json',self.data/'x:ads','//server/share/new','C:relative']:
            with patch.object(module,'run',side_effect=AssertionError('No run')),self.assertRaises((ValueError,OSError)):module.assess_staged_candidate(self.data,self.paths,self.pins,out)
        self.paths['policy']=self.paths['old_readiness']
        with self.assertRaises(ValueError):self.assess()
    def test_directory_race_and_partial_receipt_preserved(self):
        original=module.BoundedJSONIO.verify;calls=0
        def race(io):
            nonlocal calls
            result=original(io);calls+=1
            if calls==4:self.out.mkdir();(self.out/'owner').write_text('기존')
            return result
        with patch.object(module.BoundedJSONIO,'verify',race),self.assertRaises(ValueError):self.assess()
        self.assertEqual((self.out/'owner').read_text(),'기존');self.assertFalse((self.out/'qa-receipt.json').exists())
    def test_minimal_failed_capture_can_complete_qa_but_not_claim_capture_success(self):
        def failed_capture(*args,**kwargs):
            result=self.report();result['connectivity_diagnostics']=failure_capture('FAILED_DIAGNOSTIC');Path(args[2]).write_text(json.dumps(result),encoding='utf-8');return result
        with patch.object(module,'run',side_effect=failed_capture):r=self.assess()
        self.assertEqual(r['connectivity_capture_status'],'FAILED_DIAGNOSTIC');self.assertFalse(r['execution_authorized'])
    def test_cli_has_no_execute_resume_and_ascii_summary(self):
        from scripts import assess_staged_candidate as cli
        argv=['assess_staged_candidate.py','--data-root',str(self.data),'--output-dir',str(self.out)]
        for role in module.ROLES:argv+=['--'+role.replace('_','-'),str(self.paths[role]),'--'+role.replace('_','-')+'-sha256',self.pins[role]]
        with patch.object(sys,'argv',argv),patch.object(module,'run',side_effect=self.fake_run),patch.object(sys,'stdout',io.StringIO()) as output:self.assertEqual(cli.main(),0);self.assertTrue(output.getvalue().isascii())
        for flag in ['--execute','--resume']:
            with patch.object(sys,'argv',argv+[flag]),patch.object(sys,'stderr',io.StringIO()),self.assertRaises(SystemExit):cli.main()

if __name__=='__main__':unittest.main()
