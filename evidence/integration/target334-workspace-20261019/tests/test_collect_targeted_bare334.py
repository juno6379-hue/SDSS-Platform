"""Unit 334 isolated tests: 128MiB explicit preflight and LedgerMetadataIO adapter.

Verifies:
1. 64MiB legacy bottleneck fails closed with FILE_LIMIT on 69.6MB source manifest.
2. Explicit v3 128MiB preflight resolves the bottleneck and validates the 69.6MB source manifest.
3. LedgerMetadataIO adapter integrates with CollectionLedger under explicit profile.
4. Preserves 136,314,880B pending reservation across reservation, execution and settlement.
5. Fails closed on invalid transitions, unowned batches, and pin drifts.
6. Dry-run execution under explicit v3 profile.
"""
import copy
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / 'scripts'))
sys.path.insert(0, str(WORKSPACE / 'backend'))
sys.path.insert(0, str(WORKSPACE / 'tests'))

import collect_targeted_bare as module
from app.ml import manifest_resource_profile as profile
from app.data import targeted_bare_plan as plan_module
from app.data import targeted_source_profile as contract
from app.data.targeted_source_profile import MARKER as SOURCE_MARKER, SUPPORT_MARKER
from app.data.ledger_metadata_io import LedgerMetadataIO
from app.data.budget import CollectionLedger


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


class Target334Fixture:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.data_dir = self.root / 'data'
        self.evidence_dir = self.root / 'evidence/integration'
        self.output_dir = self.root / 'data/first-group-training-esri-v1'
        self.budget_dir = self.root / 'data/first-group-training-budget'
        self.configs_dir = self.root / 'configs'
        for d in (self.data_dir, self.evidence_dir, self.output_dir / 'sources',
                  self.output_dir / 'patches', self.budget_dir, self.configs_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.affine = from_origin(500000, 9300000, 10, 10)
        self.label_path = self.data_dir / 'label.tif'
        values = np.ones((512, 512), dtype='uint8')
        values[:256, :256] = 8
        with rasterio.open(self.label_path, 'w', driver='GTiff', count=1, dtype='uint8',
                           width=512, height=512, transform=self.affine, crs='EPSG:32748') as ds:
            ds.write(values, 1)

        self.patch_dir = self.output_dir / 'patches/original'
        self.patch_dir.mkdir(parents=True, exist_ok=True)
        self.existing_image = self.patch_dir / 'image.tif'
        with rasterio.open(self.existing_image, 'w', driver='GTiff', count=1, dtype='uint8',
                           width=16, height=16, transform=from_origin(470000, 9300000, 10, 10), crs='EPSG:32748') as ds:
            ds.write(np.ones((16, 16), dtype='uint8'), 1)
        self.existing_label = self.patch_dir / 'label.tif'
        with rasterio.open(self.existing_label, 'w', driver='GTiff', count=1, dtype='uint8',
                           width=16, height=16, transform=from_origin(470000, 9300000, 10, 10), crs='EPSG:32748') as ds:
            ds.write(np.ones((16, 16), dtype='uint8'), 1)
        self.existing_quality = self.patch_dir / 'quality.tif'
        with rasterio.open(self.existing_quality, 'w', driver='GTiff', count=1, dtype='uint8',
                           width=16, height=16, transform=from_origin(470000, 9300000, 10, 10), crs='EPSG:32748') as ds:
            ds.write(np.ones((16, 16), dtype='uint8'), 1)

        convert = Transformer.from_crs(32748, 4326, always_xy=True)
        native = [self.affine * p for p in ((0, 0), (256, 0), (256, 256), (0, 256))]
        xy = [convert.transform(*p) for p in native]
        self.native_corners = [list(p) for p in native]
        self.bbox = [min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy)]

        self.boundary_path = self.data_dir / 'boundary.json'
        boundary = {'features': [{'properties': {'province_id': 'banten'}, 'geometry': {'type': 'Polygon',
                    'coordinates': [[[self.bbox[0] - .2, self.bbox[1] - .2],
                                     [self.bbox[2] + .2, self.bbox[1] - .2],
                                     [self.bbox[2] + .2, self.bbox[3] + .2],
                                     [self.bbox[0] - .2, self.bbox[3] + .2],
                                     [self.bbox[0] - .2, self.bbox[1] - .2]]]}}]}
        write_json(self.boundary_path, boundary)

        self.aggregate_path = self.output_dir / 'annual-window-report.json'
        self.original_scene = {
            'patch_id': 'original',
            'scene_id': 'original-scene',
            'quality_status': 'quality_eligible',
            'split': 'val',
            'province': 'banten',
            'year': 2025,
            'image_path': str(self.existing_image),
            'label_path': str(self.existing_label),
            'quality_mask_path': str(self.existing_quality),
            'source_window': {
                'path': str(self.existing_image),
                'sha256': sha(self.existing_image)
            },
            'patch_sha256': {
                'image': sha(self.existing_image),
                'label': sha(self.existing_label),
                'quality_mask': sha(self.existing_quality)
            },
            'sample_class_coverage': {'1': 65536}
        }
        self.aggregate = {
            'scenes': [copy.deepcopy(self.original_scene)],
            'historical_noneligible_patches': [],
            'source_manifests': []
        }
        write_json(self.aggregate_path, self.aggregate)

        self.lineage_path = self.data_dir / 'lineage.json'
        source_lineage = {
            'year': '2025',
            'label_year': 2025,
            'label_source_url': 'https://example.invalid/lc2025/reference.tif',
            'source_crops': {'raw-esri_io.tif': {'path': str(self.label_path), 'sha256': sha(self.label_path)}}
        }
        write_json(self.lineage_path, {'scenes': [source_lineage]})

        self.proposal_path = self.evidence_dir / 'proposal.json'
        proposal = {
            'ranked_windows': [{
                'year': 2025,
                'province': 'banten',
                'fixed_split': 'val',
                'source_crop_path': 'data/label.tif',
                'source_crop_sha256': sha(self.label_path),
                'local_window_xy': [0, 0],
                'declared_weak_label_bare_pixels': 65536
            }]
        }
        write_json(self.proposal_path, proposal)

        # Historical ledgers
        self.hist1_path = self.root / 'data/first-group-annual/run-result.json'
        self.hist2_path = self.root / 'data/first-group-recovery32/run-result.json'
        write_json(self.hist1_path, {'reserved_or_transferred_bytes_including_prior': 1000000})
        write_json(self.hist2_path, {'reserved_or_transferred_bytes_including_prior': 2000000})
        self.historical_refs = [
            {'path': str(self.hist1_path.resolve()), 'sha256': sha(self.hist1_path)},
            {'path': str(self.hist2_path.resolve()), 'sha256': sha(self.hist2_path)}
        ]

        # Pending reservation source directory with config.json and raw-B02.tif
        self.pending_dir = self.output_dir / 'sources/preserved-old-pending'
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.pending_config = {'aois': [{'id': 'banten', 'bbox': [105, -7, 106, -6]}], 'window_size': 256}
        self.pending_config_sha = hashlib.sha256(json.dumps(self.pending_config, sort_keys=True).encode()).hexdigest()
        write_json(self.pending_dir / 'config.json', self.pending_config)

        self.pending_b02 = self.pending_dir / 'raw-B02.tif'
        with rasterio.open(self.pending_b02, 'w', driver='GTiff', count=1, dtype='uint8',
                           width=256, height=256, transform=from_origin(460000, 9300000, 10, 10), crs='EPSG:32748') as ds:
            ds.write(np.ones((256, 256), dtype='uint8'), 1)

        # Active ledger with preserved pending 136,314,880B
        self.ledger_path = self.budget_dir / 'global-ledger.json'
        self.pending_reservation = {
            'status': 'pending',
            'reserved_bytes': 136314880,
            'charged_bytes': 136314880,
            'config_sha256': self.pending_config_sha
        }
        self.ledger_state = {
            'version': 1,
            'historical_ledgers': copy.deepcopy(self.historical_refs),
            'historical_charged_bytes': 2000000,
            'additional_maximum_bytes': 4 * 1024**3,
            'new_charged_bytes': 136314880,
            'external_research_metadata_body_bytes': 3675728,
            'combined_maximum_bytes': 2000000 + 4 * 1024**3,
            'batches': {
                'preserved-old-pending': copy.deepcopy(self.pending_reservation)
            },
            'rate_limit_active': False
        }
        write_json(self.ledger_path, self.ledger_state)

        # Base config
        self.base_config_path = self.configs_dir / 'first-group.collection.json'
        base_config = {
            'collection': 'sentinel-2-l2a',
            'endpoint': 'earth-search',
            'max_asset_bytes': 268435456,
            'max_total_bytes': 64 * 1024**2,
            'bands': ['blue', 'green', 'red', 'nir', 'swir16', 'swir22'],
            'cloud_cover': 20,
            'window_size': 256,
            'aois': [{'id': 'banten', 'bbox': self.bbox}]
        }
        write_json(self.base_config_path, base_config)

        # Target definitions
        self.target_a = {
            'target_id': 'target-bare-a',
            'proposal_window_index': 0,
            'province': 'banten',
            'fixed_split': 'val',
            'year': 2025,
            'source_label_ref': {'path': 'data/label.tif', 'sha256': sha(self.label_path)},
            'source_lineage_ref': {'path': 'data/lineage.json', 'sha256': sha(self.lineage_path)},
            'source_label_window': [0, 0, 256, 256],
            'source_label_grid': {'crs': 'EPSG:32748', 'transform': list(self.affine)[:6], 'width': 512, 'height': 512},
            'target_bbox_wgs84': self.bbox,
            'target_footprint_native': {'crs': 'EPSG:32748', 'corners': self.native_corners},
            'declared_bare_pixels': 65536
        }

        self.plan_v1 = {
            'schema_version': 1,
            'kind': 'TARGETED_BARE_256_COLLECTION_PLAN',
            'proposal_ref': {'path': 'evidence/integration/proposal.json', 'sha256': sha(self.proposal_path)},
            'current_manifest_ref': {'path': 'data/first-group-training-esri-v1/annual-window-report.json', 'sha256': sha(self.aggregate_path)},
            'boundary_ref': {'path': 'data/boundary.json', 'sha256': sha(self.boundary_path)},
            'policy': {**contract.POLICY, 'maximum_new_batches': 1},
            'targets': [copy.deepcopy(self.target_a)]
        }

        self.request_v1 = {
            'schema_version': 1,
            'maximum_batches': 1,
            'plan': copy.deepcopy(self.plan_v1),
            'ledger_ref': {'path': 'data/first-group-training-budget/global-ledger.json', 'sha256': sha(self.ledger_path)}
        }

        # v3 explicit request
        self.plan_v2 = contract.upgrade_plan_v1(self.plan_v1, dict(contract.MARKER))
        self.request_v3 = {
            'schema_version': 3,
            'maximum_batches': 1,
            'manifest_profile': dict(SOURCE_MARKER),
            'local_support_profile': dict(SUPPORT_MARKER),
            'plan': copy.deepcopy(self.plan_v2),
            'ledger_ref': {'path': 'data/first-group-training-budget/global-ledger.json', 'sha256': sha(self.ledger_path)}
        }

    def expand_aggregate_to_69m(self, target_bytes=69564847):
        """Pad aggregate JSON with trailing spaces up to target_bytes (~69.6MB)."""
        content = self.aggregate_path.read_bytes()
        assert len(content) < target_bytes
        padding_needed = target_bytes - len(content)
        with self.aggregate_path.open('ab') as stream:
            remaining = padding_needed
            chunk = b' ' * min(1024 * 1024, remaining)
            while remaining > 0:
                to_write = min(len(chunk), remaining)
                stream.write(chunk[:to_write])
                remaining -= to_write
        new_size = self.aggregate_path.stat().st_size
        assert new_size == target_bytes
        new_sha = sha(self.aggregate_path)
        # Update references in plans
        self.request_v1['plan']['current_manifest_ref']['sha256'] = new_sha
        self.request_v3['plan']['current_manifest_ref']['sha256'] = new_sha
        return new_sha


class Target334IsolatedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.f = Target334Fixture(self.temp.name)

    def tearDown(self):
        module.service.configure_request_circuit(None)
        self.temp.cleanup()

    def test_legacy_v1_fails_closed_with_file_limit_on_69m_manifest(self):
        """Verifies the legacy 64MiB bottleneck: 69.6MB manifest fails closed."""
        self.f.expand_aggregate_to_69m()
        req_sha = module.digest(self.f.request_v1)
        # Legacy validate_request calls prepare_targeted_bare_jobs which caps source at 64MiB
        with self.assertRaises(ValueError) as ctx:
            module.validate_request(self.f.root, self.f.request_v1, req_sha)
        err = str(ctx.exception)
        self.assertIn('TARGETED_LOCAL_PLAN_', err)
        self.assertIn('FILE_LIMIT', err)

    def test_explicit_v3_preflight_resolves_69m_bottleneck(self):
        """Verifies that explicit v3 128MiB profile processes 69.6MB manifest without FILE_LIMIT."""
        self.f.expand_aggregate_to_69m()
        req_sha = module.digest(self.f.request_v3)
        checked = module.validate_request(self.f.root, self.f.request_v3, req_sha)
        self.assertEqual(checked['root'], self.f.root)
        self.assertEqual(len(checked['jobs']), 1)
        self.assertEqual(checked['jobs'][0]['nominal_patches'], 1)
        self.assertEqual(checked['manifest_profile'], dict(SOURCE_MARKER))
        self.assertEqual(checked['local_support_profile'], dict(SUPPORT_MARKER))
        # Verify source sha matches
        self.assertEqual(checked['source_sha256'], sha(self.f.aggregate_path))

    def test_explicit_dry_run_returns_verified_status_without_ledger_writes(self):
        """Verifies dry-run under v3 returns LOCAL_DISPATCH_INPUTS_VERIFIED without mutating ledger."""
        self.f.expand_aggregate_to_69m()
        ledger_before = self.f.ledger_path.read_bytes()
        req_sha = module.digest(self.f.request_v3)
        result = module.run_targeted(self.f.root, self.f.request_v3, req_sha, execute=False)
        self.assertEqual(result['status'], 'LOCAL_DISPATCH_INPUTS_VERIFIED')
        self.assertFalse(result['executed'])
        self.assertFalse(result['live_scene_and_window_verified'])
        self.assertFalse(result['learning_ready'])
        self.assertEqual(result['manifest_profile'], dict(SOURCE_MARKER))
        self.assertEqual(result['local_support_profile'], dict(SUPPORT_MARKER))
        self.assertEqual(self.f.ledger_path.read_bytes(), ledger_before)

    def test_execution_with_ledger_metadata_io_preserves_old_pending_reservation(self):
        """Verifies that execute=True binds LedgerMetadataIO and preserves 136,314,880B old pending."""
        self.f.expand_aggregate_to_69m()
        req_sha = module.digest(self.f.request_v3)

        def mock_collect(config, directory, **kwargs):
            self.assertTrue(kwargs['execute'])
            self.assertIn('collection_guard', kwargs)
            kwargs['collection_guard'].b02_checked = True
            write_json(directory / 'window-state.json', {'http_body_bytes': 2048})
            return {'scenes': [], 'batch_circuit_breaker': {}}

        mock_row = {
            'patch_id': 'target-bare-patch',
            'scene_id': 'target-scene',
            'quality_status': 'quality_eligible',
            'split': 'val',
            'province': 'banten',
            'year': 2025,
            'sample_class_coverage': {'8': 500, '1': 65036}
        }

        with patch.object(module, 'collect_windows', side_effect=mock_collect), \
             patch.object(module, 'materialize_patches', return_value=[mock_row]):
            result = module.run_targeted(self.f.root, self.f.request_v3, req_sha, execute=True)

        self.assertEqual(result['status'], 'BOUNDED_TARGETED_STAGE_FINISHED')
        self.assertTrue(result['executed'])
        self.assertEqual(result['execution']['finalized_batches'], 1)
        self.assertFalse(result['learning_ready'])
        self.assertFalse(result['scientific_accuracy_validated'])

        # Verify ledger state on disk:
        state = json.loads(self.f.ledger_path.read_text(encoding='utf-8'))
        # 136,314,880B pending must be EXACTLY preserved
        self.assertIn('preserved-old-pending', state['batches'])
        self.assertEqual(state['batches']['preserved-old-pending'], self.f.pending_reservation)

        # Newly executed batch must be settled
        job_key = result['batches'][0]['key']
        self.assertIn(job_key, state['batches'])
        self.assertEqual(state['batches'][job_key]['status'], 'settled')
        self.assertEqual(state['batches'][job_key]['charged_bytes'], 2048)

        # Net charged bytes must reflect old pending + new batch charged bytes
        expected_charged = 136314880 + 2048
        self.assertEqual(state['new_charged_bytes'], expected_charged)

    def test_ledger_adapter_fails_closed_on_invalid_transition(self):
        """Verifies fail-closed when an invalid transition attempts to touch preserved pending."""
        self.f.expand_aggregate_to_69m()
        req_sha = module.digest(self.f.request_v3)

        def mock_collect(config, directory, **kwargs):
            kwargs['collection_guard'].b02_checked = True
            write_json(directory / 'window-state.json', {'http_body_bytes': 100})
            return {'scenes': [], 'batch_circuit_breaker': {}}

        # Force a transition failure by corrupting the ledger during work
        def corrupt_ledger_during_work(config, directory, **kwargs):
            # Tamper with the old pending batch on disk while worker is running
            state = json.loads(self.f.ledger_path.read_text(encoding='utf-8'))
            state['batches']['preserved-old-pending']['charged_bytes'] = 999
            write_json(self.f.ledger_path, state)
            kwargs['collection_guard'].b02_checked = True
            write_json(directory / 'window-state.json', {'http_body_bytes': 100})
            return {'scenes': [], 'batch_circuit_breaker': {}}

        with patch.object(module, 'collect_windows', side_effect=corrupt_ledger_during_work), \
             patch.object(module, 'materialize_patches', return_value=[]):
            with self.assertRaises(module.TargetedExecutionFailure) as ctx:
                module.run_targeted(self.f.root, self.f.request_v3, req_sha, execute=True)

        progress = ctx.exception.progress
        self.assertEqual(progress['reservation_status'], 'ALL_ATTEMPTS_CONFIRMED_RESERVED')
        self.assertEqual(progress['settlement_status'], 'INCOMPLETE_OR_UNVERIFIED')

    def test_contract_validation_rejects_tampered_manifest_marker_before_io(self):
        """Verifies that invalid schema 3 markers fail closed before opening files."""
        tampered_request = copy.deepcopy(self.f.request_v3)
        tampered_request['manifest_profile']['sha256'] = '0' * 64
        with self.assertRaises(contract.TargetSourceContractError):
            module.validate_request(self.f.root, tampered_request, module.digest(tampered_request))

    def test_contract_validation_rejects_missing_support_marker_before_io(self):
        """Verifies that missing support marker fails closed before opening files."""
        tampered_request = copy.deepcopy(self.f.request_v3)
        tampered_request.pop('local_support_profile')
        with self.assertRaises(contract.TargetSourceContractError):
            module.validate_request(self.f.root, tampered_request, module.digest(tampered_request))

    def test_unregistered_batch_key_cannot_be_reserved(self):
        """Verifies that LedgerMetadataIO stops when an unallowed key attempts reservation."""
        with profile.scope(SOURCE_MARKER['name']):
            allowed = {'allowed-batch': 'b' * 64}
            adapter = LedgerMetadataIO(
                root=self.f.root,
                ledger_ref={'path': str(self.f.ledger_path.resolve()), 'sha256': sha(self.f.ledger_path)},
                historical_refs=copy.deepcopy(self.f.historical_refs),
                allowed_batches=allowed,
                manifest_profile=dict(SOURCE_MARKER)
            )
            ledger = CollectionLedger(self.f.ledger_path, [p.resolve() for p, _ in adapter._history],
                                      initial_metadata_charge=3675728, metadata_io=adapter)
            with self.assertRaisesRegex(ValueError, 'LEDGER_RESERVE_NOT_ALLOWED'):
                ledger.reserve('unallowed-key', 1000, 'b' * 64)
            self.assertTrue(adapter._stopped)

    def test_unowned_batch_key_cannot_be_settled(self):
        """Verifies that LedgerMetadataIO stops when attempting to settle an unowned batch."""
        with profile.scope(SOURCE_MARKER['name']):
            allowed = {'allowed-batch': 'b' * 64}
            adapter = LedgerMetadataIO(
                root=self.f.root,
                ledger_ref={'path': str(self.f.ledger_path.resolve()), 'sha256': sha(self.f.ledger_path)},
                historical_refs=copy.deepcopy(self.f.historical_refs),
                allowed_batches=allowed,
                manifest_profile=dict(SOURCE_MARKER)
            )
            ledger = CollectionLedger(self.f.ledger_path, [p.resolve() for p, _ in adapter._history],
                                      initial_metadata_charge=3675728, metadata_io=adapter)
            # Cannot settle preserved-old-pending because it was not reserved by this adapter instance
            with self.assertRaisesRegex(ValueError, 'LEDGER_SETTLE_NOT_OWNED'):
                ledger.settle('preserved-old-pending', 1000)
            self.assertTrue(adapter._stopped)


if __name__ == '__main__':
    unittest.main()
