from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
from pathlib import Path
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.data.targeted_execution import TargetedPreparationController
from app.data.targeted_asset_geometry import inspect_targeted_asset_geometry
from app.data.targeted_scene_claims import SceneClaimRegistry


class TargetedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'data').mkdir()
        self.output = self.root/'data'/'new-targets'; self.output.mkdir()
        for name, resolution in [('b02.tif', .001), ('label.tif', .002)]:
            with rasterio.open(self.root/'data'/name, 'w', driver='GTiff', count=1,
                               dtype='uint8', width=256, height=256, crs='EPSG:4326',
                               transform=from_origin(105, -6, resolution, resolution)) as ds:
                ds.write(np.ones((256, 256), dtype='uint8'), 1)
        self.seed = {'schema_version': 1, 'kind': 'DECLARED_SCENE_SPLIT_HISTORY',
                     'source_manifest_sha256': 'a'*64, 'scenes': []}
        self.registry = SceneClaimRegistry(self.seed)
        self.geometry = {'schema_version': 1, 'kind': 'TARGETED_ASSET_GEOMETRY_REQUEST',
                         'target_year': 2025, 'image_year': 2025, 'label_year': 2025,
                         'target_bbox_wgs84': [105.01, -6.2, 105.2, -6.01],
                         **{role+'_ref': {'path': 'data/'+name, 'sha256': hashlib.sha256(
                             (self.root/'data'/name).read_bytes()).hexdigest()}
                            for role, name in [('image', 'b02.tif'), ('label', 'label.tif')]}}

    def tearDown(self):
        self.temp.cleanup()

    def controller(self, split='val', registry=None, parent=None):
        return TargetedPreparationController(self.root, parent or self.output, split, registry or self.registry)

    def request(self, name='target-a', scene='scene-a', owner='worker-a', split='val'):
        return {'schema_version': 1, 'scene_id': scene, 'split': split, 'owner_id': owner,
                'output_name': name, 'geometry_request': copy.deepcopy(self.geometry)}

    def race(self, pairs):
        barrier = Barrier(len(pairs))
        def run(pair):
            barrier.wait(timeout=10)
            return pair[0].prepare(pair[1])
        with ThreadPoolExecutor(max_workers=len(pairs)) as pool:
            return list(pool.map(run, pairs))

    def test_actual_native_assets_reserve_without_execution_or_source_changes(self):
        before = {p: p.read_bytes() for p in (self.root/'data').glob('*.tif')}
        request = self.request(); initial = copy.deepcopy(request)
        out = self.controller().prepare(request)
        self.assertEqual(out['status'], 'LOCAL_PREPARED_EXECUTION_BLOCKED', out)
        self.assertTrue(out['output_reserved']); self.assertEqual(list((self.output/'target-a').iterdir()), [])
        self.assertTrue(out['asset_geometry']['local_bytes_verified'])
        self.assertFalse(out['asset_geometry']['same_grid_asserted'])
        for key in ('execution_supported', 'inventory_verified', 'budget_verified', 'rate_limit_verified',
                    'quality_verified', 'preprocessing_complete', 'settlement_complete', 'training_ready'):
            self.assertFalse(out[key])
        self.assertEqual(initial, request)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.root/'data').glob('*.tif')})

    def test_existing_directory_or_file_never_overwritten(self):
        path = self.output/'target-a'; path.mkdir(); (path/'keep').write_bytes(b'original')
        self.assertEqual(self.controller().prepare(self.request())['issue'], 'OUTPUT_ALREADY_EXISTS')
        self.assertEqual((path/'keep').read_bytes(), b'original')
        other = self.output/'target-file'; other.write_bytes(b'file')
        self.assertEqual(self.controller().prepare(self.request('target-file'))['issue'], 'OUTPUT_ALREADY_EXISTS')
        self.assertEqual(other.read_bytes(), b'file'); self.assertEqual(self.registry.snapshot()['claim_count'], 0)

    def test_exclusive_output_race_one_winner(self):
        outcomes = self.race([(self.controller(), self.request()),
                              (self.controller(), self.request(scene='other', owner='worker-b'))])
        self.assertEqual(sum(o['output_reserved'] for o in outcomes), 1)
        self.assertEqual([o['issue'] for o in outcomes].count('OUTPUT_ALREADY_EXISTS'), 1)
        self.assertEqual(self.registry.snapshot()['claim_count'], 1)

    def test_shared_scene_race_releases_only_loser_empty_output(self):
        outcomes = self.race([(self.controller(), self.request()),
                              (self.controller(), self.request('target-b', owner='worker-b'))])
        self.assertEqual(sum(o['status'] == 'LOCAL_PREPARED_EXECUTION_BLOCKED' for o in outcomes), 1)
        loser = next(o for o in outcomes if o['issue'] == 'SCENE_ALREADY_CLAIMED')
        self.assertEqual(loser['cleanup'], 'OWN_EMPTY_RESERVATION_RELEASED')
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_fixed_split_and_seeded_split_veto(self):
        self.assertEqual(self.controller().prepare(self.request(split='train'))['issue'], 'FIXED_SPLIT_CONFLICT')
        seed = copy.deepcopy(self.seed); seed['scenes'] = [{'scene_id': 'scene-a', 'split': 'test'}]
        out = self.controller(registry=SceneClaimRegistry(seed)).prepare(self.request())
        self.assertEqual(out['issue'], 'DECLARED_SPLIT_CONFLICT')
        self.assertEqual(out['cleanup'], 'OWN_EMPTY_RESERVATION_RELEASED')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_pin_failure_releases_own_empty_output_and_keeps_claim(self):
        value = self.request(); value['geometry_request']['image_ref']['sha256'] = 'f'*64
        out = self.controller().prepare(value)
        self.assertEqual(out['issue'], 'FILE_PIN_MISMATCH')
        self.assertEqual(out['cleanup'], 'OWN_EMPTY_RESERVATION_RELEASED')
        self.assertEqual(self.registry.snapshot()['claim_count'], 1)
        retry = self.controller().prepare(self.request('target-b', owner='other'))
        self.assertEqual(retry['issue'], 'SCENE_ALREADY_CLAIMED')
        replay = self.controller().prepare(self.request('target-c'))
        self.assertEqual(replay['issue'], 'SCENE_CLAIM_REPLAY_REQUIRES_EXISTING_OUTPUT')
        self.assertEqual(replay['cleanup'], 'OWN_EMPTY_RESERVATION_RELEASED')

    def test_failure_preserves_other_files_and_existing_reservations(self):
        (self.output/'other-reservation').mkdir()
        def inspect(*args):
            (self.output/'target-a'/'foreign-file').write_bytes(b'keep')
            return {'local_bytes_verified': False, 'issue': 'FILE_PIN_MISMATCH'}
        with patch('app.data.targeted_execution.inspect_targeted_asset_geometry', side_effect=inspect):
            out = self.controller().prepare(self.request())
        self.assertEqual(out['cleanup'], 'PRESERVED')
        self.assertEqual((self.output/'target-a'/'foreign-file').read_bytes(), b'keep')
        self.assertTrue((self.output/'other-reservation').is_dir())

    def test_changed_parent_identity_preserves_old_directory(self):
        old = self.output.with_name('renamed-parent')
        def inspect(*args):
            self.output.rename(old); self.output.mkdir()
            return inspect_targeted_asset_geometry(*args)
        with patch('app.data.targeted_execution.inspect_targeted_asset_geometry', side_effect=inspect):
            out = self.controller().prepare(self.request())
        self.assertEqual(out['issue'], 'OUTPUT_PARENT_CHANGED')
        self.assertEqual(out['cleanup'], 'PRESERVED'); self.assertTrue((old/'target-a').is_dir())

    def test_replaced_leaf_not_removed_on_failure(self):
        def inspect(*args):
            (self.output/'target-a').rename(self.output/'original-owned')
            (self.output/'target-a').mkdir()
            return inspect_targeted_asset_geometry(*args)
        with patch('app.data.targeted_execution.inspect_targeted_asset_geometry', side_effect=inspect):
            out = self.controller().prepare(self.request())
        self.assertEqual(out['issue'], 'OUTPUT_RESERVATION_CHANGED')
        self.assertEqual(out['cleanup'], 'PRESERVED')
        self.assertTrue((self.output/'target-a').is_dir())
        self.assertTrue((self.output/'original-owned').is_dir())

    def test_reparse_directory_attribute_rejected_without_symlink_privilege(self):
        from types import SimpleNamespace
        import stat
        from app.data.targeted_execution import _directory_identity
        attributes = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_file_attributes=0x400,
                                     st_dev=1, st_ino=2)
        with patch.object(Path, 'lstat', return_value=attributes):
            with self.assertRaisesRegex(ValueError, 'OUTPUT_PATH_INVALID'):
                _directory_identity(self.output)

    def test_unsafe_names_bad_controller_and_request_rejected(self):
        controller = self.controller()
        for name in ('../escape', 'a/b', 'a\\b', 'CON', 'COM1', 'x.', 'x ', '', 'A'*81):
            self.assertEqual(controller.prepare(self.request(name))['issue'], 'REQUEST_INVALID')
        for parent in (self.root, self.root/'data', self.output/'missing'):
            self.assertEqual(self.controller(parent=parent).prepare(self.request())['issue'], 'CONTROLLER_INVALID')
        value = self.request(); value['schema_version'] = True
        self.assertEqual(controller.prepare(value)['issue'], 'REQUEST_INVALID')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_symlink_parent_or_leaf_rejected_without_touching_target(self):
        link = self.root/'data'/'alias'
        try:
            link.symlink_to(self.output, target_is_directory=True)
        except OSError:
            self.skipTest('OS does not permit symlink creation')
        self.assertEqual(self.controller(parent=link).prepare(self.request())['issue'], 'CONTROLLER_INVALID')
        target = self.output/'preserve'; target.mkdir(); (target/'keep').write_bytes(b'original')
        (self.output/'target-a').symlink_to(target, target_is_directory=True)
        self.assertEqual(self.controller().prepare(self.request())['issue'], 'OUTPUT_ALREADY_EXISTS')
        self.assertEqual((target/'keep').read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
