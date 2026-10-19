"""작은 합성 metadata package만 검증·복사. 실제 후보나 QA/영상은 실행하지 않는다."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_candidate_materialization as fixture
from backend.app.ml import candidate_staging as module
from backend.app.ml.candidate_materialization import materialize_split_candidate


class CandidateStagingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.CandidateMaterializationTests();self.f.setUp();self.evidence=self.f.f.workspace/'evidence';self.evidence.mkdir();moved=self.evidence/'saved.json';self.f.saved.rename(moved);self.f.saved=moved;self.f.paths['saved_plan']=moved;self.package=self.evidence/'new-package'
        materialize_split_candidate(self.f.f.root,self.f.paths,self.f.pins,self.package,evidence_root=self.evidence)
        self.receipt=self.package/'receipt.json';self.receipt_pin=self.f.f.sha(self.receipt);self.doc=json.loads(self.receipt.read_text(encoding='utf-8'));self.out=self.f.f.root/'new-stage';self.pins=copy.deepcopy(self.f.pins)
        self.originals={p:p.read_bytes() for p in [*self.f.paths.values(),*self.package.iterdir()]}
    def tearDown(self):self.f.tearDown()
    def stage(self):return module.stage_split_candidate(self.f.f.root,self.package,self.receipt_pin,self.pins,self.out,evidence_root=self.evidence)
    def rewrite(self,doc):self.receipt.write_text(json.dumps(doc),encoding='utf-8');self.receipt_pin=self.f.f.sha(self.receipt)
    def test_identical_bytes_new_data_receipt_without_qa(self):
        result=self.stage();self.assertEqual(result['status'],'METADATA_STAGED_FOR_QA');self.assertEqual(result['next_step'],'NEXT_QA_NOT_PERFORMED');self.assertEqual((self.out/'candidate.json').read_bytes(),(self.package/'candidate.json').read_bytes())
        self.assertEqual(self.f.f.sha(self.out/'candidate.json'),self.doc['outputs']['candidate']['sha256']);self.assertEqual(json.loads((self.out/'staging-receipt.json').read_text(encoding='utf-8')),result)
        for key in ['qa_performed','readiness_assess_called','registered','registry_called','ready_for_training','scientific_accuracy_validated','execution_authorized','settlement_authorized']:self.assertIs(result[key],False)
        self.assertEqual(self.originals,{p:p.read_bytes() for p in self.originals})
    def test_external_three_pins_and_receipt_pin_mandatory(self):
        for role in module.INPUT_ROLES:
            for value in [None,True,'A'*64,'0'*64]:
                self.pins=copy.deepcopy(self.f.pins);self.pins[role]=value
                with self.assertRaises(ValueError):self.stage()
                self.assertFalse(self.out.exists())
        self.pins=copy.deepcopy(self.f.pins)
        for pin in [None,True,'A'*64,'0'*64]:
            with self.assertRaises(ValueError):module.stage_split_candidate(self.f.f.root,self.package,pin,self.pins,self.out,evidence_root=self.evidence)
    def test_exact_receipt_keys_status_and_fifteen_false_flags(self):
        mutations=[lambda d:d.update(extra=True),lambda d:d.pop('scope'),lambda d:d.update(schema_version=True),lambda d:d.update(metadata_integrity_verified=1),lambda d:d.update(proposed_refund_bytes=False),lambda d:d.update(status='READY')]
        mutations += [lambda d,key=key:d.update({key:0}) for key in module.FALSE_FIELDS]
        for change in mutations:
            doc=copy.deepcopy(self.doc);change(doc);self.rewrite(doc)
            with self.assertRaises(ValueError):self.stage()
            self.assertFalse(self.out.exists())
    def test_receipt_sizes_names_refs_and_count_tamper_fail_closed(self):
        changes=[lambda d:d['outputs']['candidate'].update(name='../candidate.json'),lambda d:d['outputs']['plan'].update(bytes=True),lambda d:d['inputs']['source'].update(bytes=d['inputs']['source']['bytes']+1),lambda d:d['inputs']['source'].update(sha256='0'*64),lambda d:d['inputs']['source'].update(path='https://unread.invalid/x'),lambda d:d.update(candidate_row_count=True),lambda d:d.update(source_row_count=99),lambda d:d['fixed_province_splits'].update(banten='test'),lambda d:d.update(projected_after={}),lambda d:d.update(derived_manifest_version='invalid')]
        for change in changes:
            doc=copy.deepcopy(self.doc);change(doc);self.rewrite(doc)
            with self.assertRaises(ValueError):self.stage()
            self.assertFalse(self.out.exists())
    def test_receipt_strict_parser_and_byte_cap_before_stage(self):
        raws=[b'{"a":1,"a":2}',b'{"a":NaN}',b'['*33+b'0'+b']'*33,json.dumps({'quote':'"'}).encode('utf-16'),b' '*65537]
        for raw in raws:
            self.receipt.write_bytes(raw);self.receipt_pin=self.f.f.sha(self.receipt)
            with self.assertRaises(ValueError):self.stage()
            self.assertFalse(self.out.exists())
    def test_receipt_uses_separate_64k_read_context(self):
        original=module.BoundedJSONIO.read;caps=[]
        def observe(io,path,role,*args):
            if Path(path)==self.receipt:caps.append(io.input_caps[role])
            return original(io,path,role,*args)
        with patch.object(module.BoundedJSONIO,'read',observe):self.stage()
        self.assertTrue(caps);self.assertEqual(set(caps),{65536})
    def test_receipt_growth_read_stops_at_64k_plus_one(self):
        real=Path.open;counts=[]
        class Grown:
            def __init__(self,stream):self.stream=stream;self.total=0
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,n):
                counts.append(n);amount=min(n,65537-self.total);self.total+=amount;return b'x'*amount
        def opened(path,*args,**kwargs):
            stream=real(path,*args,**kwargs)
            return Grown(stream) if path==self.receipt else stream
        with patch('pathlib.Path.open',opened),self.assertRaises(ValueError):self.stage()
        self.assertEqual(sum(counts),65537);self.assertTrue(all(0<n<=65536 for n in counts));self.assertFalse(self.out.exists())
    def test_package_logical_retarget_before_stage_rejected(self):
        original=module._confined;calls=0
        def changed(scope,path):
            nonlocal calls
            result=original(scope,path)
            if Path(path)==self.package:
                calls+=1
                if calls>1:return self.evidence/'retargeted'
            return result
        with patch.object(module,'_confined',side_effect=changed),self.assertRaises(ValueError):self.stage()
        self.assertGreater(calls,1);self.assertFalse(self.out.exists())
    def test_old_new_plan_entire_typed_match_required(self):
        path=self.package/'plan.json';plan=json.loads(path.read_text(encoding='utf-8'));plan['training_executed']=True;path.write_text(json.dumps(plan),encoding='utf-8')
        doc=copy.deepcopy(self.doc);doc['outputs']['plan'].update(sha256=self.f.f.sha(path),bytes=path.stat().st_size);self.rewrite(doc)
        with self.assertRaises(ValueError):self.stage()
    def test_full_validator_exact_candidate_called_once_and_no_assess(self):
        original=module.validate_split_repair_plan
        with patch.object(module,'validate_split_repair_plan',wraps=original) as validate,patch('backend.app.ml.readiness.assess',side_effect=AssertionError('QA 금지')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('무제한읽기 금지')):
            result=self.stage();self.assertEqual(validate.call_count,1);self.assertIn('candidate_path',validate.call_args.kwargs);self.assertFalse(result['readiness_assess_called'])
    def test_scope_existing_parent_new_directory_and_windows_aliases(self):
        for out in [self.f.f.workspace/'outside-data',self.f.f.root,self.f.f.root/'missing'/'new',self.f.f.root/'CON.json',self.f.f.root/'x:ads','//server/share/new','C:relative']:
            with self.assertRaises((ValueError,OSError)):module.stage_split_candidate(self.f.f.root,self.package,self.receipt_pin,self.pins,out,evidence_root=self.evidence)
    def test_disjoint_roots_and_validator_qa_claims_enforced(self):
        for data,evidence in [(self.f.f.workspace,self.evidence),(self.f.f.root,self.f.f.workspace)]:
            with self.assertRaises(ValueError):module.stage_split_candidate(data,self.package,self.receipt_pin,self.pins,self.out,evidence_root=evidence)
        original=module.validate_split_repair_plan
        for key in ['raster_files_rehashed','spatial_overlap_rechecked','exact_class_counts_recomputed']:
            def false_claim(*args,key=key,**kwargs):
                result=original(*args,**kwargs);result[key]=True;return result
            with patch.object(module,'validate_split_repair_plan',side_effect=false_claim),self.assertRaises(ValueError):self.stage()
            self.assertFalse(self.out.exists())
    def test_copy_reads_are_bounded_and_early_eof_preserves_partial(self):
        source=self.package/'candidate.json';stamp=module._stamp(source.stat());real=Path.open;calls=[]
        class Wrapped:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,size):calls.append(size);return b''
        def opened(path,*args,**kwargs):
            stream=real(path,*args,**kwargs)
            return Wrapped(stream) if path==source else stream
        output=self.f.f.root/'early-eof.json'
        with patch('pathlib.Path.open',opened),self.assertRaises(ValueError):module._copy_bytes(source,output,stamp,self.doc['outputs']['candidate']['sha256'],module.POLICY['input_caps']['candidate'])
        self.assertTrue(calls and all(0<n<=65536 for n in calls));self.assertEqual(output.read_bytes(),b'')
    def test_copy_failure_preserves_partial_without_completion(self):
        def failed(source,destination,*args):destination.write_bytes(b'{');raise OSError('부분쓰기')
        with patch.object(module,'_copy_bytes',side_effect=failed),self.assertRaises(OSError):self.stage()
        self.assertEqual((self.out/'candidate.json').read_bytes(),b'{');self.assertFalse((self.out/'staging-receipt.json').exists())
    def test_source_mutation_after_copy_prevents_receipt(self):
        original=module._copy_bytes
        def change(*args):
            result=original(*args);source=self.f.paths['source'];source.write_bytes(source.read_bytes()+b' ');return result
        with patch.object(module,'_copy_bytes',side_effect=change),self.assertRaises(ValueError):self.stage()
        self.assertTrue((self.out/'candidate.json').exists());self.assertFalse((self.out/'staging-receipt.json').exists())
    def test_copy_growth_and_truncation_or_wrong_sha_rejected(self):
        source=self.package/'candidate.json';stamp=module._stamp(source.stat());out=self.f.f.root/'raw-copy.json'
        with self.assertRaises(ValueError):module._copy_bytes(source,out,stamp,'0'*64,module.POLICY['input_caps']['candidate'])
        self.assertTrue(out.exists());source.write_bytes(source.read_bytes()+b' ')
        with self.assertRaises(ValueError):module._copy_bytes(source,self.f.f.root/'not-created.json',stamp,self.doc['outputs']['candidate']['sha256'],module.POLICY['input_caps']['candidate'])
        self.assertFalse((self.f.f.root/'not-created.json').exists())
    def test_directory_race_and_output_retarget_refused(self):
        original=module.validate_split_repair_plan
        def race(*args,**kwargs):result=original(*args,**kwargs);self.out.mkdir();(self.out/'owner').write_text('기존');return result
        with patch.object(module,'validate_split_repair_plan',side_effect=race),self.assertRaises(ValueError):self.stage()
        self.assertEqual((self.out/'owner').read_text(),'기존');self.assertFalse((self.out/'staging-receipt.json').exists())
    def test_partial_receipt_preserved_and_invalid(self):
        original=module.BoundedJSONIO.write
        def failed(io,path,*args):
            if Path(path).name=='staging-receipt.json':Path(path).write_bytes(b'{');raise OSError('영수증부분실패')
            return original(io,path,*args)
        with patch.object(module.BoundedJSONIO,'write',failed),self.assertRaises(OSError):self.stage()
        with self.assertRaises(ValueError):json.loads((self.out/'staging-receipt.json').read_bytes())
    def test_cli_cp949_ascii_and_existing_stage_never_overwritten(self):
        # The production CLI fixes evidence=repo/evidence. Keep synthetic DATA in
        # a unique repo/data temp directory so the two scopes remain disjoint.
        from backend.app.ml.split_planning import plan_split_repair
        root=fixture.fixture.ROOT
        with tempfile.TemporaryDirectory(dir=root/'data') as temporary:
            data=Path(temporary);source=data/'first-group-training-esri-v1/annual-window-report.json';source.parent.mkdir();source.write_bytes(self.f.paths['source'].read_bytes())
            readiness=data/'first-group/readiness.json';readiness.parent.mkdir();readiness.write_bytes(self.f.paths['readiness'].read_bytes())
            paths={'source':source,'readiness':readiness,'saved_plan':self.evidence/'cli-saved.json'}
            plan=plan_split_repair(source,self.f.f.sha(source),province_splits=module.FIXED_PROVINCE_SPLITS,readiness_path=readiness,readiness_sha256=self.f.f.sha(readiness),data_root=data)
            paths['saved_plan'].write_text(json.dumps(plan),encoding='utf-8');pins={r:self.f.f.sha(p) for r,p in paths.items()};package=self.evidence/'cli-package'
            materialize_split_candidate(data,paths,pins,package,evidence_root=self.evidence);out=data/'cli-stage'
            command=[sys.executable,str(root/'scripts/stage_split_candidate.py'),'--data-root',str(data),'--package-dir',str(package),'--receipt-sha256',self.f.f.sha(package/'receipt.json'),'--output-dir',str(out)]
            for role in module.INPUT_ROLES:command+=['--'+role.replace('_','-')+'-sha256',pins[role]]
            env={**os.environ,'PYTHONPATH':str(root/'.runtime'),'PYTHONIOENCODING':'cp949'};result=subprocess.run(command,capture_output=True,env=env)
            self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());before={p:p.read_bytes() for p in out.iterdir()}
            again=subprocess.run(command,capture_output=True,env=env);self.assertEqual(again.returncode,1);self.assertTrue(again.stderr.isascii());self.assertEqual(before,{p:p.read_bytes() for p in out.iterdir()})

if __name__=='__main__':unittest.main()
