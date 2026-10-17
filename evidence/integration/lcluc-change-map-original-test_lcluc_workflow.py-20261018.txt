"""TempStore fabricated admission boundary + genuine tiny CPU inference only."""
import copy
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
import torch

from backend.app import lcluc_workflow as workflow
from backend.app.dataset_registry import register_version
from backend.app.ml.network import TinyUNet
from backend.app.ml.raster import CLASS_NAMES
from backend.app.store import Store


class LclucWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root)
        self.model_dir = self.root/'models'/'fixture';self.model_dir.mkdir(parents=True)
        self.checkpoint = self.model_dir/'best.pt'
        self.signature = {'bands':[1,2,3], 'band_names':['blue','green','red'], 'scale':.0001, 'offset':0,
                          'patch_size':16, 'class_names':CLASS_NAMES, 'version':'fixture-training-v1',
                          'normalization_mode':'global', 'synthetic':False,
                          'reference_kind':'worldcover_weak_label', 'fixture_only':'FABRICATED_ADMISSION_NOT_SCIENTIFIC_APPROVAL'}
        self.save_checkpoint()
        training = self.model_dir/'report.json';training.write_text('{"fixture_only":true}',encoding='utf-8')
        self.model = {'id':'fixture-model','status':'Deployed','independent_evaluation':True,'synthetic':False,
                      'reference_kind':'worldcover_weak_label','checkpoint_path':'models/fixture/best.pt',
                      'checkpoint_sha256':self.sha(self.checkpoint),'training_report_sha256':self.sha(training),
                      'evaluation':{'reference_kind':'expert_independent','checkpoint_sha256':self.sha(self.checkpoint),
                                    'fixture_only':'MOCK_APPROVAL_BOUNDARY_NOT_INDEPENDENT_SCIENCE'}}
        self.model['model_version_declaration']={'schema_version':1,'source':'CALLER_EXPLICIT_REGISTRATION','version':'v1',
              'checkpoint_sha256':self.model['checkpoint_sha256'],'training_report_sha256':self.model['training_report_sha256']}
        self.store.put('models',self.model)
        self.request={'schema_version':1,'capability':workflow.CAPABILITY,'trace_id':'trace-fixture','idempotency_key':'key-fixture',
                      'model_ref':{'id':'fixture-model','version':'v1','sha256':self.model['checkpoint_sha256']},'images':[]}
        self.input_manifests=[]
        for year in (2020,2021):
            image=self.root/f'image-{year}.tif'
            with rasterio.open(image,'w',driver='GTiff',width=16,height=16,count=3,dtype='uint16',crs='EPSG:3857',
                               transform=from_origin(100,200,10,10),nodata=0) as dataset:
                dataset.write(np.full((3,16,16),100+year-2020,dtype='uint16'))
                dataset.descriptions=tuple(self.signature['band_names'])
            quality=self.root/f'quality-{year}.json';quality.write_text('{"fixture_only":"MOCK_VALIDATED_METADATA"}',encoding='utf-8')
            manifest={'schema_version':'0.2.0','dataset_id':f'fixture-input-{year}','version':'v1',
                      'source':{'institution':'synthetic fixture','product':'mock admission raster','license':'test only'},
                      'data_type':'raster','spatial':{'bbox':[100,40,101,41],'crs':'EPSG:4326'},
                      'temporal':{'start':f'{year}-01-01T00:00:00Z','end':f'{year}-12-31T00:00:00Z','calendar':'gregorian'},
                      'quality_status':'VALIDATED','quality_report_ref':quality.name,'access_class':'PUBLIC',
                      'sha256':self.sha(image),'artifact_uri':image.name,'lineage':[]}
            register_version(self.store,manifest)
            self.input_manifests.append(manifest)
            self.request['images'].append({'year':year,'input_ref':{'id':manifest['dataset_id'],'version':'v1','sha256':manifest['sha256']},
                                           'quality_report_sha256':self.sha(quality)})

    def tearDown(self):
        self.temp.cleanup()

    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()

    def save_checkpoint(self):
        model=TinyUNet(3)
        with torch.no_grad():
            for parameter in model.parameters():parameter.zero_()
            model.head.bias[1]=1
        torch.save({'architecture':'tiny_unet','state_dict':model.state_dict(),'manifest':self.signature},self.checkpoint)

    def gate_reject(self):
        runner=unittest.mock.Mock(side_effect=AssertionError('runner must not execute'))
        result=workflow.execute_lcluc_workflow(self.store,self.request,_runner=runner)
        self.assertEqual(result['status'],'BLOCKED');runner.assert_not_called()
        self.assertEqual(self.store.list(workflow.KIND),[])
        self.assertFalse((self.root/'results').exists())
        return result

    def update_model(self,**changes):
        self.model.update(changes);self.store.put('models',self.model)

    def test_actual_cpu_inference_change_report_trace_and_hashed_artifacts(self):
        inputs={p:p.read_bytes() for p in self.root.glob('image*')}
        checkpoint=self.checkpoint.read_bytes();request=copy.deepcopy(self.request)
        result=workflow.execute_lcluc_workflow(self.store,self.request)
        self.assertEqual(result['status'],'SUCCEEDED',result)
        self.assertEqual(result['trace_id'],'trace-fixture')
        self.assertEqual(result['request_snapshot']['model_ref'],self.request['model_ref'])
        self.assertEqual(result['request_snapshot']['images'],self.request['images'])
        self.assertNotIn('idempotency_key',result['request_snapshot'])
        self.assertFalse(result['scientific_accuracy_validated']);self.assertFalse(result['standard_gmais_result'])
        report=json.loads((self.root/result['report_path']).read_text(encoding='utf-8'))
        self.assertEqual(report['years'],[2020,2021]);self.assertIn('2020-2021',report['changes'])
        self.assertEqual(report['changes']['2020-2021']['valid_pixels'],256)
        self.assertEqual(len(result['artifacts']),7)
        for item in result['artifacts']:self.assertEqual(self.sha(self.root/item['path']),item['sha256'])
        with patch.object(workflow,'_gate',side_effect=AssertionError('replay must not run admission')):
            replay=workflow.execute_lcluc_workflow(self.store,self.request)
        self.assertTrue(replay['replayed']);self.assertEqual(replay['id'],result['id'])
        self.assertEqual(inputs,{p:p.read_bytes() for p in inputs});self.assertEqual(checkpoint,self.checkpoint.read_bytes())
        self.assertEqual(request,self.request)

    def test_invalid_shape_versions_bool_year_and_raw_paths_rejected_without_claim(self):
        for change in ({'schema_version':True},{'capability':'external-agent'},{'trace_id':'../escape'},{'image_path':'arbitrary'}):
            request={**self.request,**change}
            with self.assertRaises(workflow.WorkflowError):workflow.execute_lcluc_workflow(self.store,request)
        for year in (True,2020.0,1899):
            request=copy.deepcopy(self.request);request['images'][0]['year']=year
            with self.assertRaises(workflow.WorkflowError):workflow.execute_lcluc_workflow(self.store,request)
        request=copy.deepcopy(self.request);request['model_ref']['version']=' latest '
        with self.assertRaises(workflow.WorkflowError):workflow.execute_lcluc_workflow(self.store,request)
        request=copy.deepcopy(self.request);request['model_ref']['id']='https://host/model?secret=token'
        with self.assertRaises(workflow.WorkflowError):workflow.execute_lcluc_workflow(self.store,request)
        self.assertEqual(self.store.list(workflow.KIND),[])

    def test_model_deployment_evaluation_version_checkpoint_and_training_hash_gates(self):
        original=copy.deepcopy(self.model)
        for change in ({'status':'Draft'},{'independent_evaluation':1},{'evaluation':{}},{'model_version_declaration':None},
                       {'training_report_sha256':'a'*64},{'synthetic':True},{'synthetic':None}):
            self.model=copy.deepcopy(original);self.update_model(**change);self.gate_reject()
        self.model=original;self.update_model()
        self.checkpoint.write_bytes(b'changed-checkpoint-secret-path')
        result=self.gate_reject();self.assertNotIn('secret',str(result))

    def test_missing_synthetic_false_per_scene_and_unsupported_architecture_block(self):
        for field,value in (('synthetic',True),('synthetic',None),('reference_kind','synthetic_fixture_only'),('normalization_mode','per_scene_product_metadata'),('bands',[True,2,3]),('scale',0)):
            original=copy.deepcopy(self.signature);self.signature[field]=value;self.save_checkpoint()
            sha=self.sha(self.checkpoint);self.model['checkpoint_sha256']=sha;self.model['evaluation']['checkpoint_sha256']=sha
            self.model['model_version_declaration']['checkpoint_sha256']=sha;self.request['model_ref']['sha256']=sha
            self.update_model();self.gate_reject();self.signature=original
        self.save_checkpoint()
        saved=torch.load(self.checkpoint,weights_only=True);saved['architecture']='unetplusplus'
        torch.save(saved,self.checkpoint);sha=self.sha(self.checkpoint)
        self.model['checkpoint_sha256']=sha;self.model['evaluation']['checkpoint_sha256']=sha
        self.model['model_version_declaration']['checkpoint_sha256']=sha;self.request['model_ref']['sha256']=sha
        self.update_model();self.gate_reject()

    def test_registry_access_quality_year_and_quality_report_pin_fail_closed(self):
        first=self.input_manifests[0]
        from backend.app.dataset_registry import version_key,canonical_manifest
        original=self.store.get('dataset_versions',version_key(first['dataset_id'],'v1'))
        for field,value in (('access_class','RESTRICTED'),('quality_status','RAW'),('data_type','document')):
            record=copy.deepcopy(original);record['manifest'][field]=value
            record['manifest'],record['manifest_sha256']=canonical_manifest(record['manifest']);self.store.put('dataset_versions',record)
            self.gate_reject()
        self.store.put('dataset_versions',original)
        self.request['images'][0]['year']=2019;self.gate_reject();self.request['images'][0]['year']=2020
        self.request['images'][0]['quality_report_sha256']='a'*64;self.gate_reject()

    def test_header_memory_checkpoint_file_and_band_description_limits(self):
        with patch.object(workflow,'MAX_READ_ESTIMATE',1):self.gate_reject()
        with patch.object(workflow,'MAX_CHECKPOINT_BYTES',1):self.gate_reject()
        image=self.root/self.input_manifests[0]['artifact_uri']
        with rasterio.open(image,'r+') as raster:raster.descriptions=('red','green','blue')
        # Preserve explicit Registry consistency, isolate the semantic band gate.
        from backend.app.dataset_registry import canonical_manifest,version_key
        record=self.store.get('dataset_versions',version_key('fixture-input-2020','v1'))
        record['manifest']['sha256']=self.sha(image);record['manifest'],record['manifest_sha256']=canonical_manifest(record['manifest'])
        self.store.put('dataset_versions',record);self.request['images'][0]['input_ref']['sha256']=record['manifest']['sha256']
        self.assertEqual(self.gate_reject()['issue'],'RASTER_BAND_SIGNATURE_MISMATCH')

    def test_same_key_different_payload_conflicts_without_second_runner(self):
        with patch.object(workflow,'_gate',return_value=({},{})):
            first=workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_: (_ for _ in ()).throw(RuntimeError('private path')))
            self.assertEqual(first['status'],'FAILED');self.assertEqual(first['issue'],'LOCAL_EXECUTION_FAILED')
            changed=copy.deepcopy(self.request);changed['trace_id']='different-trace'
            with self.assertRaisesRegex(workflow.WorkflowError,'IDEMPOTENCY_CONFLICT'):
                workflow.execute_lcluc_workflow(self.store,changed,_runner=lambda *_:self.fail('second runner'))

    def test_concurrent_claim_once_running_replay_failure_no_automatic_retry(self):
        started,release=threading.Event(),threading.Event();calls=[]
        def runner(*_):
            calls.append(1);started.set();release.wait(5);raise RuntimeError('private-secret')
        with patch.object(workflow,'_gate',return_value=({},{})),ThreadPoolExecutor(max_workers=2) as pool:
            future=pool.submit(workflow.execute_lcluc_workflow,self.store,self.request,_runner=runner)
            self.assertTrue(started.wait(5))
            duplicate=workflow.execute_lcluc_workflow(self.store,self.request,_runner=runner)
            self.assertEqual(duplicate['status'],'RUNNING');self.assertTrue(duplicate['replayed'])
            release.set();failed=future.result()
            replay=workflow.execute_lcluc_workflow(self.store,self.request,_runner=runner)
        self.assertEqual(len(calls),1);self.assertEqual(failed['status'],'FAILED');self.assertTrue(replay['replayed'])
        self.assertNotIn('private',str(failed))

    def test_gate_change_after_claim_and_partial_files_are_not_retried(self):
        with patch.object(workflow,'_gate',side_effect=[({}, {'model':'before'}),({}, {'model':'after'})]):
            result=workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:self.fail('gate changed'))
        self.assertEqual(result['status'],'FAILED');self.assertEqual(result['issue'],'ADMISSION_CHANGED_AFTER_CLAIM')
        self.request['idempotency_key']='partial-key'
        def partial(payload,root):
            path=root/'results'/payload['output_id'];path.mkdir(parents=True);(path/'partial.txt').write_text('preserve')
            raise OSError('private-path')
        result=workflow.execute_lcluc_workflow(self.store,self.request,_runner=partial)
        self.assertEqual(result['status'],'FAILED')
        partials=list((self.root/'results').rglob('partial.txt'));self.assertEqual(len(partials),1)
        replay=workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:self.fail('retry'))
        self.assertTrue(replay['replayed']);self.assertEqual(partials[0].read_text(),'preserve')

    def test_successful_report_tampering_rejects_replay_without_rerun(self):
        result=workflow.execute_lcluc_workflow(self.store,self.request);self.assertEqual(result['status'],'SUCCEEDED')
        (self.root/result['report_path']).write_text('changed-output',encoding='utf-8')
        with self.assertRaisesRegex(workflow.WorkflowError,'STORED_OUTPUT_CHANGED'):
            workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:self.fail('rerun'))

    def test_strict_json_and_cli_require_explicit_execute_and_data_root(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1.0}',b'x'*16385):
            with self.assertRaises(workflow.WorkflowError):workflow.strict_request_json(raw)
        path=Path(__file__).resolve().parents[1]/'scripts/run_lcluc_workflow.py'
        spec=importlib.util.spec_from_file_location('workflow_cli',path);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        with patch('sys.argv',['workflow','--data-root',str(self.root),'--request','unused']),patch.object(cli,'Store',side_effect=AssertionError('store')) as store,patch('sys.stderr',io.StringIO()):
            with self.assertRaises(SystemExit):cli.main()
            store.assert_not_called()

    def test_growing_stream_stops_after_bound_plus_one(self):
        path=self.root/'small.bin';path.write_bytes(b'a')
        class Growing(io.BytesIO):
            def close(self):self.bytes_read=self.tell()  # Keep counter inspectable.
        stream=Growing(b'0123456789')
        with patch.object(Path,'open',return_value=stream):
            with self.assertRaisesRegex(workflow.WorkflowError,'FILE_LIMIT_OR_INTEGRITY'):
                workflow._file(path,3)
        self.assertEqual(stream.bytes_read,4)

    def test_output_namespace_retarget_is_blocked_without_runner(self):
        original=Path.resolve
        def retarget(path,*args,**kwargs):
            if path.parent.name=='lcluc-workflows':return self.root/'wrong-output'/path.name
            return original(path,*args,**kwargs)
        with patch.object(Path,'resolve',retarget):
            self.assertEqual(self.gate_reject()['issue'],'OUTPUT_NAMESPACE_UNAVAILABLE')

    def test_nonfinite_runner_report_cannot_be_success(self):
        with patch.object(workflow,'_gate',return_value=({},{})):
            result=workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:{'invalid':float('inf')})
        self.assertEqual(result['status'],'FAILED');self.assertEqual(result['issue'],'LOCAL_EXECUTION_FAILED')

    def test_initial_store_error_is_sanitized_without_runner(self):
        with patch.object(self.store,'get',side_effect=OSError('private-token-and-path')):
            with self.assertRaisesRegex(workflow.WorkflowError,'^LOCAL_WORKFLOW_UNAVAILABLE$'):
                workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:self.fail('runner'))

    def test_concurrent_claim_between_initial_miss_and_admission_replays_existing(self):
        _,digest=workflow._request(self.request)
        identifier=hashlib.sha256(self.request['idempotency_key'].encode()).hexdigest()
        def concurrent_claim(*_):
            self.store.put(workflow.KIND,{'id':identifier,'status':'RUNNING','request_sha256':digest})
            raise workflow.WorkflowError('OUTPUT_NAMESPACE_UNAVAILABLE')
        with patch.object(workflow,'_gate',side_effect=concurrent_claim):
            result=workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:self.fail('second runner'))
        self.assertEqual(result['status'],'RUNNING');self.assertTrue(result['replayed'])

    def test_claim_race_replay_hashing_occurs_after_transaction_is_released(self):
        _,digest=workflow._request(self.request)
        identifier=hashlib.sha256(self.request['idempotency_key'].encode()).hexdigest()
        self.store.put(workflow.KIND,{'id':identifier,'status':'RUNNING','request_sha256':digest})
        native_connect=self.store.connect;native_existing=workflow._existing;active=[]
        @contextmanager
        def connect():
            with native_connect() as connection:
                active.append(1)
                try:yield connection
                finally:active.pop()
        def existing(*args):
            self.assertFalse(active)
            return native_existing(*args)
        with patch.object(self.store,'get',side_effect=KeyError),patch.object(self.store,'connect',connect),patch.object(workflow,'_gate',return_value=({},{})),patch.object(workflow,'_existing',side_effect=existing):
            result=workflow.execute_lcluc_workflow(self.store,self.request,_runner=lambda *_:self.fail('runner'))
        self.assertEqual(result['status'],'RUNNING');self.assertTrue(result['replayed'])


if __name__=='__main__':unittest.main()
