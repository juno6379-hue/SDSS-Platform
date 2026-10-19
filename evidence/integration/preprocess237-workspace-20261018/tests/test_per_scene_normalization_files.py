"""Only temporary opaque bytes/JSON; no raster, checkpoint or operating data."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.ml import per_scene_normalization_files as api


def sha(raw):return hashlib.sha256(raw).hexdigest()


class PerSceneNormalizationFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.image=self.root/'image.bin';self.image.write_bytes(b'opaque image role bytes, NOT a validated raster')
        self.metadata=self.root/'metadata.xml';self.metadata.write_bytes(b'<test_fixture>not official</test_fixture>')
        self.evidence_path=self.root/'evidence.json'
        names=['B02','B03','B04','B08','B11','B12']
        self.manifest={'normalization_mode':'per_scene_product_metadata','bands':list(range(1,7)),'band_names':names.copy()}
        self.source={'scene_id':'scene_fixture','image_sha256':sha(self.image.read_bytes()),'band_names':names.copy()}
        self.evidence={'status':'verified_product_metadata','product_id':'scene_fixture','band_names':names.copy(),
            'scale':[.0001]*6,'offset':[0]*6,'source_url':'caller attribution only',
            'source_metadata_path':'metadata.xml','source_metadata_sha256':sha(self.metadata.read_bytes())}
        self.normalization={'scale':.0001,'offset':0,'evidence_path':'evidence.json','evidence_sha256':''}
        self.rebind()

    def rebind(self, raw=None):
        raw=(json.dumps(self.evidence,ensure_ascii=False)+'\n').encode() if raw is None else raw
        self.evidence_path.write_bytes(raw)
        self.normalization['evidence_sha256']=sha(raw)

    def verify(self, **kwargs):
        args={'data_root':self.root,'checkpoint_manifest':self.manifest,'source_scene':self.source,
              'normalization':self.normalization,'image_path':'image.bin'}
        args.update(kwargs)
        return api.verify_per_scene_normalization_files(**args)

    def test_actual_three_role_bytes_exact12_and_checkpoint_authority_execution_unverified(self):
        result=self.verify()
        self.assertEqual(set(result),{'schema_version','scope','status','issue','declaration_observation','file_bindings',
            'artifact_bytes_verified','checkpoint_artifact_verified','source_authority_verified','scientific_accuracy_validated',
            'execution_authorized','workflow_supported'})
        self.assertEqual(result['status'],'FILES_MATCHED_UNVERIFIED');self.assertIsNone(result['issue'])
        self.assertIs(result['artifact_bytes_verified'],True)
        self.assertEqual(result['file_bindings'],dict.fromkeys(('image','normalization_evidence','source_metadata'),'MATCH'))
        for key in ('checkpoint_artifact_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            self.assertIs(result[key],False)
        self.assertFalse(result['declaration_observation']['artifact_bytes_verified'])

    def test_each_role_hash_mutation_retains_only_prior_snapshot_bindings(self):
        for role,path in (('normalization_evidence',self.evidence_path),('image',self.image),('source_metadata',self.metadata)):
            raw=path.read_bytes();path.write_bytes(raw+b'tamper')
            result=self.verify();self.assertEqual(result['status'],'BLOCKED')
            self.assertEqual(result['issue'],{'code':'SHA256_MISMATCH','field':role})
            self.assertEqual(result['file_bindings'][role],'MISMATCH');self.assertFalse(result['artifact_bytes_verified'])
            path.write_bytes(raw)

    def test_missing_files_no_implicit_generation_and_private_error(self):
        for role,path in (('normalization_evidence',self.evidence_path),('image',self.image),('source_metadata',self.metadata)):
            raw=path.read_bytes();path.unlink();result=self.verify()
            self.assertEqual(result['issue'],{'code':'FILE_UNAVAILABLE','field':role})
            self.assertNotIn(str(self.root),str(result));self.assertFalse(path.exists());path.write_bytes(raw)

    def test_per_role_limits_and_growth_abort_without_consuming_unbounded_stream(self):
        for constant,role in (('MAX_EVIDENCE','normalization_evidence'),('MAX_IMAGE','image'),('MAX_METADATA','source_metadata')):
            with patch.object(api,constant,1):
                self.assertEqual(self.verify()['issue'],{'code':'FILE_LIMIT','field':role})
        original_open=Path.open
        image=self.image
        class Growing:
            def __init__(self,stream):self.stream=stream;self.reads=0
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,size):
                self.reads+=1
                if self.reads==1:
                    with original_open(image,'ab') as output:output.write(b'X'*100)
                return self.stream.read(size)
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return Growing(stream) if path==image and args==('rb',) else stream
        with patch.object(api,'MAX_IMAGE',100),patch.object(Path,'open',opened):
            self.assertEqual(self.verify()['issue'],{'code':'FILE_LIMIT','field':'image'})

    def test_rebound_duplicate_nonfinite_surrogate_utf8_depth_and_node_json_reject(self):
        invalid=[b'{"status":1,"status":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":"\\ud800"}',b'{"\\ud800":1}',b'\xff',b'[]',
                 ('{"x":'+'['*65+'0'+']'*65+'}').encode()]
        for raw in invalid:
            self.rebind(raw);result=self.verify()
            self.assertEqual(result['issue'],{'code':'EVIDENCE_JSON_INVALID','field':'normalization_evidence'})
            self.assertEqual(result['file_bindings']['normalization_evidence'],'MATCH')
        self.rebind()
        with patch.object(api,'MAX_JSON_NODES',2):
            self.assertEqual(self.verify()['issue']['code'],'EVIDENCE_JSON_INVALID')

    def test_declared_valid_sha_does_not_equal_verified_bytes_and_semantic_rebinding_still_blocks(self):
        self.source['image_sha256']='0'*64
        self.assertEqual(self.verify()['issue'],{'code':'SHA256_MISMATCH','field':'image'})
        self.source['image_sha256']=sha(self.image.read_bytes())
        self.evidence['product_id']='other';self.rebind();result=self.verify()
        self.assertEqual(result['issue']['code'],'DECLARATION_NOT_CONSISTENT')
        self.assertEqual(result['declaration_observation']['status'],'DECLARATION_MISMATCH')
        self.assertEqual(result['file_bindings']['normalization_evidence'],'MATCH')
        self.assertEqual(result['file_bindings']['image'],'NOT_CHECKED')
        self.assertFalse(result['artifact_bytes_verified'])

    def test_opaque_path_validation_for_all_roles_and_windows_separator_support(self):
        bad=['../image.bin','/image.bin','C:\\image.bin','https://example.invalid/a','a//b','a/./b','a/../b','a/','file.','file ']
        for value in bad:
            self.assertEqual(self.verify(image_path=value)['issue'],{'code':'PATH_INVALID','field':'image'})
        for value in bad:
            before=self.normalization['evidence_path'];self.normalization['evidence_path']=value
            self.assertEqual(self.verify()['issue'],{'code':'PATH_INVALID','field':'normalization_evidence'})
            self.normalization['evidence_path']=before
        self.evidence['source_metadata_path']='../metadata.xml';self.rebind()
        self.assertEqual(self.verify()['issue'],{'code':'PATH_INVALID','field':'source_metadata'})
        (self.root/'nested').mkdir();self.metadata.rename(self.root/'nested'/'metadata.xml')
        self.evidence['source_metadata_path']='nested\\metadata.xml';self.rebind()
        self.assertEqual(self.verify()['status'],'FILES_MATCHED_UNVERIFIED')

    def test_global_and_malformed_source_norm_per_scene_have_no_filesystem_access(self):
        with patch.object(Path,'open',side_effect=AssertionError('I/O')),patch.object(Path,'resolve',side_effect=AssertionError('I/O')):
            result=self.verify(checkpoint_manifest={'normalization_mode':'global'},data_root=object(),image_path=object())
            self.assertEqual(result['status'],'OUT_OF_SCOPE')
            for field in ('source_scene','normalization'):
                result=self.verify(**{field:None})
                self.assertEqual(result['issue']['code'],'DECLARATION_NOT_CONSISTENT')

    def test_root_is_explicit_absolute_existing_and_no_custom_fspath_callback(self):
        class Poison:
            def __fspath__(self):raise AssertionError('callback forbidden')
        self.assertEqual(self.verify(data_root=Poison())['issue'],{'code':'INVALID_INPUT','field':'data_root'})
        for value in ('relative_root',self.root/'missing',self.image):
            self.assertEqual(self.verify(data_root=value)['issue'],{'code':'ROOT_UNAVAILABLE','field':'data_root'})
        self.assertEqual(self.verify(data_root=str(self.root))['status'],'FILES_MATCHED_UNVERIFIED')
        with patch.object(Path,'resolve',side_effect=AssertionError('UNC must not be accessed')):
            self.assertEqual(self.verify(data_root='\\\\server\\share')['issue'],{'code':'ROOT_UNAVAILABLE','field':'data_root'})
            self.assertEqual(self.verify(data_root='//server/share')['issue'],{'code':'ROOT_UNAVAILABLE','field':'data_root'})

    def test_ancestor_link_predicate_and_nonregular_file_fail_closed(self):
        original=Path.is_symlink
        for selected,code in ((self.root,'ROOT_UNAVAILABLE'),(self.image,'PATH_INVALID'),(self.root.parent,'ROOT_UNAVAILABLE')):
            with patch.object(Path,'is_symlink',lambda path: path==selected or original(path)):
                self.assertEqual(self.verify()['issue']['code'],code)
        self.image.unlink();self.image.mkdir()
        self.assertEqual(self.verify()['issue'],{'code':'FILE_UNAVAILABLE','field':'image'})

    def test_real_symlink_reject_where_host_allows_otherwise_predicate_boundary_only(self):
        target=self.root/'real.bin';self.image.rename(target)
        try:
            self.image.symlink_to(target)
        except OSError:
            target.rename(self.image)
            original=Path.is_symlink
            with patch.object(Path,'is_symlink',lambda path:path==self.image or original(path)):
                self.assertEqual(self.verify()['issue']['code'],'PATH_INVALID')
        else:
            self.assertEqual(self.verify()['issue']['code'],'PATH_INVALID')
            self.image.unlink();target.rename(self.image)

    def test_mtime_changed_during_read_blocks_even_same_bytes(self):
        original_open=Path.open;image=self.image
        class Changed:
            def __init__(self,stream):self.stream=stream;self.once=False
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,size):
                result=self.stream.read(size)
                if not self.once:
                    self.once=True;attrs=image.stat();os.utime(image,ns=(attrs.st_atime_ns,attrs.st_mtime_ns+1000000000))
                return result
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return Changed(stream) if path==image and args==('rb',) else stream
        with patch.object(Path,'open',opened):
            self.assertEqual(self.verify()['issue'],{'code':'FILE_CHANGED','field':'image'})

    def test_same_image_and_metadata_path_allowed_but_not_a_raster_claim(self):
        self.evidence.update(source_metadata_path='image.bin',source_metadata_sha256=self.source['image_sha256']);self.rebind()
        result=self.verify();self.assertTrue(result['artifact_bytes_verified']);self.assertFalse(result['workflow_supported'])

    def test_inputs_files_immutable_and_no_raw_paths_in_output(self):
        before=copy.deepcopy((self.manifest,self.source,self.normalization,self.evidence))
        files={p.name:p.read_bytes() for p in self.root.iterdir()}
        result=self.verify()
        self.assertEqual(before,(self.manifest,self.source,self.normalization,self.evidence))
        self.assertEqual(files,{p.name:p.read_bytes() for p in self.root.iterdir()})
        self.assertNotIn(str(self.root),str(result));self.assertNotIn('metadata.xml',str(result))


if __name__=='__main__':unittest.main()
