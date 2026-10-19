"""Synthetic bounded split JSON tests; never touches real candidates or raster data."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_ml_split_validation as fixtures
from backend.app.ml import split_planning as planner,split_validation as validator,split_json_io as module


def policy(cap=1024*1024,depth=32):
    return {'input_caps':{r:cap for r in module.INPUT_ROLES},'output_caps':{r:cap for r in module.OUTPUT_ROLES},'max_depth':depth}


class SplitBoundedIOTests(unittest.TestCase):
    def setUp(self):self.f=fixtures.SplitValidationTests();self.f.setUp();self.io=policy()
    def tearDown(self):self.f.tearDown()
    def validate(self,io=None):return validator.validate_split_repair_plan(self.f.saved,self.f.source,self.f.sha,province_splits=self.f.splits,candidate_path=self.f.candidate,candidate_sha256=planner.digest(self.f.candidate),io_policy=io or self.io)
    def test_default_and_optin_plan_validation_same_metadata_and_no_inputs_changed(self):
        before={p:p.read_bytes() for p in self.f.root.iterdir()}
        self.assertEqual(planner.plan_split_repair(self.f.source,self.f.sha,province_splits=self.f.splits),planner.plan_split_repair(self.f.source,self.f.sha,province_splits=self.f.splits,io_policy=self.io))
        self.assertEqual(self.f.validate(candidate_path=self.f.candidate,candidate_sha256=planner.digest(self.f.candidate)),self.validate())
        self.assertEqual(before,{p:p.read_bytes() for p in self.f.root.iterdir()})
    def test_policy_exact_keys_bool_float_negative_excess_and_snapshot_copy(self):
        changes=[lambda p:p.update(extra=1),lambda p:p.update(max_depth=True),lambda p:p.update(max_depth=65),lambda p:p['input_caps'].update(source=True),lambda p:p['input_caps'].update(source=1.0),lambda p:p['input_caps'].update(source=0),lambda p:p['output_caps'].update(candidate=module.MAX_BYTES+1)]
        for change in changes:
            p=policy();change(p)
            with self.assertRaises(ValueError):module.BoundedJSONIO(p)
        p=policy();io=module.BoundedJSONIO(p);p['input_caps']['source']=1
        self.assertEqual(io.input_caps['source'],1024*1024)
        with self.assertRaises(TypeError):io.input_caps['source']=1
        with self.assertRaises(AttributeError):io.max_depth=1
    def test_planner_and_writer_required_pins_cannot_be_none(self):
        for pin in [None,True,0,'A'*64,'x']:
            with patch('pathlib.Path.open',side_effect=AssertionError('No open')),self.assertRaises(ValueError):planner.plan_split_repair(self.f.source,pin,province_splits=self.f.splits,io_policy=self.io)
        for pin in [None,True,0,'A'*64,'x']:
            with self.assertRaises(ValueError):planner.plan_split_repair(self.f.source,self.f.sha,province_splits=self.f.splits,readiness_path=self.f.source,readiness_sha256=pin,io_policy=self.io)
        for role in ['source','readiness']:
          for pin in [None,True,0,'A'*64,'x']:
            report=copy.deepcopy(self.f.plan)
            if role=='source':report['source_manifest']['sha256']=pin
            else:report['readiness_reference']={'path':str(self.f.source),'sha256':pin}
            output=self.f.root/('missing-'+role)/'plan.json'
            with self.assertRaises(ValueError):planner.write_plan(report,output,io_policy=self.io)
            self.assertFalse(output.parent.exists())
    def test_each_input_role_cap_is_used(self):
        paths={'source':self.f.source,'saved_plan':self.f.saved,'candidate':self.f.candidate}
        for role in paths:
            p=policy();p['input_caps'][role]=1
            with self.assertRaises(ValueError):self.validate(p)
        readiness=self.f.root/'readiness.json';readiness.write_text('{}',encoding='utf-8');p=policy();p['input_caps']['readiness']=1
        with self.assertRaises(ValueError):planner.plan_split_repair(self.f.source,self.f.sha,province_splits=self.f.splits,readiness_path=readiness,readiness_sha256=planner.digest(readiness),io_policy=p)
    def test_preflight_rejects_oversize_without_open(self):
        p=policy();p['input_caps']['source']=1
        with patch('pathlib.Path.open',side_effect=AssertionError('No open')),self.assertRaises(ValueError):module.BoundedJSONIO(p).read(self.f.source,'source')
    def test_strict_utf8_dupe_nonfinite_bom_depth_and_surrogate(self):
        target=self.f.root/'invalid.json'
        raws=[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'\xef\xbb\xbf{}',json.dumps({'escaped':'"','deep':[[[]]]}).encode('utf-16'),b'{"a":"\\ud800"}',b'['*33+b'0'+b']'*33]
        for raw in raws:
            target.write_bytes(raw)
            with self.assertRaises((ValueError,UnicodeError)):module.BoundedJSONIO(policy()).read(target,'source')
    def test_depth_container_semantics_same_for_measure_and_read(self):
        io=module.BoundedJSONIO(policy(depth=1));target=self.f.root/'depth.json'
        size=io.measure({'scalar':'escaped " [ {'},'plan');io.write(target,{'scalar':'escaped " [ {'},'plan',size)
        self.assertEqual(io.read(target,'source')[0],{'scalar':'escaped " [ {'})
        for document in [[{}],{'nested':[]}]:
            with self.assertRaises(ValueError):io.measure(document,'plan')
    def test_read_cap_plus_one_no_unbounded_read_and_growth_detected(self):
        target=self.f.root/'small.json';target.write_bytes(b'{}');io=module.BoundedJSONIO(policy(cap=2));calls=[];real=Path.open
        class Wrapped:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,n):calls.append(n);return self.stream.read(n)
        def opened(path,*args,**kwargs):return Wrapped(real(path,*args,**kwargs))
        with patch('pathlib.Path.open',opened):self.assertEqual(io.read(target,'source')[0],{})
        self.assertEqual(calls,[3,1]);self.assertTrue(all(0<n<=module.CHUNK for n in calls))
        calls=[]
        class Grown(Wrapped):
            def read(self,n):calls.append(n);return b'{}x' if len(calls)==1 else b''
        with patch('pathlib.Path.open',lambda path,*args,**kwargs:Grown(real(path,*args,**kwargs))),self.assertRaises(ValueError):module.BoundedJSONIO(policy(cap=2)).read(target,'source')
        self.assertEqual(calls,[3])
    def test_descriptor_state_and_logical_retarget_detected(self):
        io=module.BoundedJSONIO(policy());real=module._stamp;calls=0
        def changed(value):
            nonlocal calls
            out=real(value);calls+=1
            return (out[0]+1,*out[1:]) if calls==2 else out
        with patch.object(module,'_stamp',side_effect=changed),self.assertRaises(ValueError):io.read(self.f.source,'source')
        io=module.BoundedJSONIO(policy());io.read(self.f.source,'source');realresolve=Path.resolve
        def retarget(path,*args,**kwargs):return self.f.saved if path==self.f.source else realresolve(path,*args,**kwargs)
        with patch('pathlib.Path.resolve',retarget),self.assertRaises(ValueError):io.verify()
    def test_all_validator_reopens_and_final_reads_use_same_bounded_context(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('No unbounded read')):
            self.assertTrue(validator.validate_split_repair_plan(self.f.saved,self.f.source,self.f.sha,province_splits=self.f.splits,io_policy=self.io)['plan_integrity_valid'])
            self.assertEqual(planner.digest(self.f.source,io_policy=self.io),self.f.sha)
            self.assertEqual(validator.load_json_document(self.f.saved,io_policy=self.io)['status'],'PLAN_ONLY')
    def test_change_during_recomputation_cannot_escape_final_verification(self):
        original=validator.plan_split_repair
        def changing(*args,**kwargs):
            result=original(*args,**kwargs);self.f.source.write_bytes(self.f.source.read_bytes()+b' ');return result
        with patch.object(validator,'plan_split_repair',side_effect=changing),self.assertRaises(ValueError):self.validate()
    def test_writer_roundtrip_preserves_false_candidate_and_legacy_json_format(self):
        candidate=self.f.root/'bounded-candidate.json';output=self.f.root/'bounded-plan.json'
        planner.write_plan(self.f.plan,output,derived_manifest=candidate,io_policy=self.io)
        self.assertEqual(json.loads(candidate.read_text(encoding='utf-8')),json.loads(self.f.candidate.read_text(encoding='utf-8')))
        self.assertEqual(json.loads(output.read_text(encoding='utf-8')),self.f.plan)
        self.assertEqual(output.read_bytes(),self.f.saved.read_bytes());self.assertEqual(candidate.read_bytes(),self.f.candidate.read_bytes())
        result=validator.validate_split_repair_plan(output,self.f.source,self.f.sha,province_splits=self.f.splits,candidate_path=candidate,candidate_sha256=planner.digest(candidate,io_policy=self.io,role='candidate'),io_policy=self.io)
        self.assertTrue(result['candidate_integrity_valid'] if 'candidate_integrity_valid' in result else result['candidate_validation']['candidate_integrity_valid'])
        doc=json.loads(candidate.read_text(encoding='utf-8'));self.assertIs(doc['executed'],False);self.assertIs(doc['learning_ready'],False)
    def test_both_output_caps_measured_before_any_parent_or_file_creation(self):
        for role in ['plan','candidate']:
            output=self.f.root/f'new-{role}'/'plan.json';candidate=output.parent/'candidate.json';p=policy();p['output_caps'][role]=1
            with self.assertRaises(ValueError):planner.write_plan(self.f.plan,output,derived_manifest=candidate,io_policy=p)
            self.assertFalse(output.parent.exists())
    def test_invalid_output_nan_unicode_cycle_depth_rejected_before_mkdir(self):
        for value in [float('nan'),'\ud800',[[[]]]]:
            report=copy.deepcopy(self.f.plan);report['extra']=value;output=self.f.root/'not-created'/'plan.json'
            p=policy(depth=2 if type(value) is list else 32)
            with self.assertRaises((ValueError,UnicodeError)):planner.write_plan(report,output,io_policy=p)
            self.assertFalse(output.parent.exists())
        report=copy.deepcopy(self.f.plan);report['cycle']=report
        with self.assertRaises(ValueError):planner.write_plan(report,self.f.root/'cycle'/'plan.json',io_policy=self.io)
    def test_existing_outputs_input_alias_and_reserved_paths_protected(self):
        for output in [self.f.saved,self.f.source,self.f.root/'CON.json',self.f.root/'x.json:stream']:
            with self.assertRaises(ValueError):planner.write_plan(self.f.plan,output,io_policy=self.io)
        self.assertEqual(self.f.originals,{p:p.read_bytes() for p in self.f.root.iterdir()})
    def test_writer_readiness_cap_and_context_reuse_preserves_first_binding(self):
        readiness=self.f.root/'readiness.json';readiness.write_text('{"synthetic":true}',encoding='utf-8')
        report=copy.deepcopy(self.f.plan);report['readiness_reference']={'path':str(readiness),'sha256':planner.digest(readiness)}
        p=policy();p['input_caps']['readiness']=1;output=self.f.root/'no-ready-write'/'plan.json'
        with self.assertRaises(ValueError):planner.write_plan(report,output,io_policy=p)
        self.assertFalse(output.parent.exists())
        io=module.BoundedJSONIO(policy());io.read(self.f.source,'source',self.f.sha);self.f.source.write_bytes(self.f.source.read_bytes()+b' ')
        with self.assertRaises(ValueError):planner.digest(self.f.source,io_policy=io)
    def test_output_stream_rechecks_byte_cap_after_measurement(self):
        io=module.BoundedJSONIO(policy(cap=20));target=self.f.root/'stream-limit.json'
        size=io.measure({'a':1},'plan')
        with patch.object(io,'chunks',return_value=iter([b'{',b'x'*21])),self.assertRaises(ValueError):io.write(target,{},'plan',size)
        self.assertEqual(target.read_bytes(),b'{')
    def test_stream_write_failure_retains_partial_new_file_and_existing_inputs(self):
        output=self.f.root/'partial'/'plan.json';candidate=output.parent/'candidate.json';original=module.BoundedJSONIO.write;calls=0
        def failed(io,path,*args):
            nonlocal calls
            calls+=1
            if calls==2:
                with Path(path).open('xb') as stream:stream.write(b'{')
                raise OSError('Synthetic disk failure')
            return original(io,path,*args)
        with patch.object(module.BoundedJSONIO,'write',failed),self.assertRaises(OSError):planner.write_plan(self.f.plan,output,derived_manifest=candidate,io_policy=self.io)
        self.assertEqual(output.read_bytes(),b'{');self.assertTrue(candidate.exists())
        for p,raw in self.f.originals.items():self.assertEqual(p.read_bytes(),raw)
    def test_input_mutation_after_output_raises_and_leaves_no_verified_receipt(self):
        output=self.f.root/'end'/'plan.json';original=module.BoundedJSONIO.write
        def changed(*args):
            original(*args);self.f.source.write_bytes(self.f.source.read_bytes()+b' ')
        with patch.object(module.BoundedJSONIO,'write',changed),self.assertRaises(ValueError):planner.write_plan(self.f.plan,output,io_policy=self.io)
        self.assertTrue(output.exists());self.assertEqual(set(p.name for p in output.parent.iterdir()),{'plan.json'})
    def test_remote_paths_rejected_before_resolve_or_open(self):
        for path in ['https://example.invalid/a.json','//server/share/a.json','C:relative.json']:
            with patch('pathlib.Path.resolve',side_effect=AssertionError('No remote resolve')),self.assertRaises(ValueError):module.BoundedJSONIO(policy()).read(path,'source')

if __name__=='__main__':unittest.main()
