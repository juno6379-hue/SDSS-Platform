"""200 단일 coordinator 경계. Temp 실제 원장/2worker, provider/199 inventory Mock."""
import copy
from contextlib import ExitStack,redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import os
import subprocess
import sys
from unittest.mock import patch

import test_deficit_candidate_guard as fixtures
import app.data.deficit_candidate_guard as helper
from scripts import collect_deficit_guarded as subject


class CollectDeficitGuardedTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.CandidateFixture(methodName='runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.output=self.root/'data/first-group-training-esri-v1'
        for leaf in ('sources','patches'):(self.output/leaf).mkdir(parents=True,exist_ok=True)
        config=json.loads((subject.ROOT/'configs/collection.example.json').read_text(encoding='utf-8'))
        config['aois']=self.fixture.config['aois'];self.fixture.config=config
        self.fixture.save('config',config)
        self.fixture.request['config_ref']=self.fixture.ref('config')
        self.fixture.proposal['config_sha256']=self.fixture.sha('config')
        self.pending={f'old-pending-{i}':{'status':'pending','reserved_bytes':68157440,'charged_bytes':68157440,'config_sha256':str(i)*64} for i in (1,2)}
        self.fixture.ledger.update(version=1,historical_ledgers=[],historical_charged_bytes=0,
             combined_maximum_bytes=4*1024**3,new_charged_bytes=136314880,batches=copy.deepcopy(self.pending))
        self.fixture.save('ledger',self.fixture.ledger);self.fixture.request['ledger_ref']=self.fixture.ref('ledger')
        self.original={'patch_id':'old-row','province':'banten','year':'2024','split':'val','scene_id':'old-scene',
             'quality_status':'quality_insufficient','spatial_location_id':'banten/old/r0-c0','sample_class_coverage':{'1':100}}
        self.fixture.source['scenes']=[copy.deepcopy(self.original)]
        self.fixture.save('source',self.fixture.source);self.fixture.request['current_manifest_ref']=self.fixture.ref('source')
        self.fixture.candidate['source_snapshot_sha256']=self.fixture.sha('source')
        self.fixture.proposal['source_sha256']=self.fixture.sha('source');self.fixture.update_proposal()
        self.request=copy.deepcopy(self.fixture.request)
        self.lock=self.root/'data/first-group-training-budget/global-ledger.execution.lock'
        self.lock.parent.mkdir(parents=True,exist_ok=True)
        self.addCleanup(subject.service.configure_request_circuit,None)
        self.addCleanup(subject.service.configure_request_spacing,0)

    def two_jobs(self):
        from pyproj import Transformer
        second=copy.deepcopy(self.fixture.candidate)
        second.update(spatial_window_id='centers182-banten-second',lon=106.3)
        forward=Transformer.from_crs(4326,second['grid_crs'],always_xy=True)
        inverse=Transformer.from_crs(second['grid_crs'],4326,always_xy=True)
        x,y=forward.transform(second['lon'],second['lat'])
        points=[inverse.transform(a,b) for a,b in ((x-5120,y+5120),(x+5120,y+5120),(x+5120,y-5120),(x-5120,y-5120))]
        second['bbox']=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
        self.fixture.proposal['candidates'].append(second);self.fixture.update_proposal()
        self.request['proposal_ref']=self.fixture.ref('proposal')
        self.request['selected'].append({'spatial_window_id':second['spatial_window_id'],'year':2024})
        self.request['maximum_batches']=2

    def proof_stack(self):
        stack=ExitStack()
        stack.enter_context(patch.object(helper,'inspect_targeted_inventory',return_value=copy.deepcopy(self.fixture.proof)))
        stack.enter_context(patch.object(helper,'_physical_inventory',return_value=copy.deepcopy(self.fixture.physical)))
        return stack

    def execute(self,collect=None,rows=None,**options):
        with self.proof_stack(),patch.object(subject,'collect_windows',side_effect=collect or self.collect) as remote, \
             patch.object(subject,'materialize_patches',return_value=rows or []) as materialize:
            value=subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request),execute=True,**options)
        return value,remote,materialize

    def collect(self,config,directory,**kwargs):
        self.assertTrue(kwargs['execute']);self.assertTrue(self.lock.exists())
        self.assertIsInstance(kwargs['collection_guard'],helper.DeficitCandidateLiveGuard)
        self.assertEqual(config['window_size'],1024)
        self.assertIn('priority_source_classes',kwargs['selection_context'])
        kwargs['collection_guard'].b02_checked=True
        (directory/'window-state.json').write_text(json.dumps({'http_body_bytes':97}),encoding='utf-8')
        return {'scenes':[],'batch_circuit_breaker':None}

    def row(self):
        identifier=self.request['selected'][0]['spatial_window_id']
        return {'patch_id':'new','province':'banten','year':2024,'split':'val','scene_id':'new-scene',
             'spatial_location_id':f'banten/{identifier}/r0-c0','quality_status':'quality_eligible','sample_class_coverage':{'1':1000}}

    def test_dry_run_never_constructs_ledger_lock_outputs_or_collects(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.proof_stack(),patch.object(subject,'CollectionLedger') as ledger,patch.object(subject,'collect_windows') as remote:
            out=subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request))
        self.assertFalse(out['executed']);ledger.assert_not_called();remote.assert_not_called()
        self.assertFalse(self.lock.exists())
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_existing_lock_rejected_without_proof_or_writes(self):
        self.lock.write_text('prior-owner',encoding='utf-8')
        with patch.object(subject,'prepare_deficit_candidate_jobs') as prepare:
            with self.assertRaises(FileExistsError):subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request),execute=True)
        prepare.assert_not_called();self.assertEqual(self.lock.read_text(),'prior-owner')

    def test_wrong_digest_fails_before_helper_and_cleans_owned_lock(self):
        with patch.object(subject,'prepare_deficit_candidate_jobs') as prepare:
            with self.assertRaisesRegex(ValueError,'DEFICIT_REQUEST_PIN_MISMATCH'):
                subject.run_deficit_guarded(self.root,self.request,'f'*64,execute=True)
        prepare.assert_not_called();self.assertFalse(self.lock.exists())

    def test_helper_proof_is_recomputed_under_global_lock(self):
        actual=subject.prepare_deficit_candidate_jobs
        def observed(*args):
            self.assertTrue(self.lock.exists())
            self.assertEqual(self.lock.read_text(),str(subject.os.getpid()))
            return actual(*args)
        with patch.object(subject,'prepare_deficit_candidate_jobs',side_effect=observed) as prepare:
            result,_,_=self.execute()
        self.assertEqual(prepare.call_count,1);self.assertTrue(result['executed'])

    def test_failed_local_check_only_reports_bounded_uppercase_issue(self):
        variants=[(False,'CENTER_INPUT_UNAVAILABLE','DEFICIT_LOCAL_PROOF_INVALID_CENTER_INPUT_UNAVAILABLE'),
                  (True,'COORDINATOR_NOT_CONNECTED','DEFICIT_LOCAL_PROOF_INVALID'),
                  (False,'C:/private/token-secret','DEFICIT_LOCAL_PROOF_INVALID'),
                  (False,'A'*49,'DEFICIT_LOCAL_PROOF_INVALID')]
        for passed,issue,expected in variants:
            with self.subTest(passed=passed,issue=issue),patch.object(subject,'prepare_deficit_candidate_jobs',
                  return_value={'local_checks_passed':passed,'issue':issue}):
                with self.assertRaises(ValueError) as caught:
                    subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request))
            self.assertEqual(str(caught.exception),expected)

    def test_isolated_cli_bootstrap_reaches_real_delayed_inventory_import(self):
        # Launch the actual CLI file, with Temp cwd and no ROOT on PYTHONPATH.
        # sitecustomize mocks only the request reader and helper's orchestration;
        # the delayed package import and empty Temp physical inventory are real.
        hook=r'''
import os,sys,json,hashlib
from pathlib import Path
root=Path(os.environ['DEFICIT208_SOURCE_ROOT']);temp=Path(os.environ['DEFICIT208_TEMP_ROOT'])
sys.path.insert(0,str(root/'backend'))
import app.ml.per_scene_normalization_files as files
import app.data.deficit_candidate_guard as helper
def snapshot(root,path,maximum,field,copy_bytes=False):
    assert field=='request','operational read forbidden'
    return (hashlib.sha256(b'{}').hexdigest(),b'{}') if copy_bytes else (hashlib.sha256(b'{}').hexdigest(),None)
files._snapshot=snapshot
def prepare(root,request):
    try:
        physical=helper._physical_inventory(temp,{'scenes':[]},{'batches':{}})
        assert physical['physical_patch_count']==0
        issue='TEMP_BOOTSTRAP_IMPORT_VERIFIED'
    except ModuleNotFoundError:
        issue='CENTER_INPUT_UNAVAILABLE'
    return {'local_checks_passed':False,'issue':issue}
helper.prepare_deficit_candidate_jobs=prepare
'''
        with tempfile.TemporaryDirectory() as directory:
            temp=Path(directory)
            for leaf in ('data/first-group-training-esri-v1/patches','data/first-group-training-esri-v1/sources'):
                (temp/leaf).mkdir(parents=True,exist_ok=True)
            (temp/'sitecustomize.py').write_text(hook,encoding='utf-8')
            environment=dict(os.environ)
            environment.update(PYTHONPATH=str(temp)+os.pathsep+str(subject.ROOT/'.runtime'),PYTHONIOENCODING='utf-8',
                DEFICIT208_SOURCE_ROOT=str(subject.ROOT),DEFICIT208_TEMP_ROOT=str(temp))
            run=subprocess.run([sys.executable,str(subject.ROOT/'scripts/collect_deficit_guarded.py'),
                '--request','evidence/integration/isolated208-request.json','--expected-request-sha256',subject.digest({})],
                cwd=temp,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['issue'],'DEFICIT_LOCAL_PROOF_INVALID_TEMP_BOOTSTRAP_IMPORT_VERIFIED',run.stdout)
        self.assertFalse(result['execute_requested']);self.assertFalse(result['execution_started'])

    def test_inventory_failure_diagnostic_reaches_actual_isolated_cli_stdout(self):
        hook=r'''
import os,sys,hashlib
from pathlib import Path
root=Path(os.environ['INVENTORY218_SOURCE_ROOT'])
sys.path.insert(0,str(root/'backend'))
import app.ml.per_scene_normalization_files as files
import app.data.deficit_candidate_guard as helper
def snapshot(root,path,maximum,field,copy_bytes=False):
    assert field=='request','operational read forbidden'
    return hashlib.sha256(b'{}').hexdigest(),b'{}'
files._snapshot=snapshot
def prepare(root,request):
    return {'local_checks_passed':False,'issue':'CENTER_FULL_INVENTORY_NOT_VERIFIED',
        'inventory_diagnostic':{'resource_profile':'DEFICIT_LOCAL_SUPPORT_3G_V1',
          'max_files':10000,'max_support_bytes':3*1024**3,'issue':'INVENTORY_LIMIT',
          'current_asset':'private/path',
          'observed':{'enumerated_files':1515,'support_files':1275,'support_bytes':2166734413,
                      'secret':'private/path'}}}
helper.prepare_deficit_candidate_jobs=prepare
'''
        with tempfile.TemporaryDirectory() as directory:
            temp=Path(directory);(temp/'sitecustomize.py').write_text(hook,encoding='utf-8')
            environment=dict(os.environ)
            environment.update(PYTHONPATH=str(temp)+os.pathsep+str(subject.ROOT/'.runtime'),
                PYTHONIOENCODING='utf-8',INVENTORY218_SOURCE_ROOT=str(subject.ROOT))
            run=subprocess.run([sys.executable,str(subject.ROOT/'scripts/collect_deficit_guarded.py'),
                '--request','evidence/integration/isolated218-request.json',
                '--expected-request-sha256',subject.digest({})],cwd=temp,env=environment,
                capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['issue'],'DEFICIT_LOCAL_PROOF_INVALID_CENTER_FULL_INVENTORY_NOT_VERIFIED')
        self.assertEqual(result['inventory_diagnostic']['observed']['support_bytes'],2166734413)
        self.assertEqual(result['inventory_diagnostic']['issue'],'INVENTORY_LIMIT')
        self.assertFalse(result['execution_started']);self.assertFalse(result['execute_requested'])
        self.assertNotIn('private',run.stdout)

    def test_failed_inventory_diagnostic_cannot_authorize_reservation_and_lock_releases(self):
        before={p:p.read_bytes() for p in self.fixture.paths.values()}
        diagnostic=helper._inventory_diagnostic({'issue':'INVENTORY_LIMIT','observed':{
            'support_bytes':3*1024**3+1}})
        with patch.object(subject,'prepare_deficit_candidate_jobs',return_value={
             'local_checks_passed':False,'issue':'CENTER_FULL_INVENTORY_NOT_VERIFIED',
             'inventory_diagnostic':diagnostic}),patch.object(subject,'CollectionLedger') as ledger, \
             patch.object(subject,'collect_windows') as worker:
            with self.assertRaises(subject.DeficitLocalProofFailure) as caught:
                subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request),execute=True)
        self.assertEqual(caught.exception.inventory_diagnostic,diagnostic)
        ledger.assert_not_called();worker.assert_not_called();self.assertFalse(self.lock.exists())
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_inventory_diagnostic_is_optional_and_never_reports_contaminated_success(self):
        diagnostic=helper._inventory_diagnostic({'issue':'INVENTORY_LIMIT'})
        for passed,value in ((True,diagnostic),(False,{'resource_profile':'private/path'})):
            with patch.object(subject,'prepare_deficit_candidate_jobs',return_value={
                 'local_checks_passed':passed,'issue':'COORDINATOR_NOT_CONNECTED',
                 'inventory_diagnostic':value}):
                with self.assertRaises(subject.DeficitLocalProofFailure) as caught:
                    subject.validate_request(self.root,self.request,subject.digest(self.request))
            self.assertIsNone(caught.exception.inventory_diagnostic)

    def test_measured_settlement_preserves_pending_records_and_source_prefix(self):
        result,remote,materialize=self.execute(rows=[self.row()])
        self.assertEqual(remote.call_count,1);materialize.assert_called_once()
        self.assertEqual(result['execution']['submitted_batches'],1)
        self.assertEqual(result['batches'][0]['charged_bytes'],97)
        state=json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))
        for k,v in self.pending.items():self.assertEqual(state['batches'][k],v)
        self.assertEqual(state['new_charged_bytes'],136314880+97)
        aggregate=json.loads(self.fixture.paths['source'].read_text(encoding='utf-8'))
        self.assertEqual(aggregate['scenes'],[self.original,self.row()])
        self.assertFalse(self.lock.exists());self.assertFalse(result['learning_ready'])
        self.assertEqual(result['execution_progress']['settlement_status'],'ALL_RESERVED_SETTLED')

    def test_two_workers_share_scene_and_window_claims_and_preserve_old_files(self):
        self.two_jobs();barrier=threading.Barrier(2);guards=[]
        model=self.root/'data/model-preserved.bin';model.write_bytes(b'original model')
        partial=self.output/'sources/old-pending-1';partial.mkdir();(partial/'partial.bin').write_bytes(b'original partial')
        def collect(config,directory,**kwargs):
            guards.append(kwargs['collection_guard']);barrier.wait(timeout=10)
            return self.collect(config,directory,**kwargs)
        with patch.object(subject.service,'configure_request_spacing',wraps=subject.service.configure_request_spacing) as spacing:
            out,remote,_=self.execute(collect=collect)
        self.assertEqual(out['execution']['submitted_batches'],2)
        self.assertEqual(out['execution']['finalized_batches'],2)
        self.assertEqual(remote.call_count,2);spacing.assert_called_once_with(2)
        self.assertIs(guards[0].scenes,guards[1].scenes)
        self.assertIs(guards[0].windows,guards[1].windows)
        self.assertEqual(model.read_bytes(),b'original model')
        self.assertEqual((partial/'partial.bin').read_bytes(),b'original partial')
        state=json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))
        for key,row in self.pending.items():self.assertEqual(state['batches'][key],row)

    def test_real_native_source_1024_then_materializer_is_called(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        def collect(config,directory,**kwargs):
            self.collect(config,directory,**kwargs)
            path=directory/'image.tif'
            with rasterio.open(path,'w',driver='GTiff',count=6,dtype='uint16',width=1024,height=1024,
                 crs='EPSG:32748',transform=from_origin(500000,9300000,10,10)) as ds:
                ds.write(np.ones((6,1024,1024),dtype='uint16'))
            return {'scenes':[{'status':'rgb_window_downloaded','image_path':str(path)}]}
        _,_,materialize=self.execute(collect=collect)
        materialize.assert_called_once()

    def test_actual_temp_materializer_writes_sixteen_patches_and_preserves_prefix(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        import collect_training_grid as grid
        boundary=self.root/'data/first-group-boundaries/selected-six.geojson'
        boundary.parent.mkdir();boundary.write_text(json.dumps(self.fixture.boundary),encoding='utf-8')
        def collect(config,directory,**kwargs):
            self.collect(config,directory,**kwargs)
            profile={'driver':'GTiff','dtype':'uint16','width':1024,'height':1024,
                     'crs':'EPSG:32748','transform':from_origin(500000,9300000,10,10)}
            for name,count in (('image',6),('label',1),('quality',1)):
                with rasterio.open(directory/(name+'.tif'),'w',count=count,**profile) as ds:
                    ds.write(np.ones((count,1024,1024),dtype='uint16'))
            return {'scenes':[{'status':'rgb_window_downloaded','scene_id':'new-scene','year':'2024',
                'image_path':str(directory/'image.tif'),'label_path':str(directory/'label.tif'),
                'quality_mask_path':str(directory/'quality.tif')}]}
        with self.proof_stack(),patch.object(subject,'collect_windows',side_effect=collect),patch.object(grid,'ROOT',self.root):
            result=subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request),execute=True)
        self.assertEqual(result['batches'][0]['patches'],16)
        self.assertEqual(len(list((self.output/'patches').rglob('image.tif'))),16)
        rows=json.loads(self.fixture.paths['source'].read_text(encoding='utf-8'))['scenes']
        self.assertEqual(rows[0],self.original);self.assertEqual(len(rows),17)

    def test_cli_without_execute_is_read_only_and_uses_fixed_digest(self):
        request_path=self.root/'evidence/integration/request.json';request_path.parent.mkdir(parents=True)
        request_path.write_text(json.dumps(self.request),encoding='utf-8')
        output=io.StringIO()
        with self.proof_stack(),patch.object(subject,'ROOT',self.root), \
             patch.object(subject.sys,'argv',['collect_deficit_guarded.py','--request','evidence/integration/request.json',
                          '--expected-request-sha256',subject.digest(self.request)]),redirect_stdout(output):
            code=subject.main()
        self.assertEqual(code,0);self.assertFalse(json.loads(output.getvalue())['executed'])
        self.assertFalse(self.lock.exists())

    def test_truncated_source_cannot_reach_materializer(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        def collect(config,directory,**kwargs):
            self.collect(config,directory,**kwargs);path=directory/'image.tif'
            with rasterio.open(path,'w',driver='GTiff',count=6,dtype='uint16',width=256,height=256,
                 crs='EPSG:32748',transform=from_origin(500000,9300000,10,10)) as ds:
                ds.write(np.ones((6,256,256),dtype='uint16'))
            return {'scenes':[{'status':'rgb_window_downloaded','image_path':str(path)}]}
        out,_,materialize=self.execute(collect=collect)
        materialize.assert_not_called();self.assertEqual(out['batches'][0]['patches'],0)
        self.assertTrue(out['batches'][0]['live_b02_checked'])

    def test_missing_b02_witness_cannot_materialize(self):
        def collect(config,directory,**kwargs):
            (directory/'window-state.json').write_text('{"http_body_bytes":23}')
            return {'scenes':[]}
        out,_,materialize=self.execute(collect=collect)
        materialize.assert_not_called();self.assertEqual(out['batches'][0]['patches'],0)
        self.assertFalse(out['batches'][0]['live_b02_checked'])

    def test_changed_active_input_rejected_after_fresh_helper_proof(self):
        actual=subject.prepare_deficit_candidate_jobs
        def changed(*args):
            out=actual(*args);self.fixture.paths['source'].write_text('{"scenes":[]}');return out
        with self.proof_stack(),patch.object(subject,'prepare_deficit_candidate_jobs',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'DEFICIT_ACTIVE_INPUT_CHANGED'):
                subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request),execute=True)
        self.assertFalse(self.lock.exists())

    def test_pinned_data_snapshot_refs_are_allowed_when_active_sha_matches(self):
        snapshot=self.root/'data/fixed-source.json';snapshot.write_bytes(self.fixture.paths['source'].read_bytes())
        ledger_snapshot=self.root/'data/fixed-ledger.json';ledger_snapshot.write_bytes(self.fixture.paths['ledger'].read_bytes())
        self.request['current_manifest_ref']['path']=snapshot.relative_to(self.root).as_posix()
        self.request['ledger_ref']['path']=ledger_snapshot.relative_to(self.root).as_posix()
        before=snapshot.read_bytes(),ledger_snapshot.read_bytes()
        out,_,_=self.execute()
        self.assertTrue(out['executed'])
        self.assertEqual(before,(snapshot.read_bytes(),ledger_snapshot.read_bytes()))
        self.assertNotEqual(self.fixture.paths['ledger'].read_bytes(),ledger_snapshot.read_bytes())

    def test_post_reserve_selection_failure_preserves_full_pending_and_reports_execution(self):
        with patch.object(subject,'balanced_coverage',side_effect=ValueError('synthetic selection failure')):
            with self.assertRaises(subject.DeficitExecutionFailure) as caught:self.execute()
        state=json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))
        new=[v for k,v in state['batches'].items() if k not in self.pending]
        self.assertEqual(len(new),1);self.assertEqual(new[0]['status'],'pending')
        self.assertEqual(new[0]['charged_bytes'],68157440)
        self.assertEqual(caught.exception.progress['collector_entered_batches'],[])
        self.assertEqual(caught.exception.progress['settled_batches'],[])

    def test_contaminated_proof_flags_job_size_and_config_digest_fail_closed(self):
        with self.proof_stack():good=subject.prepare_deficit_candidate_jobs(self.root,self.request)
        for mutate in ('local','inventory','request','size','config','execution'):
            value=copy.deepcopy(good)
            if mutate=='local':value['local_checks_passed']=False
            if mutate=='inventory':value['inventory']['pending_footprints_verified']=False
            if mutate=='request':value['request_sha256']='0'*64
            if mutate=='size':value['job_proposals'][0]['nominal_patches']=1
            if mutate=='config':value['job_proposals'][0]['config_sha256']='0'*64
            if mutate=='execution':value['execution_supported']=True
            with self.subTest(mutate=mutate),patch.object(subject,'prepare_deficit_candidate_jobs',return_value=value):
                with self.assertRaises(ValueError):subject.run_deficit_guarded(self.root,self.request,subject.digest(self.request),execute=True)
            self.assertFalse(self.lock.exists())

    def test_output_collision_is_not_overwritten_or_reserved(self):
        with self.proof_stack():proof=subject.prepare_deficit_candidate_jobs(self.root,self.request)
        directory=self.output/'sources'/proof['job_proposals'][0]['key'];directory.mkdir()
        (directory/'keep').write_bytes(b'original')
        before=self.fixture.paths['ledger'].read_bytes()
        with self.assertRaises(FileExistsError):self.execute()
        self.assertEqual(before,self.fixture.paths['ledger'].read_bytes())
        self.assertEqual((directory/'keep').read_bytes(),b'original')

    def test_physical_sixteen_patch_projection_refuses_before_reserve(self):
        self.fixture.physical['physical_patch_count']=2985
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))['batches'],self.pending)

    def test_worker_finally_failure_retains_full_unsettled_reservation(self):
        original=subject.write_json
        def fail_terminal(path,value):
            if path.name=='worker-result.json':raise OSError('synthetic terminal failure')
            return original(path,value)
        with patch.object(subject,'write_json',side_effect=fail_terminal):
            with self.assertRaises(subject.DeficitExecutionFailure) as caught:self.execute()
        state=json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))
        new=[v for k,v in state['batches'].items() if k not in self.pending]
        self.assertEqual(len(new),1);self.assertEqual(new[0]['status'],'pending')
        self.assertEqual(new[0]['charged_bytes'],68157440)
        self.assertEqual(caught.exception.progress['settled_batches'],[])

    def test_publication_failure_distinguishes_completed_settlement(self):
        original=subject.write_json
        def fail_aggregate(path,value):
            if path==self.fixture.paths['source']:raise OSError('synthetic publish failure')
            return original(path,value)
        with patch.object(subject,'write_json',side_effect=fail_aggregate):
            with self.assertRaises(subject.DeficitExecutionFailure) as caught:self.execute()
        self.assertEqual(len(caught.exception.progress['settled_batches']),1)
        self.assertEqual(caught.exception.progress['published_batches'],[])
        self.assertEqual(json.loads(self.fixture.paths['source'].read_text(encoding='utf-8'))['scenes'],[self.original])

    def test_settle_exception_keeps_pending_and_publication_unconfirmed(self):
        with patch.object(subject.CollectionLedger,'settle',side_effect=OSError('synthetic settle failure')):
            with self.assertRaises(subject.DeficitExecutionFailure) as caught:self.execute()
        self.assertEqual(caught.exception.progress['settled_batches'],[])
        state=json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))
        self.assertTrue(all(v['status']=='pending' for v in state['batches'].values()))

    def test_cleanup_failure_reports_completed_settlement_but_unknown_cleanup(self):
        original=Path.unlink
        def unlink(path,*args,**kwargs):
            if path==self.lock:raise OSError('synthetic lock cleanup failure')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',unlink):
            with self.assertRaises(subject.DeficitExecutionFailure) as caught:self.execute()
        self.assertEqual(len(caught.exception.progress['settled_batches']),1)
        self.assertEqual(caught.exception.progress['cleanup_status'],'INCOMPLETE_OR_UNVERIFIED')
        self.assertTrue(self.lock.exists())

    def test_429_event_is_preserved_in_settlement_and_no_followup_requests(self):
        def collect(config,directory,**kwargs):
            self.collect(config,directory,**kwargs)
            reason={'reason':'provider_http_429','http_status':429}
            return {'scenes':[],'batch_circuit_breaker':reason}
        out,remote,_=self.execute(collect=collect)
        self.assertTrue(out['execution']['circuit_open']);self.assertEqual(remote.call_count,1)
        self.assertTrue(json.loads(self.fixture.paths['ledger'].read_text(encoding='utf-8'))['rate_limit_active'])


if __name__=='__main__':unittest.main()
