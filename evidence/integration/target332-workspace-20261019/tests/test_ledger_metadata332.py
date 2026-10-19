import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.data import budget as module
from backend.app.data.budget import CollectionLedger
from backend.app.data.ledger_metadata_io import LedgerMetadataIO
from backend.app.data import targeted_atomic_json as writer
from backend.app.ml import manifest_resource_profile as profile


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def load_legacy():
    fixture = Path(__file__).parent/'fixtures/budget332_legacy.py'
    if sha(fixture) != '9ad96b0e9d44cb8018ed15f214dac4e2b2fb89a743f79cd15b31de1f4a828b77':
        raise RuntimeError('LEGACY_FIXTURE_CHANGED')
    spec = importlib.util.spec_from_file_location('legacy332', fixture)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root/'ledger.json'
        self.histories = [self.root/'history1.json', self.root/'history2.json']
        for n, path in enumerate(self.histories): path.write_text(json.dumps({'prior':n}),encoding='utf-8')
        self.refs = [{'path':str(path),'sha256':sha(path)} for path in self.histories]
        self.old_pending = {'old1':{'status':'pending','reserved_bytes':65,'charged_bytes':65,'config_sha256':'1'*64},
                            'old2':{'status':'pending','reserved_bytes':70,'charged_bytes':70,'config_sha256':'2'*64}}
        self.initial = {'version':1,'historical_ledgers':self.refs,'historical_charged_bytes':42,
            'additional_maximum_bytes':1000,'new_charged_bytes':135,'external_research_metadata_body_bytes':0,
            'combined_maximum_bytes':1042,'batches':copy.deepcopy(self.old_pending),'rate_limit_active':False,
            'custom_preserved':{'data':['old']}}
        self.path.write_text(json.dumps(self.initial,ensure_ascii=False,indent=2),encoding='utf-8')
        self.raw = self.path.read_bytes(); self.pin = sha(self.path)
        self.allowed = {'new1':'a'*64,'new2':'b'*64}

    def adapter(self, **options):
        args = dict(root=self.root, ledger_ref={'path':str(self.path),'sha256':self.pin},
            historical_refs=copy.deepcopy(self.refs), allowed_batches=dict(self.allowed),
            manifest_profile=dict(profile.MARKER))
        args.update(options)
        return LedgerMetadataIO(**args)

    def ledger(self, **options):
        io = self.adapter(**options)
        return CollectionLedger(self.path,self.histories,1000,metadata_io=io), io

    def assert_old_pending(self, state):
        for key, value in self.old_pending.items(): self.assertEqual(state['batches'][key], value)

    def test_reserve_settle_and_old_rows_exact_same_budget(self):
        with profile.scope(profile.NAME) as budget:
            profile.charge(9)
            ledger, io = self.ledger(); first = budget.bytes
            self.assertTrue(ledger.reserve('new1',100,'a'*64))
            pending = ledger.snapshot(); self.assertEqual(pending['new_charged_bytes'],235)
            self.assert_old_pending(pending)
            state = ledger.settle('new1',40,report_path='result.json')
            self.assertEqual(state['new_charged_bytes'],175)
            self.assert_old_pending(state)
            self.assertEqual(state['custom_preserved'],self.initial['custom_preserved'])
            self.assertIs(io._budget,budget); self.assertGreater(budget.bytes,first)
            self.assertGreater(budget.writes,0); self.assertEqual(io._pin,sha(self.path))
            self.assertFalse(ledger.reserve('new1',100,'a'*64))
        self.assertFalse(self.path.with_suffix('.lock').exists())

    def test_second_allowed_key_and_exact_charge(self):
        with profile.scope(profile.NAME):
            ledger, _ = self.ledger()
            ledger.reserve('new1',100,'a'*64); ledger.reserve('new2',200,'b'*64)
            state = ledger.settle('new2',0)
            self.assertEqual(state['new_charged_bytes'],235)
            state = ledger.settle('new1',100)
            self.assertEqual(state['new_charged_bytes'],235); self.assert_old_pending(state)

    def test_marker_and_scope_required(self):
        with self.assertRaisesRegex(ValueError,'SCOPE_REQUIRED'): self.adapter()
        with profile.scope(profile.NAME), patch.object(Path,'open',side_effect=AssertionError('open')):
            for marker in (None,True,dict(profile.MARKER,cap=1),{'name':profile.NAME,'sha256':'0'*64}):
                with self.assertRaises(ValueError): self.adapter(manifest_profile=marker)

    def test_allowlist_max_two(self):
        with profile.scope(profile.NAME):
            for allowed in ({},True,{'a':'x'},{'a':'a'*64,'b':'b'*64,'c':'c'*64}):
                with self.assertRaises(ValueError): self.adapter(allowed_batches=allowed)

    def test_constructor_history_order_exact(self):
        with profile.scope(profile.NAME):
            io = self.adapter()
            with self.assertRaisesRegex(ValueError,'CONSTRUCTOR_BINDING'):
                CollectionLedger(self.path,list(reversed(self.histories)),1000,metadata_io=io)

    def test_ledger_history_order_exact(self):
        state = copy.deepcopy(self.initial); state['historical_ledgers'].reverse()
        self.path.write_text(json.dumps(state)); self.pin=sha(self.path)
        with profile.scope(profile.NAME):
            with self.assertRaisesRegex(ValueError,'HISTORY_BINDING'): self.ledger()

    def test_external_reference_path_before_read(self):
        with profile.scope(profile.NAME), patch.object(Path,'open',side_effect=AssertionError('open')):
            with self.assertRaisesRegex(ValueError,'OUTSIDE_ROOT'):
                self.adapter(ledger_ref={'path':str(self.root.parent/'other'),'sha256':self.pin})

    def test_reference_alias_rejected(self):
        with profile.scope(profile.NAME):
            with self.assertRaisesRegex(ValueError,'ALIAS'):
                self.adapter(historical_refs=[self.refs[0],self.refs[0]])

    def test_no_auto_initialization(self):
        self.path.unlink()
        with profile.scope(profile.NAME):
            with self.assertRaises(FileNotFoundError): self.ledger()
        self.assertFalse(self.path.exists()); self.assertFalse(self.path.with_suffix('.lock').exists())

    def test_existing_key_cannot_be_allowed(self):
        with profile.scope(profile.NAME):
            with self.assertRaisesRegex(ValueError,'NOT_NEW'):
                self.ledger(allowed_batches={'old1':'1'*64})

    def test_wrong_current_pin(self):
        with profile.scope(profile.NAME):
            with self.assertRaises(profile.ProfileResourceError):
                self.ledger(ledger_ref={'path':str(self.path),'sha256':'0'*64})
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_wrong_history_pin(self):
        refs=copy.deepcopy(self.refs); refs[0]['sha256']='0'*64
        state=copy.deepcopy(self.initial); state['historical_ledgers']=refs
        self.path.write_text(json.dumps(state)); self.pin=sha(self.path)
        with profile.scope(profile.NAME):
            with self.assertRaises(profile.ProfileResourceError): self.ledger(historical_refs=refs)

    def test_history_replacement_stops_no_write(self):
        with profile.scope(profile.NAME):
            ledger, io = self.ledger()
            self.histories[0].write_bytes(b'{}')
            with self.assertRaises(profile.ProfileResourceError): ledger.reserve('new1',100,'a'*64)
            self.assertTrue(io._stopped)
            with self.assertRaisesRegex(ValueError,'STOPPED'): ledger.snapshot()
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_ledger_eight_mib_before_read_open(self):
        with self.path.open('wb') as stream: stream.truncate(8388609)
        with profile.scope(profile.NAME), patch.object(Path,'open',side_effect=AssertionError('open')):
            with self.assertRaisesRegex(profile.ProfileResourceError,'FILE_LIMIT'): self.ledger()

    def test_history_eight_mib_before_its_open(self):
        with self.histories[0].open('wb') as stream: stream.truncate(8388609)
        original=Path.open
        def guarded(path,*args,**kwargs):
            if path==self.histories[0]: raise AssertionError('oversize opened')
            return original(path,*args,**kwargs)
        with profile.scope(profile.NAME), patch.object(Path,'open',guarded):
            with self.assertRaisesRegex(profile.ProfileResourceError,'FILE_LIMIT'): self.ledger()

    def test_strict_duplicate_json(self):
        self.path.write_bytes(b'{"version":1,"version":1}'); self.pin=sha(self.path)
        with profile.scope(profile.NAME):
            with self.assertRaisesRegex(ValueError,'Duplicate'): self.ledger()

    def test_unknown_key_and_wrong_config_and_bool_amount(self):
        for key,amount,config in (('other',1,'a'*64),('new1',1,'c'*64),('new1',True,'a'*64)):
            with profile.scope(profile.NAME):
                ledger, io = self.ledger()
                with self.assertRaisesRegex(ValueError,'NOT_ALLOWED'): ledger.reserve(key,amount,config)
                self.assertTrue(io._stopped)
            self.assertEqual(self.path.read_bytes(),self.raw)

    def test_old_pending_never_settled(self):
        with profile.scope(profile.NAME):
            ledger, io = self.ledger()
            with self.assertRaisesRegex(ValueError,'NOT_OWNED'): ledger.settle('old1',0)
            self.assertTrue(io._stopped)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_settle_only_this_instance_reserved(self):
        with profile.scope(profile.NAME):
            ledger, _ = self.ledger(); ledger.reserve('new1',100,'a'*64)
            self.pin=sha(self.path)
            other, _ = self.ledger(allowed_batches={'new2':'b'*64})
            with self.assertRaisesRegex(ValueError,'NOT_OWNED'): other.settle('new1',0)
        self.assertEqual(json.loads(self.path.read_bytes())['batches']['new1']['status'],'pending')

    def test_settle_measurement_bounds(self):
        with profile.scope(profile.NAME):
            ledger,_ = self.ledger(); ledger.reserve('new1',100,'a'*64)
            with self.assertRaises(ValueError): ledger.settle('new1',101)
            self.assertEqual(ledger.snapshot()['new_charged_bytes'],235)

    def test_bool_measurement_rejected(self):
        with profile.scope(profile.NAME):
            ledger,_=self.ledger(); ledger.reserve('new1',100,'a'*64)
            with self.assertRaisesRegex(ValueError,'NOT_OWNED'): ledger.settle('new1',False)

    def test_429_circuit_and_old_pending_preserved(self):
        with profile.scope(profile.NAME):
            ledger,_=self.ledger(); ledger.reserve('new1',100,'a'*64)
            state=ledger.settle('new1',100,rate_limit={'http_status':429})
            self.assertTrue(state['rate_limit_active']); self.assert_old_pending(state)
            with self.assertRaisesRegex(RuntimeError,'429'): ledger.reserve('new2',100,'b'*64)

    def test_semantic_old_row_modification_rejected(self):
        with profile.scope(profile.NAME):
            ledger,io=self.ledger(); state=ledger.snapshot()
            state['batches']['new1']={'status':'pending','reserved_bytes':100,'charged_bytes':100,'config_sha256':'a'*64}
            state['new_charged_bytes']+=100; state['batches']['old1']['charged_bytes']=0
            with ledger.locked():
                with self.assertRaisesRegex(ValueError,'TRANSITION'): ledger._save(state)
            self.assertTrue(io._stopped)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_global_constants_modification_rejected(self):
        with profile.scope(profile.NAME):
            ledger,_=self.ledger(); state=ledger.snapshot()
            state['batches']['new1']={'status':'pending','reserved_bytes':100,'charged_bytes':100,'config_sha256':'a'*64}
            state['new_charged_bytes']+=100; state['external_research_metadata_body_bytes']=1
            with ledger.locked():
                with self.assertRaisesRegex(ValueError,'TRANSITION'): ledger._save(state)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_partial_write_stops_original_unchanged(self):
        def partial(stream,block): return stream.write(block[:3])
        with profile.scope(profile.NAME):
            ledger,io=self.ledger()
            with patch.object(writer,'_write_once',partial):
                with self.assertRaisesRegex(ValueError,'INCOMPLETE') as caught: ledger.reserve('new1',100,'a'*64)
            self.assertTrue(io._stopped); self.assertEqual(io._owned,set()); self.assertEqual(io._pin,self.pin)
            self.assertEqual(caught.exception.ledger_metadata_commit_outcome,'NOT_ATTEMPTED')
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_unknown_write_conservative_stops_no_refund(self):
        with profile.scope(profile.NAME) as budget:
            ledger,io=self.ledger()
            with patch.object(writer,'_measure',side_effect=OSError()):
                with self.assertRaisesRegex(ValueError,'MEASUREMENT_UNKNOWN') as caught: ledger.reserve('new1',100,'a'*64)
            self.assertGreater(budget.writes,0); self.assertTrue(io._stopped)
            self.assertFalse(caught.exception.atomic_json_measurement_known)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_postcommit_failure_no_pin_advance_no_retry(self):
        original=profile.bounded_json_digest
        def fail_after_replace(path,*args,**kwargs):
            if path==self.path and sha(self.path)!=self.pin: raise OSError('postcommit')
            return original(path,*args,**kwargs)
        with profile.scope(profile.NAME):
            ledger,io=self.ledger()
            with patch.object(profile,'bounded_json_digest',fail_after_replace):
                with self.assertRaises(OSError) as caught: ledger.reserve('new1',100,'a'*64)
            self.assertEqual(caught.exception.ledger_metadata_commit_outcome,'APPLIED')
            self.assertEqual(io._pin,self.pin); self.assertTrue(io._stopped)
            with self.assertRaisesRegex(ValueError,'STOPPED'): ledger.snapshot()
        state=json.loads(self.path.read_bytes()); self.assertEqual(state['new_charged_bytes'],235)
        self.assert_old_pending(state)

    def test_history_change_during_write_reports_applied(self):
        sync=writer._sync
        def changed(stream):
            sync(stream); self.histories[0].write_bytes(b'{}')
        with profile.scope(profile.NAME):
            ledger,io=self.ledger()
            with patch.object(writer,'_sync',changed):
                with self.assertRaises(profile.ProfileResourceError) as caught: ledger.reserve('new1',100,'a'*64)
            self.assertEqual(caught.exception.ledger_metadata_commit_outcome,'APPLIED')
            self.assertTrue(io._stopped); self.assertEqual(io._pin,self.pin)
        self.assert_old_pending(json.loads(self.path.read_bytes()))

    def test_exhaustion_propagates_no_save(self):
        with profile.scope(profile.NAME) as budget:
            ledger,io=self.ledger(); budget._maximum=budget.bytes
            with self.assertRaises(profile.ProfileResourceError): ledger.reserve('new1',100,'a'*64)
            self.assertTrue(io._stopped)
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.assertFalse(self.path.with_suffix('.lock').exists())

    def test_different_operation_rejected(self):
        with profile.scope(profile.NAME): ledger,io=self.ledger()
        with profile.scope(profile.NAME):
            with self.assertRaisesRegex(ValueError,'SCOPE_OR_OWNER'): ledger.snapshot()
        self.assertTrue(io._stopped)

    def test_lock_competition_no_removal_of_other_lock(self):
        with profile.scope(profile.NAME):
            ledger,_=self.ledger()
            with ledger.locked():
                with self.assertRaises(FileExistsError): ledger.reserve('new1',100,'a'*64)
                self.assertTrue(self.path.with_suffix('.lock').exists())
        self.assertFalse(self.path.with_suffix('.lock').exists())

    def test_legacy_none_exact_bytes_and_errors(self):
        legacy=load_legacy()
        class Fixed:
            @staticmethod
            def now(tz): return datetime(2026,1,1,tzinfo=timezone.utc)
        outputs=[]
        for cls,mod in ((legacy.CollectionLedger,legacy),(CollectionLedger,module)):
            self.path.write_bytes(self.raw)
            with patch.object(mod,'datetime',Fixed):
                ledger=cls(self.path,self.histories,1000)
                self.assertEqual(ledger.snapshot(),self.initial)
                ledger.reserve('legacy',80,'f'*64)
                ledger.settle('legacy',23,report_path='r.json')
                outputs.append(self.path.read_bytes())
                with self.assertRaises(RuntimeError): ledger.settle('legacy',0)
        self.assertEqual(outputs[0],outputs[1])

    def test_legacy_initialization_exact(self):
        legacy=load_legacy()
        self.histories[-1].write_text(json.dumps({'reserved_or_transferred_bytes_including_prior':42}))
        self.path.unlink()
        old=legacy.CollectionLedger(self.path,self.histories,1000,7).snapshot()
        new=CollectionLedger(self.path,self.histories,1000,7,metadata_io=None).snapshot()
        self.assertEqual(old,new)

    def test_legacy_fixture_strict_missing_and_tamper(self):
        with patch.object(Path,'read_bytes',return_value=b'changed'):
            with self.assertRaisesRegex(RuntimeError,'FIXTURE_CHANGED'): load_legacy()


if __name__=='__main__': unittest.main()
