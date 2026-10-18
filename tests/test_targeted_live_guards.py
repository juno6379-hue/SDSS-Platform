"""Live-guard contract tests with synthetic local geometry; network is absent."""
import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from app.data.targeted_live_guards import TargetedLiveGuard, TargetedWindowClaims, scene_registry
from app.data.targeted_scene_claims import SceneClaimRegistry


class TargetedLiveGuardTests(unittest.TestCase):
    def setUp(self):
        self.aoi = {'id': 'banten-target', 'bbox': [105.7, -6.3, 105.8, -6.2]}
        self.job = {'key': 'worker-a', 'year': 2025, 'split': 'val', 'province': 'banten',
                    'config': {'aois': [copy.deepcopy(self.aoi)]}}
        self.target = {'target_footprint_native': {'crs': 'EPSG:32748',
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


if __name__ == '__main__':
    unittest.main()
