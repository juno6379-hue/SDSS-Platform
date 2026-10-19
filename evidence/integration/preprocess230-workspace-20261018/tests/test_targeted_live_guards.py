"""Live-guard contract tests with synthetic local geometry; network is absent."""
import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from app.data.targeted_live_guards import TargetedLiveGuard, TargetedWindowClaims, scene_registry
from app.data.targeted_scene_claims import SceneClaimRegistry
from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS


class TargetedLiveGuardTests(unittest.TestCase):
    def setUp(self):
        self.aoi = {'id': 'banten-target', 'province_id': 'banten', 'bbox': [105.7, -6.3, 105.8, -6.2]}
        self.job = {'key': 'worker-a', 'year': 2025, 'split': 'val', 'province': 'banten',
                    'config': {'aois': [copy.deepcopy(self.aoi)]}}
        self.target = {'province':'banten','fixed_split':'val','year':2025,
                       'target_bbox_wgs84':copy.deepcopy(self.aoi['bbox']),
                       'target_footprint_native': {'crs': 'EPSG:32748',
                       'corners': [[500000, 9300000], [502560, 9300000],
                                   [502560, 9297440], [500000, 9297440]]}}
        self.item = {'id': 'S2A_MSIL2A_20250601T030405_N0511_R000_T48MXU_20250601T040405', 'datetime': '2025-06-01T03:04:05Z',
                     'assets': {key: {'href': 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/'+key+'.tif'}
                                for key in ('B02', 'B03', 'SCL')}}
        self.seed = {'schema_version': 1, 'kind': 'DECLARED_SCENE_SPLIT_HISTORY',
                     'source_manifest_sha256': 'a'*64, 'scenes': []}
        self.scenes = SceneClaimRegistry(self.seed)
        self.windows = TargetedWindowClaims([])
        self.guard = self.make_guard()

    def make_guard(self, owner=None, scenes=None, windows=None):
        job = copy.deepcopy(self.job)
        if owner: job['key'] = owner
        return TargetedLiveGuard(job, copy.deepcopy(self.target), scenes or self.scenes, windows or self.windows)

    def geometry(self, *, left=500000, top=9300000, width=256, height=256, resolution=10):
        # All fields emitted by the real169 service hook, not a simplified bbox stub.
        return {'schema_version': 1, 'crs': 'EPSG:32748',
                'source_bounds': [490000, 9200000, 600000, 9400000],
                'source_transform': [resolution, 0, 490000, 0, -resolution, 9400000],
                'source_width': 11000, 'source_height': 20000,
                'requested_bbox_wgs84': copy.deepcopy(self.aoi['bbox']), 'requested_side': width,
                'window': {'col_off': 1000, 'row_off': 1000, 'width': width, 'height': height},
                'window_transform': [resolution, 0, left, 0, -resolution, top],
                'window_width': width, 'window_height': height}

    def select(self, guard=None, item=None, year='2025'):
        (guard or self.guard).on_scene(item or self.item, self.aoi, year)

    def test_actual_collector_string_year_selects_scene_and_b02_witness(self):
        self.select()
        self.guard.on_window(self.item['assets']['B02']['href'], self.geometry())
        self.assertTrue(self.guard.b02_checked)
        self.assertEqual(self.scenes.snapshot()['claim_count'], 1)
        self.assertFalse(self.scenes.snapshot()['execution_supported'])
        self.assertFalse(hasattr(self.guard, 'training_ready'))

    def test_scene_requery_same_owner_is_rejected_and_claim_kept(self):
        self.select()
        with self.assertRaisesRegex(ValueError, 'TARGET_SCENE_SPLIT_OR_CLAIM_CONFLICT'):
            self.select()
        self.assertEqual(self.scenes.snapshot()['claim_count'], 1)

    def test_cross_split_seed_veto_and_quarantined_seed(self):
        for history in ([{'scene_id': self.item['id'], 'split': 'train'}],
                        [{'scene_id': self.item['id'], 'split': 'train'},
                         {'scene_id': self.item['id'], 'split': 'val'}]):
            seed = copy.deepcopy(self.seed); seed['scenes'] = history
            registry = SceneClaimRegistry(seed)
            with self.assertRaisesRegex(ValueError, 'TARGET_SCENE_SPLIT_OR_CLAIM_CONFLICT'):
                self.select(self.make_guard(scenes=registry))
            self.assertEqual(registry.snapshot()['claim_count'], 0)

    def test_failed_b02_check_retains_scene_claim(self):
        self.select()
        with self.assertRaisesRegex(ValueError, 'TARGET_B02_GRID_INVALID'):
            self.guard.on_window(self.item['assets']['B02']['href'], self.geometry(width=255))
        self.assertFalse(self.guard.b02_checked)
        with self.assertRaisesRegex(ValueError, 'TARGET_SCENE_SPLIT_OR_CLAIM_CONFLICT'):
            self.select(self.make_guard(owner='worker-b'))
        self.assertEqual(self.scenes.snapshot()['claim_count'], 1)

    def test_preselection_scl_observed_but_unselected_imagery_denied(self):
        self.guard.on_window(self.item['assets']['SCL']['href'], self.geometry(width=128, height=128, resolution=20))
        self.assertIsNone(self.guard.selected); self.assertFalse(self.guard.b02_checked)
        with self.assertRaisesRegex(ValueError, 'SCENE_REQUIRED_BEFORE_IMAGERY'):
            self.guard.on_window(self.item['assets']['B02']['href'], self.geometry())
        self.select()
        with self.assertRaisesRegex(ValueError, 'UNDECLARED_SELECTED_ASSET'):
            self.guard.on_window('https://sentinel-cogs.s3.us-west-2.amazonaws.com/other.tif', self.geometry())

    def test_year_matched_esri_reference_reusable_without_b02_witness(self):
        # Reference pixels are reused; they must not acquire an image scene/window.
        from app.data.references import esri_annual_plan
        url = esri_annual_plan(2025, self.item['id'])['url']
        for index, guard in enumerate((self.guard, self.make_guard(owner='worker-b'))):
            item = copy.deepcopy(self.item)
            if index: item['id'] = item['id'].replace('S2A_', 'S2B_')
            self.select(guard, item)
            guard.on_window(url, self.geometry(width=512, height=512))
            self.assertFalse(guard.b02_checked)
            with self.assertRaisesRegex(ValueError, 'UNDECLARED_SELECTED_ASSET'):
                guard.on_window(url.replace('lulctimeseries.blob.core.windows.net', 'example.org'), self.geometry())

    def test_b02_alignment_over_one_pixel_rejected_and_exact_boundary_allowed(self):
        self.select()
        with self.assertRaisesRegex(ValueError, 'TARGET_B02_ALIGNMENT_SHORTFALL'):
            self.guard.on_window(self.item['assets']['B02']['href'], self.geometry(left=500011))
        self.assertFalse(self.guard.b02_checked)
        self.guard.on_window(self.item['assets']['B02']['href'], self.geometry(left=500010))
        self.assertTrue(self.guard.b02_checked)

    def test_same_owner_bands_overlap_allowed_other_owner_blocked(self):
        self.select()
        self.guard.on_window(self.item['assets']['B02']['href'], self.geometry())
        self.guard.on_window(self.item['assets']['B03']['href'], self.geometry())
        other = self.make_guard(owner='worker-b')
        item = copy.deepcopy(self.item); item['id'] = item['id'].replace('S2A_', 'S2B_')
        self.select(other, item)
        with self.assertRaisesRegex(ValueError, 'LIVE_SUPPORT_WINDOW_OVERLAP'):
            other.on_window(item['assets']['B03']['href'], self.geometry())
        self.assertFalse(other.b02_checked)

    def test_historical_support_overlap_denied_but_edge_touch_allowed(self):
        history = [{'crs': 'EPSG:32748', 'bounds': [500000, 9297440, 502560, 9300000]}]
        windows = TargetedWindowClaims(history)
        with self.assertRaisesRegex(ValueError, 'LIVE_SUPPORT_WINDOW_OVERLAP'):
            windows.claim('worker-a', 'EPSG:32748', [500001, 9297441, 502559, 9299999])
        windows.claim('worker-a', 'EPSG:32748', [502560, 9297440, 505120, 9300000])

    def test_concurrent_overlapping_workers_claim_exactly_once(self):
        barrier = Barrier(2)
        def claim(owner):
            barrier.wait(timeout=10)
            try:
                self.windows.claim(owner, 'EPSG:32748', [500000, 9297440, 502560, 9300000])
                return 'claimed'
            except ValueError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(claim, ['worker-a', 'worker-b']))
        self.assertCountEqual(outcomes, ['claimed', 'LIVE_SUPPORT_WINDOW_OVERLAP'])

    def test_invalid_year_split_aoi_or_grid_fails_without_claim_or_witness(self):
        for year in ('2024', True, '2025garbage'):
            with self.assertRaises(ValueError): self.select(year=year)
        for timestamp in ('2025garbage', '2025-06-01', '2025-06-01T03:04:05'):
            item = copy.deepcopy(self.item); item['datetime'] = timestamp
            with self.assertRaises(ValueError): self.select(item=item)
        bad_aoi = copy.deepcopy(self.aoi); bad_aoi['bbox'][0] += .01
        with self.assertRaisesRegex(ValueError, 'TARGET_SCENE_AOI_CHANGED'):
            self.guard.on_scene(self.item, bad_aoi, '2025')
        job = copy.deepcopy(self.job); job['split'] = 'test'
        bad_guard = TargetedLiveGuard(job, self.target, self.scenes, self.windows)
        with self.assertRaises(ValueError): self.select(bad_guard)
        self.assertEqual(self.scenes.snapshot()['claim_count'], 0)
        self.select()
        invalid = self.geometry(); invalid['window_transform'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'WINDOW_GRID_INVALID'):
            self.guard.on_window(self.item['assets']['B02']['href'], invalid)
        self.assertFalse(self.guard.b02_checked)

    def test_registry_includes_historical_noneligible_split_rows(self):
        manifest = {'scenes': [{'scene_id': 'scene', 'split': 'val'}],
                    'historical_noneligible_patches': [{'scene_id': 'scene', 'split': 'test'}]}
        registry = scene_registry(manifest, 'b'*64)
        self.assertEqual(registry.snapshot()['quarantined_scene_count'], 1)
        self.assertIsNone(registry.claim({'schema_version': 1, 'scene_id': 'scene',
                                         'split': 'val', 'owner_id': 'worker-a'})['claim'])

    def province_case(self, province, year=2025):
        # Observed example native zones, not a province->CRS product policy.
        epsgs={'south_sulawesi':32750,'gorontalo':32651,'southeast_sulawesi':32751,
               'east_java':32749,'banten':32748,'west_java':32748}
        epsg=epsgs[province];split=FIXED_PROVINCE_SPLITS[province]
        aoi=copy.deepcopy(self.aoi);aoi.update(id=province+'-target',province_id=province)
        job=copy.deepcopy(self.job)
        job.update(province=province,split=split,year=year,key=f'{province}-{year}',config={'aois':[aoi]})
        target=copy.deepcopy(self.target)
        target.update(province=province,fixed_split=split,year=year)
        target['target_footprint_native']['crs']='EPSG:'+str(epsg)
        item=copy.deepcopy(self.item)
        item['datetime']=item['datetime'].replace('2025',str(year))
        tile=f'T{epsg%100:02d}'+('NAA' if epsg<32700 else 'MAA')
        item['id']=item['id'].replace('2025',str(year)).replace('T48MXU',tile)
        geometry=self.geometry();geometry['crs']='EPSG:'+str(epsg)
        return job,target,aoi,item,geometry

    def test_six_fixed_provinces_all_six_years_support_three_splits(self):
        encountered=set()
        for province in FIXED_PROVINCE_SPLITS:
            for year in range(2020,2026):
                with self.subTest(province=province,year=year):
                    job,target,aoi,item,geometry=self.province_case(province,year)
                    registry=SceneClaimRegistry(self.seed)
                    guard=TargetedLiveGuard(job,target,registry,TargetedWindowClaims([]))
                    guard.on_scene(item,aoi,str(year))
                    guard.on_window(item['assets']['B02']['href'],geometry)
                    self.assertTrue(guard.b02_checked)
                    self.assertEqual(registry.snapshot()['claims'][0]['split'],FIXED_PROVINCE_SPLITS[province])
                    encountered.add(job['split'])
                    self.assertFalse(registry.snapshot()['execution_supported'])
        self.assertEqual(encountered,{'train','val','test'})

    def test_all_provinces_reject_caller_split_reassignment_before_preselection_scl(self):
        for province in FIXED_PROVINCE_SPLITS:
            job,target,aoi,item,geometry=self.province_case(province)
            job['split']=next(s for s in ('train','val','test') if s!=job['split'])
            target['fixed_split']=job['split']
            registry=SceneClaimRegistry(self.seed)
            guard=TargetedLiveGuard(job,target,registry,TargetedWindowClaims([]))
            with self.assertRaisesRegex(ValueError,'TARGET_SCENE_YEAR_OR_SPLIT_INVALID'):
                guard.on_window(item['assets']['SCL']['href'],geometry)
            self.assertEqual(registry.snapshot()['claim_count'],0)

    def test_unknown_province_target_binding_and_province_aoi_mutation_fail_closed(self):
        for change in ('unknown','target_province','target_split','target_year','bbox','province_id','extra_aoi'):
            with self.subTest(change=change):
                job,target,aoi,item,geometry=self.province_case('west_java')
                if change=='unknown':job['province']='unknown'
                elif change=='target_province':target['province']='banten'
                elif change=='target_split':target['fixed_split']='train'
                elif change=='target_year':target['year']=2024
                elif change=='bbox':job['config']['aois'][0]['bbox'][0]+=.001
                elif change=='province_id':job['config']['aois'][0]['province_id']='banten'
                elif change=='extra_aoi':job['config']['aois'].append(copy.deepcopy(aoi))
                guard=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),TargetedWindowClaims([]))
                with self.assertRaises(ValueError):guard.on_scene(item,aoi,'2025')
                self.assertFalse(guard.b02_checked)

    def test_metric_native_crs_is_not_hardcoded_per_province_and_unsupported_units_fail(self):
        job,target,aoi,item,geometry=self.province_case('south_sulawesi')
        # A different *matching* actual metre-based native zone is permitted;
        # 175 validates its local label/boundary; this test does not claim geography.
        target['target_footprint_native']['crs']=geometry['crs']='EPSG:32751'
        guard=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),TargetedWindowClaims([]))
        guard.on_scene(item,aoi,'2025');guard.on_window(item['assets']['B02']['href'],geometry)
        self.assertTrue(guard.b02_checked)
        for crs in ('EPSG:4326','EPSG:2277','EPSG:4979','INVALID'):
            bad=copy.deepcopy(target);bad['target_footprint_native']['crs']=crs
            guard=TargetedLiveGuard(job,bad,SceneClaimRegistry(self.seed),TargetedWindowClaims([]))
            with self.assertRaisesRegex(ValueError,'TARGET_NATIVE_CRS_UNSUPPORTED'):
                guard.on_scene(item,aoi,'2025')

    def test_new_province_b02_crs_mismatch_and_reference_spoof_never_witness(self):
        job,target,aoi,item,geometry=self.province_case('gorontalo')
        guard=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),TargetedWindowClaims([]))
        guard.on_scene(item,aoi,'2025')
        wrong=copy.deepcopy(geometry);wrong['crs']='EPSG:32751'
        with self.assertRaisesRegex(ValueError,'TARGET_B02_GRID_INVALID'):
            guard.on_window(item['assets']['B02']['href'],wrong)
        with self.assertRaisesRegex(ValueError,'UNDECLARED_SELECTED_ASSET'):
            guard.on_window(guard.label_url.replace('/lc2025/','/lc2024/'),geometry)
        wrong=copy.deepcopy(geometry);wrong['crs']='EPSG:4326'
        with self.assertRaisesRegex(ValueError,'TARGET_NATIVE_CRS_UNSUPPORTED'):
            guard.on_window(guard.label_url,wrong)
        self.assertFalse(guard.b02_checked)

    def test_train_and_test_shared_scene_conflict_and_history_support_reject(self):
        registry=SceneClaimRegistry(self.seed)
        cases=[self.province_case('east_java'),self.province_case('west_java')]
        shared_item=cases[0][3]
        first=TargetedLiveGuard(cases[0][0],cases[0][1],registry,TargetedWindowClaims([]))
        first.on_scene(shared_item,cases[0][2],'2025')
        second=TargetedLiveGuard(cases[1][0],cases[1][1],registry,TargetedWindowClaims([]))
        with self.assertRaisesRegex(ValueError,'TARGET_SCENE_SPLIT_OR_CLAIM_CONFLICT'):
            second.on_scene(shared_item,cases[1][2],'2025')
        job,target,aoi,item,geometry=self.province_case('southeast_sulawesi')
        windows=TargetedWindowClaims([{'crs':geometry['crs'],'bounds':[500000,9297440,502560,9300000]}])
        guard=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),windows)
        with self.assertRaisesRegex(ValueError,'LIVE_SUPPORT_WINDOW_OVERLAP'):
            guard.on_window(item['assets']['SCL']['href'],geometry)
        self.assertFalse(guard.b02_checked)

    def test_new_province_failed_window_claim_is_retained_and_other_owner_denied(self):
        job,target,aoi,item,geometry=self.province_case('east_java')
        windows=TargetedWindowClaims([])
        guard=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),windows)
        guard.on_window(item['assets']['SCL']['href'],geometry)
        # Later scene year failure does not refund the observed source footprint.
        with self.assertRaises(ValueError):guard.on_scene(item,aoi,'2024')
        job['key']='another-owner'
        other=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),windows)
        with self.assertRaisesRegex(ValueError,'LIVE_SUPPORT_WINDOW_OVERLAP'):
            other.on_window(item['assets']['SCL']['href'],geometry)

    def test_input_objects_cannot_reassign_bound_province_after_construction(self):
        job,target,aoi,item,geometry=self.province_case('west_java')
        guard=TargetedLiveGuard(job,target,SceneClaimRegistry(self.seed),TargetedWindowClaims([]))
        original_aoi=copy.deepcopy(aoi)
        job['province']='banten';target['fixed_split']='train'
        job['config']['aois'][0]['bbox'][0]+=.1
        guard.on_scene(item,original_aoi,'2025')
        guard.on_window(item['assets']['B02']['href'],geometry)
        self.assertTrue(guard.b02_checked)


if __name__ == '__main__':
    unittest.main()
