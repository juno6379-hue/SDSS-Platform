"""Dispatcher boundary tests. Execute cases mock ONLY request validation/IO.

Actual CollectionLedger and run_two_workers operate on temporary data. These
tests do not constitute157/167 approval or actual provider download success.
"""
import copy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import collect_targeted_bare as module


class CollectTargetedBareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.output = self.root/'data/first-group-training-esri-v1'
        for leaf in ('sources', 'patches'): (self.output/leaf).mkdir(parents=True)
        self.ledger_path = self.root/'data/first-group-training-budget/global-ledger.json'
        self.ledger_path.parent.mkdir(parents=True)
        self.lock = self.ledger_path.with_suffix('.execution.lock')
        self.pending = {'status': 'pending', 'reserved_bytes': 136314880,
                        'charged_bytes': 136314880, 'config_sha256': 'a'*64}
        self.state = {'version': 1, 'historical_ledgers': [], 'historical_charged_bytes': 0,
                      'additional_maximum_bytes': 4*1024**3, 'new_charged_bytes': 136314880,
                      'batches': {'preserved-old-pending': copy.deepcopy(self.pending)}, 'rate_limit_active': False}
        self.write(self.ledger_path, self.state)
        self.original = {'patch_id': 'original', 'scene_id': 'original-scene', 'quality_status': 'quality_eligible', 'split': 'train',
                         'province': 'banten', 'year': 2020, 'sample_class_coverage': {'1': 65536}}
        self.aggregate_path = self.output/'annual-window-report.json'
        self.aggregate = {'scenes': [copy.deepcopy(self.original)], 'source_manifests': []}
        self.write(self.aggregate_path, self.aggregate)
        config = module.load_config(ROOT/'configs/collection.example.json')
        self.job = {'key': 'target256-test', 'target_id': 'target-a', 'province': 'banten', 'year': 2025,
                    'split': 'val', 'config': config, 'config_sha256': 'b'*64, 'selection_context': {}}
        self.request = {'schema_version': 1, 'maximum_batches': 1, 'plan': {
            'current_manifest_ref': {'path': self.aggregate_path.relative_to(self.root).as_posix(),
                                     'sha256': self.sha(self.aggregate_path)}},
            'ledger_ref': {'path': self.ledger_path.relative_to(self.root).as_posix(), 'sha256': self.sha(self.ledger_path)}}

    def tearDown(self):
        module.service.configure_request_circuit(None)
        self.temp.cleanup()

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def checked(self):
        return {'root': self.root, 'jobs': [copy.deepcopy(self.job)], 'aggregate': copy.deepcopy(self.aggregate),
                'aggregate_path': self.aggregate_path, 'ledger_path': self.ledger_path,
                'source_sha256': self.sha(self.aggregate_path), 'inventory': [{'assets': []}],
                'physical_inventory': {'physical_patch_count': 1}, 'maximum_new_physical_patches': 1,
                'targets': {'target-a': {}}, 'request_sha256': module.digest(self.request)}

    def run_mocked(self, collect, rows=None, **extra):
        stack = ExitStack()
        stack.enter_context(patch.object(module, 'validate_request', return_value=self.checked()))
        stack.enter_context(patch.object(module, 'collect_windows', side_effect=collect))
        materialize = stack.enter_context(patch.object(module, 'materialize_patches', return_value=rows or []))
        with stack:
            result = module.run_targeted(self.root, self.request, module.digest(self.request), execute=True, **extra)
        return result, materialize

    def row(self, bare=300):
        return {'patch_id': 'new-target', 'scene_id': 'new-scene', 'quality_status': 'quality_eligible', 'split': 'val',
                'province': 'banten', 'year': 2025, 'sample_class_coverage': {'8': bare, '1': 65536-bare}}

    def measured_collect(self, config, directory, **kwargs):
        self.assertTrue(kwargs['execute']); self.assertIn('collection_guard', kwargs)
        kwargs['collection_guard'].b02_checked = True
        self.write(directory/'window-state.json', {'http_body_bytes': 1234})
        return {'scenes': [], 'batch_circuit_breaker': {}}

    def test_wrong_request_sha_rejected_before_source_or_ledger_mutation(self):
        before = self.ledger_path.read_bytes(), self.aggregate_path.read_bytes()
        with patch.object(module, 'collect_windows') as collect:
            with self.assertRaisesRegex(ValueError, 'TARGETED_REQUEST_PIN_MISMATCH'):
                module.run_targeted(self.root, self.request, 'f'*64, execute=True)
        collect.assert_not_called(); self.assertFalse(self.lock.exists())
        self.assertEqual(before, (self.ledger_path.read_bytes(), self.aggregate_path.read_bytes()))

    def test_manifest_pin_drift_rejected_read_only(self):
        self.request['plan']['current_manifest_ref']['sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'TARGETED_SOURCE_CHANGED'):
            module.validate_request(self.root, self.request, module.digest(self.request))
        self.assertEqual(json.loads(self.ledger_path.read_text(encoding='utf-8')), self.state)

    def test_ledger_pin_drift_rejected_without_refund(self):
        changed = copy.deepcopy(self.state); changed['new_charged_bytes'] += 1
        self.write(self.ledger_path, changed)
        with self.assertRaisesRegex(ValueError, 'FILE_PIN_MISMATCH'):
            module.validate_request(self.root, self.request, module.digest(self.request))
        self.assertEqual(json.loads(self.ledger_path.read_text(encoding='utf-8')), changed)

    def test_existing_global_lock_is_preserved_without_validation_or_dispatch(self):
        self.lock.write_bytes(b'existing-owner')
        with patch.object(module, 'validate_request') as validate:
            with self.assertRaises(FileExistsError):
                module.run_targeted(self.root, self.request, module.digest(self.request), execute=True)
        validate.assert_not_called(); self.assertEqual(self.lock.read_bytes(), b'existing-owner')

    def test_dry_run_does_not_construct_ledger_reserve_output_or_execute(self):
        with patch.object(module, 'validate_request', return_value=self.checked()), \
                patch.object(module, 'CollectionLedger') as ledger, patch.object(module, 'collect_windows') as collect:
            result = module.run_targeted(self.root, self.request, module.digest(self.request))
        ledger.assert_not_called(); collect.assert_not_called()
        self.assertFalse(result['executed']); self.assertFalse(result['live_scene_and_window_verified'])
        self.assertEqual(list((self.output/'sources').iterdir()), []); self.assertFalse(self.lock.exists())

    def test_existing_exclusive_output_even_empty_is_not_reused_or_charged(self):
        original = self.output/'sources'/self.job['key']; original.mkdir()
        before = self.ledger_path.read_bytes()
        with patch.object(module, 'validate_request', return_value=self.checked()), \
                patch.object(module, 'collect_windows') as collect:
            with self.assertRaises(FileExistsError):
                module.run_targeted(self.root, self.request, module.digest(self.request), execute=True)
        collect.assert_not_called(); self.assertTrue(original.is_dir())
        self.assertEqual(self.ledger_path.read_bytes(), before); self.assertFalse(self.lock.exists())

    def test_real_ledger_and_workers_preserve_pending_and_append_only_new_rows(self):
        result, materialize = self.run_mocked(self.measured_collect, [self.row()])
        state = json.loads(self.ledger_path.read_text(encoding='utf-8'))
        self.assertEqual(state['batches']['preserved-old-pending'], self.pending)
        self.assertEqual(state['batches'][self.job['key']]['charged_bytes'], 1234)
        self.assertEqual(state['new_charged_bytes'], self.state['new_charged_bytes']+1234)
        rows = json.loads(self.aggregate_path.read_text(encoding='utf-8'))['scenes']
        self.assertEqual(rows[0], self.original); self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['targeted_bare_pixels'], 300); materialize.assert_called_once()
        self.assertEqual(result['execution']['finalized_batches'], 1)
        self.assertFalse(result['learning_ready']); self.assertFalse(result['scientific_accuracy_validated'])
        self.assertFalse(self.lock.exists())

    def test_bare_minimum_applies_after_materialization_without_inventing_quality(self):
        result, _ = self.run_mocked(self.measured_collect, [self.row(255)])
        self.assertEqual(json.loads(self.aggregate_path.read_text(encoding='utf-8'))['scenes'], [self.original])
        receipt = json.loads((self.output/'sources'/self.job['key']/'worker-result.json').read_text(encoding='utf-8'))
        row = receipt['targeted_unenrolled_patches'][0]
        self.assertEqual(row['quality_status'], 'quality_eligible')
        self.assertEqual(row['targeted_bare_class_status'], 'insufficient')
        self.assertEqual(result['batches'][0]['patches'], 0)
        self.assertEqual(result['batches'][0]['eligible'], 0)

    def test_absent_b02_witness_never_materializes_or_yields_patches(self):
        def collect(config, directory, **kwargs):
            self.write(directory/'window-state.json', {'http_body_bytes': 97})
            return {'scenes': [], 'batch_circuit_breaker': {}}
        result, materialize = self.run_mocked(collect, [self.row()])
        materialize.assert_not_called(); self.assertEqual(result['batches'][0]['patches'], 0)
        self.assertEqual(json.loads(self.aggregate_path.read_text(encoding='utf-8'))['scenes'], [self.original])

    def test_unmeasured_worker_finally_failure_settles_full_reservation(self):
        original_write = module.write_json
        def write(path, value):
            if Path(path).name in ('config.json', 'worker-result.json'):
                raise OSError('mock write interruption')
            return original_write(path, value)
        with patch.object(module, 'validate_request', return_value=self.checked()), \
                patch.object(module, 'write_json', side_effect=write), patch.object(module, 'collect_windows') as collect:
            result = module.run_targeted(self.root, self.request, module.digest(self.request), execute=True)
        collect.assert_not_called(); state = json.loads(self.ledger_path.read_text(encoding='utf-8'))
        self.assertEqual(state['batches'][self.job['key']]['charged_bytes'], module.COG_BATCH+module.METADATA_BATCH)
        self.assertEqual(state['batches']['preserved-old-pending'], self.pending)
        self.assertEqual(result['batches'][0]['patches'], 0); self.assertFalse(self.lock.exists())

    def test_provider_circuit_is_settled_globally_and_stops_future_dispatch(self):
        circuit = {'reason': 'provider_http_429', 'retry_after': '120'}
        def collect(config, directory, **kwargs):
            self.write(directory/'window-state.json', {'http_body_bytes': 97})
            return {'scenes': [], 'batch_circuit_breaker': circuit}
        result, _ = self.run_mocked(collect)
        state = json.loads(self.ledger_path.read_text(encoding='utf-8'))
        self.assertTrue(state['rate_limit_active']); self.assertEqual(state['last_rate_limit'], circuit)
        self.assertTrue(result['execution']['circuit_open']); self.assertTrue(result['batches'][0]['rate_limited'])
        self.assertEqual(state['batches']['preserved-old-pending'], self.pending)
        self.assertFalse(self.lock.exists())

    def test_second_output_collision_rolls_back_only_own_empty_first_output(self):
        existing = self.output/'patches'/self.job['key']; existing.mkdir(); (existing/'keep').write_bytes(b'keep')
        with patch.object(module, 'validate_request', return_value=self.checked()), \
                patch.object(module, 'collect_windows') as collect:
            with self.assertRaises(FileExistsError):
                module.run_targeted(self.root, self.request, module.digest(self.request), execute=True)
        collect.assert_not_called(); self.assertEqual((existing/'keep').read_bytes(), b'keep')
        self.assertFalse((self.output/'sources'/self.job['key']).exists())
        self.assertEqual(json.loads(self.ledger_path.read_text(encoding='utf-8')), self.state)

    def physical_row(self, name):
        folder=self.output/'patches'/name;folder.mkdir(parents=True)
        row=self.row()
        for role in ('image','label','quality'):
            path=folder/(role+'.tif');path.write_bytes(b'physical-count-only-not-a-raster')
            row[role+'_path' if role!='quality' else 'quality_mask_path']=str(path)
        return row

    def test_f3_counts_unenrolled_receipt_and_unreported_partial_directory(self):
        enrolled=self.physical_row('enrolled');unenrolled=self.physical_row('unenrolled')
        directory=self.output/'sources'/'target256-old';directory.mkdir()
        self.write(directory/'worker-result.json',{'targeted_unenrolled_patches':[unenrolled]})
        partial=self.output/'patches'/'partial';partial.mkdir();(partial/'quality.tif').write_bytes(b'partial')
        state=copy.deepcopy(self.state);state['batches']['target256-old']={}
        result=module.physical_patch_inventory(self.root,{'scenes':[enrolled]},state)
        self.assertEqual(result['physical_patch_count'],3)
        self.assertEqual(result['referenced_patch_count'],2)
        self.assertEqual(result['unreferenced_physical_directories'],1)

    def test_f3_duplicate_or_missing_references_and_missing_receipts_fail_closed(self):
        row=self.physical_row('enrolled')
        with self.assertRaisesRegex(ValueError,'TARGETED_PATCH_REFERENCE_DUPLICATE'):
            module.physical_patch_inventory(self.root,{'scenes':[row,row]},self.state)
        Path(row['label_path']).unlink()
        with self.assertRaisesRegex(ValueError,'TARGETED_PATCH_REFERENCE_UNAVAILABLE'):
            module.physical_patch_inventory(self.root,{'scenes':[row]},self.state)
        state=copy.deepcopy(self.state);state['batches']['target256-missing']={}
        with self.assertRaisesRegex(ValueError,'TARGETED_WORKER_RECEIPT_UNAVAILABLE'):
            module.physical_patch_inventory(self.root,{'scenes':[]},state)

    def test_f3_existing_unenrolled_alias_cannot_be_registered_twice(self):
        row=self.physical_row('enrolled')
        directory=self.output/'sources'/'target256-old';directory.mkdir()
        self.write(directory/'worker-result.json',{'targeted_unenrolled_patches':[copy.deepcopy(row)]})
        with self.assertRaisesRegex(ValueError,'TARGETED_PATCH_REFERENCE_DUPLICATE'):
            module.physical_patch_inventory(self.root,{'scenes':[row]},self.state)

    def validate_with_synthetic_plans(self,count,jobs):
        # F3 boundary only: native157/167 and count snapshot are explicit mocks.
        directory=self.root/'configs';directory.mkdir(exist_ok=True)
        self.write(directory/'first-group.collection.json',{})
        request=copy.deepcopy(self.request);request['maximum_batches']=len(jobs)
        request['plan']['targets']=[{'target_id':job['target_id'],'target_footprint_native':{}} for job in jobs]
        physical={'physical_patch_count':count,'limit':3000,'observation_sha256':'a'*64}
        with patch.object(module,'prepare_targeted_bare_jobs',return_value={
                'status':'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED','issue':None,'job_proposals':jobs}), \
                patch.object(module,'inspect_targeted_inventory',return_value={
                    'status':'LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED','issue':None,'assets':[]}), \
                patch.object(module,'physical_patch_inventory',return_value=physical):
            return module.validate_request(self.root,request,module.digest(request))

    def bounded_job(self,key='target256-test',target='target-a'):
        job=copy.deepcopy(self.job);job.update(key=key,target_id=target,nominal_patches=1)
        job['config'].update(window_size=256,aois=job['config']['aois'][:1],years=[2025])
        return job

    def test_f3_reserves_maximum_additional_slots_and_rejects_oversized_job(self):
        first=self.bounded_job();second=self.bounded_job('target256-second','target-b')
        checked=self.validate_with_synthetic_plans(2999,[first])
        self.assertEqual(checked['maximum_new_physical_patches'],1)
        with self.assertRaisesRegex(ValueError,'TARGETED_PHYSICAL_PATCH_LIMIT'):
            self.validate_with_synthetic_plans(2999,[first,second])
        oversized=self.bounded_job();oversized['config']['window_size']=1024
        with self.assertRaisesRegex(ValueError,'TARGETED_MAXIMUM_NEW_PATCHES_INVALID'):
            self.validate_with_synthetic_plans(1,[oversized])

    def test_f2_second_reserve_failure_reports_first_worker_settlement(self):
        checked=self.checked();second=copy.deepcopy(self.job);second['key']='target256-collision'
        checked['jobs'].append(second);checked['maximum_new_physical_patches']=2
        (self.output/'sources'/second['key']).mkdir()
        request=copy.deepcopy(self.request);request['maximum_batches']=2
        with patch.object(module,'validate_request',return_value=checked), \
                patch.object(module,'collect_windows',side_effect=self.measured_collect):
            with self.assertRaises(module.TargetedExecutionFailure) as caught:
                module.run_targeted(self.root,request,module.digest(request),execute=True)
        progress=caught.exception.progress
        self.assertEqual(progress['reserved_batches'],[self.job['key']])
        self.assertEqual(progress['settled_batches'],[self.job['key']])
        self.assertEqual(progress['published_batches'],[self.job['key']])
        self.assertEqual(progress['settlement_status'],'ALL_RESERVED_SETTLED')
        self.assertEqual(progress['transfer_status'],'NOT_INDEPENDENTLY_VERIFIED')
        state=json.loads(self.ledger_path.read_text(encoding='utf-8'))
        self.assertEqual(state['batches'][self.job['key']]['status'],'settled')
        self.assertEqual(state['batches']['preserved-old-pending'],self.pending)

    def test_f2_settlement_failure_stays_pending_and_is_not_false_nonexecution(self):
        with patch.object(module,'validate_request',return_value=self.checked()), \
                patch.object(module,'collect_windows',side_effect=self.measured_collect), \
                patch.object(module.CollectionLedger,'settle',side_effect=OSError('mock settlement failure')):
            with self.assertRaises(module.TargetedExecutionFailure) as caught:
                module.run_targeted(self.root,self.request,module.digest(self.request),execute=True)
        progress=caught.exception.progress
        self.assertEqual(progress['collector_entered_batches'],[self.job['key']])
        self.assertEqual(progress['settlement_status'],'INCOMPLETE_OR_UNVERIFIED')
        self.assertEqual(progress['finalization_attempted_batches'],[self.job['key']])
        state=json.loads(self.ledger_path.read_text(encoding='utf-8'))
        self.assertEqual(state['batches'][self.job['key']]['status'],'pending')
        self.assertEqual(state['batches'][self.job['key']]['charged_bytes'],module.COG_BATCH+module.METADATA_BATCH)

    def test_f2_publication_failure_distinguishes_successful_financial_settlement(self):
        original=module.write_json
        def write(path,value):
            if path==self.aggregate_path:raise OSError('mock publication failure')
            return original(path,value)
        with patch.object(module,'validate_request',return_value=self.checked()), \
                patch.object(module,'collect_windows',side_effect=self.measured_collect), \
                patch.object(module,'write_json',side_effect=write):
            with self.assertRaises(module.TargetedExecutionFailure) as caught:
                module.run_targeted(self.root,self.request,module.digest(self.request),execute=True)
        self.assertEqual(caught.exception.progress['settlement_status'],'ALL_RESERVED_SETTLED')
        self.assertEqual(caught.exception.progress['publication_status'],'INCOMPLETE_OR_UNVERIFIED')
        self.assertEqual(json.loads(self.aggregate_path.read_text(encoding='utf-8')),self.aggregate)

    def test_f2_reserve_exception_after_write_preserves_unknown_pending_status(self):
        original=module.CollectionLedger.reserve
        def reserve(ledger,*args):
            original(ledger,*args)
            raise RuntimeError('mock failure after reservation write')
        with patch.object(module,'validate_request',return_value=self.checked()), \
                patch.object(module.CollectionLedger,'reserve',reserve), \
                patch.object(module,'collect_windows') as collect:
            with self.assertRaises(module.TargetedExecutionFailure) as caught:
                module.run_targeted(self.root,self.request,module.digest(self.request),execute=True)
        collect.assert_not_called()
        self.assertEqual(caught.exception.progress['reservation_status'],'INCOMPLETE_OR_UNVERIFIED')
        self.assertEqual(caught.exception.progress['settlement_status'],'INCOMPLETE_OR_UNVERIFIED')
        state=json.loads(self.ledger_path.read_text(encoding='utf-8'))
        self.assertEqual(state['batches'][self.job['key']]['status'],'pending')
        self.assertEqual(state['batches']['preserved-old-pending'],self.pending)

    def test_f2_cleanup_failure_retains_execution_and_settlement_progress(self):
        original=Path.unlink
        def unlink(path,*args,**kwargs):
            if path==self.lock:raise PermissionError('mock lock cleanup failure')
            return original(path,*args,**kwargs)
        with patch.object(module,'validate_request',return_value=self.checked()), \
                patch.object(module,'collect_windows',side_effect=self.measured_collect), \
                patch.object(Path,'unlink',unlink):
            with self.assertRaises(module.TargetedExecutionFailure) as caught:
                module.run_targeted(self.root,self.request,module.digest(self.request),execute=True)
        progress=caught.exception.progress
        self.assertEqual(progress['cleanup_status'],'INCOMPLETE_OR_UNVERIFIED')
        self.assertEqual(progress['settlement_status'],'ALL_RESERVED_SETTLED')
        self.assertEqual(progress['publication_status'],'ALL_RESERVED_PUBLISHED')
        self.assertTrue(self.lock.exists())

    def test_f3_oversized_source_is_blocked_before_physical_materialization(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        image=self.root/'data/oversized-source.tif'
        with rasterio.open(image,'w',driver='GTiff',width=512,height=512,count=1,dtype='uint8',
                           crs='EPSG:32748',transform=from_origin(500000,9300000,10,10)) as dataset:
            dataset.write(np.ones((1,512,512),dtype='uint8'))
        def collect(config,directory,**kwargs):
            kwargs['collection_guard'].b02_checked=True
            self.write(directory/'window-state.json',{'http_body_bytes':97})
            return {'scenes':[{'status':'rgb_window_downloaded','image_path':str(image)}]}
        result,materialize=self.run_mocked(collect,[self.row()])
        materialize.assert_not_called()
        self.assertEqual(result['batches'][0]['patches'],0)
        self.assertEqual(json.loads(self.aggregate_path.read_text(encoding='utf-8'))['scenes'],[self.original])

    def test_f2_cli_subprocess_failure_json_and_exit_code_are_phase_sensitive(self):
        # CLI renderer only: harmless child fixture replaces run_targeted; actual
        # progress generation is independently exercised above with real workers.
        driver=self.root/'cli-fixture.py'
        driver.write_text('''import sys
from pathlib import Path
sys.path.insert(0,sys.argv.pop(1))
import collect_targeted_bare as m
m.ROOT=Path(sys.argv.pop(1))
phase=sys.argv.pop(1)
def fail(*args,**kwargs):
    if phase=="after":
        raise m.TargetedExecutionFailure({"reserved_batches":["fixture"],"settled_batches":[],
            "execution_started":True,"transfer_status":"NOT_INDEPENDENTLY_VERIFIED",
            "settlement_status":"INCOMPLETE_OR_UNVERIFIED"})
    raise ValueError("TARGETED_REQUEST_PIN_MISMATCH")
m.run_targeted=fail
raise SystemExit(m.main())
''',encoding='utf-8')
        directory=self.root/'evidence/integration';directory.mkdir(parents=True)
        request=directory/'request.json';self.write(request,{})
        for phase,executed,status in [('before',False,'BLOCKED'),('after',None,'TARGETED_EXECUTION_FAILED')]:
            child=subprocess.run([sys.executable,str(driver),str(ROOT/'scripts'),str(self.root),phase,
                '--request',str(request),'--expected-request-sha256','a'*64,'--execute'],
                capture_output=True,text=True,encoding='utf-8',timeout=30)
            self.assertEqual(child.returncode,2,child.stderr)
            result=json.loads(child.stdout)
            self.assertIs(result['executed'],executed);self.assertEqual(result['status'],status)
            self.assertEqual(result['execution_started'],phase=='after')


if __name__ == '__main__':
    unittest.main()
