"""Independent bytes-to-safe-summary contract; actual Temp paths vs explicit mocks."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.runtime'), str(ROOT / 'backend')]
import rasterio
import torch
from jsonschema import Draft202012Validator
from app import annual_diagnostics_service as module
spec = importlib.util.spec_from_file_location('independent_policy_fixture', ROOT / 'evidence/integration/mask-policy-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/annual_diagnostics_service.py'
FROZEN = '709e011bc7abbd050b316e8ac5586a2f9421ed2019a7ca66f31e9090db65f98e'
TEST_FROZEN = '40776b85f4c8562312d1df06b22531389ec75845e59342b24ea2cf066b752558'
SCHEMAS = {
    'contracts/internal/lcluc-annual-diagnostics-request.schema.json': 'c1e90cc402f08a5d08d19ca76832d54727b756a6048b0a03b973d790f66a8f94',
    'contracts/internal/lcluc-annual-diagnostics-response.schema.json': '56d5a0110de527f68d326f6af90f33fc2289f209d7ada002f5f860061544b8c6'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified', 'registry_aoi_verified',
    'source_authority_verified', 'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')
PRIVATE = 'SYNTHETIC_PRIVATE_C:/not-a-real-file/registry-secret'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class Independent(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.Independent(); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store, self.root, self.rows, self.fixture = self.base.store, self.base.root, self.base.rows, self.base.fixture
        self.schemas = [json.loads((ROOT / path).read_text(encoding='utf-8-sig')) for path in SCHEMAS]
        self.request_validator, self.response_validator = [Draft202012Validator(schema) for schema in self.schemas]
        for schema in self.schemas: Draft202012Validator.check_schema(schema)
        self.last_parent = None

    def request(self, count=2, numerator=1, denominator=2):
        value = dict(schema_version=1, capability='landcover.input_diagnostics',
            model_ref=copy.deepcopy(self.fixture.model_ref), training_report_sha256=self.fixture.report_sha,
            requested_years=copy.deepcopy(self.rows[:count]), policy=fixtures.policy(numerator, denominator))
        self.request_validator.validate(value)
        return value

    def read(self, raw, core=None):
        before = {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        actual_get, actual_read, actual_core = self.store.get, rasterio.io.DatasetReader.read, module.inspect_annual_mask_policy
        calls = []; pixels = []
        def observed_get(kind, key): calls.append((kind, key)); return actual_get(kind, key)
        def observed_read(dataset, *args, **kwargs):
            self.assertEqual(dataset.count, 1); pixels.append((args, kwargs))
            return actual_read(dataset, *args, **kwargs)
        def observed_core(*args):
            value = actual_core(*args) if core is None else core(*args)
            self.last_parent = value
            return value
        with patch.object(self.store, 'get', observed_get), patch.object(self.store, 'put', side_effect=AssertionError('write')), \
             patch.object(torch, 'load', wraps=torch.load) as model_load, \
             patch.object(rasterio.io.DatasetReader, 'read', observed_read), \
             patch.object(rasterio.io.DatasetReader, 'read_masks', side_effect=AssertionError('intrinsic masks')), \
             patch.object(module, 'inspect_annual_mask_policy', side_effect=observed_core) as core_call:
            result = module.read_annual_diagnostic_service(self.store, raw)
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()})
        self.response_validator.validate(result)
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'request_sha256', 'blocking_stage', 'issue',
            'per_year_observations', 'caller_policy_evaluated', 'caller_policy_met', 'artifact_bytes_verified', *FLAGS})
        for flag in FLAGS: self.assertIs(result[flag], False)
        text = json.dumps(result, ensure_ascii=False, allow_nan=False)
        self.assertNotIn(PRIVATE, text)
        self.assertNotIn('artifact_uri', text); self.assertNotIn('registry_bindings', text)
        self.assertNotIn('models/', text); self.assertNotIn('parent_annual_observation', text)
        return result, calls, pixels, model_load.call_count, core_call.call_count

    def real_parent(self):
        self.assertEqual(self.read(canonical(self.request()))[0]['status'], 'CALLER_POLICY_MET_UNVERIFIED')
        return copy.deepcopy(self.last_parent)

    def test_actual_two_and_six_years_safe_schema_summary_same_io(self):
        for count in (2, 6):
            request = self.request(count); raw = canonical(request)
            result, calls, pixels, loads, core_calls = self.read(raw)
            self.assertEqual(result['status'], 'CALLER_POLICY_MET_UNVERIFIED')
            self.assertEqual((len(calls), len(pixels), loads, core_calls), (1 + 6 * count, count, 1, 1))
            self.assertEqual(result['request_sha256'], sha(raw))
            self.assertIsNone(result['blocking_stage']); self.assertIsNone(result['issue'])
            self.assertEqual(len(result['per_year_observations']), count)
            self.assertEqual({r['status'] for r in result['per_year_observations']}, {'MET'})

    def test_request_strict_json_bounds_types_and_semantics_are_zero_io(self):
        bad = [b'', b'{}', b'[]', b'\xff', b'\xef\xbb\xbf{}', b'{"x":NaN}', b'{"x":Infinity}',
            b'{"schema_version":1,"schema_version":1}', b'{"x":1.0}', b'{"x":12345678901234567}',
            b'[' * 17 + b'0' + b']' * 17, b'[0,' * 4097 + b'0' + b']' * 4097,
            b'"' + b'x' * 513 + b'"', b'{"x":"\\ud800"}', b' ' * 16385, bytearray(b'{}'), '{}']
        request = self.request(); request['schema_version'] = True; bad.append(canonical(request))
        request = self.request(6); request['requested_years'][5]['mask_ref']['version'] = 'latest'; bad.append(canonical(request))
        request = self.request(); request['policy']['minimum_valid_numerator'] = True; bad.append(canonical(request))
        for raw in bad:
            result, calls, pixels, loads, core_calls = self.read(raw)
            self.assertEqual(result['status'], 'INVALID_REQUEST')
            self.assertEqual((calls, pixels, loads, core_calls), ([], [], 0, 0))
            self.assertIsNone(result['request_sha256'])

    def test_canonical_hash_key_order_whitespace_and_escaped_brackets_stability(self):
        parent = self.real_parent(); request = self.request()
        encoded = canonical(request)
        reordered = json.dumps(dict(reversed(list(request.items()))), ensure_ascii=False, indent=2).encode()
        padded = encoded + b' ' * (16384 - len(encoded))
        for raw in (encoded, reordered, padded):
            result, calls, pixels, loads, core_calls = self.read(raw, core=lambda *a: copy.deepcopy(parent))
            self.assertEqual(result['request_sha256'], sha(encoded))
            self.assertEqual(result['status'], 'CALLER_POLICY_MET_UNVERIFIED')
            self.assertEqual((calls, pixels, loads, core_calls), ([], [], 0, 1))
        self.assertEqual(self.read(padded + b' ', core=lambda *a: parent)[0]['status'], 'INVALID_REQUEST')
        request['model_ref']['version'] = 'Unicode 정규화 " quote \\ slash ' + '[' * 20 + ']' * 20
        raw = canonical(request)
        result, _, _, _, core_calls = self.read(raw, core=lambda *a: copy.deepcopy(parent))
        self.assertEqual(result['status'], 'CALLER_POLICY_MET_UNVERIFIED')
        self.assertEqual(result['request_sha256'], sha(raw)); self.assertEqual(core_calls, 1)

    def test_real_policy_not_met_and_source_blocked_are_fixed_safe_summaries(self):
        result, calls, pixels, loads, core_calls = self.read(canonical(self.request(2, 500001, 1000000)))
        self.assertEqual(result['status'], 'CALLER_POLICY_NOT_MET')
        self.assertEqual(result['blocking_stage'], 'POLICY')
        self.assertEqual(result['issue'], dict(code='CALLER_POLICY_NOT_MET', year=2020))
        self.assertEqual((len(calls), len(pixels), loads, core_calls), (13, 2, 1, 1))
        checkpoint = self.fixture.model_dir / 'best.pt'; checkpoint.write_bytes(checkpoint.read_bytes() + b'tampered')
        result, calls, pixels, loads, core_calls = self.read(canonical(self.request()))
        self.assertEqual(result['status'], 'SOURCE_BLOCKED')
        self.assertEqual(result['blocking_stage'], 'ANNUAL')
        self.assertEqual(result['issue'], dict(code='SOURCE_BLOCKED', year=None))
        self.assertEqual((len(calls), len(pixels), loads, core_calls), (1, 0, 0, 1))

    def test_mocked_parent_privacy_type_counts_and_status_subclass_are_fail_closed(self):
        parent = self.real_parent(); raw = canonical(self.request()); callbacks = []
        class Evil(str):
            def __eq__(self, other): callbacks.append(other); return True
        changes = [lambda p: p.update(scope=PRIVATE), lambda p: p.update(execution_authorized=True),
            lambda p: p.update(caller_policy_met=1), lambda p: p.update(extra=PRIVATE),
            lambda p: p['per_year_observations'][0].update(status=PRIVATE),
            lambda p: p['per_year_observations'][0].update(status=Evil(PRIVATE)),
            lambda p: p.update(scope=Evil(PRIVATE)),
            lambda p: p['per_year_observations'][0]['counts'].update(valid_pixels=True),
            lambda p: p['per_year_observations'][0]['counts'].update(invalid_pixels=0)]
        for change in changes:
            simulated = copy.deepcopy(parent); change(simulated)
            result, calls, pixels, loads, core_calls = self.read(raw, core=lambda *a: simulated)
            self.assertEqual(result['status'], 'OUTPUT_INVALID')
            self.assertEqual(result['blocking_stage'], 'OUTPUT')
            self.assertEqual((calls, pixels, loads, core_calls), ([], [], 0, 1))
        self.assertEqual(callbacks, [])
        def raised(*args): raise RuntimeError(PRIVATE)
        self.assertEqual(self.read(raw, core=raised)[0]['status'], 'OUTPUT_INVALID')

    def test_mocked_blocked_parent_issue_is_projected_not_disclosed(self):
        parent = self.real_parent(); raw = canonical(self.request())
        for status, stage in (('ANNUAL_DIAGNOSTICS_BLOCKED', 'ANNUAL'), ('POLICY_INPUT_BLOCKED', 'COUNTS')):
            simulated = copy.deepcopy(parent)
            simulated.update(status=status, issue=dict(code=PRIVATE, field=PRIVATE, year=2021),
                caller_policy_evaluated=False, caller_policy_met=False, artifact_bytes_verified=False,
                parent_annual_observation=dict(private=PRIVATE))
            simulated['per_year_observations'] = [dict(year=2020 + i, status='NOT_CHECKED', counts=None, policy_met=None) for i in range(2)]
            result, _, _, _, _ = self.read(raw, core=lambda *a: simulated)
            self.assertEqual(result['status'], 'SOURCE_BLOCKED')
            self.assertEqual(result['blocking_stage'], stage)
            self.assertEqual(result['issue'], dict(code='SOURCE_BLOCKED', year=2021))

    def test_core_argument_mutation_cannot_change_projection_policy_or_year_baseline(self):
        parent = self.real_parent(); request = self.request(); raw = canonical(request)
        def mutate_policy(store, ref, report, rows, policy):
            policy['minimum_valid_numerator'] = 0
            simulated = copy.deepcopy(parent); simulated['policy'] = policy
            return simulated
        def mutate_year(store, ref, report, rows, policy):
            rows[0]['year'] = 2199
            simulated = copy.deepcopy(parent); simulated['per_year_observations'][0]['year'] = 2199
            return simulated
        for core in (mutate_policy, mutate_year):
            result, _, _, _, _ = self.read(raw, core=core)
            self.assertEqual(result['status'], 'OUTPUT_INVALID')
            self.assertEqual(result['request_sha256'], sha(raw))
        self.assertEqual(request, json.loads(raw))


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '4c14031cbc46384423dd4761d1bec01ea8e2222e'
    checks = []
    for name in ('backend/app/ml/annual_mask_policy.py', 'backend/app/ml/annual_quality_mask_diagnostics.py',
                 'backend/app/ml/registered_binary_mask_values.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    test_sha = sha((ROOT / 'tests/test_annual_diagnostics_service.py').read_bytes())
    schemas = {path: dict(sha256=sha((ROOT / path).read_bytes()), frozen_matches=sha((ROOT / path).read_bytes()) == expected) for path, expected in SCHEMAS.items()}
    payload = dict(scope='SYNTHETIC_TEMP_BYTES_TO_SAFE_SUMMARY_PLUS_MOCKED_OUTPUT_BOUNDARY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), test_sha256=test_sha, schemas=schemas,
        frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN, frozen_test_matches=test_sha == TEST_FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_checkpoint_reads_or_writes=0, image_pixel_reads=0, intrinsic_mask_reads=0,
        training_inference_calls=0, API_UI_changes=0, frontend_build_browser_runs=0,
        limitations=['Actual2/6-year TempStore/GTiff/untrained checkpoint is distinct from explicit mocked malformed-parent/privacy/mutation cases.',
          'Canonical request SHA binds normalized supplied request semantics, not user identity, authority, atomic snapshot, scientific/QA/model or execution approval.',
          'Schema shape validation complements runtime integer/ratio/status consistency checks; raw nested Registry/path objects are intentionally excluded.',
          'No route/main/API/UI connection yet; inherited Store/Torch/GDAL resource limits remain. No front/build/browser/full-backend rerun. Prior1184 is historical; do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/diagnostic-service-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] and payload['frozen_test_matches'] and all(v['frozen_matches'] for v in schemas.values()) else 1)
