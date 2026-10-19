"""임시 JSON·기하와 모의 support로199 경계만 검사한다. 운영 자료는 읽지 않는다."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from app.data import deficit_candidate_guard as subject
from app.data.targeted_live_guards import TargetedLiveGuard, TargetedWindowClaims
from app.data.targeted_scene_claims import SceneClaimRegistry
from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS


class CandidateFixture(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root/'data').mkdir(); (self.root/'configs').mkdir()
        self.paths = {'source': self.root/'data/first-group-training-esri-v1/annual-window-report.json',
            'ledger': self.root/'data/first-group-training-budget/global-ledger.json',
            'boundary': self.root/'data/boundary.json', 'config': self.root/'configs/base.json',
            'prior': self.root/'data/prior.json', 'proposal': self.root/'data/proposal.json'}
        centers = {'south_sulawesi': (119,-5), 'gorontalo': (123,.5), 'southeast_sulawesi': (122,-4),
                   'banten': (106,-6), 'west_java': (108,-7), 'east_java': (113,-8)}
        self.source = {'scenes': []}
        self.ledger = {'batches': {}, 'additional_maximum_bytes': 4*1024**3, 'new_charged_bytes': 0,
                       'external_research_metadata_body_bytes': 0, 'rate_limit_active': False}
        self.boundary = {'features': [{'properties': {'province_id': p},
            'geometry': {'type': 'Polygon', 'coordinates': [[[x-1.3,y-1.3],[x+1.3,y-1.3],
            [x+1.3,y+1.3],[x-1.3,y+1.3],[x-1.3,y-1.3]]]}} for p,(x,y) in centers.items()]}
        self.config = {'aois': [{'id': p} for p in centers]}
        self.prior = {'schema_version': 1, 'executed_network': False, 'candidates': []}
        self.save('source', self.source); self.save('ledger', self.ledger)
        self.save('boundary', self.boundary); self.save('config', self.config); self.save('prior', self.prior)
        from pyproj import Transformer
        crs = 'EPSG:32748'; lon,lat = 106,-6
        x,y = Transformer.from_crs(4326,crs,always_xy=True).transform(lon,lat)
        inverse = Transformer.from_crs(crs,4326,always_xy=True)
        pts = [inverse.transform(xx,yy) for xx,yy in [(x-5120,y+5120),(x+5120,y+5120),
                                                      (x+5120,y-5120),(x-5120,y-5120)]]
        self.candidate = {'province':'banten','fixed_split':'val','spatial_window_id':'centers182-banten-abcdef123456',
            'lon':lon,'lat':lat,'bbox':[min(p[0] for p in pts),min(p[1] for p in pts),
            max(p[0] for p in pts),max(p[1] for p in pts)],'grid_crs':crs,'window_size':1024,
            'boundary_sha256':self.sha('boundary'),'source_snapshot_sha256':self.sha('source'),
            'years':[2024],'reference':'esri_io','class_presence_verified':False,
            'actual_quality_eligible':False,'execution_supported':False}
        self.proposal = {'schema_version':1,'executed_network':False,'collector_consumption_approved':False,
            'full_pending_support_inventory_verified':False,'source_sha256':self.sha('source'),
            'boundary_sha256':self.sha('boundary'),'config_sha256':self.sha('config'),
            'prior_plan_sha256':self.sha('prior'),'candidates':[self.candidate]}
        self.save('proposal', self.proposal)
        self.request = {'schema_version':1,'kind':'GUARDED_DEFICIT_1024_REQUEST',
            'proposal_ref':self.ref('proposal'),'current_manifest_ref':self.ref('source'),
            'ledger_ref':self.ref('ledger'),'boundary_ref':self.ref('boundary'),
            'config_ref':self.ref('config'),'prior_plan_ref':self.ref('prior'),
            'selected':[{'spatial_window_id':self.candidate['spatial_window_id'],'year':2024}],
            'maximum_batches':1}
        self.proof = {'inventory_verified':True,'pending_footprints_verified':True,
                      'source_pins_verified':True,'assets':[]}
        self.physical = {'physical_patch_count':0,'limit':3000,'observation_sha256':'a'*64}

    def save(self, role, value):
        self.paths[role].parent.mkdir(parents=True, exist_ok=True)
        self.paths[role].write_text(json.dumps(value), encoding='utf-8')

    def sha(self, role): return hashlib.sha256(self.paths[role].read_bytes()).hexdigest()

    def ref(self, role): return {'path':self.paths[role].relative_to(self.root).as_posix(),'sha256':self.sha(role)}

    def update_proposal(self):
        self.save('proposal', self.proposal); self.request['proposal_ref'] = self.ref('proposal')

    def run_prepare(self, *, proof=None, physical=None):
        with patch.object(subject, 'inspect_targeted_inventory', return_value=copy.deepcopy(self.proof if proof is None else proof)) as inventory, \
             patch.object(subject, '_physical_inventory', return_value=copy.deepcopy(self.physical if physical is None else physical)) as disk:
            result = subject.prepare_deficit_candidate_jobs(self.root, self.request)
        return result, inventory, disk


class PreflightTests(CandidateFixture):
    def test_valid_plan_stays_blocked_one_inventory_no_input_writes(self):
        before = {p:p.read_bytes() for p in self.paths.values()}; request = copy.deepcopy(self.request)
        result, inventory, disk = self.run_prepare()
        self.assertTrue(result['local_checks_passed'], result)
        self.assertEqual(result['status'], 'EXECUTION_BLOCKED')
        self.assertFalse(result['execution_supported']); self.assertFalse(result['collection_executed'])
        self.assertEqual(inventory.call_count, 1); self.assertEqual(disk.call_count, 2)
        self.assertEqual(inventory.call_args.kwargs,{'max_bytes':3*1024**3})
        self.assertEqual(result['inventory_diagnostic']['resource_profile'],'DEFICIT_LOCAL_SUPPORT_3G_V1')
        self.assertEqual(result['job_proposals'][0]['nominal_patches'], 16)
        self.assertEqual(result['job_proposals'][0]['config']['window_size'], 1024)
        self.assertEqual(result['job_proposals'][0]['config']['transient_asset_retries'], 0)
        self.assertEqual(self.request, request)
        self.assertEqual(before, {p:p.read_bytes() for p in before})
        self.assertFalse(self.proposal['collector_consumption_approved'])

    def test_request_types_selection_caps_and_extra_keys_fail_before_inventory(self):
        for change in ('bool', 'extra', 'three', 'duplicate', 'bad_year'):
            old = copy.deepcopy(self.request)
            if change == 'bool': self.request['maximum_batches'] = True
            if change == 'extra': self.request['execute'] = True
            if change == 'three': self.request['maximum_batches'] = 3
            if change == 'duplicate': self.request['maximum_batches'] = 2; self.request['selected'] *= 2
            if change == 'bad_year': self.request['selected'][0]['year'] = True
            result, inventory, _ = self.run_prepare()
            self.assertFalse(result['local_checks_passed'], change); inventory.assert_not_called()
            self.request = old

    def test_stale_proposal_config_prior_and_declared_approval_fail_closed(self):
        for field in ('source_sha256','config_sha256','prior_plan_sha256','boundary_sha256',
                      'collector_consumption_approved'):
            old = copy.deepcopy(self.proposal)
            self.proposal[field] = True if field == 'collector_consumption_approved' else '0'*64
            self.update_proposal()
            result, inventory, _ = self.run_prepare()
            self.assertFalse(result['local_checks_passed'], field); inventory.assert_not_called()
            self.proposal = old

    def test_mutable_active_source_cannot_be_replaced_by_old_snapshot(self):
        frozen = self.root/'data/frozen.json'; frozen.write_bytes(self.paths['source'].read_bytes())
        self.request['current_manifest_ref']['path'] = frozen.relative_to(self.root).as_posix()
        self.paths['source'].write_text('{"scenes":[],"changed":true}', encoding='utf-8')
        result, inventory, _ = self.run_prepare()
        self.assertEqual(result['issue'], 'CENTER_ACTIVE_INPUT_CHANGED'); inventory.assert_not_called()

    def test_three_full_inventory_flags_are_required(self):
        for key in ('inventory_verified','pending_footprints_verified','source_pins_verified'):
            proof = copy.deepcopy(self.proof); proof[key] = False
            result, inventory, disk = self.run_prepare(proof=proof)
            self.assertEqual(result['issue'], 'CENTER_FULL_INVENTORY_NOT_VERIFIED')
            self.assertEqual(inventory.call_count, 1); disk.assert_not_called()

    def test_inventory_failure_retains_bounded_diagnostic_without_paths_or_writes(self):
        before={p:p.read_bytes() for p in self.paths.values()}
        proof={'inventory_verified':False,'pending_footprints_verified':False,'source_pins_verified':False,
               'issue':'INVENTORY_LIMIT','current_asset':'private/path','assets':[{'path':'private/path'}],
               'observed':{'enumerated_files':1515,'support_files':1275,'support_bytes':2166734413,
                           'secret':'private/path'}}
        result,inventory,disk=self.run_prepare(proof=proof)
        self.assertEqual(result['issue'],'CENTER_FULL_INVENTORY_NOT_VERIFIED')
        self.assertEqual(result['inventory_diagnostic'],{'resource_profile':'DEFICIT_LOCAL_SUPPORT_3G_V1',
            'max_files':10000,'max_support_bytes':3*1024**3,'issue':'INVENTORY_LIMIT',
            'observed':{'enumerated_files':1515,'support_files':1275,'support_bytes':2166734413}})
        self.assertIsNone(result['inventory']);self.assertEqual(result['job_proposals'],[])
        inventory.assert_called_once();disk.assert_not_called()
        self.assertNotIn('private',json.dumps(result))
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_inventory_diagnostic_rejects_unbounded_or_noninteger_fields(self):
        for value in (True,-1,1.0,2**63,'private/path',None):
            diagnostic=subject._inventory_diagnostic({'issue':'private/path',
                'observed':{key:value for key in ('enumerated_files','support_files','support_bytes')}})
            self.assertIsNone(diagnostic['issue'])
            self.assertTrue(all(v is None for v in diagnostic['observed'].values()))

    def test_support_overlap_and_physical_3000_boundary(self):
        good, _, _ = self.run_prepare()
        native = good['targets'][0]['target_footprint_native']
        from shapely.geometry import Polygon
        proof = copy.deepcopy(self.proof)
        proof['assets'] = [{'crs':native['crs'],'bounds':list(Polygon(native['corners']).bounds)}]
        result, _, disk = self.run_prepare(proof=proof)
        self.assertEqual(result['issue'], 'LIVE_SUPPORT_WINDOW_OVERLAP'); disk.assert_not_called()
        result, _, _ = self.run_prepare(physical={**self.physical,'physical_patch_count':2985})
        self.assertEqual(result['issue'], 'CENTER_PHYSICAL_CAP')
        result, _, _ = self.run_prepare(physical={**self.physical,'physical_patch_count':2984})
        self.assertTrue(result['local_checks_passed'])

    def test_circuit_budget_and_accounting_keep_reservations_unchanged(self):
        for change in ('circuit','budget','accounting'):
            ledger = copy.deepcopy(self.ledger)
            if change == 'circuit': ledger['rate_limit_active'] = True
            if change == 'budget':
                ledger['new_charged_bytes'] = 4*1024**3-subject.BATCH_BYTES+1
                ledger['external_research_metadata_body_bytes'] = ledger['new_charged_bytes']
            if change == 'accounting': ledger['new_charged_bytes'] = 1
            self.save('ledger', ledger); self.request['ledger_ref'] = self.ref('ledger')
            before = self.paths['ledger'].read_bytes()
            result, inventory, _ = self.run_prepare()
            self.assertFalse(result['local_checks_passed']); inventory.assert_not_called()
            self.assertEqual(self.paths['ledger'].read_bytes(), before)

    def test_undeclared_year_split_geometry_and_prior_reuse_are_rejected(self):
        for change in ('year','split','bbox','size','prior'):
            old = copy.deepcopy(self.proposal); prior = copy.deepcopy(self.prior)
            c = self.proposal['candidates'][0]
            if change == 'year': c['years'] = [2025]
            if change == 'split': c['fixed_split'] = 'train'
            if change == 'bbox': c['bbox'][0] += .01
            if change == 'size': c['window_size'] = 256
            if change == 'prior':
                self.prior['candidates'] = [copy.deepcopy(c)]; self.save('prior', self.prior)
                self.request['prior_plan_ref'] = self.ref('prior')
                self.proposal['prior_plan_sha256'] = self.sha('prior')
            self.update_proposal()
            result, inventory, _ = self.run_prepare()
            self.assertFalse(result['local_checks_passed'], change); inventory.assert_not_called()
            self.proposal = old; self.prior = prior; self.save('prior', prior)
            self.request['prior_plan_ref'] = self.ref('prior')

    def test_met_cell_and_existing_batch_block_before_support(self):
        self.source['scenes'] = [{'province':'banten','year':'2024','quality_status':'quality_eligible'}]*28
        self.save('source', self.source); self.request['current_manifest_ref'] = self.ref('source')
        self.proposal['source_sha256'] = self.sha('source')
        self.proposal['candidates'][0]['source_snapshot_sha256'] = self.sha('source'); self.update_proposal()
        result, inventory, _ = self.run_prepare()
        self.assertEqual(result['issue'], 'CENTER_CELL_ALREADY_MET'); inventory.assert_not_called()
        self.source['scenes'] = []; self.save('source', self.source)
        self.request['current_manifest_ref'] = self.ref('source'); self.proposal['source_sha256'] = self.sha('source')
        self.proposal['candidates'][0]['source_snapshot_sha256'] = self.sha('source'); self.update_proposal()
        key = 'parallel-v2-extra-banten-2024-'+self.candidate['spatial_window_id']
        self.ledger['batches'][key] = {'status':'settled','reserved_bytes':1,'charged_bytes':0}
        self.save('ledger', self.ledger); self.request['ledger_ref'] = self.ref('ledger')
        result, inventory, _ = self.run_prepare()
        self.assertEqual(result['issue'], 'CENTER_BATCH_ALREADY_RESERVED'); inventory.assert_not_called()

    def test_final_active_input_change_never_returns_jobs(self):
        def change(*_):
            self.paths['ledger'].write_text('{"changed":true}', encoding='utf-8')
            return copy.deepcopy(self.proof)
        with patch.object(subject,'inspect_targeted_inventory',side_effect=change), \
             patch.object(subject,'_physical_inventory',return_value=self.physical):
            result = subject.prepare_deficit_candidate_jobs(self.root,self.request)
        self.assertFalse(result['local_checks_passed']); self.assertEqual(result['job_proposals'], [])

    def test_two_jobs_use_32_physical_slots_and_exact_batch_limit(self):
        from pyproj import Transformer
        second = copy.deepcopy(self.candidate)
        second.update(spatial_window_id='centers182-banten-second',lon=106.3)
        forward = Transformer.from_crs(4326,second['grid_crs'],always_xy=True)
        inverse = Transformer.from_crs(second['grid_crs'],4326,always_xy=True)
        x,y = forward.transform(second['lon'],second['lat'])
        pts = [inverse.transform(xx,yy) for xx,yy in [(x-5120,y+5120),(x+5120,y+5120),
                                                      (x+5120,y-5120),(x-5120,y-5120)]]
        second['bbox'] = [min(p[0] for p in pts),min(p[1] for p in pts),
                          max(p[0] for p in pts),max(p[1] for p in pts)]
        self.proposal['candidates'].append(second); self.update_proposal()
        self.request['selected'].append({'spatial_window_id':second['spatial_window_id'],'year':2024})
        result, inventory, _ = self.run_prepare()
        self.assertFalse(result['local_checks_passed']); inventory.assert_not_called()
        self.request['maximum_batches'] = 2
        result, inventory, _ = self.run_prepare(physical={**self.physical,'physical_patch_count':2968})
        self.assertTrue(result['local_checks_passed'],result)
        self.assertEqual(len(result['job_proposals']),2); self.assertEqual(inventory.call_count,1)
        self.assertEqual(len({j['key'] for j in result['job_proposals']}),2)
        result, _, _ = self.run_prepare(physical={**self.physical,'physical_patch_count':2969})
        self.assertEqual(result['issue'],'CENTER_PHYSICAL_CAP')

    def test_physical_reader_reused_without_ledger_constructor_or_main(self):
        for folder in ('patches','sources'):
            (self.root/'data/first-group-training-esri-v1'/folder).mkdir()
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        with patch('app.data.budget.CollectionLedger',side_effect=AssertionError('원장 생성 금지')):
            physical = subject._physical_inventory(self.root,{'scenes':[]},{'batches':{}})
        self.assertEqual(physical['physical_patch_count'],0)
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))

    def test_import_alone_does_not_load_collector_cli(self):
        code = ('import sys; import app.data.deficit_candidate_guard; '
                'assert "scripts.collect_targeted_bare" not in sys.modules')
        child = subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=30,
                               env=os.environ.copy())
        self.assertEqual(child.returncode,0,child.stderr)


class LiveGuardTests(CandidateFixture):
    def setUp(self):
        super().setUp()
        prepared, _, _ = self.run_prepare()
        self.assertTrue(prepared['local_checks_passed'],prepared)
        self.job = prepared['job_proposals'][0]; self.target = prepared['targets'][0]
        self.aoi = self.job['config']['aois'][0]
        self.item = {'id':'S2A_MSIL2A_20240601T030405_N0511_R000_T48MXU_20240601T040405',
                     'datetime':'2024-06-01T03:04:05Z','assets':{key:{'href':'https://example.org/'+key+'.tif'}
                     for key in ('B02','B03','SCL')}}
        self.seed = {'schema_version':1,'kind':'DECLARED_SCENE_SPLIT_HISTORY',
                     'source_manifest_sha256':'a'*64,'scenes':[]}

    def guard(self, *, windows=None, seed=None, job=None):
        return subject.DeficitCandidateLiveGuard(job or self.job,self.target,
            SceneClaimRegistry(seed or self.seed),windows or TargetedWindowClaims([]))

    def geometry(self, *, width=1024,height=1024,shift=0,resolution=10):
        from shapely.geometry import Polygon
        left,bottom,right,top = Polygon(self.target['target_footprint_native']['corners']).bounds
        return {'crs':self.target['target_footprint_native']['crs'],
            'requested_bbox_wgs84':copy.deepcopy(self.aoi['bbox']),'requested_side':width,
            'window_transform':[resolution,0,left+shift,0,-resolution,top],
            'window_width':width,'window_height':height,
            'window':{'col_off':0,'row_off':0,'width':width,'height':height}}

    def select(self, guard): guard.on_scene(self.item,self.aoi,'2024')

    def test_selected_b02_1024_and_parent_256_contract_remain_separate(self):
        guard = self.guard(); self.select(guard)
        guard.on_window(self.item['assets']['B02']['href'],self.geometry())
        self.assertTrue(guard.b02_checked)
        parent = TargetedLiveGuard(self.job,self.target,SceneClaimRegistry(self.seed),TargetedWindowClaims([]))
        self.select(parent)
        with self.assertRaisesRegex(ValueError,'TARGET_B02_GRID_INVALID'):
            parent.on_window(self.item['assets']['B02']['href'],self.geometry())

    def test_b02_256_truncated_wrong_resolution_or_crs_rejected(self):
        for geometry in (self.geometry(width=256,height=256),self.geometry(width=1023),
                         self.geometry(resolution=20),{**self.geometry(),'crs':'EPSG:32749'}):
            guard = self.guard(); self.select(guard)
            with self.assertRaises(ValueError): guard.on_window(self.item['assets']['B02']['href'],geometry)
            self.assertFalse(guard.b02_checked)
            self.assertIsNone(guard.alignment_diagnostic())

    def test_alignment_one_pixel_allowed_over_one_pixel_denied(self):
        guard = self.guard(); self.select(guard)
        with self.assertRaisesRegex(ValueError,'CENTER_B02_ALIGNMENT_SHORTFALL'):
            guard.on_window(self.item['assets']['B02']['href'],self.geometry(shift=11))
        guard.on_window(self.item['assets']['B02']['href'],self.geometry(shift=10))
        self.assertTrue(guard.b02_checked)

    def test_alignment_diagnostic_signed_edges_detached_and_stale_reset(self):
        guard = self.guard(); self.select(guard)
        for shift in (-11, 11):
            geometry = self.geometry(shift=shift)
            with self.assertRaisesRegex(ValueError, 'CENTER_B02_ALIGNMENT_SHORTFALL'):
                guard.on_window(self.item['assets']['B02']['href'], geometry)
            diagnostic = guard.alignment_diagnostic()
            self.assertTrue(diagnostic['available'])
            self.assertEqual(diagnostic['delta_actual_minus_planned_m'], [shift, 0, shift, 0])
            self.assertEqual(diagnostic['abs_delta_m'], [11, 0, 11, 0])
            self.assertAlmostEqual(diagnostic['excess_over_tolerance_m'][0], .999999)
            self.assertFalse(guard.b02_checked)
            geometry['window_transform'][2] = 0
            diagnostic['actual_bounds_m'][0] = 0
            self.assertNotEqual(guard.alignment_diagnostic()['actual_bounds_m'][0], 0)
            self.assertNotIn('https', json.dumps(guard.alignment_diagnostic()))
        guard.on_window(self.item['assets']['SCL']['href'], self.geometry())
        self.assertIsNone(guard.alignment_diagnostic())
        guard.on_window(self.item['assets']['B02']['href'], self.geometry())
        self.assertIsNone(guard.alignment_diagnostic())

    def test_alignment_diagnostic_boundary_and_unavailable_do_not_change_guard(self):
        guard = self.guard(); self.select(guard)
        # Isolate the exact comparison boundary from large-coordinate subtraction rounding.
        planned = (0., 0., 0., 0.)
        for shift in (-10.000001, 10.000001):
            actual = tuple(v+shift for v in planned)
            with patch.object(subject, '_rectangle') as rectangle, patch.object(subject, '_bounds', return_value=actual):
                rectangle.return_value.bounds = planned
                guard.on_window(self.item['assets']['B02']['href'], self.geometry())
            self.assertIsNone(guard.alignment_diagnostic())
        for actual in ((float('nan'), 0., 0., 0.), (float('inf'), 0., 0., 0.)):
            with patch.object(subject, '_bounds', return_value=actual):
                with self.assertRaisesRegex(ValueError, 'CENTER_B02_ALIGNMENT_SHORTFALL'):
                    guard.on_window(self.item['assets']['B02']['href'], self.geometry())
            self.assertFalse(guard.alignment_diagnostic()['available'])
        with patch.object(subject, '_rectangle') as rectangle, \
             patch.object(subject, '_bounds', return_value=(1e308, 0., 1e308, 1.)):
            rectangle.return_value.bounds = (-1e308, 0., -1e308, 1.)
            with self.assertRaisesRegex(ValueError, 'CENTER_B02_ALIGNMENT_SHORTFALL'):
                guard.on_window(self.item['assets']['B02']['href'], self.geometry())
        self.assertFalse(guard.alignment_diagnostic()['available'])

    def test_alignment_diagnostic_formatter_failure_preserves_original_error(self):
        guard = self.guard(); self.select(guard)
        # _metric_crs is still the real projected-metre validator; formatting alone fails.
        crs = MagicMock(); crs.to_epsg.side_effect = RuntimeError('https://private/token')
        guard._record_alignment_failure((0., 0., 1., 1.), (11., 0., 12., 1.), crs, self.geometry())
        self.assertEqual(guard.alignment_diagnostic()['reason'], 'ALIGNMENT_DIAGNOSTIC_UNAVAILABLE')
        with patch.object(subject.DeficitCandidateLiveGuard, '_record_alignment_failure', wraps=guard._record_alignment_failure):
            with self.assertRaisesRegex(ValueError, 'CENTER_B02_ALIGNMENT_SHORTFALL'):
                guard.on_window(self.item['assets']['B02']['href'], self.geometry(shift=11))
        with patch.object(guard, '_record_alignment_failure', side_effect=RuntimeError('secret diagnostic failure')):
            with self.assertRaisesRegex(ValueError, 'CENTER_B02_ALIGNMENT_SHORTFALL'):
                guard.on_window(self.item['assets']['B02']['href'], self.geometry(shift=-11))
        self.assertIsNone(guard.alignment_diagnostic())

    def test_parent_scl_label_asset_and_cross_split_protections(self):
        guard = self.guard()
        guard.on_window(self.item['assets']['SCL']['href'],self.geometry())
        self.assertFalse(guard.b02_checked)
        with self.assertRaisesRegex(ValueError,'SCENE_REQUIRED_BEFORE_IMAGERY'):
            guard.on_window(self.item['assets']['B02']['href'],self.geometry())
        self.select(guard)
        guard.on_window(guard.label_url,self.geometry(width=2048,height=2048))
        self.assertFalse(guard.b02_checked)
        with self.assertRaisesRegex(ValueError,'UNDECLARED_SELECTED_ASSET'):
            guard.on_window('https://example.org/wrong.tif',self.geometry())
        seed = {**self.seed,'scenes':[{'scene_id':self.item['id'],'split':'train'}]}
        with self.assertRaisesRegex(ValueError,'TARGET_SCENE_SPLIT_OR_CLAIM_CONFLICT'):
            self.select(self.guard(seed=seed))

    def test_binding_size_owner_aoi_and_historical_window_mutations_block(self):
        for change in ('size','owner','bbox'):
            job = copy.deepcopy(self.job)
            if change == 'size': job['config']['window_size'] = 256
            if change == 'owner': job['key'] = None
            if change == 'bbox': job['config']['aois'][0]['bbox'][0] += .01
            guard = self.guard(job=job)
            with self.assertRaises(ValueError): guard.on_window(self.item['assets']['SCL']['href'],self.geometry())
        from shapely.geometry import Polygon
        history = [{'crs':self.target['target_footprint_native']['crs'],
                    'bounds':list(Polygon(self.target['target_footprint_native']['corners']).bounds)}]
        guard = self.guard(windows=TargetedWindowClaims(history)); self.select(guard)
        with self.assertRaisesRegex(ValueError,'LIVE_SUPPORT_WINDOW_OVERLAP'):
            guard.on_window(self.item['assets']['B02']['href'],self.geometry())

    def test_service_hook_rejects_before_pixel_read(self):
        from app.data import service
        import rasterio
        from rasterio.crs import CRS
        from affine import Affine
        guard = self.guard(); self.select(guard)
        bad = self.geometry(shift=11); dataset = MagicMock()
        dataset.__enter__.return_value = dataset
        dataset.crs = CRS.from_user_input(bad['crs']); dataset.width = dataset.height = 4096
        dataset.bounds = (0,0,40960,40960); dataset.transform = Affine(*bad['window_transform'])
        dataset.index.return_value = (1024,1024)
        dataset.window_transform.return_value = Affine(*bad['window_transform'])
        url = self.item['assets']['B02']['href']
        with patch.object(service,'resolve_asset_url',return_value=url), \
             patch.object(service,'HTTPRangeReader'), patch.object(rasterio,'open',return_value=dataset):
            with self.assertRaisesRegex(ValueError,'CENTER_B02_ALIGNMENT_SHORTFALL'):
                service._read_cog_window_impl(url,self.aoi['bbox'],1024,1024**2,{},
                    window_guard=lambda geometry:guard.on_window(url,geometry))
        dataset.read.assert_not_called(); self.assertFalse(guard.b02_checked)
        self.assertEqual(guard.alignment_diagnostic()['code'], 'CENTER_B02_ALIGNMENT_SHORTFALL')

    def test_preflight_and_live_guard_preserve_all_six_fixed_splits(self):
        from pyproj import Transformer
        centers = {'south_sulawesi':(119,-5),'gorontalo':(123,.5),'southeast_sulawesi':(122,-4),
                   'banten':(106,-6),'west_java':(108,-7),'east_java':(113,-8)}
        splits = set()
        for province,(lon,lat) in centers.items():
            with self.subTest(province=province):
                candidate = copy.deepcopy(self.candidate)
                epsg = (32600 if lat>=0 else 32700)+int((lon+180)//6)+1
                crs = 'EPSG:'+str(epsg)
                x,y = Transformer.from_crs(4326,crs,always_xy=True).transform(lon,lat)
                inverse = Transformer.from_crs(crs,4326,always_xy=True)
                pts = [inverse.transform(xx,yy) for xx,yy in [(x-5120,y+5120),(x+5120,y+5120),
                                                              (x+5120,y-5120),(x-5120,y-5120)]]
                candidate.update(province=province,fixed_split=FIXED_PROVINCE_SPLITS[province],
                    lon=lon,lat=lat,grid_crs=crs,spatial_window_id='centers182-'+province,
                    bbox=[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)])
                self.proposal['candidates'] = [candidate]; self.update_proposal()
                self.request['selected'] = [{'spatial_window_id':candidate['spatial_window_id'],'year':2024}]
                result, _, _ = self.run_prepare()
                self.assertTrue(result['local_checks_passed'],result)
                self.job,self.target = result['job_proposals'][0],result['targets'][0]
                self.aoi = self.job['config']['aois'][0]
                self.item['id'] = 'S2A_MSIL2A_20240601T030405_R000_T%02d%s_20240601T040405' % (
                    epsg%100,'NAA' if lat>=0 else 'MAA')
                guard = self.guard(); self.select(guard)
                guard.on_window(self.item['assets']['B02']['href'],self.geometry())
                self.assertTrue(guard.b02_checked); splits.add(self.job['split'])
        self.assertEqual(splits,{'train','val','test'})


if __name__ == '__main__': unittest.main()
