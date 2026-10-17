"""Independent124+125 composition checks with fresh TempStore/checkpoint bytes."""
import copy
import hashlib
import importlib.util
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.runtime'), str(ROOT / 'backend')]
import torch
from app.ml.network import TinyUNet
from app.ml import pinned_scene_normalization as module

# Reuse this reviewer's own independent fresh three-registration fixture, not
# implementation tests or operating Store; its tests are not discovered/run.
spec = importlib.util.spec_from_file_location('independent_three_refs', ROOT / 'evidence/integration/registry-normalization-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/pinned_scene_normalization.py'
FROZEN = 'b4553a8c3163f8f7213e745b8f8b4ccb989300fd48e49286e0eecadbb900b9e1'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('state_dict_verified', 'raster_header_verified', 'quality_report_verified', 'quality_mask_verified',
         'source_authority_verified', 'access_authorization_verified', 'other_lineage_parents_verified',
         'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.scene = fixtures.Independent()
        self.scene.setUp()
        self.addCleanup(self.scene.tearDown)
        self.store, self.root = self.scene.store, self.scene.root
        self.directory = self.root / 'models' / 'pinned-126'
        self.directory.mkdir(parents=True)
        self.checkpoint = self.directory / 'best.pt'
        self.report = self.directory / 'report.json'
        self.manifest = dict(copy.deepcopy(self.scene.checkpoint), synthetic=True, marker='actual CPU checkpoint')
        self.saved = dict(architecture='tiny_unet', manifest=self.manifest, state_dict=TinyUNet(6).state_dict())
        self.version = '  고정 모델 126  '
        self.bind()

    def bind(self):
        buffer = io.BytesIO(); torch.save(self.saved, buffer)
        raw = buffer.getvalue(); self.checkpoint.write_bytes(raw)
        self.model_ref = dict(id='pinned-126', version=self.version, sha256=sha(raw))
        report = dict(model_id='pinned-126', training_state='completed', checkpoint_sha256=sha(raw),
            input_signature=dict(normalization_mode='global', band_names=['REPORT_DECOY'] * 6),
            manifest=dict(normalization_mode='global', marker='REPORT_NOT_CHECKPOINT'))
        raw = json.dumps(report).encode(); self.report.write_bytes(raw); self.report_sha = sha(raw)
        self.store.put('models', dict(id='pinned-126', status='Draft', synthetic=True,
            checkpoint_path=r'models\pinned-126\best.pt', checkpoint_sha256=self.model_ref['sha256'],
            training_report_sha256=self.report_sha, model_version_declaration=dict(schema_version=1,
                source='CALLER_EXPLICIT_REGISTRATION', version=self.version,
                checkpoint_sha256=self.model_ref['sha256'], training_report_sha256=self.report_sha)))

    def read(self, **overrides):
        args = dict(store=self.store, model_ref=self.model_ref, training_report_sha256=self.report_sha,
            image_ref=self.scene.refs[0], evidence_ref=self.scene.refs[1], metadata_ref=self.scene.refs[2])
        args.update(overrides)
        before = self.store.db.read_bytes()
        get = self.store.get; calls = []
        def record_get(kind, key): calls.append((kind, key)); return get(kind, key)
        with patch.object(self.store, 'get', record_get), \
             patch.object(self.store, 'put', side_effect=AssertionError('write forbidden')), \
             patch.object(TinyUNet, 'forward', side_effect=AssertionError('inference forbidden')), \
             patch.object(TinyUNet, 'load_state_dict', side_effect=AssertionError('state validation forbidden')):
            result = module.inspect_pinned_scene_normalization(**args)
        self.assertEqual(before, self.store.db.read_bytes())
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'model_observation',
            'scene_observation', 'checkpoint_artifact_verified', 'training_report_artifact_verified',
            'registry_references_verified', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'PINNED_MODEL_REGISTERED_SCENE_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls

    def test_actual_manifest_forwarded_once_report_decoy_unused_no_execution(self):
        original = module.read_registered_per_scene_files
        captured = []
        def scene(store, actual, *refs):
            captured.append(actual)
            self.assertEqual(actual, self.manifest)
            return original(store, actual, *refs)
        with patch.object(module, 'read_registered_per_scene_files', scene): result, calls = self.read()
        self.assertEqual(result['status'], 'PINNED_SCENE_MATCHED_UNVERIFIED')
        self.assertIsNone(result['issue'])
        self.assertEqual([kind for kind, key in calls], ['models'] + ['dataset_versions'] * 3)
        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0], result['model_observation']['checkpoint_manifest'])
        for flag in ('checkpoint_artifact_verified', 'training_report_artifact_verified',
                     'registry_references_verified', 'artifact_bytes_verified'): self.assertIs(result[flag], True)
        self.assertIs(result['scene_observation']['checkpoint_artifact_verified'], False)
        self.assertIs(result['model_observation']['state_dict_verified'], False)

    def test_global_actual_checkpoint_ignores_invalid_scene_refs(self):
        self.manifest['normalization_mode'] = 'global'; self.bind()
        result, calls = self.read(image_ref=object(), evidence_ref=object(), metadata_ref=object())
        self.assertEqual(result['status'], 'OUT_OF_SCOPE')
        self.assertIsNone(result['issue'])
        self.assertEqual(calls, [('models', 'pinned-126')])
        self.assertEqual(result['scene_observation']['status'], 'OUT_OF_SCOPE')
        self.assertIs(result['checkpoint_artifact_verified'], True)
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_model_hash_failures_never_call_scene_reader(self):
        for path in (self.checkpoint, self.report):
            original = path.read_bytes(); path.write_bytes(original + b'changed')
            with patch.object(module, 'read_registered_per_scene_files', side_effect=AssertionError('scene forbidden')) as scene:
                result, calls = self.read(image_ref=object())
            self.assertEqual(result['status'], 'MODEL_BLOCKED')
            self.assertEqual(result['issue'], dict(code='MODEL_OBSERVATION_BLOCKED', field='model'))
            self.assertEqual(calls, [('models', 'pinned-126')]); scene.assert_not_called()
            self.assertIsNone(result['scene_observation'])
            self.assertIs(result['artifact_bytes_verified'], False)
            self.assertEqual(result['checkpoint_artifact_verified'], path == self.report)
            path.write_bytes(original)

    def test_model_version_pin_conflict_stops_before_scene(self):
        ref = dict(self.model_ref, version='different')
        result, calls = self.read(model_ref=ref)
        self.assertEqual(result['status'], 'MODEL_BLOCKED')
        self.assertEqual(result['model_observation']['issue']['code'], 'PIN_CONFLICT')
        self.assertEqual(calls, [('models', 'pinned-126')])

    def test_each_scene_asset_tamper_keeps_model_history_but_not_aggregate_success(self):
        for name in ('image.bin', 'evidence.json', '원 metadata.xml'):
            path = self.root / name; original = path.read_bytes(); path.write_bytes(original + b'tampered')
            result, calls = self.read()
            self.assertEqual(result['status'], 'SCENE_BLOCKED')
            self.assertEqual(result['issue'], dict(code='SCENE_OBSERVATION_BLOCKED', field='scene'))
            self.assertIs(result['checkpoint_artifact_verified'], True)
            self.assertIs(result['training_report_artifact_verified'], True)
            self.assertIs(result['registry_references_verified'], True)
            self.assertIs(result['artifact_bytes_verified'], False)
            path.write_bytes(original)

    def test_scene_extension_missing_and_fixed_ref_conflict(self):
        self.scene.mutate(0, lambda m: m['source'].pop('scene_id'))
        result, calls = self.read()
        self.assertEqual(result['status'], 'SCENE_BLOCKED')
        self.assertEqual(result['scene_observation']['issue']['code'], 'SCENE_DECLARATION_MISSING')
        self.assertIs(result['registry_references_verified'], True)
        wrong = dict(self.scene.refs[0], sha256='0' * 64)
        result, calls = self.read(image_ref=wrong)
        self.assertEqual(result['status'], 'SCENE_BLOCKED')
        self.assertEqual(result['scene_observation']['issue']['code'], 'REGISTRY_REFERENCE_CONFLICT')
        self.assertIs(result['registry_references_verified'], False)

    def test_stage_exceptions_have_fixed_safe_issues_and_no_path_leak(self):
        private = 'private C:/sensitive/model/path'
        with patch.object(module, 'read_pinned_model_checkpoint_manifest', side_effect=ValueError(private)), \
             patch.object(module, 'read_registered_per_scene_files') as scene:
            result, calls = self.read()
        self.assertEqual(result['status'], 'MODEL_BLOCKED'); scene.assert_not_called()
        self.assertNotIn(private, json.dumps(result))
        with patch.object(module, 'read_registered_per_scene_files', side_effect=ValueError(private)):
            result, calls = self.read()
        self.assertEqual(result['status'], 'SCENE_BLOCKED')
        self.assertNotIn(private, json.dumps(result))
        self.assertIs(result['checkpoint_artifact_verified'], True)
        self.assertIs(result['artifact_bytes_verified'], False)

    def test_no_caller_manifest_or_path_parameter_exists(self):
        self.assertEqual(list(inspect.signature(module.inspect_pinned_scene_normalization).parameters),
            ['store', 'model_ref', 'training_report_sha256', 'image_ref', 'evidence_ref', 'metadata_ref'])
        with self.assertRaises(TypeError):
            module.inspect_pinned_scene_normalization(self.store, self.model_ref, self.report_sha,
                *self.scene.refs, checkpoint_manifest=dict(normalization_mode='global'))


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '2a980f91eeb86ff61df65eed5c4f2d266aa5f540'
    checks = []
    for name in ('backend/app/ml/model_checkpoint_manifest.py', 'backend/app/ml/registered_per_scene_files.py',
                 'backend/app/ml/per_scene_normalization_files.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_CPU_CHECKPOINT_AND_REGISTERED_SCENE_COMPOSITION', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        fixture='Fresh actual TinyUNet6 CPU torch.save/load and three actual TempStore register_version calls; no training/inference.',
        operating_Store_API_registration_checkpoint_reads_or_writes=0, inference_training_state_load_calls=0,
        UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Composition observes actual pinned manifest and one registered scene only; no execution/approval/raster/mask/QA/authority/science verification.',
          'Nested partial checkpoint/report/registry true flags are prior role observations, not aggregate success.',
          'Inherited safe_globals/RSS/time/Store predecode/multifile atomicity limits of124/125 remain.',
          'Internal helper unwired to API/UI/Workflow; no front/build/browser or full-backend rerun. Prior1184 history is not new. Do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/pinned-scene-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
