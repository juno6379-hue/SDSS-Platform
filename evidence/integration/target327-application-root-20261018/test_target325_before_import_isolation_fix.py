import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.ml import manifest_resource_profile as profile
from app.data import targeted_bare_plan as plan_module
from app.data import targeted_source_profile as contract
from app.data import targeted_source_io as adapter
import test_targeted_bare_plan as fixtures

legacy_path=ROOT/'tests/fixtures/target325/legacy_targeted_bare_plan.py.fixture'
legacy_raw=legacy_path.read_bytes()
if hashlib.sha256(legacy_raw).hexdigest()!='3fe849e76e64a0d64804c76f99f3ca073b2241fa9aa0c6e1fa74412a6845bfa1':
    # Filled from the immutable baseline by the preparation runner, never fallback.
    raise ValueError('LEGACY_175_FIXTURE_PIN_INVALID')
legacy_spec=importlib.util.spec_from_loader('app.data.legacy_target325',loader=None)
legacy=importlib.util.module_from_spec(legacy_spec)
exec(compile(legacy_raw,str(legacy_path),'exec'),legacy.__dict__)
profile_path=ROOT/'tests/fixtures/target325/legacy_manifest_profile.py.fixture'
profile_raw=profile_path.read_bytes()
if hashlib.sha256(profile_raw).hexdigest()!='e74a18bc20d928a58cced7738cb3b8a3e3b1a4e5ca7a0196bfea7adef52362c3':
    raise ValueError('LEGACY_PROFILE_FIXTURE_PIN_INVALID')
old_profile=importlib.util.module_from_spec(importlib.util.spec_from_loader('app.ml.legacy_profile325',loader=None))
exec(compile(profile_raw,str(profile_path),'exec'),old_profile.__dict__)


class NarrowCapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='target325-caps-');self.root=Path(self.temp.name)
        self.path=self.root/'a.json';self.path.write_bytes(b'{"scenes":[],"x":1}')
    def tearDown(self):self.temp.cleanup()

    def test_default_and_none_are_exact(self):
        for method in (profile.read_metadata,profile.bounded_json_digest):
            self.assertEqual(method(self.path,'source'),method(self.path,'source',maximum_bytes=None))
        self.assertEqual(old_profile.read_metadata(self.path,'source'),profile.read_metadata(self.path,'source'))
        self.assertEqual(old_profile.bounded_json_digest(self.path,'source'),profile.bounded_json_digest(self.path,'source'))

    def test_narrow_exact_boundary_and_effective_tree_cap(self):
        size=self.path.stat().st_size
        from app.ml import split_json_io
        original=split_json_io._tree;caps=[]
        def tree(value,depth,cap):caps.append(cap);return original(value,depth,cap)
        with patch.object(split_json_io,'_tree',side_effect=tree):
            with profile.scope(profile.NAME):profile.read_metadata(self.path,'source',maximum_bytes=size)
        self.assertEqual(caps,[size])
        with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_FILE_LIMIT'):
            profile.read_metadata(self.path,'source',maximum_bytes=size-1)

    def test_percall_invalid_values_before_open(self):
        for value in (True,False,0,-1,1.0,'8',[],{},256<<20):
            for method in (profile.read_metadata,profile.bounded_json_digest):
                with self.subTest(value=value,method=method.__name__), patch.object(Path,'open',side_effect=AssertionError('opened')):
                    with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_NARROW_CAP_INVALID'):
                        method(self.path,'source',maximum_bytes=value)

    def test_ledger8m_overcap_before_open(self):
        self.path.write_bytes(b'{}')
        with self.path.open('r+b') as f:f.truncate((8<<20)+1)
        with patch.object(Path,'open',side_effect=AssertionError('opened')):
            with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_FILE_LIMIT'):
                profile.read_metadata(self.path,'status_report',maximum_bytes=8<<20)

    def test_source128_overcap_before_open(self):
        with self.path.open('r+b') as f:f.truncate((128<<20)+1)
        with patch.object(Path,'open',side_effect=AssertionError('opened')):
            with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_FILE_LIMIT'):
                profile.read_metadata(self.path,'source',maximum_bytes=128<<20)

    def test_declared_role_cap_cannot_be_raised(self):
        with self.assertRaisesRegex(profile.ProfileResourceError,'NARROW_CAP_INVALID'):
            profile.bounded_json_digest(self.path,'pointer',maximum_bytes=65537)

    def test_hash_mismatch(self):
        with profile.scope(profile.NAME),self.assertRaisesRegex(profile.ProfileResourceError,'PIN_MISMATCH'):
            profile.read_metadata(self.path,'source','0'*64,maximum_bytes=32)

    def test_growth_during_actual_read_is_detected_and_charged(self):
        original=profile.charge;fired=False
        def grow(n,kind='read'):
            nonlocal fired
            original(n,kind)
            if not fired:
                fired=True
                with self.path.open('ab') as stream:stream.write(b' ')
        with profile.scope(profile.NAME) as budget,patch.object(profile,'charge',side_effect=grow):
            with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_CHANGED'):
                profile.read_metadata(self.path,'source',maximum_bytes=64)
            self.assertGreater(budget.reads,0)

    def test_replaced_same_content_before_open_fails_identity(self):
        original=profile.require_io_room;fired=False
        def replace(n):
            nonlocal fired
            original(n)
            if not fired:
                fired=True;p=self.root/'replacement.json';p.write_bytes(self.path.read_bytes());p.replace(self.path)
        with profile.scope(profile.NAME),patch.object(profile,'require_io_room',side_effect=replace):
            with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_CHANGED'):
                profile.read_metadata(self.path,'source',maximum_bytes=64)

    def test_row_history_and_depth_resource_errors(self):
        variants=[({'scenes':[{}]*3000,'historical_noneligible_patches':[{}]},'ROW_LIMIT'),
                  ({'scenes':{},'historical_noneligible_patches':[]},'ROW_LIMIT')]
        for value,code in variants:
            self.path.write_text(json.dumps(value),encoding='utf-8')
            with profile.scope(profile.NAME),self.assertRaisesRegex(profile.ProfileResourceError,code):
                profile.read_metadata(self.path,'source')
        self.path.write_text('['*33+'0'+']'*33,encoding='utf-8')
        with profile.scope(profile.NAME),self.assertRaisesRegex(profile.ProfileResourceError,'DEPTH_LIMIT'):
            profile.read_metadata(self.path,'source')

    def test_shared_scope_budget_exhaustion_not_reset(self):
        size=self.path.stat().st_size
        with profile.scope(profile.NAME) as budget:
            budget._maximum=size*2-1
            profile.read_metadata(self.path,'source')
            with profile.scope(profile.NAME) as inner:
                self.assertIs(inner,budget)
                with self.assertRaisesRegex(profile.ProfileResourceError,'IO_LIMIT'):profile.read_metadata(self.path,'source')
            self.assertEqual(budget.reads,size)


class LocalPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.TargetedBarePlanTests();self.fixture.setUp();self.root=self.fixture.root
        self.fixture.write('data/ledger.json',{'batches':{}})
        self.request={'schema_version':3,'plan':contract.upgrade_plan_v1(self.fixture.plan,dict(contract.MARKER)),
                      'ledger_ref':self.fixture.ref('data/ledger.json'),'maximum_batches':2,
                      'manifest_profile':dict(contract.MARKER),'local_support_profile':dict(contract.SUPPORT_MARKER)}
    def tearDown(self):self.fixture.tearDown()

    def test_explicit_local175_path_success_false_and_canonical_bound(self):
        original=copy.deepcopy(self.request)
        with profile.scope(profile.NAME) as budget:
            result=plan_module.prepare_explicit_targeted_bare_jobs(self.root,self.request,self.fixture.base)
            self.assertEqual(result['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',result)
            self.assertIs(profile.active(),budget)
            self.assertGreater(budget.reads,0)
        self.assertIs(result['execution_supported'],False)
        self.assertIs(result['coordinator_connected'],False)
        self.assertEqual(result['request_sha256'],contract.validate_request_v3(self.request).request_sha256)
        self.assertEqual(self.request,original)
        self.assertNotEqual(result['plan_sha256'],legacy.prepare_targeted_bare_jobs(self.root,self.fixture.plan,self.fixture.base)['plan_sha256'])

    def test_markers_fail_before_root_or_any_file_open(self):
        for path in ('outer','inner'):
            value=copy.deepcopy(self.request)
            (value if path=='outer' else value['plan'])['manifest_profile']['name']='unknown'
            with patch.object(adapter,'_root',side_effect=AssertionError('root accessed')):
                with self.assertRaises(contract.TargetSourceContractError):
                    plan_module.prepare_explicit_targeted_bare_jobs(self.root,value,self.fixture.base)

    def test_implementation_descriptor_mismatch_before_root(self):
        with patch.object(profile,'DESCRIPTOR',{**profile.DESCRIPTOR,'manifest_bytes':256<<20}),patch.object(adapter,'_root',side_effect=AssertionError('root accessed')):
            with self.assertRaisesRegex(profile.ProfileResourceError,'IMPLEMENTATION_MISMATCH'):
                plan_module.prepare_explicit_targeted_bare_jobs(self.root,self.request,self.fixture.base)

    def test_legacy_result_and_errors_exact_even_ambient128(self):
        variants=[copy.deepcopy(self.fixture.plan) for _ in range(4)]
        variants[1]['targets'][0]['year']=True;variants[2]['schema_version']=2;variants[3]['policy']['window_size']=1024
        for value in variants:
            before=legacy.prepare_targeted_bare_jobs(self.root,value,self.fixture.base)
            with profile.scope(profile.NAME):after=plan_module.prepare_targeted_bare_jobs(self.root,value,self.fixture.base)
            self.assertEqual(after,before)

    def test_legacy64_unchanged_with_sparse_overcap(self):
        p=self.root/'data/aggregate.json'
        with p.open('r+b') as f:f.truncate((64<<20)+1)
        value=copy.deepcopy(self.fixture.plan);value['current_manifest_ref']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        with profile.scope(profile.NAME):
            before=legacy.prepare_targeted_bare_jobs(self.root,value,self.fixture.base)
            after=plan_module.prepare_targeted_bare_jobs(self.root,value,self.fixture.base)
        self.assertEqual(after,before);self.assertEqual(after['issue'],'FILE_LIMIT')

    def test_cache_hit_has_zero_actual_read_and_pin_mismatch_fails(self):
        with profile.scope(profile.NAME) as budget:
            reader=adapter._Reader(self.root);ref=self.request['ledger_ref'];reader.read(ref,'ledger');n=budget.reads
            reader.read(ref,'ledger');self.assertEqual(budget.reads,n)
            with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_CHANGED'):
                reader.read({**ref,'sha256':'0'*64},'ledger')

    def test_final_same_content_replacement_detected(self):
        with profile.scope(profile.NAME):
            reader=adapter._Reader(self.root);reader.read(self.request['ledger_ref'],'ledger')
            p=self.root/'data/ledger.json';other=self.root/'data/other.json';other.write_bytes(p.read_bytes());other.replace(p)
            with self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_JSON_CHANGED'):reader.recheck()

    def test_resource_error_propagates_past_175_catches(self):
        original=adapter._Reader.read
        def fail(self,ref,role):
            if role=='proposal':raise profile.ProfileResourceError('MANIFEST_JSON_IO_LIMIT')
            return original(self,ref,role)
        with patch.object(adapter._Reader,'read',fail),self.assertRaisesRegex(profile.ProfileResourceError,'IO_LIMIT'):
            plan_module.prepare_explicit_targeted_bare_jobs(self.root,self.request,self.fixture.base)

    def test_no_170_or_worker_or_network_import(self):
        import socket
        with patch.object(socket,'socket',side_effect=AssertionError('HTTP')):
            result=plan_module.prepare_explicit_targeted_bare_jobs(self.root,self.request,self.fixture.base)
        self.assertFalse(result['coordinator_connected'])
        self.assertNotIn('collect_targeted_bare',sys.modules)


if __name__=='__main__':unittest.main(verbosity=2)
