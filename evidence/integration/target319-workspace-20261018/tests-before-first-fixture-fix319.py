"""Offline synthetic declarations only; no operating data or pipeline execution."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


s = load('target319_subject', ROOT/'backend/app/data/targeted_source_profile.py')
old = load('target319_legacy232', ROOT/'baseline/backend/app/data/targeted_inventory_profile.py')


def plan():
    ref = lambda name: dict(path=name, sha256='a'*64)
    return dict(schema_version=1, kind='TARGETED_BARE_256_COLLECTION_PLAN',
                proposal_ref=ref('evidence/integration/synthetic/proposal.json'),
                current_manifest_ref=ref('data/synthetic/source.json'),
                boundary_ref=ref('data/synthetic/boundary.json'),
                policy={**s.POLICY, 'maximum_new_batches':1}, targets=[dict(
                    target_id='synthetic', proposal_window_index=0, province='east_java', fixed_split='train', year=2025,
                    source_label_ref=ref('data/synthetic/label.tif'), source_lineage_ref=ref('data/synthetic/report.json'),
                    source_label_window=[0,0,256,256], source_label_grid=dict(crs='EPSG:32749', transform=[10,0,0,0,-10,2560],width=256,height=256),
                    target_bbox_wgs84=[112,-8,113,-7], target_footprint_native=dict(crs='EPSG:32749',corners=[[0,0],[2560,0],[2560,2560],[0,2560]]), declared_bare_pixels=512)])


def request():
    return dict(schema_version=3, plan=s.upgrade_plan_v1(plan(),dict(s.MARKER)),
                ledger_ref=dict(path='data/synthetic/ledger.json',sha256='b'*64), maximum_batches=1,
                local_support_profile=dict(s.SUPPORT_MARKER), manifest_profile=dict(s.MARKER))


class Contracts(unittest.TestCase):
    def reject(self, value, code=None):
        with self.assertRaises(s.TargetSourceContractError) as caught:
            s.validate_request_v3(value)
        if code: self.assertEqual(str(caught.exception), code)
        self.assertRegex(str(caught.exception), r'^TARGET_SOURCE_[A-Z_]+$')

    def test_descriptor_exact_common_profile(self):
        self.assertEqual(s.DIGEST,'db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4')
        self.assertEqual(s.SUPPORT_MARKER,old.MARKER)

    def test_immutable_limits_and_descriptors(self):
        for table in (s.ROLE_LIMITS,s.DESCRIPTOR,s.MARKER,s.SUPPORT_DESCRIPTOR):
            with self.assertRaises(TypeError):table['anything']=1
        self.assertEqual(s.ROLE_LIMITS['ledger'],8<<20)
        self.assertEqual(s.ROLE_LIMITS['lineage'],8<<20)
        self.assertEqual(s.ROLE_LIMITS['source'],128<<20)
        self.assertEqual(s.ROLE_LIMITS_SHA256,hashlib.sha256(s._canonical(dict(s.ROLE_LIMITS)).encode()).hexdigest())

    def test_upgrade_deepcopy_and_original_unmodified(self):
        original=plan(); saved=copy.deepcopy(original); marker=dict(s.MARKER)
        upgraded=s.upgrade_plan_v1(original,marker)
        self.assertEqual(original,saved)
        upgraded['targets'][0]['year']=2020; marker['name']='changed'
        self.assertEqual(original,saved)
        self.assertEqual(upgraded['manifest_profile'],s.MARKER)

    def test_canonical_v3_preserved_and_envelope_is_not_executable_planv1(self):
        value=request(); checked=s.validate_request_v3(value)
        self.assertEqual(checked.request_sha256,hashlib.sha256(s._canonical(value).encode()).hexdigest())
        envelope=s.inventory_envelope_v3(value)
        self.assertEqual(envelope['schema_version'],2)
        self.assertEqual(envelope['plan']['schema_version'],2)
        self.assertNotIn('manifest_profile',envelope)
        self.assertIn('manifest_profile',envelope['plan'])
        self.assertNotEqual(old.request_sha256(envelope),checked.request_sha256)
        fields={'schema_version','plan','ledger_ref','maximum_batches'}
        self.assertEqual(old.inventory_kwargs(envelope,fields,'INVALID'),{'max_files':10000,'max_bytes':3<<30})

    def test_return_copy_cannot_mutate_validated_digest(self):
        value=request(); checked=s.validate_request_v3(value); digest=checked.request_sha256
        value['plan']['targets'][0]['year']=2020
        checked.to_dict()['plan']['targets'][0]['year']=2021
        checked.inventory_envelope()['plan']['targets'][0]['year']=2022
        self.assertEqual(checked.to_dict()['plan']['targets'][0]['year'],2025)
        self.assertEqual(checked.request_sha256,digest)
        with self.assertRaises(FrozenInstanceError):checked.execution_supported=True

    def test_token_not_accepted_as_request(self):
        self.reject(s.validate_request_v3(request()))

    def test_all_authority_false(self):
        checked=s.validate_request_v3(request())
        for key in ('execution_supported','source_bytes_verified','source_profile_connected','training_ready'):
            self.assertIs(getattr(checked,key),False)

    def test_pure_no_open_socket_or_environment_profile_import(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')), patch.object(Path,'open',side_effect=AssertionError('I/O')), patch.object(socket,'socket',side_effect=AssertionError('HTTP')):
            checked=s.validate_request_v3(request())
            self.assertIs(checked.execution_supported,False)

    def test_outer_versions(self):
        for version in (True,False,1,2,4,3.0,'3',None):
            with self.subTest(version=version):
                value=request();value['schema_version']=version;self.reject(value)

    def test_plan_versions(self):
        for version in (True,False,1,3,2.0,'2',None):
            value=request();value['plan']['schema_version']=version;self.reject(value)

    def test_unknown_or_missing_outer_keys(self):
        for key in s.OUTER_KEYS:
            value=request();del value[key];self.reject(value)
        for key in ('execute','manifest_bytes','maximum_json_io_bytes','max_depth','max_nodes','caps'):
            value=request();value[key]=128;self.reject(value)

    def test_profile_markers_both_exact_and_required(self):
        for path in ('outer','plan','support'):
            for replacement in (None,True,{},dict(name=s.NAME,sha256='0'*64),dict(s.MARKER,manifest_bytes=1),dict(name=True,sha256=s.DIGEST)):
                value=request();target=value['plan'] if path=='plan' else value
                target['local_support_profile' if path=='support' else 'manifest_profile']=replacement
                self.reject(value)

    def test_nested_key_and_policy_cap_manipulation(self):
        for key in ('manifest_bytes','manifest_profile_override','execution_supported'):
            value=request();value['plan'][key]=1;self.reject(value)
        for key in s.POLICY:
            value=request();value['plan']['policy'][key]=True;self.reject(value)
        value=request();value['plan']['policy']['max_total_bytes']=1;self.reject(value)

    def test_batch_count_exact(self):
        for n in (True,False,0,3,1.0,'1',2):
            value=request();value['maximum_batches']=n;self.reject(value)

    def test_two_targets_explicit_valid(self):
        value=request();value['plan']['policy']['maximum_new_batches']=2;value['maximum_batches']=2
        other=copy.deepcopy(value['plan']['targets'][0]);other['target_id']='second';value['plan']['targets'].append(other)
        self.assertEqual(len(s.validate_request_v3(value).to_dict()['plan']['targets']),2)

    def test_duplicate_targets_and_empty(self):
        value=request();value['plan']['targets']=[];self.reject(value)
        value=request();value['maximum_batches']=2;value['plan']['policy']['maximum_new_batches']=2
        value['plan']['targets']*=2;self.reject(value)

    def test_reference_sha_and_path_aliases(self):
        for path in ('../data/x','data/../x','data//x','data/./x','data\\x','https://example/x','C:/data/x','/data/x','data/x\x00'):
            value=request();value['ledger_ref']['path']=path;self.reject(value)
        for sha in ('a'*63,'A'*64,True,'g'*64):
            value=request();value['ledger_ref']['sha256']=sha;self.reject(value)

    def test_bad_target_types_and_fixedsplit(self):
        for field, n in [('year',True),('year',2026),('proposal_window_index',False),('fixed_split','test'),('declared_bare_pixels',True),('declared_bare_pixels',255),('declared_bare_pixels',65537)]:
            value=request();value['plan']['targets'][0][field]=n;self.reject(value)

    def test_nonfinite_huge_numbers_and_utf8_surrogates(self):
        for n in (float('nan'),float('inf'),-float('inf'),10**10000,'\ud800'):
            value=request();value['plan']['targets'][0]['target_bbox_wgs84'][0]=n;self.reject(value)
        value=request();value['\ud800']=1;self.reject(value,'TARGET_SOURCE_UTF8_INVALID')

    def test_subclasses_and_bytes_fail_without_invoking_methods(self):
        class Evil(dict):
            def items(self):raise AssertionError('prototype executed')
        class EvilList(list):
            def __iter__(self):raise AssertionError('prototype executed')
        self.reject(Evil(request()))
        value=request();value['plan']['targets']=EvilList(value['plan']['targets']);self.reject(value)
        self.reject(b'not UTF8 JSON')

    def test_cycles_depth_nodes_and_canonical_utf8_size(self):
        value=request();value['cycle']=value;self.reject(value)
        nested=0
        for _ in range(34):nested=[nested]
        value=request();value['deep']=nested;self.reject(value)
        with self.assertRaises(s.TargetSourceContractError):s._copy([[0]*256 for _ in range(200)])
        with self.assertRaises(s.TargetSourceContractError):s._copy(['é'*4096]*256)

    def test_caller_mutation_after_detachment_never_revalidated_original(self):
        value=request();original=s._canonical;mutated=False
        def mutate(detached):
            nonlocal mutated
            if not mutated:
                mutated=True;value['maximum_batches']=True;value['plan']['targets'][0]['year']=False
            return original(detached)
        with patch.object(s,'_canonical',side_effect=mutate):checked=s.validate_request_v3(value)
        self.assertEqual(checked.to_dict()['maximum_batches'],1)
        self.assertEqual(checked.to_dict()['plan']['targets'][0]['year'],2025)

    def test_detected_iteration_mutation_is_fixed_code(self):
        value=request();fired=False
        def trace(frame,event,arg):
            nonlocal fired
            if not fired and event=='line' and frame.f_code.co_name=='clone' and frame.f_locals.get('item') is value and 'key' in frame.f_locals:
                fired=True;value['added_during_iteration']=1
            return trace
        prior=sys.gettrace()
        try:
            sys.settrace(trace)
            self.reject(value,'TARGET_SOURCE_INPUT_CHANGED')
        finally:sys.settrace(prior)
        self.assertTrue(fired)

    def test_key_order_invariance_and_nonascii_canonical_utf8(self):
        value=request();value['ledger_ref']['path']='data/합성/ledger.json'
        reverse={k:value[k] for k in reversed(value)}
        first=s.validate_request_v3(value);second=s.validate_request_v3(reverse)
        self.assertEqual(first.request_sha256,second.request_sha256)
        self.assertIn('합성',first.canonical_json)

    def test_legacy232_v1_v2_exact_and_new_version_rejected(self):
        fields={'schema_version','plan','ledger_ref','maximum_batches'}
        legacy={k:request()[k] for k in fields};legacy['schema_version']=1;legacy['plan']=plan()
        before=copy.deepcopy(legacy);self.assertEqual(old.inventory_kwargs(legacy,fields,'OLD'),{})
        s.validate_request_v3(request());self.assertEqual(legacy,before)
        legacy['schema_version']=2;legacy['local_support_profile']=dict(old.MARKER)
        self.assertEqual(old.inventory_kwargs(legacy,fields,'OLD'),{'max_files':10000,'max_bytes':3<<30})
        with self.assertRaisesRegex(ValueError,'^OLD$'):old.inventory_kwargs(request(),fields,'OLD')

    def test_bad_upgrades_cannot_smuggle_marker_into_legacy(self):
        value=plan();value['manifest_profile']=dict(s.MARKER)
        with self.assertRaises(s.TargetSourceContractError):s.upgrade_plan_v1(value,dict(s.MARKER))
        value=plan();value['schema_version']=True
        with self.assertRaises(s.TargetSourceContractError):s.upgrade_plan_v1(value,dict(s.MARKER))


if __name__=='__main__':unittest.main(verbosity=2)
