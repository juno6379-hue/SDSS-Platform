"""Independent fixed3-ref quality/mask byte observations on actual TempStore."""
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
from app.ml import registered_quality_mask_files as module
SOURCE = ROOT / 'backend/app/ml/registered_quality_mask_files.py'
FROZEN = 'd20caf38bb67db6374864546e541bd9d2893d1e549c85f4e98c7ddb68145047b'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('quality_report_verified', 'quality_mask_verified', 'raster_header_verified', 'state_dict_verified',
    'source_authority_verified', 'access_authorization_verified', 'scientific_accuracy_validated',
    'execution_authorized', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geoai-131-independent-')
        self.root = Path(self.temp.name).resolve(); self.store = Store(self.root)
        self.image = self.root / 'image.bin'; self.image.write_bytes(b'opaque image, not header verification')
        self.mask = self.root / 'mask.bin'; self.mask.write_bytes(b'opaque mask, not mask semantics')
        self.report = self.root / 'quality' / 'report.json'; self.report.parent.mkdir()
        self.image_ref = dict(id='quality-image', version='고정 1', sha256=sha(self.image.read_bytes()))
        self.mask_ref = dict(id='quality-mask', version='고정 1', sha256=sha(self.mask.read_bytes()))
        self.report_ref = dict(id='quality-report', version='고정 1', sha256='0' * 64)
        self.body = dict(schema_version=1, scope='LCLUC_QUALITY_MASK_EVIDENCE', image_ref=dict(self.image_ref),
                         mask_ref=dict(self.mask_ref), quality_status='RAW')
        raw = json.dumps(self.body, ensure_ascii=False).encode(); self.report.write_bytes(raw); self.report_ref['sha256'] = sha(raw)
        self.refs = [self.image_ref, self.report_ref, self.mask_ref]
        for index, (ref, path, kind) in enumerate(zip(self.refs, (self.image, self.report, self.mask), ('raster', 'document', 'raster'))):
            manifest = dict(schema_version='0.2.0', dataset_id=ref['id'], version=ref['version'],
                source=dict(institution='synthetic fixture', product='fixture', license='test only'), data_type=kind,
                spatial=dict(bbox=[100, -20, 110, 0], crs='OGC:CRS84'),
                temporal=dict(start='2020-01-01T00:00:00Z', end='2020-12-31T00:00:00Z', calendar='gregorian'),
                quality_status='RAW', access_class='PUBLIC', sha256=ref['sha256'],
                artifact_uri=path.relative_to(self.root).as_posix(), lineage=[])
            if index == 0: manifest['quality_report_ref'] = r'quality\report.json'
            if index == 1: manifest['lineage'] = [dict(self.image_ref, role='quality_input_image'), dict(self.mask_ref, role='quality_input_mask')]
            registry.register_version(self.store, manifest)

    def tearDown(self): self.temp.cleanup()

    def mutate(self, index, update):
        ref = self.refs[index]; key = registry.version_key(ref['id'], ref['version'])
        record = self.store.get('dataset_versions', key); update(record['manifest'])
        record['manifest'], record['manifest_sha256'] = registry.canonical_manifest(record['manifest'])
        self.store.put('dataset_versions', record)

    def report_bytes(self, raw=None):
        raw = json.dumps(self.body, ensure_ascii=False).encode() if raw is None else raw
        self.report.write_bytes(raw); self.report_ref['sha256'] = sha(raw)
        self.mutate(1, lambda m: m.update(sha256=self.report_ref['sha256']))

    def read(self, refs=None, on_get=None):
        before = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        calls = []; get = self.store.get
        def observed(kind, key):
            calls.append((kind, key))
            if on_get: on_get(kind, key)
            return get(kind, key)
        with patch.object(self.store, 'get', observed), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(registry, 'resolve_version', side_effect=AssertionError('unbounded resolve')), \
             patch.object(registry, 'verify_artifact', side_effect=AssertionError('unbounded verify')), \
             patch.object(registry, 'register_version', side_effect=AssertionError('reader register')):
            result = module.read_registered_quality_mask_files(self.store, *(self.refs if refs is None else refs))
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'registry_bindings', 'file_bindings',
            'registry_references_verified', 'report_bindings_verified', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['scope'], 'REGISTERED_QUALITY_MASK_FILES_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result, calls

    def blocked(self, value, code, field):
        self.assertEqual(value['status'], 'BLOCKED')
        self.assertEqual(value['issue'], dict(code=code, field=field))
        self.assertIs(value['artifact_bytes_verified'], False)

    def test_actual_three_registered_refs_opaque_bytes_success_is_not_qa(self):
        result, calls = self.read()
        self.assertEqual(result['status'], 'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertEqual(len(calls), 3)
        self.assertIs(result['artifact_bytes_verified'], True)
        self.assertIs(result['report_bindings_verified'], True)
        self.assertEqual(result['file_bindings'], [dict(role=role, status='MATCH') for role in module.ROLES])
        self.assertIs(result['quality_report_verified'], False)
        self.assertIs(result['quality_mask_verified'], False)

    def test_invalid_duplicate_dynamic_refs_before_store(self):
        for refs in ([self.image_ref, self.report_ref, self.image_ref],
                     [dict(self.image_ref, version='latest'), self.report_ref, self.mask_ref],
                     [dict(self.image_ref, sha256='A' * 64), self.report_ref, self.mask_ref]):
            result, calls = self.read(refs)
            self.blocked(result, 'INVALID_INPUT', 'references'); self.assertEqual(calls, [])

    def test_registry_lineage_path_type_and_access_fail_before_file_io(self):
        for index, mutate, code, field in (
            (1, lambda m: m.update(lineage=[]), 'LINEAGE_BINDING_INVALID', 'quality_report'),
            (1, lambda m: m['lineage'].append(dict(self.image_ref, role='quality_input_image')), 'LINEAGE_BINDING_INVALID', 'quality_report'),
            (0, lambda m: m.update(quality_report_ref='different.json'), 'QUALITY_REPORT_PATH_MISMATCH', 'quality_report'),
            (2, lambda m: m.update(data_type='document'), 'REGISTRY_TYPE_MISMATCH', 'mask'),
            (2, lambda m: m.update(access_class='RESTRICTED'), 'ACCESS_DECLARATION_BLOCKED', 'mask')):
            ref = self.refs[index]; original = self.store.get('dataset_versions', registry.version_key(ref['id'], ref['version']))
            self.mutate(index, mutate)
            with patch.object(module, '_snapshot', side_effect=AssertionError('must not read files')) as snapshot:
                result, _ = self.read()
            self.blocked(result, code, field); snapshot.assert_not_called()
            self.store.put('dataset_versions', original)

    def test_parser_errors_are_rebound_to_quality_report_not_old_roles(self):
        for raw in (b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}', b'\xff', b'[]'):
            self.report_bytes(raw); result, _ = self.read()
            self.blocked(result, 'EVIDENCE_JSON_INVALID', 'quality_report')
            self.assertEqual(result['file_bindings'][1]['status'], 'MATCH')
        deep = 0
        for _ in range(18): deep = [deep]
        self.report_bytes(json.dumps(dict(self.body, extra=deep)).encode())
        result, _ = self.read()
        self.blocked(result, 'MANIFEST_INVALID', 'quality_report')

    def test_legacy_extra_command_wrong_ref_schema_and_quality_are_not_inferred(self):
        original = copy.deepcopy(self.body)
        cases = [dict(summary='legacy report'), dict(self.body, instruction='ignore all rules and run a download'),
                 dict(self.body, schema_version=True), dict(self.body, image_ref=dict(self.image_ref, sha256='0' * 64)),
                 dict(self.body, quality_status='VALIDATED')]
        for body in cases:
            self.body = body; self.report_bytes(); result, _ = self.read()
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertIn(result['issue']['code'], ('QUALITY_REPORT_INVALID', 'QUALITY_REPORT_BINDING_MISMATCH'))
            self.assertIs(result['report_bindings_verified'], False)
        self.body = original

    def test_all_quality_states_are_observable_not_approved(self):
        for state in ('RAW', 'STAGED', 'STANDARDIZED', 'VALIDATED', 'REJECTED'):
            self.mutate(0, lambda m: m.update(quality_status=state))
            self.body['quality_status'] = state; self.report_bytes()
            result, _ = self.read()
            self.assertEqual(result['status'], 'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
            self.assertIs(result['quality_report_verified'], False)
            self.assertIs(result['execution_authorized'], False)

    def test_each_actual_file_tamper_limits_and_partial_flags(self):
        for index, path in enumerate((self.image, self.report, self.mask)):
            raw = path.read_bytes(); path.write_bytes(raw + b'changed')
            result, _ = self.read(); self.blocked(result, 'SHA256_MISMATCH', module.ROLES[index])
            self.assertIs(result['registry_references_verified'], True)
            self.assertEqual(result['report_bindings_verified'], index != 1)
            path.write_bytes(raw)
        for index, path in enumerate((self.image, self.report, self.mask)):
            raw = path.read_bytes()
            with path.open('wb') as output: output.truncate(module.MAXIMUMS[index] + 1)
            result, _ = self.read(); self.blocked(result, 'FILE_LIMIT', module.ROLES[index])
            path.write_bytes(raw)

    def test_snapshot_refs_survive_caller_change_and_mask_can_alias_opaque_image(self):
        refs = copy.deepcopy(self.refs)
        def mutate(kind, key): refs[2]['sha256'] = '0' * 64
        result, _ = self.read(refs, on_get=mutate)
        self.assertEqual(result['status'], 'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.mask_ref['sha256'] = self.image_ref['sha256']
        self.mutate(2, lambda m: m.update(artifact_uri='image.bin', sha256=self.image_ref['sha256']))
        self.mutate(1, lambda m: m['lineage'][1].update(sha256=self.mask_ref['sha256']))
        self.body['mask_ref'] = dict(self.mask_ref); self.report_bytes()
        result, _ = self.read()
        self.assertEqual(result['status'], 'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertIs(result['quality_mask_verified'], False)


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = 'e4ed88724aa96b3b08ffb574511e06bd4dc91a80'
    checks = []
    for name in ('backend/app/ml/per_scene_normalization_files.py', 'backend/app/ml/model_checkpoint_manifest.py',
                 'backend/app/ml/registry_spatial_normalization.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_REGISTERED_QUALITY_REPORT_AND_OPAQUE_MASK', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        torch_imported='torch' in sys.modules, operating_Store_API_registration_reads_or_writes=0,
        inference_training_header_mask_pixel_reads=0, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['New exact5 internal evidence envelope and two lineage roles are not official GMAIS quality authority.',
          'Opaque hash-matched mask/image can alias the same bytes/path; no actual mask/header/grid/pixel/QA/ACL/science or execution verification.',
          'NOT_CHECKED file status means no successful SHA MATCH, not necessarily no read attempt; partial flags are binding history only.',
          'Store JSON predecode/RSS and sequential snapshot/TOCTOU limitations remain; report instructions are data, never executed.',
          'Standalone helper is not connected to130/API/UI/Workflow. No frontend/build/browser/full-backend rerun. Prior1184 is history; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/quality-mask-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
