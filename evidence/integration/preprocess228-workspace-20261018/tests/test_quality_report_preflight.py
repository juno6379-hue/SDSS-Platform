"""Read-only pre-registration checks on newly created temporary fixtures only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app.data import quality_report_preflight as api
from app.data import quality_report_storage as writer
from app.dataset_registry import canonical_manifest
from app.store import Store
import test_quality_report_storage as fixtures


class QualityReportPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.QualityReportStorageTests.setUpClass()
        cls.addClassCleanup(fixtures.QualityReportStorageTests.doClassCleanups)

    def setUp(self):
        self.fixture = fixtures.QualityReportStorageTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root; self.f = self.fixture.fixture; self.sidecar = self.fixture.sidecar
        self.assertEqual(self.fixture.write()['status'],'FILES_WRITTEN_UNREGISTERED')

    def inspect(self):
        return api.inspect_stored_quality_report(self.root,self.f.image,self.f.mask,self.f.identity,self.f.metadata,self.sidecar)

    def assert_closed(self,result,code=None):
        self.assertEqual(result['status'],'BLOCKED'); self.assertEqual(len(result),23)
        if code: self.assertEqual(result['issue']['code'],code)
        self.assertFalse(result['stored_report_files_verified']); self.assertFalse(result['manifest_schema_verified'])
        for key in ('report_output_uri','manifest_output_uri','report_sha256','manifest_sha256','fixed_refs','report_manifest_draft'):
            self.assertIsNone(result[key])
        self.assertTrue(all(row == {'role':role,'verified':False,'bytes':None}
            for row,role in zip(result['files'],('report','manifest'))))
        self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))

    def test_actual_two_files_exact23_no_writer_store_input_open_or_mutation(self):
        before = {p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        inputs = copy.deepcopy((self.f.image,self.f.mask,self.f.identity,self.f.metadata))
        real_open = api.os.open; opened = []
        def readonly(path,flags,*args,**kwargs):
            opened.append(Path(path).name)
            self.assertEqual(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_EXCL),0)
            return real_open(path,flags,*args,**kwargs)
        with (patch.object(api.os,'open',side_effect=readonly),patch.object(writer,'write_quality_report_files',side_effect=AssertionError('no writer')),
             patch.object(Store,'put',side_effect=AssertionError('no DB')),patch.object(api,'complete_quality_report',wraps=api.complete_quality_report) as complete):
            result = self.inspect()
        complete.assert_called_once(); self.assertEqual(opened,['quality.json',self.sidecar])
        self.assertEqual(len(result),23); self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertTrue(result['stored_report_files_verified']); self.assertTrue(result['manifest_schema_verified'])
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
        for key,path in (('report_sha256','quality.json'),('manifest_sha256',self.sidecar)):
            self.assertEqual(result[key],hashlib.sha256(before[path]).hexdigest())
        self.assertEqual(inputs,(self.f.image,self.f.mask,self.f.identity,self.f.metadata))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        result['report_manifest_draft']['source']['product'] = 'caller-return-mutation'
        self.assertNotEqual(self.inspect()['report_manifest_draft']['source']['product'],'caller-return-mutation')

    def test_missing_partial_tampered_and_noncanonical_files_closed(self):
        for name in ('quality.json',self.sidecar):
            path = self.root/name; original = path.read_bytes()
            for raw in (b'',original[:11],original+b' ',b'{"private":"SECRET_PATH"}'):
                path.write_bytes(raw)
                result = self.inspect(); self.assert_closed(result,'FILE_BYTES_MISMATCH')
                self.assertNotIn('SECRET_PATH',json.dumps(result))
            path.unlink(); self.assert_closed(self.inspect(),'FILE_UNAVAILABLE')
            path.write_bytes(original)

    def test_limit_and_growing_read_fail_without_partial_observations(self):
        path = self.root/self.sidecar; original = path.read_bytes()
        path.write_bytes(b'x'*(api.MAX_FILE_BYTES+1))
        self.assert_closed(self.inspect(),'FILE_LIMIT'); path.write_bytes(original)
        with patch.object(api.os,'read',return_value=b'x'*65536):
            self.assert_closed(self.inspect(),'FILE_LIMIT')

    def test_first_file_changes_while_second_read_final_stat_rejects(self):
        original = api._snapshot
        def mutate(path,parents,field):
            value = original(path,parents,field)
            if field == 'manifest': (self.root/'quality.json').write_bytes(b'CHANGED_AFTER_FIRST_READ')
            return value
        with patch.object(api,'_snapshot',side_effect=mutate): self.assert_closed(self.inspect(),'FILE_CHANGED')

    def test_change_during_fd_read_is_detected(self):
        original = api.os.read; changed = False
        def mutate(fd,amount):
            nonlocal changed
            raw = original(fd,amount)
            if not changed:
                changed = True
                with (self.root/'quality.json').open('ab') as stream: stream.write(b'x')
            return raw
        with patch.object(api.os,'read',side_effect=mutate): self.assert_closed(self.inspect(),'FILE_CHANGED')

    def test_all_path_policies_before_file_open(self):
        for value in ('../escape','C:\\escape','/absolute','a//b','CON.json','x:ads','IMAGE.BIN','quality.json','bad?.json','x\u200b.json'):
            self.sidecar = value
            with patch.object(api.os,'open',side_effect=AssertionError('no native open')): self.assert_closed(self.inspect())
        self.sidecar = 'different/sidecar.json'; self.assert_closed(self.inspect(),'OUTPUT_PARENT_MISMATCH')

    def test_reparse_and_parent_identity_guards_mock(self):
        original = Path.lstat
        class Reparse:
            def __init__(self,info): self.info = info
            def __getattr__(self,key): return getattr(self.info,key)
            st_file_attributes = 0x400
        def reparse(path,*args,**kwargs):
            info = original(path,*args,**kwargs)
            return Reparse(info) if path == self.root/'quality.json' else info
        with patch.object(Path,'lstat',reparse): self.assert_closed(self.inspect(),'FILE_INVALID')
        with patch.object(api,'_check_parents',side_effect=api._Invalid('DIRECTORY_CHANGED','output_parent')):
            self.assert_closed(self.inspect(),'DIRECTORY_CHANGED')

    def test_untrusted_completion_output_before_io_and_mutation_after_check(self):
        complete = api.complete_quality_report
        def poison(*args):
            result = complete(*args); result['execution_authorized'] = 0; return result
        with patch.object(api,'complete_quality_report',side_effect=poison),patch.object(api,'_root',side_effect=AssertionError('no IO')):
            self.assert_closed(self.inspect(),'COMPLETION_OUTPUT_INVALID')
        producer = complete(self.f.image,self.f.mask,self.f.identity,self.f.metadata); original_same = api._same
        def mutate(actual,expected):
            equal = original_same(actual,expected)
            if actual is producer:
                producer['report_bytes'] = b'POISON'; producer['report_manifest_draft']['source']['product'] = 'POISON'
            return equal
        with patch.object(api,'complete_quality_report',return_value=producer),patch.object(api,'_same',side_effect=mutate):
            self.assertEqual(self.inspect()['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')

    def test_actual_schema_failure_after_exact_stored_bytes_no_draft_leak(self):
        # Explicit validator-policy fixture: run real canonical_manifest against a
        # temporary stricter schema without changing the repository schema file.
        from app import dataset_registry
        from jsonschema import Draft202012Validator
        schema = copy.deepcopy(dataset_registry.manifest_validator().schema)
        schema['required'].append('TEST_REQUIRED_SCHEMA_FIELD')
        with patch.object(dataset_registry,'manifest_validator',return_value=Draft202012Validator(schema)):
            self.assert_closed(self.inspect(),'MANIFEST_SCHEMA_INVALID')

    def test_schema_return_shape_digest_type_and_postvalidation_mutation(self):
        valid = canonical_manifest(api.complete_quality_report(self.f.image,self.f.mask,self.f.identity,self.f.metadata)['report_manifest_draft'])
        for result in ([*valid],(valid[0],'0'*64),(None,valid[1]),(valid[0],True)):
            with patch.object(api,'canonical_manifest',return_value=result): self.assert_closed(self.inspect(),'MANIFEST_SCHEMA_OUTPUT_INVALID')
        checked = copy.deepcopy(valid); original = api._same
        def mutate(actual,expected):
            equal = original(actual,expected)
            if actual is checked[0]: checked[0]['source']['product'] = 'PRIVATE_POISON'
            return equal
        with patch.object(api,'canonical_manifest',return_value=checked),patch.object(api,'_same',side_effect=mutate):
            result = self.inspect()
        self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertNotIn('PRIVATE_POISON',json.dumps(result))

    def test_cold_local_schema_read_once_but_no_database_write(self):
        from app.dataset_registry import manifest_validator
        manifest_validator.cache_clear(); original = Path.read_text; schema_reads = []
        def read_text(path,*args,**kwargs):
            schema_reads.append(path.name); return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read_text),patch.object(Store,'connect',side_effect=AssertionError('no DB')):
            self.assertEqual(self.inspect()['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertEqual(schema_reads,['dataset-manifest.schema.json'])


if __name__ == '__main__': unittest.main()
