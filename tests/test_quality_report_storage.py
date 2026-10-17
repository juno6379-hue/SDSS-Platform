"""Exclusive new Temp files only; partial outputs are never rolled back."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import quality_report_storage as api
from app.dataset_registry import register_version
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store
import test_quality_report_completion as fixtures


class QualityReportStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.QualityReportCompletionTests.setUpClass()
        cls.addClassCleanup(fixtures.QualityReportCompletionTests.doClassCleanups)

    def setUp(self):
        self.fixture = fixtures.QualityReportCompletionTests(); self.fixture.setUp()
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.sidecar = 'quality.manifest.json'
        source = self.fixture.fixture.fixture.fixture
        for manifest,index in ((self.fixture.image,0),(self.fixture.mask,2)):
            (self.root/manifest['artifact_uri']).write_bytes(source.paths[index].read_bytes())

    def write(self):
        f = self.fixture
        return api.write_quality_report_files(self.root,f.image,f.mask,f.identity,f.metadata,self.sidecar)

    def test_new_two_files_exact21_excl_hashes_no_store_and_source_inputs_unchanged(self):
        f = self.fixture; before = copy.deepcopy((f.image,f.mask,f.identity,f.metadata))
        source = {name:(self.root/name).read_bytes() for name in ('image.bin','mask.bin')}
        with patch.object(api,'complete_quality_report',wraps=api.complete_quality_report) as complete,patch.object(Store,'put',side_effect=AssertionError('no Store')):
            result = self.write()
        complete.assert_called_once(); self.assertEqual(len(result),21)
        self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED'); self.assertTrue(result['stored_outputs_verified'])
        self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))
        self.assertTrue(all(o['created'] and o['verified'] for o in result['outputs']))
        for field,path in (('report_sha256','quality.json'),('manifest_sha256',self.sidecar)):
            self.assertEqual(result[field],hashlib.sha256((self.root/path).read_bytes()).hexdigest())
        self.assertEqual((f.image,f.mask,f.identity,f.metadata),before)
        self.assertEqual(source,{name:(self.root/name).read_bytes() for name in source})

    def test_existing_either_output_any_content_no_overwrite_or_replay(self):
        for path in ('quality.json',self.sidecar):
            (self.root/path).write_bytes(b'EXISTING_DO_NOT_CHANGE')
            with patch.object(api,'_write_new',side_effect=AssertionError('precheck0')):
                result = self.write()
            self.assertEqual(result['issue']['code'],'OUTPUT_ALREADY_EXISTS')
            self.assertEqual((self.root/path).read_bytes(),b'EXISTING_DO_NOT_CHANGE')
            (self.root/path).unlink()  # Test fixture setup only, not product cleanup.
        first = self.write(); raw = (self.root/'quality.json').read_bytes(); second = self.write()
        self.assertEqual(first['status'],'FILES_WRITTEN_UNREGISTERED')
        self.assertEqual(second['issue']['code'],'OUTPUT_ALREADY_EXISTS'); self.assertEqual((self.root/'quality.json').read_bytes(),raw)

    def test_no_mkdir_parent_mismatch_path_alias_reserved_ads_and_controls(self):
        for char in '<>"|?*':
            self.sidecar = 'bad'+char+'.json'
            with patch.object(api.os,'open',side_effect=AssertionError('no native open')):
                result = self.write()
            self.assertEqual(result['issue']['code'],'PATH_INVALID')
            self.assertEqual(result['status'],'BLOCKED')
            self.assertFalse((self.root/'quality.json').exists())
        for value in ('../other.json','/other.json','C:\\other.json','https://x/out','a//b','x. /y',
                      'CON.json','com1.json','LPT¹.json','x:stream','x\u200b.json','x\x00.json','quality.json','IMAGE.BIN'):
            self.sidecar = value
            with patch.object(api,'_write_new',side_effect=AssertionError('no write')):
                self.assertEqual(self.write()['status'],'BLOCKED')
        self.sidecar = 'missing/sidecar.json'
        self.assertEqual(self.write()['issue']['code'],'OUTPUT_PARENT_MISMATCH')
        self.assertFalse((self.root/'missing').exists())

    def test_same_missing_parent_no_creation_and_quality_ref_collision(self):
        self.fixture.identity['artifact_uri'] = 'missing/quality.json'; self.fixture.image['quality_report_ref'] = 'missing/quality.json'
        self.sidecar = 'missing/manifest.json'
        self.assertEqual(self.write()['issue']['code'],'DIRECTORY_UNAVAILABLE')
        self.assertFalse((self.root/'missing').exists())
        self.fixture.identity['artifact_uri'] = 'quality.json'; self.fixture.image['quality_report_ref'] = 'quality.json'
        self.fixture.mask['quality_report_ref'] = self.sidecar = 'old-quality.json'
        self.assertEqual(self.write()['issue']['code'],'OUTPUT_PATH_CONFLICT')

    def test_second_creation_race_preserves_first_and_existing_second(self):
        original = api._write_new
        def race(path,raw,parents,output):
            if output['role'] == 'manifest': path.write_bytes(b'OTHER_CREATOR')
            return original(path,raw,parents,output)
        with patch.object(api,'_write_new',side_effect=race): result = self.write()
        self.assertEqual(result['status'],'PARTIAL_FILES_PRESERVED')
        self.assertTrue(result['outputs'][0]['verified']); self.assertFalse(result['outputs'][1]['created'])
        self.assertTrue((self.root/'quality.json').exists()); self.assertEqual((self.root/self.sidecar).read_bytes(),b'OTHER_CREATOR')
        self.assertFalse(result['stored_outputs_verified'])

    def test_short_write_loop_and_fsync_failure_partial_file_never_deleted(self):
        original = os.write
        with patch.object(api.os,'write',side_effect=lambda fd,data:original(fd,data[:7])):
            self.assertEqual(self.write()['status'],'FILES_WRITTEN_UNREGISTERED')
        # A separate fixture directory for a failure path, no retry overwrite.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); f = self.fixture
            with patch.object(api.os,'fsync',side_effect=OSError('PRIVATE')):
                result = api.write_quality_report_files(root,f.image,f.mask,f.identity,f.metadata,self.sidecar)
            self.assertEqual(result['status'],'PARTIAL_FILES_PRESERVED'); self.assertTrue((root/'quality.json').exists())
            self.assertFalse((root/self.sidecar).exists()); self.assertNotIn('PRIVATE',json.dumps(result))

    def test_mutable139_parent_output_not_used_after_verified_snapshot(self):
        f = self.fixture; producer = api.complete_quality_report(f.image,f.mask,f.identity,f.metadata)
        original_bytes = producer['report_bytes']; same = api._same
        def poison(actual,expected):
            verified = same(actual,expected)
            if type(expected) is dict and expected.get('scope') == 'UNREGISTERED_EXPLICIT_QUALITY_REPORT_COMPLETION_ONLY' and verified:
                actual['report_bytes'] = b'POISON'; actual['report_manifest_draft']['source']['institution'] = 'POISON'
            return verified
        with patch.object(api,'complete_quality_report',return_value=producer),patch.object(api,'_same',side_effect=poison): result = self.write()
        self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED')
        self.assertEqual((self.root/'quality.json').read_bytes(),original_bytes)
        self.assertNotIn('POISON',(self.root/self.sidecar).read_text())

    def test_untrusted_completion_rejected_before_file_access_and_custom_root(self):
        f = self.fixture; parent = api.complete_quality_report(f.image,f.mask,f.identity,f.metadata)
        parent['registry_registered'] = True
        with patch.object(api,'complete_quality_report',return_value=parent),patch.object(api,'_root',side_effect=AssertionError('no IO')):
            result = self.write()
        self.assertEqual(result['issue']['code'],'COMPLETION_OUTPUT_INVALID'); self.assertFalse((self.root/'quality.json').exists())
        class CustomRoot:
            def __fspath__(self): raise AssertionError('custom fspath not called')
        result = api.write_quality_report_files(CustomRoot(),f.image,f.mask,f.identity,f.metadata,self.sidecar)
        self.assertEqual(result['issue']['code'],'ROOT_INVALID')

    def test_link_and_reparse_parent_checks_fail_closed(self):
        (self.root/'outputs').mkdir(); self.fixture.identity['artifact_uri'] = 'outputs/quality.json'
        self.fixture.image['quality_report_ref'] = 'outputs/quality.json'; self.sidecar = 'outputs/manifest.json'
        original = Path.lstat
        class Reparse:
            st_mode = 0o040755; st_file_attributes = 0x400; st_reparse_tag = 0xA0000003
        def tagged(path,*args,**kwargs): return Reparse() if path == self.root/'outputs' else original(path,*args,**kwargs)
        with patch.object(Path,'lstat',new=tagged): result = self.write()
        self.assertEqual(result['issue']['code'],'DIRECTORY_UNAVAILABLE'); self.assertFalse((self.root/'outputs/quality.json').exists())

    def test_written_manifest_temp_registration_and_real_consumption_separate(self):
        result = self.write(); self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED')
        report = json.loads((self.root/self.sidecar).read_bytes()); store = Store(self.root)
        for manifest in (self.fixture.image,self.fixture.mask,report): register_version(store,manifest)
        refs = result['fixed_refs']
        observed = inspect_registered_binary_mask_values(store,refs['image_ref'],refs['quality_report_ref'],refs['mask_ref'])
        self.assertTrue(observed['mask_values_verified']); self.assertFalse(observed['execution_authorized'])


if __name__ == '__main__': unittest.main()
