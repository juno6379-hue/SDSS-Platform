"""Independent actual TempStore registration fixtures; operating Store untouched."""
import copy
import hashlib
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
from app import dataset_registry as registry
from app.store import Store
from app.ml import registered_per_scene_files as module

SOURCE = ROOT / 'backend/app/ml/registered_per_scene_files.py'
FROZEN = '8c36bf4f5715784db59c46f378878675702804878ba132d272657e5c86ff2866'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('checkpoint_artifact_verified', 'raster_header_verified', 'quality_report_verified',
         'quality_mask_verified', 'source_authority_verified', 'access_authorization_verified',
         'other_lineage_parents_verified', 'state_dict_verified', 'scientific_accuracy_validated',
         'execution_authorized', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geoai-125-independent-')
        self.root = Path(self.temp.name).resolve()
        self.store = Store(self.root)
        self.names = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
        self.checkpoint = dict(normalization_mode='per_scene_product_metadata', bands=list(range(1, 7)), band_names=self.names[:])
        image = self.root / 'image.bin'; image.write_bytes(b'non-raster image bytes: no header claim')
        metadata = self.root / '원 metadata.xml'; metadata.write_bytes(b'<opaque source/>')
        self.image_ref = dict(id='image-125', version='고정 1', sha256=sha(image.read_bytes()))
        self.metadata_ref = dict(id='metadata-125', version='고정 1', sha256=sha(metadata.read_bytes()))
        self.evidence = dict(status='verified_product_metadata', product_id='explicit-scene-125',
            band_names=self.names[:], scale=[.0001] * 6, offset=[0.] * 6,
            source_url='https://example.invalid/not-contacted', source_metadata_path=metadata.name,
            source_metadata_sha256=self.metadata_ref['sha256'])
        evidence = self.root / 'evidence.json'; evidence.write_text(json.dumps(self.evidence), encoding='utf-8')
        self.evidence_ref = dict(id='evidence-125', version='고정 1', sha256=sha(evidence.read_bytes()))
        self.refs = (self.image_ref, self.evidence_ref, self.metadata_ref)
        self.manifests = []
        for ref, path, kind in zip(self.refs, (image, evidence, metadata), ('raster', 'document', 'document')):
            manifest = dict(schema_version='0.2.0', dataset_id=ref['id'], version=ref['version'],
                source=dict(institution='synthetic fixture', product='product-family-not-scene-id', license='test only'),
                data_type=kind, spatial=dict(bbox=[106, -7, 107, -6], crs='OGC:CRS84'),
                temporal=dict(start='2024-01-01T00:00:00Z', end='2024-12-31T00:00:00Z', calendar='gregorian'),
                quality_status='RAW', access_class='PUBLIC', sha256=ref['sha256'], artifact_uri=path.name, lineage=[])
            self.manifests.append(manifest)
        self.manifests[0]['source'].update(scene_id='explicit-scene-125', band_names=self.names[:])
        self.manifests[1]['lineage'] = [dict(self.image_ref, role='normalization_input_image'),
            dict(self.metadata_ref, role='normalization_source_metadata'),
            dict(id='unresolved-other-parent', version='v1', sha256='e' * 64, role='other-parent')]
        for manifest in self.manifests: registry.register_version(self.store, manifest)

    def tearDown(self): self.temp.cleanup()

    def mutate(self, role, mutation):
        # Deliberately constructed changed TempStore metadata, never a production
        # immutable-version update or a newly approved data record.
        ref = self.refs[role]; key = registry.version_key(ref['id'], ref['version'])
        record = self.store.get('dataset_versions', key)
        mutation(record['manifest'])
        snapshot, digest = registry.canonical_manifest(record['manifest'])
        record.update(manifest=snapshot, manifest_sha256=digest)
        self.store.put('dataset_versions', record)

    def read(self, checkpoint=None, refs=None):
        refs = self.refs if refs is None else refs
        before = self.store.db.read_bytes()
        actual_get = self.store.get
        calls = []
        def get(kind, key): calls.append((kind, key)); return actual_get(kind, key)
        with patch.object(self.store, 'get', get), \
             patch.object(self.store, 'put', side_effect=AssertionError('reader write')), \
             patch.object(registry, 'resolve_version', side_effect=AssertionError('unbounded resolver')), \
             patch.object(registry, 'verify_artifact', side_effect=AssertionError('unbounded artifact read')), \
             patch.object(registry, 'register_version', side_effect=AssertionError('reader registration')):
            result = module.read_registered_per_scene_files(self.store, self.checkpoint if checkpoint is None else checkpoint, *refs)
        self.assertEqual(before, self.store.db.read_bytes())
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'registry_bindings',
            'file_observation', 'registry_references_verified', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'REGISTERED_PER_SCENE_FILES_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls

    def blocked(self, value, code, field):
        self.assertEqual(value['status'], 'BLOCKED')
        self.assertEqual(value['issue'], dict(code=code, field=field))
        self.assertIs(value['artifact_bytes_verified'], False)

    def test_actual_three_registrations_readonly_success_and_no_parent_recursion(self):
        original = copy.deepcopy(self.refs)
        result, calls = self.read()
        self.assertEqual(result['status'], 'REGISTERED_FILES_MATCHED_UNVERIFIED')
        self.assertEqual(len(calls), 3)
        self.assertEqual({kind for kind, key in calls}, {'dataset_versions'})
        self.assertEqual(self.refs, original)
        self.assertIs(result['artifact_bytes_verified'], True)
        self.assertIs(result['registry_references_verified'], True)
        self.assertEqual([b['role'] for b in result['registry_bindings']], list(module.ROLES))
        self.assertEqual(result['file_observation']['status'], 'FILES_MATCHED_UNVERIFIED')
        self.assertEqual(set(result['file_observation']['file_bindings'].values()), {'MATCH'})
        # Registry product-family differs from explicit scene: no product inference.

    def test_global_1_to_16_outside_scope_without_registry_access(self):
        for count in range(1, 17):
            result, calls = self.read(checkpoint=dict(normalization_mode='global', bands=list(range(count))), refs=(object(), object(), object()))
            self.assertEqual(result['status'], 'OUT_OF_SCOPE')
            self.assertEqual(calls, [])

    def test_explicit_source_fields_missing_or_wrong_no_checkpoint_inference(self):
        for key in ('scene_id', 'band_names'):
            original = copy.deepcopy(self.store.get('dataset_versions', registry.version_key(self.image_ref['id'], self.image_ref['version'])))
            self.mutate(0, lambda m: m['source'].pop(key))
            result, _ = self.read()
            self.blocked(result, 'SCENE_DECLARATION_MISSING', 'image')
            self.assertIs(result['registry_references_verified'], True)
            self.store.put('dataset_versions', original)
        self.mutate(0, lambda m: m['source'].update(band_names=['wrong'] * 6))
        result, _ = self.read()
        self.blocked(result, 'DECLARATION_NOT_CONSISTENT', 'scene_files')

    def test_lineage_roles_missing_duplicate_and_wrong_pin(self):
        original = copy.deepcopy(self.store.get('dataset_versions', registry.version_key(self.evidence_ref['id'], self.evidence_ref['version'])))
        for mutation in (lambda m: m.update(lineage=[]),
                         lambda m: m['lineage'].append(dict(self.image_ref, role='normalization_input_image')),
                         lambda m: m['lineage'][0].update(sha256='0' * 64)):
            self.mutate(1, mutation)
            result, _ = self.read()
            self.blocked(result, 'LINEAGE_BINDING_INVALID', 'normalization_evidence')
            self.store.put('dataset_versions', original)

    def test_duplicate_refs_dynamic_version_and_pin_conflict(self):
        result, calls = self.read(refs=(self.image_ref, self.image_ref, self.metadata_ref))
        self.blocked(result, 'INVALID_INPUT', 'references'); self.assertEqual(calls, [])
        wrong = dict(self.image_ref, version='latest')
        result, calls = self.read(refs=(wrong, self.evidence_ref, self.metadata_ref))
        self.blocked(result, 'INVALID_INPUT', 'references'); self.assertEqual(calls, [])
        wrong = dict(self.image_ref, sha256='0' * 64)
        result, _ = self.read(refs=(wrong, self.evidence_ref, self.metadata_ref))
        self.blocked(result, 'REGISTRY_REFERENCE_CONFLICT', 'image')

    def test_quality_declarations_all_diagnostic_public_not_acl(self):
        for state in ('RAW', 'STAGED', 'STANDARDIZED', 'VALIDATED', 'REJECTED'):
            for role in range(3):
                self.mutate(role, lambda m: m.update(quality_status=state, quality_report_ref='nonexistent-quality.json'))
            result, _ = self.read()
            self.assertEqual(result['status'], 'REGISTERED_FILES_MATCHED_UNVERIFIED')
            self.assertEqual({b['quality_status'] for b in result['registry_bindings']}, {state})
            self.assertIs(result['quality_report_verified'], False)
            self.assertIs(result['access_authorization_verified'], False)
        self.mutate(0, lambda m: m.update(access_class='RESTRICTED'))
        result, _ = self.read()
        self.blocked(result, 'ACCESS_DECLARATION_BLOCKED', 'image')

    def test_types_and_metadata_canonical_pin_tampering(self):
        self.mutate(0, lambda m: m.update(data_type='document'))
        result, _ = self.read()
        self.blocked(result, 'REGISTRY_TYPE_MISMATCH', 'image')
        self.mutate(0, lambda m: m.update(data_type='raster'))
        key = registry.version_key(self.image_ref['id'], self.image_ref['version'])
        record = self.store.get('dataset_versions', key)
        record['manifest']['source']['product'] = 'modified-without-digest'
        self.store.put('dataset_versions', record)
        result, _ = self.read()
        self.blocked(result, 'REGISTRY_REFERENCE_CONFLICT', 'image')

    def test_metadata_ref_path_and_real_three_role_bytes(self):
        alternate = self.root / 'duplicate-metadata.xml'
        alternate.write_bytes((self.root / '원 metadata.xml').read_bytes())
        self.mutate(2, lambda m: m.update(artifact_uri=alternate.name))
        result, _ = self.read()
        self.blocked(result, 'EVIDENCE_BINDING_INVALID', 'source_metadata')
        self.mutate(2, lambda m: m.update(artifact_uri='원 metadata.xml'))
        (self.root / 'image.bin').write_bytes(b'tampered')
        result, _ = self.read()
        self.blocked(result, 'DECLARATION_NOT_CONSISTENT', 'scene_files')
        self.assertEqual(result['file_observation']['issue'], dict(code='SHA256_MISMATCH', field='image'))

    def test_file_change_between_registry_join_and_123_read_is_rejected(self):
        original = module.verify_per_scene_normalization_files
        def late_change(*args):
            (self.root / 'image.bin').write_bytes(b'changed after registry/evidence join')
            return original(*args)
        with patch.object(module, 'verify_per_scene_normalization_files', late_change):
            result, _ = self.read()
        self.blocked(result, 'DECLARATION_NOT_CONSISTENT', 'scene_files')
        self.assertIs(result['registry_references_verified'], True)
        self.assertEqual(result['file_observation']['issue'], dict(code='SHA256_MISMATCH', field='image'))


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '4824b45aada7ba677381bdfad5a9739e12bd2dd5'
    checks = []
    for name in ('backend/app/dataset_registry.py', 'backend/app/store.py', 'backend/app/ml/per_scene_normalization_files.py',
                 'backend/app/ml/model_checkpoint_manifest.py', 'backend/app/lcluc_workflow.py',
                 'backend/app/main.py', 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_REGISTERED_THREE_REF_TEMPSTORE_ONLY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_writes=0, training_inference_checkpoint_loads=0,
        torch_imported='torch' in sys.modules, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['source.scene_id/band_names and two lineage roles are new internal consuming rules, not official GMAIS authority.',
          'Coefficient values come from pinned evidence: no independent physical calibration proof. Caller checkpoint manifest remains unverified.',
          'PUBLIC is declaration-only read policy, not ACL permission; quality state including REJECTED is observable, not QA approval.',
          'Store.get decodes database JSON before bounded returned-tree inspection; no predecode hard memory limit or atomic multi-record/file snapshot.',
          'Other lineage parents, actual raster/header/mask, model state, authority, science and execution remain unverified.',
          'Unwired helper needs no API/UI/frontend/build/browser or new full-backend run. Prior1184 is historical; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/registry-normalization-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
