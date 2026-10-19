"""TempStore + actual CPU TinyUNet save/load; never training or inference."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import torch
from app.ml.network import TinyUNet
from app.ml import model_checkpoint_manifest as api
from app.store import Store


def sha(raw):return hashlib.sha256(raw).hexdigest()


class UntrustedFixture:
    pass


class ModelCheckpointManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.store=Store(self.root)
        self.directory=self.root/'models'/'fixture';self.directory.mkdir(parents=True)
        self.checkpoint=self.directory/'best.pt';self.report_path=self.directory/'report.json'
        self.manifest={'bands':[1,2,3,4,5,6],'band_names':['B02','B03','B04','B08','B11','B12'],
            'normalization_mode':'per_scene_product_metadata','version':'DATASET_VERSION_NOT_MODEL_VERSION',
            'synthetic':True,'reference_kind':'synthetic_fixture','class_names':['c'+str(i) for i in range(9)],'patch_size':16}
        self.saved={'architecture':'tiny_unet','manifest':copy.deepcopy(self.manifest),'state_dict':TinyUNet(6).state_dict()}
        self.model={'id':'fixture','status':'Draft','synthetic':True,'checkpoint_path':'models/fixture/best.pt'}
        self.ref={'id':'fixture','version':' v1 ','sha256':''}
        self.report={'model_id':'fixture','training_state':'completed','model_version':' v1 '}
        self.bind_saved()

    def bind_report(self):
        raw=(json.dumps(self.report,allow_nan=False)+'\n').encode();self.report_path.write_bytes(raw)
        self.report_sha=sha(raw)
        self.model['training_report_sha256']=self.report_sha
        self.model['model_version_declaration']={'schema_version':1,'source':'CALLER_EXPLICIT_REGISTRATION',
            'version':' v1 ','checkpoint_sha256':self.ref['sha256'],'training_report_sha256':self.report_sha}
        self.store.put('models',self.model)

    def bind_raw(self,raw):
        self.checkpoint.write_bytes(raw);self.ref['sha256']=sha(raw);self.model['checkpoint_sha256']=sha(raw)
        self.report['checkpoint_sha256']=sha(raw);self.bind_report()

    def bind_saved(self):
        stream=io.BytesIO();torch.save(self.saved,stream);self.bind_raw(stream.getvalue())

    def read(self,**kwargs):
        args={'store':self.store,'model_ref':self.ref,'training_report_sha256':self.report_sha};args.update(kwargs)
        return api.read_pinned_model_checkpoint_manifest(**args)

    def test_actual_checkpoint_manifest_exact15_no_state_or_execution_approval(self):
        before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(self.store,'put',side_effect=AssertionError('read only')):
            result=self.read()
        self.assertEqual(result['status'],'MANIFEST_BOUND_UNVERIFIED');self.assertIsNone(result['issue'])
        self.assertEqual(len(result),15);self.assertEqual(result['checkpoint_manifest'],self.manifest)
        self.assertTrue(result['checkpoint_artifact_verified']);self.assertTrue(result['training_report_artifact_verified'])
        for key in ('state_dict_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            self.assertIs(result[key],False)
        self.assertEqual(result['model_ref']['version'],' v1 ')
        self.assertNotEqual(result['checkpoint_manifest']['version'],result['model_ref']['version'])
        result['checkpoint_manifest']['bands'][0]=99
        self.assertEqual(self.saved['manifest']['bands'][0],1)
        self.assertEqual(before,{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_global_manifest_can_be_read_without_claiming_workflow_support(self):
        self.saved['manifest']['normalization_mode']='global';self.bind_saved()
        result=self.read();self.assertEqual(result['status'],'MANIFEST_BOUND_UNVERIFIED');self.assertFalse(result['workflow_supported'])

    def test_invalid_ref_before_store_and_missing_or_body_id_mismatch(self):
        with patch.object(self.store,'get',side_effect=AssertionError('no read')):
            for ref in (None,{}, {**self.ref,'id':'../fixture'},{**self.ref,'version':'latest'},{**self.ref,'sha256':True}):
                self.assertEqual(self.read(model_ref=ref)['issue']['code'],'INVALID_INPUT')
        self.assertEqual(self.read(model_ref={**self.ref,'id':'missing'})['issue']['code'],'MODEL_NOT_FOUND')
        with patch.object(self.store,'get',return_value={**self.model,'id':'other'}):
            self.assertEqual(self.read()['issue']['code'],'MODEL_RECORD_INVALID')

    def test_declaration_absent_conflict_and_original_version_strictness(self):
        for change,expected in ((lambda m:m.pop('model_version_declaration'),'REGISTRATION_NOT_BOUND'),
            (lambda m:m['model_version_declaration'].update(version='v2'),'PIN_CONFLICT'),
            (lambda m:m['model_version_declaration'].update(checkpoint_sha256='0'*64),'REGISTRATION_NOT_BOUND')):
            model=copy.deepcopy(self.model);change(model)
            with patch.object(self.store,'get',return_value=model):self.assertEqual(self.read()['issue']['code'],expected)
        self.assertEqual(self.read(model_ref={**self.ref,'version':'v1'})['issue']['code'],'PIN_CONFLICT')
        self.assertEqual(self.read(training_report_sha256='0'*64)['issue']['code'],'PIN_CONFLICT')

    def test_each_file_tamper_and_partial_byte_flags(self):
        raw=self.checkpoint.read_bytes();self.checkpoint.write_bytes(raw+b'bad')
        result=self.read();self.assertEqual(result['issue']['field'],'checkpoint');self.assertFalse(result['checkpoint_artifact_verified'])
        self.checkpoint.write_bytes(raw)
        self.report_path.write_bytes(self.report_path.read_bytes()+b'bad')
        result=self.read();self.assertTrue(result['checkpoint_artifact_verified']);self.assertFalse(result['training_report_artifact_verified'])
        self.assertIsNone(result['checkpoint_manifest'])

    def test_rebound_report_wrong_completed_identity_or_sha_and_duplicate_json(self):
        original=copy.deepcopy(self.report)
        for key,value in (('training_state','running'),('model_id','other'),('checkpoint_sha256','0'*64),('model_version',True)):
            self.report=copy.deepcopy(original);self.report[key]=value;self.bind_report()
            self.assertEqual(self.read()['issue']['code'],'TRAINING_REPORT_INVALID')
        raw=b'{"model_id":"fixture","model_id":"fixture"}'
        self.report_path.write_bytes(raw);self.report_sha=sha(raw)
        self.model['training_report_sha256']=self.report_sha;self.model['model_version_declaration']['training_report_sha256']=self.report_sha
        self.store.put('models',self.model)
        self.assertEqual(self.read()['issue']['code'],'TRAINING_REPORT_INVALID')

    def test_same_hashed_copied_bytesio_loaded_no_state_dict_or_model_forward(self):
        original=torch.load;captured=[]
        def load(stream,**kwargs):
            self.assertIsInstance(stream,io.BytesIO);self.assertEqual(sha(stream.getvalue()),self.ref['sha256'])
            self.assertEqual(kwargs,{'map_location':'cpu','weights_only':True});captured.append(True)
            return original(stream,**kwargs)
        with (patch.object(torch,'load',load),patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state load')),
              patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference'))):
            self.assertEqual(self.read()['status'],'MANIFEST_BOUND_UNVERIFIED')
        self.assertEqual(captured,[True])

    def test_ambient_safe_globals_unchanged_no_fallback_and_custom_pickle_rejected(self):
        before={id(v) for v in torch.serialization.get_safe_globals()}
        with (patch.object(torch.serialization,'add_safe_globals',side_effect=AssertionError('no mutation')),
              patch.object(torch.serialization,'clear_safe_globals',side_effect=AssertionError('no mutation'))):
            self.assertEqual(self.read()['status'],'MANIFEST_BOUND_UNVERIFIED')
        self.assertEqual(before,{id(v) for v in torch.serialization.get_safe_globals()})
        with patch.object(torch,'load',side_effect=RuntimeError('private unsupported global')) as loader:
            self.assertEqual(self.read()['issue']['code'],'CHECKPOINT_LOAD_UNAVAILABLE')
            self.assertEqual(loader.call_count,1)
            self.assertEqual(loader.call_args.kwargs,{'map_location':'cpu','weights_only':True})
        self.saved['untrusted']=UntrustedFixture();self.bind_saved()
        result=self.read();self.assertEqual(result['issue']['code'],'CHECKPOINT_LOAD_UNAVAILABLE')
        self.assertTrue(result['checkpoint_artifact_verified']);self.assertFalse(result['state_dict_verified'])

    def test_legacy_compressed_duplicate_encrypted_traversal_and_directory_archives_rejected_before_torch(self):
        legacy=io.BytesIO();torch.save(self.saved,legacy,_use_new_zipfile_serialization=False)
        bad=[legacy.getvalue()]
        encrypted=io.BytesIO()
        with zipfile.ZipFile(encrypted,'w') as z:z.writestr('archive/data.pkl',b'not pickle')
        raw=bytearray(encrypted.getvalue())
        for signature,offset in ((b'PK\x03\x04',6),(b'PK\x01\x02',8)):
            at=raw.index(signature)+offset;raw[at]|=1
        bad.append(bytes(raw))
        for names,compression in ((['archive/data.pkl'],zipfile.ZIP_DEFLATED),(['archive/data.pkl','archive/data.pkl'],zipfile.ZIP_STORED),
            (['archive/../data.pkl'],zipfile.ZIP_STORED),(['archive/'],zipfile.ZIP_STORED)):
            stream=io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(stream,'w',compression=compression) as z:
                    for name in names:z.writestr(name,b'not pickle')
            bad.append(stream.getvalue())
        for raw in bad:
            self.bind_raw(raw)
            with patch.object(torch,'load',side_effect=AssertionError('invalid archive no load')):
                self.assertEqual(self.read()['issue']['code'],'CHECKPOINT_ARCHIVE_INVALID')

    def test_archive_and_file_caps_before_load(self):
        for key in ('MAX_CHECKPOINT','MAX_REPORT'):
            with patch.object(api,key,1):self.assertEqual(self.read()['issue']['code'],'FILE_LIMIT')
        for key in ('MAX_MEMBERS','MAX_UNCOMPRESSED','MAX_MEMBER','MAX_PICKLE'):
            with patch.object(api,key,1),patch.object(torch,'load',side_effect=AssertionError('no load')):
                self.assertEqual(self.read()['issue']['code'],'CHECKPOINT_ARCHIVE_INVALID')

    def test_actual_loaded_manifest_invalid_nonjson_architecture_and_state_not_validated(self):
        for value in (torch.tensor([1]),{'nan':float('nan')},{'tuple':(1,2)},{'bad':'\ud800'}):
            self.saved['manifest']=value;self.bind_saved();self.assertEqual(self.read()['issue']['code'],'MANIFEST_INVALID')
        self.saved['manifest']=self.manifest;self.saved['architecture']='unknown';self.bind_saved()
        self.assertEqual(self.read()['issue']['code'],'CHECKPOINT_FORMAT_INVALID')
        self.saved['architecture']='tiny_unet';self.saved['state_dict']={'not_real_weights':1};self.bind_saved()
        self.assertEqual(self.read()['status'],'MANIFEST_BOUND_UNVERIFIED');self.assertFalse(self.read()['state_dict_verified'])

    def test_manifest_bounds_cycles_subclasses_keys_and_detached_budget(self):
        class SubString(str):pass
        cycle={};cycle['cycle']=cycle
        for value in (cycle,{SubString('x'):1},{'x':object()},{'x':10**1000},{'\n':1},{'x':['a'*4096]*1000}):
            with self.assertRaises(api._Invalid):api._manifest(value)
        nested={};value=nested
        for _ in range(18):value['x']={};value=value['x']
        with self.assertRaises(api._Invalid):api._manifest(nested)

    def test_namespace_and_link_and_missing_private_error(self):
        self.model['checkpoint_path']='models/other/best.pt';self.store.put('models',self.model)
        self.assertEqual(self.read()['issue']['code'],'CHECKPOINT_PATH_INVALID')
        self.model['checkpoint_path']='models\\fixture\\best.pt';self.store.put('models',self.model)
        self.assertEqual(self.read()['status'],'MANIFEST_BOUND_UNVERIFIED')
        self.checkpoint.unlink();result=self.read();self.assertEqual(result['issue']['code'],'FILE_UNAVAILABLE')
        self.assertNotIn(str(self.root),str(result['issue']))

    def test_empty_manifest_missing_state_and_caller_claims_not_wrapper_authority(self):
        self.saved={'architecture':'tiny_unet','manifest':{}};self.bind_saved()
        result=self.read();self.assertEqual(result['status'],'MANIFEST_BOUND_UNVERIFIED')
        self.assertEqual(result['checkpoint_manifest'],{});self.assertFalse(result['state_dict_verified'])
        self.saved['manifest']={'execution_authorized':True,'scientific_accuracy_validated':True}
        self.bind_saved();result=self.read()
        self.assertTrue(result['checkpoint_manifest']['execution_authorized'])
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['scientific_accuracy_validated'])


if __name__=='__main__':unittest.main()
