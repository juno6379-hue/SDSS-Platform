"""Three TempStore version records + temporary bytes; no model/inference/operating IO."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.dataset_registry import canonical_manifest, version_key
from app.store import Store
from app.ml import registered_per_scene_files as api


def sha(raw):return hashlib.sha256(raw).hexdigest()


class RegisteredPerSceneFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.store=Store(self.root)
        self.assets=self.root/'assets';self.assets.mkdir()
        self.image=self.assets/'image.bin';self.image.write_bytes(b'TEMP opaque image role only')
        self.metadata=self.assets/'metadata.xml';self.metadata.write_bytes(b'<fixture/>')
        self.evidence_path=self.assets/'evidence.json'
        self.names=['B02','B03','B04','B08','B11','B12']
        self.checkpoint={'normalization_mode':'per_scene_product_metadata','bands':list(range(1,7)),'band_names':self.names.copy()}
        self.evidence={'status':'verified_product_metadata','product_id':'EXPLICIT_SCENE',
            'band_names':self.names.copy(),'scale':.0001,'offset':[0]*6,'source_url':'caller attribution only',
            'source_metadata_path':'assets/metadata.xml','source_metadata_sha256':sha(self.metadata.read_bytes())}
        self.evidence_path.write_text(json.dumps(self.evidence),encoding='utf-8')
        self.refs=[{'id':name,'version':' v1 ','sha256':sha(path.read_bytes())} for name,path in
                   (('image-dataset',self.image),('evidence-dataset',self.evidence_path),('metadata-dataset',self.metadata))]
        self.manifests=[]
        for ref,path,kind in zip(self.refs,(self.image,self.evidence_path,self.metadata),('raster','document','document')):
            self.manifests.append({'schema_version':'0.2.0','dataset_id':ref['id'],'version':ref['version'],
                'source':{'institution':'TEST_ONLY','product':'PRODUCT_FAMILY_NOT_SCENE_ID','license':'fixture'},
                'data_type':kind,'spatial':{'bbox':[100.,-10.,110.,0.],'crs':'EPSG:4326'},
                'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T00:00:00Z','calendar':'gregorian'},
                'quality_status':'RAW','access_class':'PUBLIC','sha256':ref['sha256'],
                'artifact_uri':path.relative_to(self.root).as_posix(),'lineage':[]})
        self.manifests[0]['source'].update(scene_id='EXPLICIT_SCENE',band_names=self.names.copy())
        self.manifests[1]['lineage']=[{**self.refs[0],'role':api.LINEAGE_ROLES[0]},{**self.refs[2],'role':api.LINEAGE_ROLES[1]}]
        for index in range(3):self.save(index)

    def save(self,index):
        manifest,digest=canonical_manifest(self.manifests[index])
        self.store.put('dataset_versions',{'id':version_key(manifest['dataset_id'],manifest['version']),
            'manifest':manifest,'manifest_sha256':digest,'scientific_accuracy_validated':False,'deployment_approval':False})

    def rebind_evidence(self):
        raw=json.dumps(self.evidence).encode();self.evidence_path.write_bytes(raw)
        self.refs[1]['sha256']=sha(raw);self.manifests[1]['sha256']=sha(raw);self.save(1)

    def read(self,**kwargs):
        args={'store':self.store,'checkpoint_manifest':self.checkpoint,'image_ref':self.refs[0],
              'evidence_ref':self.refs[1],'metadata_ref':self.refs[2]};args.update(kwargs)
        return api.read_registered_per_scene_files(**args)

    def test_three_registered_refs_and_file_bytes_exact19_raw_quality_not_approval(self):
        with patch.object(self.store,'put',side_effect=AssertionError('no writes')):
            result=self.read()
        self.assertEqual(len(result),19);self.assertEqual(result['status'],'REGISTERED_FILES_MATCHED_UNVERIFIED')
        self.assertTrue(result['registry_references_verified']);self.assertTrue(result['artifact_bytes_verified'])
        self.assertEqual([b['quality_status'] for b in result['registry_bindings']],['RAW']*3)
        self.assertEqual(result['file_observation']['status'],'FILES_MATCHED_UNVERIFIED')
        for field in ('checkpoint_artifact_verified','raster_header_verified','quality_report_verified','quality_mask_verified',
                      'source_authority_verified','access_authorization_verified','other_lineage_parents_verified',
                      'state_dict_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            self.assertIs(result[field],False)

    def test_exact_three_get_calls_and_no_recursive_other_lineage_or_old_asset_verifier(self):
        self.manifests[1]['lineage'].append({'id':'unresolved-other','version':'v1','sha256':'0'*64,'role':'other'})
        self.save(1)
        with (patch.object(self.store,'get',wraps=self.store.get) as getter,
              patch('app.dataset_registry.resolve_version',side_effect=AssertionError('no resolver')),
              patch('app.dataset_registry.verify_artifact',side_effect=AssertionError('no unbounded verifier'))):
            result=self.read()
        self.assertEqual(result['status'],'REGISTERED_FILES_MATCHED_UNVERIFIED');self.assertEqual(getter.call_count,3)
        self.assertEqual([call.args for call in getter.call_args_list],[('dataset_versions',version_key(r['id'],r['version'])) for r in self.refs])

    def test_source_scene_and_bands_must_be_registered_not_invented_from_product_or_checkpoint(self):
        for field in ('scene_id','band_names'):
            original=copy.deepcopy(self.manifests[0]);del self.manifests[0]['source'][field];self.save(0)
            self.assertEqual(self.read()['issue']['code'],'SCENE_DECLARATION_MISSING')
            self.manifests[0]=original;self.save(0)
        self.manifests[0]['source']['band_names']=['X']*6;self.save(0)
        result=self.read();self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['file_observation']['declaration_observation']['status'],'DECLARATION_MISMATCH')

    def test_registered_scene_product_and_evidence_band_mismatch_block(self):
        for key,value in (('product_id','WRONG_SCENE'),('band_names',['other']*6)):
            original=copy.deepcopy(self.evidence);self.evidence[key]=value;self.rebind_evidence()
            self.assertEqual(self.read()['status'],'BLOCKED')
            self.evidence=original;self.rebind_evidence()

    def test_three_role_type_and_public_only_consumer_policy(self):
        for index in range(3):
            original=copy.deepcopy(self.manifests[index]);self.manifests[index]['data_type']='table';self.save(index)
            self.assertEqual(self.read()['issue']['code'],'REGISTRY_TYPE_MISMATCH')
            self.manifests[index]=copy.deepcopy(original);self.manifests[index]['access_class']='RESTRICTED';self.save(index)
            self.assertEqual(self.read()['issue']['code'],'ACCESS_DECLARATION_BLOCKED')
            self.manifests[index]=original;self.save(index)

    def test_all_declared_quality_states_remain_diagnostic_and_qa_body_unread(self):
        for quality in ('RAW','STAGED','STANDARDIZED','VALIDATED','REJECTED'):
            self.manifests[0]['quality_status']=quality;self.manifests[0]['quality_report_ref']='not-read-missing-quality.json';self.save(0)
            result=self.read();self.assertEqual(result['status'],'REGISTERED_FILES_MATCHED_UNVERIFIED')
            self.assertEqual(result['registry_bindings'][0]['quality_status'],quality);self.assertFalse(result['quality_report_verified'])

    def test_lineage_missing_duplicate_wrong_pin_and_opposite_role_reject(self):
        original=copy.deepcopy(self.manifests[1]['lineage'])
        variants=[[],original+[copy.deepcopy(original[0])],[{**original[0],'sha256':'0'*64},original[1]],
                  [{**original[0],'role':api.LINEAGE_ROLES[1]},{**original[1],'role':api.LINEAGE_ROLES[0]}]]
        for parents in variants:
            self.manifests[1]['lineage']=parents;self.save(1)
            self.assertEqual(self.read()['issue']['code'],'LINEAGE_BINDING_INVALID')

    def test_manifest_record_key_canonical_digest_and_requested_sha_conflict(self):
        key=version_key(self.refs[0]['id'],self.refs[0]['version']);record=self.store.get('dataset_versions',key)
        for changed in ({**record,'id':'wrong'},{**record,'manifest_sha256':'0'*64}):
            with patch.object(self.store,'get',return_value=changed):self.assertEqual(self.read()['status'],'BLOCKED')
        changed=copy.deepcopy(record);changed['manifest']['source']['scene_id']='CHANGED_WITHOUT_REPIN'
        with patch.object(self.store,'get',return_value=changed):
            self.assertEqual(self.read()['issue']['code'],'REGISTRY_REFERENCE_CONFLICT')
        bad={**self.refs[0],'sha256':'0'*64}
        self.assertEqual(self.read(image_ref=bad)['issue']['code'],'REGISTRY_REFERENCE_CONFLICT')

    def test_metadata_ref_sha_and_actualpath_cannot_be_substituted(self):
        for key,value in (('source_metadata_sha256','0'*64),('source_metadata_path','assets/other.xml')):
            original=copy.deepcopy(self.evidence);self.evidence[key]=value;self.rebind_evidence()
            self.assertEqual(self.read()['issue']['code'],'EVIDENCE_BINDING_INVALID')
            self.evidence=original;self.rebind_evidence()

    def test_evidence_copied_read_then_same_pin_second_read_detects_race(self):
        original=api.verify_per_scene_normalization_files
        def changed(*args,**kwargs):
            self.evidence_path.write_bytes(self.evidence_path.read_bytes()+b'changed')
            return original(*args,**kwargs)
        with patch.object(api,'verify_per_scene_normalization_files',changed):result=self.read()
        self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['artifact_bytes_verified'])
        self.assertEqual(result['file_observation']['issue']['code'],'SHA256_MISMATCH')

    def test_actual_each_file_tamper_size_and_path_escape_reject(self):
        for path in (self.image,self.evidence_path,self.metadata):
            raw=path.read_bytes();path.write_bytes(raw+b'tamper');self.assertEqual(self.read()['status'],'BLOCKED');path.write_bytes(raw)
        with patch.object(api,'MAX_EVIDENCE',1):self.assertEqual(self.read()['issue']['code'],'FILE_LIMIT')
        self.manifests[0]['artifact_uri']='../outside.bin';self.save(0)
        self.assertEqual(self.read()['issue']['code'],'PATH_INVALID')

    def test_global_or_invalid_refs_before_store_io_and_unknown_record_values_ignored(self):
        with patch.object(self.store,'get',side_effect=AssertionError('no Store read')):
            self.assertEqual(self.read(checkpoint_manifest={'normalization_mode':'global'})['status'],'OUT_OF_SCOPE')
            for ref in (None,{}, {**self.refs[0],'version':'latest'},{**self.refs[0],'sha256':True}):
                self.assertEqual(self.read(image_ref=ref)['issue']['code'],'INVALID_INPUT')
        self.assertEqual(self.read(metadata_ref=self.refs[1])['issue']['code'],'INVALID_INPUT')
        key=version_key(self.refs[0]['id'],self.refs[0]['version']);record=self.store.get('dataset_versions',key)
        bad=copy.deepcopy(record);bad['manifest']['unknown_root_field']={};bad['manifest']['unknown_root_field']['cycle']=bad['manifest']['unknown_root_field']
        with patch.object(self.store,'get',return_value=bad):self.assertEqual(self.read()['issue']['code'],'REGISTRY_RECORD_INVALID')

    def test_windows_paths_and_input_files_store_unchanged(self):
        for index in range(3):self.manifests[index]['artifact_uri']=self.manifests[index]['artifact_uri'].replace('/','\\');self.save(index)
        self.evidence['source_metadata_path']='assets\\metadata.xml';self.rebind_evidence()
        before=(copy.deepcopy(self.checkpoint),copy.deepcopy(self.refs),{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        with patch.object(self.store,'put',side_effect=AssertionError('read only')):result=self.read()
        self.assertEqual(result['status'],'REGISTERED_FILES_MATCHED_UNVERIFIED')
        self.assertEqual(before,(self.checkpoint,self.refs,{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}))


if __name__=='__main__':unittest.main()
