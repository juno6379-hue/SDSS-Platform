"""260 격리 합성 metadata/Temp 소비계약. 원격·운영 자료 사용 없음."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_deficit_candidate_guard as fixtures
import test_collect_deficit_guarded as workers
from app.data import deficit_candidate_guard as guard_module
from app.data.targeted_live_guards import TargetedWindowClaims
from app.data.targeted_scene_claims import SceneClaimRegistry
import collect_samples as collector
from scripts import collect_deficit_guarded as coordinator
from selection265_fixtures import load_legacy

ROOT = Path(__file__).resolve().parents[1]


class MetadataSelectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CandidateFixture(methodName='runTest')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.config.update(collection='sentinel-2-l2a', endpoint='planetary-computer')
        f.save('config', f.config); f.request['config_ref'] = f.ref('config')
        f.proposal['config_sha256'] = f.sha('config'); f.update_proposal()
        self.v1 = copy.deepcopy(f.request)
        f.request.update(schema_version=2, candidate_metadata_policy=guard_module.CANDIDATE_METADATA_POLICY)
        proof, _, _ = f.run_prepare(); self.assertTrue(proof['local_checks_passed'], proof)
        self.job = proof['job_proposals'][0]; self.target = proof['targets'][0]
        self.guard = guard_module.DeficitCandidateLiveGuard(self.job, self.target, SceneClaimRegistry({
            'schema_version':1, 'kind':'DECLARED_SCENE_SPLIT_HISTORY',
            'source_manifest_sha256':'a'*64, 'scenes':[]}), TargetedWindowClaims([]))
        self.aoi = self.job['config']['aois'][0]

    def item(self, index=0, box=None, cloud=0):
        value = {'id':'S2A-scene-'+str(index), 'collection':'sentinel-2-l2a',
                 'datetime':'2024-06-01T03:04:05.024Z', 'cloud_cover':cloud,
                 'bbox':copy.deepcopy(self.aoi['bbox'] if box is None else box),
                 'assets':{'SCL':{'href':'https://example.org/private-SCL.tif?token=SECRET'}}}
        value['stac_feature'] = {'type':'Feature', 'collection':value['collection'],
            'id':value['id'], 'bbox':copy.deepcopy(value['bbox']),
            'properties':{'datetime':value['datetime']}}
        return value

    def response(self, items): return {'source':guard_module.PC_SEARCH, 'items':items}

    def apply(self, items):
        return self.guard.filter_candidate_pool(self.response(items), self.aoi, '2024')

    def config(self, limit=5):
        config = collector.load_config(ROOT/'configs/collection.example.json')
        config.update(copy.deepcopy(self.job['config']))
        config.update(candidate_limit=limit, periods={'2024':{'start_date':'2024-06-01','end_date':'2024-09-30'}})
        return config

    def test_v2_request_and_config_digests_bind_policy_source_and_request(self):
        self.assertNotEqual(coordinator.digest(self.v1), coordinator.digest(self.fixture.request))
        self.assertEqual(self.job['config']['candidate_metadata_policy'], guard_module.CANDIDATE_METADATA_POLICY)
        self.assertEqual(self.job['config_sha256'], hashlib.sha256(json.dumps(self.job['config'],sort_keys=True).encode()).hexdigest())
        self.assertEqual(self.job['candidate_metadata_binding'], {'policy':guard_module.CANDIDATE_METADATA_POLICY,
            'request_sha256':coordinator.digest(self.fixture.request), 'source_sha256':self.fixture.sha('source')})

    def test_v1_full_proof_equals_archived_baseline_and_has_no_policy_output(self):
        baseline = load_legacy('guard')
        f = self.fixture
        results = []
        for module in (baseline, guard_module):
            with patch.object(module,'inspect_targeted_inventory',return_value=f.proof), \
                 patch.object(module,'_physical_inventory',return_value=f.physical):
                results.append(module.prepare_deficit_candidate_jobs(f.root, self.v1))
        self.assertEqual(results[0], results[1])
        self.assertNotIn('candidate_metadata_binding', results[1]['job_proposals'][0])

    def test_policy_unknown_missing_boolean_and_extra_rejected_before_inventory(self):
        f = self.fixture
        variants = []
        for value in (True, None, 'UNKNOWN', 2):
            changed = copy.deepcopy(f.request); changed['candidate_metadata_policy'] = value; variants.append(changed)
        changed = copy.deepcopy(f.request); del changed['candidate_metadata_policy']; variants.append(changed)
        changed = copy.deepcopy(self.v1); changed['candidate_metadata_policy'] = guard_module.CANDIDATE_METADATA_POLICY; variants.append(changed)
        for request in variants:
            with patch.object(guard_module,'inspect_targeted_inventory') as inventory:
                result = guard_module.prepare_deficit_candidate_jobs(f.root, request)
            self.assertFalse(result['local_checks_passed']); inventory.assert_not_called()

    def test_stable_cloud_order_full_twenty_and_no_input_mutation(self):
        rows = [self.item(i, cloud=19-i) for i in range(20)]
        before = copy.deepcopy(rows)
        accepted, summary = self.apply(rows)
        self.assertEqual([r['id'] for r in accepted], [r['id'] for r in rows[::-1]])
        self.assertEqual(summary['input_count'],20); self.assertEqual(rows,before)
        rows = [self.item(i) for i in range(3)]
        self.assertEqual([r['id'] for r in self.apply(rows)[0]], [r['id'] for r in rows])
        self.assertNotIn('https',json.dumps(summary)); self.assertNotIn('SECRET',json.dumps(summary))

    def test_bbox_missing_invalid_partial_raw_mismatch_fail_closed(self):
        a = self.aoi['bbox']; middle = (a[1]+a[3])/2
        bad = [None, [], a+[0,1], [True,*a[1:]], [float('nan'),*a[1:]],
               [float('inf'),*a[1:]], [10**1000,*a[1:]], [a[2],a[1],a[0],a[3]], [a[0],a[1],a[2],middle]]
        for box in bad:
            row = self.item(); row['bbox']=copy.deepcopy(box); row['stac_feature']['bbox']=copy.deepcopy(box)
            accepted, summary = self.apply([row]); self.assertEqual(accepted,[])
            self.assertEqual(summary['excluded_count'],1)
        row=self.item(); row['stac_feature']['bbox'][0]-=.1
        self.assertEqual(self.apply([row])[0],[])
        self.assertEqual(len(self.apply([self.item()])[0]),1) # equality includes all four AOI boundaries

    def test_identity_time_provider_response_and_binding_validation(self):
        for field,value in [('id','different'),('datetime','2023-06-01T00:00:00Z'),('datetime','invalid'),
                            ('collection','landsat-c2-l2')]:
            row=self.item();row[field]=value
            self.assertEqual(self.apply([row])[0],[])
        row=self.item();del row['stac_feature']
        self.assertEqual(self.apply([row])[0],[])
        for response in ({'items':[self.item()]},self.response([self.item(i) for i in range(21)]),
                         self.response([{**self.item(),'cloud_cover':True}])):
            with self.assertRaises(ValueError):self.guard.filter_candidate_pool(response,self.aoi,2024)
        with self.assertRaises(ValueError):self.guard.filter_candidate_pool(self.response([self.item()]),self.aoi,2023)
        self.guard.job['candidate_metadata_binding']['source_sha256']='bad'
        with self.assertRaises(ValueError):self.apply([self.item()])

    def test_first_five_metadata_rejects_allow_six_to_ten_but_scl_pool_stays_five(self):
        rows=[self.item(i) for i in range(20)]
        for row in rows[:5]: row['bbox']=None;row['stac_feature']['bbox']=None
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(collector.service,'search_stac',return_value=self.response(rows)) as search, \
             patch.object(collector,'select_quality_candidate',return_value=(None,None,[])) as select, \
             patch.object(collector.service,'read_cog_window',side_effect=AssertionError('HTTP forbidden')):
            report=collector.collect_windows(self.config(),Path(directory),True,
                collection_guard=self.guard,candidate_metadata_filter=self.guard.filter_candidate_pool)
        self.assertEqual([r['id'] for r in select.call_args.args[0]],['S2A-scene-'+str(i) for i in range(5,10)])
        self.assertEqual(search.call_count,1);self.assertEqual(search.call_args.args[0]['limit'],20)
        self.assertEqual(report['scenes'][0]['candidate_metadata_filter']['selected_pool_count'],5)
        self.assertEqual(report['scenes'][0]['status'],'quality_insufficient')

    def test_real_quality_selector_reads_only_five_and_does_not_refill_after_failure(self):
        rows=[self.item(i) for i in range(20)]
        for row in rows[:5]:row['bbox']=None;row['stac_feature']['bbox']=None
        error=collector.service.AssetTransferError('window_geometry_guard',97,True)
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(collector.service,'search_stac',return_value=self.response(rows)) as search, \
             patch.object(collector.service,'read_cog_window',side_effect=error) as pixels:
            report=collector.collect_windows(self.config(),Path(directory),True,
                collection_guard=self.guard,candidate_metadata_filter=self.guard.filter_candidate_pool)
        self.assertEqual(search.call_count,1);self.assertEqual(pixels.call_count,5)
        self.assertEqual(len(report['scenes'][0]['candidate_selection']),5)
        self.assertEqual(report['scenes'][0]['status'],'quality_insufficient')

    def test_default_256_dry_output_exactly_equals_archived_collector(self):
        baseline=load_legacy('collector')
        config=collector.load_config(ROOT/'configs/collection.example.json')
        config.update(window_size=256)
        outputs=[]
        for module in (baseline,collector):
            with tempfile.TemporaryDirectory() as directory,patch.object(collector.service,'search_stac') as search:
                outputs.append(module.collect_windows(config,Path(directory),False))
                search.assert_not_called()
        self.assertEqual(outputs[0],outputs[1])

    def test_explicit_callback_rejects_256_and_search_above_twenty_before_network(self):
        for change in ({'window_size':256},{'search_limit':21}):
            config=self.config();config.update(change)
            with tempfile.TemporaryDirectory() as directory,patch.object(collector.service,'search_stac') as search:
                with self.assertRaisesRegex(ValueError,'CENTER_METADATA_CALLBACK_INVALID'):
                    collector.collect_windows(config,Path(directory),True,
                        candidate_metadata_filter=self.guard.filter_candidate_pool)
                search.assert_not_called()

    def test_all_excluded_no_scl_or_scene_fallback_including_limit_one(self):
        for limit in (1,5):
            row=self.item();row['bbox']=None
            with tempfile.TemporaryDirectory() as directory, \
                 patch.object(collector.service,'search_stac',return_value=self.response([row])) as search, \
                 patch.object(collector,'select_quality_candidate') as select, \
                 patch.object(collector.service,'read_cog_window') as pixels, \
                 patch.object(self.guard,'on_scene') as scene:
                report=collector.collect_windows(self.config(limit),Path(directory),True,
                    collection_guard=self.guard,candidate_metadata_filter=self.guard.filter_candidate_pool)
            self.assertEqual(search.call_count,1);select.assert_not_called();pixels.assert_not_called();scene.assert_not_called()
            self.assertEqual(report['scenes'][0]['status'],'metadata_coverage_insufficient')

    def test_limit_one_filters_before_scene_and_never_falls_back_to_partial_first(self):
        partial=self.item(0);partial['bbox']=None
        good=self.item(1)
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(collector.service,'search_stac',return_value=self.response([partial,good])), \
             patch.object(self.guard,'on_scene',side_effect=ValueError('STOP_OFFLINE')) as scene, \
             patch.object(collector.service,'read_cog_window') as pixels:
            collector.collect_windows(self.config(1),Path(directory),True,
                collection_guard=self.guard,candidate_metadata_filter=self.guard.filter_candidate_pool)
        self.assertEqual(scene.call_args.args[0]['id'],good['id']);pixels.assert_not_called()

    def test_metadata_pass_does_not_bypass_existing_support_window_guard(self):
        self.assertEqual(len(self.apply([self.item()])[0]),1)
        # Before scene selection the same existing SCL support veto still runs.
        self.guard.windows.claim('old', self.target['target_footprint_native']['crs'],
            guard_module._rectangle(self.target['target_footprint_native']).bounds)
        left,bottom,right,top=guard_module._rectangle(self.target['target_footprint_native']).bounds
        geometry={'crs':self.target['target_footprint_native']['crs'], 'requested_bbox_wgs84':self.aoi['bbox'],
            'window_transform':[20,0,left,0,-20,top], 'window_width':512,'window_height':512}
        with self.assertRaisesRegex(ValueError,'LIVE_SUPPORT_WINDOW_OVERLAP'):
            self.guard.on_window('https://example.org/SCL.tif',geometry)

    def test_v2_coordinator_passes_callback_and_preserves_temp_settlement(self):
        fixture=workers.CollectDeficitGuardedTests(methodName='runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.request.update(schema_version=2,candidate_metadata_policy=guard_module.CANDIDATE_METADATA_POLICY)
        def collect(config,directory,**kwargs):
            self.assertIn('candidate_metadata_filter',kwargs)
            self.assertEqual(kwargs['candidate_metadata_filter'].__self__,kwargs['collection_guard'])
            return fixture.collect(config,directory,**kwargs)
        result,_,_=fixture.execute(collect=collect)
        self.assertEqual(result['batches'][0]['charged_bytes'],97)
        state=json.loads(fixture.fixture.paths['ledger'].read_text())
        for key,value in fixture.pending.items():self.assertEqual(state['batches'][key],value)
        self.assertEqual(state['new_charged_bytes'],136314880+97)

    def test_v1_coordinator_never_passes_optional_callback(self):
        fixture=workers.CollectDeficitGuardedTests(methodName='runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        def collect(config,directory,**kwargs):
            self.assertNotIn('candidate_metadata_filter',kwargs)
            return fixture.collect(config,directory,**kwargs)
        fixture.execute(collect=collect)

    def test_v2_binding_tamper_fails_before_reservation_or_worker(self):
        fixture=workers.CollectDeficitGuardedTests(methodName='runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.request.update(schema_version=2,candidate_metadata_policy=guard_module.CANDIDATE_METADATA_POLICY)
        with fixture.proof_stack():proof=guard_module.prepare_deficit_candidate_jobs(fixture.root,fixture.request)
        self.assertTrue(proof['local_checks_passed'])
        proof['job_proposals'][0]['candidate_metadata_binding']['source_sha256']='0'*64
        with patch.object(coordinator,'prepare_deficit_candidate_jobs',return_value=proof), \
             patch.object(coordinator,'CollectionLedger') as ledger,patch.object(coordinator,'collect_windows') as collect:
            with self.assertRaisesRegex(ValueError,'DEFICIT_METADATA_BINDING_INVALID'):
                coordinator.run_deficit_guarded(fixture.root,fixture.request,coordinator.digest(fixture.request),execute=True)
        ledger.assert_not_called();collect.assert_not_called();self.assertFalse(fixture.lock.exists())


if __name__=='__main__':unittest.main()
