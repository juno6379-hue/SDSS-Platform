import stat
from types import SimpleNamespace
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import collection_budget_status as budget


def fixture():
    batches = {key: dict(status='pending', reserved_bytes=100, charged_bytes=100, config_sha256=sha)
               for key, sha in budget.OLD_PENDING.items()}
    batches['settled-example'] = dict(status='settled', reserved_bytes=500, charged_bytes=250, config_sha256='a'*64, report_path=None)
    return dict(version=1, historical_ledgers=[dict(path='historical.json', sha256='b'*64)],
                historical_charged_bytes=1000, additional_maximum_bytes=4*1024**3,
                new_charged_bytes=460, external_research_metadata_body_bytes=10,
                combined_maximum_bytes=1000+4*1024**3, batches=batches,
                rate_limit_active=False, updated_at='2026-10-18T15:00:00+09:00')


class BudgetStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in (budget.LEDGER, budget.SOURCE):
            (self.root/name).parent.mkdir(parents=True, exist_ok=True)
        (self.root/budget.SOURCE).write_bytes(b'{"scenes":[]}')
        self.write(fixture())

    def tearDown(self):
        self.temp.cleanup()

    def write(self, value):
        (self.root/budget.LEDGER).write_text(json.dumps(value), encoding='utf-8')

    def test_read_only_consistent_totals_pending_not_double_subtracted(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        value = budget.collection_budget_status(self.root)
        self.assertTrue(value['available'])
        self.assertEqual(value['charged_including_pending_bytes'], 460)
        self.assertEqual(value['remaining_bytes'], 4*1024**3-460)
        self.assertEqual((value['old_pending_bytes'], value['old_pending_count']), (200, 2))
        self.assertEqual(value['process_verification'], 'UNKNOWN')
        self.assertFalse(value['execution_approved'])
        self.assertEqual(value['ledger_sha256'], hashlib.sha256((self.root/budget.LEDGER).read_bytes()).hexdigest())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_new_pending_is_separate_from_named_old_pending(self):
        state=fixture();state['batches']['new']=dict(status='pending', reserved_bytes=50, charged_bytes=50, config_sha256='c'*64);state['new_charged_bytes']+=50
        self.write(state);value=budget.collection_budget_status(self.root)
        self.assertEqual((value['pending_bytes'],value['pending_count']),(250,3))
        self.assertEqual(value['old_pending_bytes'],200)

    def test_invalid_schema_numbers_and_arithmetic_fail_closed(self):
        edits=[lambda s:s.update(version=True),lambda s:s.update(new_charged_bytes=True),lambda s:s.update(new_charged_bytes=-1),lambda s:s.update(new_charged_bytes=461),lambda s:s.update(additional_maximum_bytes=5*1024**3),lambda s:s.update(combined_maximum_bytes=1),lambda s:s.update(rate_limit_active=0),lambda s:s.update(updated_at='2026-10-18'),lambda s:s.update(extra=1),lambda s:s['batches']['settled-example'].update(charged_bytes=501),lambda s:s['batches'][next(iter(budget.OLD_PENDING))].update(charged_bytes=99),lambda s:s['batches'][next(iter(budget.OLD_PENDING))].update(config_sha256='d'*64),lambda s:s['batches'].pop(next(iter(budget.OLD_PENDING))),lambda s:s.update(historical_ledgers=[])]
        for edit in edits:
            with self.subTest(edit=edit):
                state=fixture();edit(state);self.write(state);result=budget.collection_budget_status(self.root)
                self.assertFalse(result['available']);self.assertNotIn('remaining_bytes',result)

    def test_duplicate_nonfinite_missing_and_oversize_unknown(self):
        path=self.root/budget.LEDGER
        for raw in [b'{"version":1,"version":1}',b'{"x":NaN}',b'{',b' '* (budget.LIMIT+1)]:
            path.write_bytes(raw);self.assertFalse(budget.collection_budget_status(self.root)['available'])
        path.unlink();self.assertFalse(budget.collection_budget_status(self.root)['available'])

    def test_linked_inputs_and_descriptor_retarget_are_rejected(self):
        original = Path.lstat
        def reparse(path):
            info = original(path)
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400) if path.name=='global-ledger.json' else info
        with patch.object(Path,'lstat',reparse):
            self.assertFalse(budget.collection_budget_status(self.root)['available'])
        original_fstat=budget.os.fstat
        def retarget(fd):
            info=original_fstat(fd)
            return SimpleNamespace(st_dev=info.st_dev,st_ino=info.st_ino+1,st_size=info.st_size,st_mtime_ns=info.st_mtime_ns,st_ctime_ns=info.st_ctime_ns)
        with patch.object(budget.os,'fstat',retarget):
            self.assertFalse(budget.collection_budget_status(self.root)['available'])
        (self.root/budget.LEDGER).unlink();(self.root/budget.LEDGER).mkdir()
        self.assertFalse(budget.collection_budget_status(self.root)['available'])

    def test_data_root_itself_must_be_nonlinked_directory(self):
        original=Path.lstat
        def linked_root(path):
            info=original(path)
            return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400) if path==self.root else info
        with patch.object(Path,'lstat',linked_root):
            self.assertFalse(budget.collection_budget_status(self.root)['available'])
        self.assertFalse(budget.collection_budget_status(self.root/budget.LEDGER)['available'])

    def test_source_cap_and_non_utf8_deep_json_are_unknown(self):
        with patch.object(budget,'SOURCE_LIMIT',2):
            self.assertFalse(budget.collection_budget_status(self.root)['available'])
        for raw in [b'\xff',b'\xef\xbb\xbf{}',b'['*17+b']'*17,b'{"x":"\x00"}']:
            (self.root/budget.LEDGER).write_bytes(raw)
            self.assertFalse(budget.collection_budget_status(self.root)['available'])

    def test_source_or_ledger_changed_between_observations_is_unknown(self):
        original=budget._read
        for target in (budget.SOURCE,budget.LEDGER):
            calls=0
            def changed(root,name,limit,keep):
                nonlocal calls
                value=original(root,name,limit,keep)
                if name==target:
                    calls+=1
                    if calls==2:return value[0],'f'*64,value[2]
                return value
            with patch.object(budget,'_read',side_effect=changed):
                self.assertFalse(budget.collection_budget_status(self.root)['available'])

    def test_identity_change_during_read_is_unknown(self):
        original=budget._identity;calls=0
        def changed(path):
            nonlocal calls
            result=original(path);calls+=1
            return (*result[:3],result[3]+1,result[4]) if calls==2 else result
        with patch.object(budget,'_identity',side_effect=changed):
            self.assertFalse(budget.collection_budget_status(self.root)['available'])


if __name__=='__main__':
    unittest.main()
