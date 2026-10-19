"""Tiny synthetic metadata candidates only; no actual datasets/assess/training."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_readiness_connectivity_lineage as fixture
from backend.app.ml import candidate_materialization as module
from backend.app.ml.split_planning import plan_split_repair


class CandidateMaterializationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReadinessConnectivityLineageTests();self.f.setUp()
        for i,row in enumerate(self.f.raw):row.update(year='2021',quality_status='quality_insufficient' if i==2 else 'quality_eligible')
        self.f.save();self.f.fresh['policy'].update(patch_size=256,min_valid_fraction=.8)
        self.f.fresh.update(class_counts_by_split={s:[209]*9 for s in ['train','val','test']},class_patch_counts_by_split={s:[0]*9 for s in ['train','val','test']})
        self.f.write_report();self.plan=plan_split_repair(self.f.manifest,self.f.sha(self.f.manifest),province_splits=module.FIXED_PROVINCE_SPLITS,readiness_path=self.f.report,readiness_sha256=self.f.sha(self.f.report),data_root=self.f.root)
        self.saved=self.f.workspace/'saved.json';self.saved.write_text(json.dumps(self.plan),encoding='utf-8')
        self.paths={'source':self.f.manifest,'readiness':self.f.report,'saved_plan':self.saved};self.pins={r:self.f.sha(p) for r,p in self.paths.items()};self.out=self.f.workspace/'new-package';self.originals={p:p.read_bytes() for p in self.paths.values()}
    def tearDown(self):self.f.tearDown()
    def run_package(self,**kwargs):return module.materialize_split_candidate(self.f.root,self.paths,self.pins,self.out,evidence_root=self.f.workspace,**kwargs)
    def test_roundtrip_receipt_pins_bytes_falseflags_and_source_preservation(self):
        r=self.run_package();self.assertEqual(r['status'],'METADATA_ROUNDTRIP_VERIFIED');self.assertEqual(r['source_row_count'],3);self.assertEqual(r['candidate_row_count'],1);self.assertEqual(r['excluded_source_row_count'],2)
        for role in ['plan','candidate']:
            info=r['outputs'][role];path=self.out/info['name'];self.assertEqual(info['sha256'],self.f.sha(path));self.assertEqual(info['bytes'],path.stat().st_size)
        self.assertEqual(json.loads((self.out/'receipt.json').read_text(encoding='utf-8')),r)
        candidate=json.loads((self.out/'candidate.json').read_text(encoding='utf-8'));self.assertEqual(candidate['scenes'],[self.f.raw[2]]);self.assertIs(candidate['executed'],False);self.assertIs(candidate['learning_ready'],False)
        for key in ['ready_for_training','registry_called','execution_authorized','scientific_accuracy_validated','automatic_resume_allowed','settlement_authorized']:self.assertIs(r[key],False)
        self.assertEqual(self.originals,{p:p.read_bytes() for p in self.paths.values()})
    def test_exact_pin_format_and_wrong_sha_leave_no_output(self):
        for role in module.INPUT_ROLES:
            for value in [None,True,'A'*64,'0'*64]:
                pins=copy.deepcopy(self.pins);pins[role]=value
                with self.assertRaises(ValueError):module.materialize_split_candidate(self.f.root,self.paths,pins,self.out,evidence_root=self.f.workspace)
                self.assertFalse(self.out.exists())
    def test_fixed_policy_tampered_plan_and_typed_false_refused(self):
        for change in [lambda d:d['policy']['province_splits'].update(banten='test'),lambda d:d.update(ready_for_training=True),lambda d:d.update(retained_row_indexes=[True])]:
            plan=copy.deepcopy(self.plan);change(plan);self.saved.write_text(json.dumps(plan),encoding='utf-8');self.pins['saved_plan']=self.f.sha(self.saved)
            with self.assertRaises(ValueError):self.run_package()
            self.assertFalse(self.out.exists())
    def test_scope_input_output_distinct_existing_directory_and_parent_required(self):
        for out in [self.f.root/'candidate-dir',self.f.workspace,self.f.workspace/'missing-parent'/'new',self.f.workspace.parent/'outside-package']:
            with self.assertRaises((ValueError,OSError)):module.materialize_split_candidate(self.f.root,self.paths,self.pins,out,evidence_root=self.f.workspace)
        paths=copy.deepcopy(self.paths);paths['source']=self.saved
        with self.assertRaises(ValueError):module.materialize_split_candidate(self.f.root,paths,self.pins,self.out,evidence_root=self.f.workspace)
    def test_windows_remote_ads_device_rejected_before_files_open(self):
        for out in [self.f.workspace/'CON.json',self.f.workspace/'x:ads',self.f.workspace/'trailing.','//remote/share/new','C:relative']:
            with patch.object(module,'write_plan',side_effect=AssertionError('No writer')),self.assertRaises(ValueError):module.materialize_split_candidate(self.f.root,self.paths,self.pins,out,evidence_root=self.f.workspace)
    def test_output_directory_race_preserves_racer_and_never_writes_receipt(self):
        original=module.validate_split_repair_plan
        def racing(*args,**kwargs):
            result=original(*args,**kwargs);self.out.mkdir();(self.out/'owner.txt').write_text('racer');return result
        with patch.object(module,'validate_split_repair_plan',side_effect=racing),self.assertRaises(ValueError):self.run_package()
        self.assertEqual((self.out/'owner.txt').read_text(),'racer');self.assertFalse((self.out/'receipt.json').exists())
    def test_writer_failure_preserves_partial_no_receipt(self):
        def failing(report,output,**kwargs):Path(output).write_bytes(b'{');raise OSError('Synthetic disk failure')
        with patch.object(module,'write_plan',side_effect=failing),self.assertRaises(OSError):self.run_package()
        self.assertEqual((self.out/'plan.json').read_bytes(),b'{');self.assertFalse((self.out/'receipt.json').exists())
    def test_candidate_tamper_roundtrip_fails_without_receipt(self):
        original=module.write_plan
        def tamper(*args,**kwargs):
            original(*args,**kwargs);path=Path(kwargs['derived_manifest']);doc=json.loads(path.read_text(encoding='utf-8'));doc['learning_ready']=True;path.write_text(json.dumps(doc),encoding='utf-8')
        with patch.object(module,'write_plan',side_effect=tamper),self.assertRaises(ValueError):self.run_package()
        self.assertTrue((self.out/'candidate.json').exists());self.assertFalse((self.out/'receipt.json').exists())
    def test_parent_retarget_before_directory_creation_rejected(self):
        original=module.validate_split_repair_plan;realresolve=Path.resolve
        def retarget(path,*args,**kwargs):
            value=realresolve(path,*args,**kwargs)
            return self.f.workspace/'retargeted' if path==self.out else value
        def changed(*args,**kwargs):
            result=original(*args,**kwargs);self.patcher=patch('pathlib.Path.resolve',retarget);self.patcher.start();return result
        try:
            with patch.object(module,'validate_split_repair_plan',side_effect=changed),self.assertRaises(ValueError):self.run_package()
        finally:
            if hasattr(self,'patcher'):self.patcher.stop()
        self.assertFalse(self.out.exists())
    def test_roundtrip_false_approval_contradiction_no_receipt(self):
        original=module.validate_split_repair_plan;calls=0
        def bad(*args,**kwargs):
            nonlocal calls
            result=original(*args,**kwargs);calls+=1
            if calls==2:result['ready_for_training']=True
            return result
        with patch.object(module,'validate_split_repair_plan',side_effect=bad),self.assertRaises(ValueError):self.run_package()
        self.assertFalse((self.out/'receipt.json').exists())
    def test_partial_receipt_failure_preserved_not_completion(self):
        original=module.BoundedJSONIO.write
        def fail(io,path,*args):
            if Path(path).name=='receipt.json':
                Path(path).write_bytes(b'{');raise OSError('Partial receipt')
            return original(io,path,*args)
        with patch.object(module.BoundedJSONIO,'write',fail),self.assertRaises(OSError):self.run_package()
        self.assertEqual((self.out/'receipt.json').read_bytes(),b'{')
        with self.assertRaises(ValueError):json.loads((self.out/'receipt.json').read_bytes())
    def test_source_change_after_roundtrip_no_receipt_and_partial_preserved(self):
        original=module.validate_split_repair_plan;calls=0
        def change(*args,**kwargs):
            nonlocal calls
            r=original(*args,**kwargs);calls+=1
            if calls==2:self.f.manifest.write_bytes(self.f.manifest.read_bytes()+b' ')
            return r
        with patch.object(module,'validate_split_repair_plan',side_effect=change),self.assertRaises(ValueError):self.run_package()
        self.assertTrue((self.out/'candidate.json').exists());self.assertFalse((self.out/'receipt.json').exists())
    def test_output_cap_and_receipt_cap_reject_without_completion(self):
        small=copy.deepcopy(module.POLICY);small['output_caps']['candidate']=1
        with patch.object(module,'POLICY',small),self.assertRaises(ValueError):self.run_package()
        self.assertTrue(self.out.is_dir());self.assertEqual(list(self.out.iterdir()),[])
        self.out.rmdir()
        with patch.object(module,'RECEIPT_CAP',1),self.assertRaises(ValueError):self.run_package()
        self.assertTrue((self.out/'candidate.json').exists());self.assertFalse((self.out/'receipt.json').exists())
    def test_safe_writer_and_validator_only_no_assess_or_pixels_or_registry(self):
        with patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No assess')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('No unbounded read')):r=self.run_package()
        self.assertFalse(r['raster_readiness_rechecked']);self.assertFalse(r['registry_called'])
    def test_existing_package_never_overwrites_and_cli_cp949(self):
        command=[sys.executable,str(fixture.ROOT/'scripts/materialize_split_candidate.py'),'--data-root',str(self.f.root),'--output-dir',str(self.out)]
        for role in module.INPUT_ROLES:command+=['--'+role.replace('_','-'),str(self.paths[role]),'--'+role.replace('_','-')+'-sha256',self.pins[role]]
        env={**os.environ,'PYTHONPATH':str(fixture.ROOT/'.runtime'),'PYTHONIOENCODING':'cp949'};r=subprocess.run(command,capture_output=True,env=env)
        self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(r.stdout.isascii());before={p:p.read_bytes() for p in self.out.iterdir()}
        again=subprocess.run(command,capture_output=True,env=env);self.assertEqual(again.returncode,1);self.assertTrue(again.stderr.isascii());self.assertEqual(before,{p:p.read_bytes() for p in self.out.iterdir()})

if __name__=='__main__':unittest.main()
