"""Actual Temp checkpoint + three registry records, no inference/operating IO."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import torch
from app.ml.network import TinyUNet
from app.ml import pinned_scene_normalization as api
import test_registered_per_scene_files as scene_fixtures


def sha(raw):return hashlib.sha256(raw).hexdigest()


class PinnedSceneNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.scene=scene_fixtures.RegisteredPerSceneFilesTests();self.scene.setUp()
        self.addCleanup(self.scene.doCleanups)
        self.store=self.scene.store;self.root=self.scene.root
        self.directory=self.root/'models'/'fixture';self.directory.mkdir(parents=True)
        self.checkpoint=self.directory/'best.pt';self.report_path=self.directory/'report.json'
        self.manifest={**copy.deepcopy(self.scene.checkpoint),'synthetic':True,'fixture_only':'UNTRAINED_CPU_CHECKPOINT'}
        self.saved={'architecture':'tiny_unet','manifest':self.manifest,'state_dict':TinyUNet(6).state_dict()}
        self.model={'id':'fixture','status':'Draft','synthetic':True,'checkpoint_path':'models/fixture/best.pt'}
        self.model_ref={'id':'fixture','version':'model-v1','sha256':''}
        self.report={'model_id':'fixture','training_state':'completed',
            'input_signature':{'normalization_mode':'global','band_names':['REPORT_DECOY']*6},
            'copied_manifest':{'normalization_mode':'global','bands':['NOT_ACTUAL_CHECKPOINT']}}
        self.bind_model()

    def bind_model(self):
        torch.save(self.saved,self.checkpoint)
        self.model_ref['sha256']=sha(self.checkpoint.read_bytes())
        self.model['checkpoint_sha256']=self.model_ref['sha256']
        self.report['checkpoint_sha256']=self.model_ref['sha256']
        raw=json.dumps(self.report).encode();self.report_path.write_bytes(raw);self.report_sha=sha(raw)
        self.model['training_report_sha256']=self.report_sha
        self.model['model_version_declaration']={'schema_version':1,'source':'CALLER_EXPLICIT_REGISTRATION',
            'version':self.model_ref['version'],'checkpoint_sha256':self.model_ref['sha256'],'training_report_sha256':self.report_sha}
        self.store.put('models',self.model)

    def inspect(self,**kwargs):
        args={'store':self.store,'model_ref':self.model_ref,'training_report_sha256':self.report_sha,
            'image_ref':self.scene.refs[0],'evidence_ref':self.scene.refs[1],'metadata_ref':self.scene.refs[2]}
        args.update(kwargs);return api.inspect_pinned_scene_normalization(**args)

    def test_actual_checkpoint_registry_join_exact20_false_approvals_and_no_writes_forward_or_state_load(self):
        before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with (patch.object(self.store,'put',side_effect=AssertionError('no writes')),
              patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')),
              patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state application')),
              patch.object(self.store,'get',wraps=self.store.get) as getter):result=self.inspect()
        self.assertEqual(len(result),20);self.assertEqual(result['status'],'PINNED_SCENE_MATCHED_UNVERIFIED');self.assertIsNone(result['issue'])
        self.assertEqual(getter.call_count,4);self.assertEqual(getter.call_args_list[0].args,('models','fixture'))
        self.assertTrue(result['checkpoint_artifact_verified']);self.assertTrue(result['training_report_artifact_verified'])
        self.assertTrue(result['registry_references_verified']);self.assertTrue(result['artifact_bytes_verified'])
        for field in ('state_dict_verified','raster_header_verified','quality_report_verified','quality_mask_verified',
                      'source_authority_verified','access_authorization_verified','other_lineage_parents_verified',
                      'scientific_accuracy_validated','execution_authorized','workflow_supported'):
            self.assertIs(result[field],False)
        self.assertEqual(before,{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_only_actual_manifest_forwarded_identity_once_no_report_decoy_or_caller_input(self):
        original=api.read_registered_per_scene_files;captured=[]
        def scene_reader(store,manifest,*refs):
            captured.append(manifest)
            self.assertEqual(manifest,self.manifest)
            self.assertEqual(manifest['normalization_mode'],'per_scene_product_metadata')
            return original(store,manifest,*refs)
        with patch.object(api,'read_registered_per_scene_files',scene_reader):result=self.inspect()
        self.assertIs(captured[0],result['model_observation']['checkpoint_manifest']);self.assertEqual(len(captured),1)
        self.assertEqual(result['status'],'PINNED_SCENE_MATCHED_UNVERIFIED')
        with self.assertRaises(TypeError):self.inspect(checkpoint_manifest=self.manifest)

    def test_model_failure_no_scene_calls_or_scene_record_reads_and_partial_flags(self):
        for path in (self.checkpoint,self.report_path):
            raw=path.read_bytes();path.write_bytes(raw+b'bad')
            with (patch.object(api,'read_registered_per_scene_files',side_effect=AssertionError('scene forbidden')) as scene,
                  patch.object(self.store,'get',wraps=self.store.get) as getter):result=self.inspect(image_ref=object(),evidence_ref=object(),metadata_ref=object())
            self.assertEqual(result['status'],'MODEL_BLOCKED');scene.assert_not_called();self.assertEqual(getter.call_count,1)
            self.assertIsNone(result['scene_observation']);self.assertFalse(result['artifact_bytes_verified'])
            self.assertEqual(result['checkpoint_artifact_verified'],path==self.report_path)
            path.write_bytes(raw)

    def test_global_actual_checkpoint_out_of_scope_scene_refs_unaccessed(self):
        self.manifest['normalization_mode']='global';self.bind_model()
        with patch.object(self.store,'get',wraps=self.store.get) as getter:
            result=self.inspect(image_ref=object(),evidence_ref=object(),metadata_ref=object())
        self.assertEqual(result['status'],'OUT_OF_SCOPE');self.assertIsNone(result['issue']);self.assertEqual(getter.call_count,1)
        self.assertEqual(result['scene_observation']['status'],'OUT_OF_SCOPE')
        self.assertTrue(result['checkpoint_artifact_verified']);self.assertFalse(result['registry_references_verified']);self.assertFalse(result['artifact_bytes_verified'])

    def test_scene_failure_keeps_model_success_and_partial_registry_observation(self):
        del self.scene.manifests[0]['source']['scene_id'];self.scene.save(0)
        result=self.inspect();self.assertEqual(result['status'],'SCENE_BLOCKED')
        self.assertTrue(result['checkpoint_artifact_verified']);self.assertTrue(result['training_report_artifact_verified'])
        self.assertTrue(result['registry_references_verified']);self.assertFalse(result['artifact_bytes_verified'])
        self.assertEqual(result['scene_observation']['issue']['code'],'SCENE_DECLARATION_MISSING')

    def test_each_scene_file_mutation_pin_and_lineage_failure_cannot_become_ready(self):
        for path in (self.scene.image,self.scene.evidence_path,self.scene.metadata):
            raw=path.read_bytes();path.write_bytes(raw+b'tampered');result=self.inspect()
            self.assertEqual(result['status'],'SCENE_BLOCKED');self.assertFalse(result['artifact_bytes_verified']);self.assertFalse(result['workflow_supported'])
            path.write_bytes(raw)
        bad={**self.scene.refs[0],'sha256':'0'*64}
        self.assertEqual(self.inspect(image_ref=bad)['status'],'SCENE_BLOCKED')
        self.scene.manifests[1]['lineage']=[];self.scene.save(1)
        self.assertEqual(self.inspect()['scene_observation']['issue']['code'],'LINEAGE_BINDING_INVALID')

    def test_checkpoint_band_mismatch_is_real_model_join_failure_after_registry(self):
        self.manifest['band_names']=['WRONG']*6;self.bind_model()
        result=self.inspect();self.assertEqual(result['model_observation']['status'],'MANIFEST_BOUND_UNVERIFIED')
        self.assertEqual(result['status'],'SCENE_BLOCKED');self.assertFalse(result['artifact_bytes_verified'])
        self.assertTrue(result['registry_references_verified'])

    def test_registry_side_change_between_model_and_scene_is_detected_without_retry(self):
        original=api.read_registered_per_scene_files
        def changed(*args,**kwargs):
            self.scene.metadata.write_bytes(b'changed after model observation')
            return original(*args,**kwargs)
        with patch.object(api,'read_registered_per_scene_files',changed) as _:
            result=self.inspect()
        self.assertEqual(result['status'],'SCENE_BLOCKED');self.assertTrue(result['checkpoint_artifact_verified'])
        self.assertFalse(result['artifact_bytes_verified'])

    def test_input_and_original_nested_results_preserved_without_promoting_nested_approvals(self):
        before=copy.deepcopy((self.model_ref,self.scene.refs,self.manifest))
        result=self.inspect();self.assertEqual(before,(self.model_ref,self.scene.refs,self.manifest))
        model=result['model_observation'];scene=result['scene_observation']
        with patch.object(api,'read_pinned_model_checkpoint_manifest',return_value=model),patch.object(api,'read_registered_per_scene_files',return_value=scene):
            again=self.inspect()
        self.assertIs(again['model_observation'],model);self.assertIs(again['scene_observation'],scene)
        self.assertFalse(again['state_dict_verified']);self.assertFalse(again['execution_authorized'])

    def test_dependency_exceptions_are_sanitized_with_stage_status_and_no_retry(self):
        with (patch.object(api,'read_pinned_model_checkpoint_manifest',side_effect=RuntimeError('private path secret')) as model,
              patch.object(api,'read_registered_per_scene_files',side_effect=AssertionError('no scene')) as scene):
            result=self.inspect();self.assertEqual(result['status'],'MODEL_BLOCKED');model.assert_called_once();scene.assert_not_called()
            self.assertNotIn('secret',str(result))
        with patch.object(api,'read_registered_per_scene_files',side_effect=RuntimeError('private path secret')) as scene:
            result=self.inspect();self.assertEqual(result['status'],'SCENE_BLOCKED');scene.assert_called_once();self.assertNotIn('secret',str(result))
            self.assertTrue(result['checkpoint_artifact_verified']);self.assertFalse(result['artifact_bytes_verified'])


if __name__=='__main__':unittest.main()
