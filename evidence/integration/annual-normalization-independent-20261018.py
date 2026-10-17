"""Independent requested-year batch checks; fresh Temp checkpoint+18 versions."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.runtime'), str(ROOT / 'backend')]
import torch
from app.dataset_registry import register_version
from app.store import Store
from app.ml.network import TinyUNet
from app.ml import pinned_annual_normalization as module

SOURCE = ROOT / 'backend/app/ml/pinned_annual_normalization.py'
FROZEN = '4589a70425dcdfc1e6f7b9a065929f74860f572284cf9fd8c021a8fb5fc81953'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('state_dict_verified', 'raster_header_verified', 'quality_report_verified', 'quality_mask_verified',
    'source_authority_verified', 'access_authorization_verified', 'other_lineage_parents_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported', 'temporal_year_verified')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geoai-127-independent-')
        self.root = Path(self.temp.name).resolve(); self.store = Store(self.root)
        self.names = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
        self.manifest = dict(normalization_mode='per_scene_product_metadata', bands=list(range(1, 7)),
                             band_names=self.names[:], synthetic=True)
        self.rows = []
        for i in range(6):
            directory = self.root / f'scene-{i}'; directory.mkdir()
            image = directory / 'image.bin'; image.write_bytes(f'opaque non-raster image-{i}'.encode())
            metadata = directory / 'source.xml'; metadata.write_bytes(f'<fixture id="{i}"/>'.encode())
            image_ref = dict(id=f'image-{i}', version='고정 1', sha256=sha(image.read_bytes()))
            metadata_ref = dict(id=f'metadata-{i}', version='고정 1', sha256=sha(metadata.read_bytes()))
            evidence = dict(status='verified_product_metadata', product_id=f'explicit-scene-{i}',
                band_names=self.names[:], scale=.0001, offset=[0] * 6,
                source_url='https://example.invalid/not-contacted',
                source_metadata_path=metadata.relative_to(self.root).as_posix(), source_metadata_sha256=metadata_ref['sha256'])
            evidence_path = directory / 'evidence.json'; evidence_path.write_text(json.dumps(evidence), encoding='utf-8')
            evidence_ref = dict(id=f'evidence-{i}', version='고정 1', sha256=sha(evidence_path.read_bytes()))
            refs = (image_ref, evidence_ref, metadata_ref)
            for role, ref, path in zip(('raster', 'document', 'document'), refs, (image, evidence_path, metadata)):
                source = dict(institution='synthetic fixture', product='product-family-not-scene', license='test only')
                if role == 'raster': source.update(scene_id=f'explicit-scene-{i}', band_names=self.names[:])
                lineage = [] if path != evidence_path else [dict(image_ref, role='normalization_input_image'),
                    dict(metadata_ref, role='normalization_source_metadata')]
                register_version(self.store, dict(schema_version='0.2.0', dataset_id=ref['id'], version=ref['version'],
                    source=source, data_type=role, spatial=dict(bbox=[106, -7, 107, -6], crs='OGC:CRS84'),
                    # Deliberately all2024 while request labels2020..2025.
                    temporal=dict(start='2024-01-01T00:00:00Z', end='2024-12-31T00:00:00Z', calendar='gregorian'),
                    quality_status='RAW', access_class='PUBLIC', sha256=ref['sha256'],
                    artifact_uri=path.relative_to(self.root).as_posix(), lineage=lineage))
            self.rows.append(dict(year=2020 + i, image_ref=image_ref, evidence_ref=evidence_ref, metadata_ref=metadata_ref))
        self.model_dir = self.root / 'models' / 'annual-127'; self.model_dir.mkdir(parents=True)
        self.saved = dict(architecture='tiny_unet', manifest=self.manifest, state_dict=TinyUNet(6).state_dict())
        self.bind_model()

    def tearDown(self): self.temp.cleanup()

    def bind_model(self):
        stream = io.BytesIO(); torch.save(self.saved, stream)
        raw = stream.getvalue(); (self.model_dir / 'best.pt').write_bytes(raw)
        self.model_ref = dict(id='annual-127', version='  명시 모델 127  ', sha256=sha(raw))
        report = dict(model_id='annual-127', checkpoint_sha256=sha(raw), training_state='completed',
                      input_signature=dict(normalization_mode='global', band_names=['DECOY'] * 6))
        raw = json.dumps(report).encode(); (self.model_dir / 'report.json').write_bytes(raw); self.report_sha = sha(raw)
        self.store.put('models', dict(id='annual-127', status='Draft', synthetic=True,
            checkpoint_path='models/annual-127/best.pt', checkpoint_sha256=self.model_ref['sha256'],
            training_report_sha256=self.report_sha, model_version_declaration=dict(schema_version=1,
                source='CALLER_EXPLICIT_REGISTRATION', version=self.model_ref['version'],
                checkpoint_sha256=self.model_ref['sha256'], training_report_sha256=self.report_sha)))

    def read(self, rows=None, ref=None, on_get=None):
        before = self.store.db.read_bytes(); calls = []; get = self.store.get
        def observed(kind, key):
            calls.append((kind, key))
            if on_get: on_get(kind, key)
            return get(kind, key)
        with patch.object(self.store, 'get', observed), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(TinyUNet, 'forward', side_effect=AssertionError('inference')):
            result = module.inspect_pinned_annual_normalization(self.store, self.model_ref if ref is None else ref,
                self.report_sha, self.rows if rows is None else rows)
        self.assertEqual(before, self.store.db.read_bytes())
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'model_observation', 'rows',
            'model_observation_calls', 'scene_observation_calls', 'checked_rows', 'checkpoint_artifact_verified',
            'training_report_artifact_verified', 'registry_references_verified', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'PINNED_MODEL_REQUESTED_YEARS_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        for counter in ('model_observation_calls', 'scene_observation_calls', 'checked_rows'):
            self.assertIs(type(result[counter]), int)
        return result, calls

    def test_actual_two_and_six_rows_one_model_same_manifest_identity_and_label_only(self):
        original = module.read_registered_per_scene_files
        for count in (2, 6):
            manifests = []
            def scene(store, manifest, *refs):
                manifests.append(manifest); return original(store, manifest, *refs)
            with patch.object(module, 'read_registered_per_scene_files', scene): result, calls = self.read(self.rows[:count])
            self.assertEqual(result['status'], 'PINNED_YEARS_MATCHED_UNVERIFIED')
            self.assertEqual(len(calls), 1 + 3 * count)
            self.assertEqual(calls[0], ('models', 'annual-127'))
            self.assertEqual(result['model_observation_calls'], 1)
            self.assertEqual(result['scene_observation_calls'], count)
            self.assertEqual(result['checked_rows'], count)
            self.assertTrue(all(m is result['model_observation']['checkpoint_manifest'] for m in manifests))
            self.assertEqual({r['status'] for r in result['rows']}, {'MATCHED_UNVERIFIED'})
            self.assertIs(result['artifact_bytes_verified'], True)
            self.assertIs(result['temporal_year_verified'], False)

    def test_invalid_shapes_years_refs_and_duplicates_are_pre_store(self):
        variants = [[], self.rows[:1], self.rows + self.rows[:1], tuple(self.rows)]
        for value in (True, '2020', 2020., 1899, 2201):
            rows = copy.deepcopy(self.rows[:2]); rows[0]['year'] = value; variants.append(rows)
        rows = copy.deepcopy(self.rows[:2]); rows.reverse(); variants.append(rows)
        rows = copy.deepcopy(self.rows[:2]); rows[1]['year'] = 2020; variants.append(rows)
        rows = copy.deepcopy(self.rows[:2]); rows[1]['image_ref'] = rows[0]['image_ref']; variants.append(rows)
        rows = copy.deepcopy(self.rows[:2]); rows[0]['metadata_ref'] = rows[0]['image_ref']; variants.append(rows)
        rows = copy.deepcopy(self.rows[:2]); rows[0]['image_ref']['version'] = 'latest'; variants.append(rows)
        rows = copy.deepcopy(self.rows[:2]); rows[0]['extra'] = True; variants.append(rows)
        for rows in variants:
            result, calls = self.read(rows)
            self.assertEqual(result['status'], 'INVALID_INPUT')
            self.assertEqual(calls, [])
            self.assertEqual(result['model_observation_calls'], 0)
            self.assertEqual(result['rows'], [])

    def test_global_valid_batch_one_model_no_scene_calls(self):
        self.manifest['normalization_mode'] = 'global'; self.bind_model()
        with patch.object(module, 'read_registered_per_scene_files', side_effect=AssertionError('scene forbidden')):
            result, calls = self.read()
        self.assertEqual(result['status'], 'OUT_OF_SCOPE')
        self.assertEqual(calls, [('models', 'annual-127')])
        self.assertEqual(result['scene_observation_calls'], 0)
        self.assertEqual({r['status'] for r in result['rows']}, {'NOT_CHECKED'})
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_model_failure_no_scene_reads(self):
        path = self.model_dir / 'best.pt'; path.write_bytes(path.read_bytes() + b'tampered')
        with patch.object(module, 'read_registered_per_scene_files', side_effect=AssertionError('scene forbidden')) as scene:
            result, calls = self.read()
        self.assertEqual(result['status'], 'MODEL_BLOCKED'); scene.assert_not_called()
        self.assertEqual(calls, [('models', 'annual-127')])
        self.assertEqual(result['checked_rows'], 0)
        self.assertEqual(result['scene_observation_calls'], 0)

    def test_failfast_middle_and_last_asset_preserves_partial_rows_not_aggregate(self):
        for index in (1, 5):
            path = self.root / f'scene-{index}' / 'image.bin'; raw = path.read_bytes(); path.write_bytes(raw + b'changed')
            result, calls = self.read()
            self.assertEqual(result['status'], 'SCENE_BLOCKED')
            self.assertEqual(result['checked_rows'], index + 1)
            self.assertEqual(result['scene_observation_calls'], index + 1)
            self.assertEqual(len(calls), 1 + 3 * (index + 1))
            self.assertEqual(result['issue']['year'], 2020 + index)
            self.assertEqual([r['status'] for r in result['rows']],
                ['MATCHED_UNVERIFIED'] * index + ['BLOCKED'] + ['NOT_CHECKED'] * (5 - index))
            self.assertIs(result['checkpoint_artifact_verified'], True)
            self.assertIs(result['registry_references_verified'], False)
            self.assertIs(result['artifact_bytes_verified'], False)
            path.write_bytes(raw)

    def test_request_snapshot_survives_later_caller_mutation(self):
        rows = copy.deepcopy(self.rows[:2])
        def mutate(kind, key):
            if kind == 'models':
                rows[1]['year'] = 2199
                rows[1]['image_ref']['sha256'] = '0' * 64
        result, _ = self.read(rows, on_get=mutate)
        self.assertEqual(result['status'], 'PINNED_YEARS_MATCHED_UNVERIFIED')
        self.assertEqual([r['year'] for r in result['rows']], [2020, 2021])

    def test_different_image_ids_same_bytes_are_not_independence_proof(self):
        # New registered ID/version legitimately pins the same physical asset;
        # uniqueness by identity must not be called physical-scene independence.
        from app.dataset_registry import version_key, canonical_manifest
        first = self.store.get('dataset_versions', version_key(self.rows[0]['image_ref']['id'], '고정 1'))
        second = self.store.get('dataset_versions', version_key(self.rows[1]['image_ref']['id'], '고정 1'))
        # Explicit adversarial Temp metadata fixture preserves each required scene
        # declaration while pointing to identical bytes; no operating mutation.
        second['manifest'].update(artifact_uri=first['manifest']['artifact_uri'], sha256=first['manifest']['sha256'])
        second['manifest'], second['manifest_sha256'] = canonical_manifest(second['manifest'])
        self.store.put('dataset_versions', second)
        self.rows[1]['image_ref']['sha256'] = first['manifest']['sha256']
        evidence = self.store.get('dataset_versions', version_key(self.rows[1]['evidence_ref']['id'], '고정 1'))
        evidence['manifest']['lineage'][0]['sha256'] = first['manifest']['sha256']
        evidence['manifest'], evidence['manifest_sha256'] = canonical_manifest(evidence['manifest'])
        self.store.put('dataset_versions', evidence)
        result, calls = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'PINNED_YEARS_MATCHED_UNVERIFIED')
        self.assertIs(result['temporal_year_verified'], False)
        self.assertIs(result['scientific_accuracy_validated'], False)


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '49d0531440fc062e30e2307a58c9d6c7846a0548'
    checks = []
    for name in ('backend/app/ml/model_checkpoint_manifest.py', 'backend/app/ml/registered_per_scene_files.py',
                 'backend/app/ml/pinned_scene_normalization.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_REQUESTED_YEARS_2_AND_6_ROWS', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        fixture='Fresh actual CPU TinyUNet6 checkpoint and18 actual TempStore dataset registrations; requested2020..2025/all manifest temporal2024.',
        operating_Store_API_registration_checkpoint_reads_or_writes=0, inference_training_calls=0,
        UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Request years are labels only, not verified manifest/header acquisition years. Distinct image id/version does not rule out same bytes/path aliases or prove independent scenes.',
          'One model read and sequential scenes are not an atomic snapshot. Inherited safe_globals/RSS/time/Store predecode/authority/ACL/raster/mask/QA/state/approval limits remain.',
          'Unwired internal observation only; no API/UI/frontend/build/browser or full-backend rerun. Prior1184 is history; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/annual-normalization-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
