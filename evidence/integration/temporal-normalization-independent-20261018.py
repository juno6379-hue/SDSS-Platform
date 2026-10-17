"""Independent same-get UTC-year policy tests; fresh TempStore/checkpoint only."""
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
from app.dataset_registry import version_key
from app.ml import registry_temporal_normalization as module
spec = importlib.util.spec_from_file_location('independent_annual_fixture', ROOT / 'evidence/integration/annual-normalization-independent-20261018.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
SOURCE = ROOT / 'backend/app/ml/registry_temporal_normalization.py'
FROZEN = '6cc04dcfb2e71745a09ed7a62b17ccc94637e5c9ad12730fe7ac3d8e20b98f15'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('physical_acquisition_year_verified', 'source_authority_verified',
         'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported')


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.Independent(); self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.store, self.rows = self.fixture.store, self.fixture.rows
        for i, row in enumerate(self.rows): self.temporal(i, self.valid(row['year']))

    def valid(self, year):
        return dict(start=f'{year}-01-01T00:00:00Z', end=f'{year}-12-31T23:59:59.999999999Z', calendar='gregorian')

    def temporal(self, index, value):
        ref = self.rows[index]['image_ref']; key = version_key(ref['id'], ref['version'])
        record = self.store.get('dataset_versions', key)
        record['manifest']['temporal'] = value
        # Constructed coherent-or-malformed Temp metadata, not a legitimate
        # immutable-version update. Raw canonical digest permits bad time tests.
        record['manifest_sha256'] = sha(json.dumps(record['manifest'], sort_keys=True, ensure_ascii=False,
            allow_nan=False, separators=(',', ':')).encode())
        self.store.put('dataset_versions', record)

    def read(self, rows=None, transform=None):
        before = self.store.db.read_bytes(); get = self.store.get; calls = []
        def observed(kind, key):
            calls.append((kind, key)); record = get(kind, key)
            return transform(kind, key, record) if transform else record
        with patch.object(self.store, 'get', observed), patch.object(self.store, 'put', side_effect=AssertionError('write')):
            result = module.inspect_registry_temporal_normalization(self.store, self.fixture.model_ref,
                self.fixture.report_sha, self.rows if rows is None else rows)
        self.assertEqual(before, self.store.db.read_bytes())
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'batch_observation',
            'temporal_observations', 'registry_temporal_year_verified', 'physical_acquisition_year_verified',
            'artifact_bytes_verified', 'source_authority_verified', 'scientific_accuracy_validated',
            'execution_authorized', 'workflow_supported'})
        self.assertEqual(result['scope'], 'PINNED_YEARS_REGISTRY_TEMPORAL_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        self.assertIs(result['batch_observation']['temporal_year_verified'], False)
        return result, calls

    def test_actual_two_and_six_rows_same_get_one_model_and_nested_false(self):
        for count in (2, 6):
            result, calls = self.read(self.rows[:count])
            self.assertEqual(result['status'], 'REGISTRY_YEARS_MATCHED_UNVERIFIED')
            self.assertEqual(len(calls), 1 + 3 * count)
            self.assertEqual(len(set(calls)), len(calls))
            self.assertEqual(len(result['temporal_observations']), count)
            self.assertIs(result['registry_temporal_year_verified'], True)
            self.assertIs(result['artifact_bytes_verified'], True)
            self.assertIs(result['physical_acquisition_year_verified'], False)
            self.assertEqual(result['batch_observation']['model_observation_calls'], 1)

    def test_timezone_normalized_year_and_nanosecond_endpoint(self):
        # Local2019/2021 endpoints both normalize wholly inside UTC2020.
        self.temporal(0, dict(start='2019-12-31T23:00:00-01:00',
            end='2021-01-01T00:59:59.999999999+01:00', calendar='gregorian'))
        result, _ = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'REGISTRY_YEARS_MATCHED_UNVERIFIED')
        self.temporal(0, dict(start='2020-01-01T00:00:00.000000001Z',
            end='2020-01-01T00:00:00.000000000Z', calendar='gregorian'))
        result, _ = self.read(self.rows[:2])
        self.assertEqual(result['issue'], dict(code='TEMPORAL_WINDOW_REVERSED', field='window', year=2020))

    def test_boundary_cross_next_year_reversed_and_zero_duration(self):
        variants = [
            (dict(start='2020-01-01T00:00:00Z', end='2021-01-01T00:00:00Z', calendar='gregorian'), 'TEMPORAL_YEAR_MISMATCH'),
            (dict(start='2019-12-31T23:59:59.999999999Z', end='2020-01-01T00:00:00Z', calendar='gregorian'), 'TEMPORAL_YEAR_MISMATCH'),
            (dict(start='2020-02-01T00:00:00Z', end='2020-01-01T00:00:00Z', calendar='gregorian'), 'TEMPORAL_WINDOW_REVERSED')]
        for temporal, code in variants:
            self.temporal(0, temporal); result, calls = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'TEMPORAL_BLOCKED')
            self.assertEqual(result['issue']['code'], code)
            self.assertEqual(len(calls), 2)
            self.assertIs(result['registry_temporal_year_verified'], False)
        self.temporal(0, dict(start='2020-01-01T00:00:00Z', end='2020-01-01T00:00:00Z', calendar='gregorian'))
        self.assertEqual(self.read(self.rows[:2])[0]['status'], 'REGISTRY_YEARS_MATCHED_UNVERIFIED')

    def test_strict_subset_nullable_calendar_offset_ascii_and_fraction(self):
        for value, code in ((None, 'TEMPORAL_FIELD_INVALID'),
            ('2020-01-01T00:00:00', 'TEMPORAL_FIELD_INVALID'),
            ('2020-01-01t00:00:00z', 'TEMPORAL_FIELD_INVALID'),
            ('2020-01-01 00:00:00Z', 'TEMPORAL_FIELD_INVALID'),
            ('٢٠٢٠-01-01T00:00:00Z', 'TEMPORAL_FIELD_INVALID'),
            ('2020-01-01T00:00:00-00:00', 'TEMPORAL_OFFSET_UNKNOWN'),
            ('2020-01-01T00:00:60Z', 'TEMPORAL_FIELD_INVALID'),
            ('2020-01-01T00:00:00.1234567890Z', 'TEMPORAL_FIELD_INVALID')):
            temporal = self.valid(2020); temporal['start'] = value
            self.temporal(0, temporal); result, _ = self.read(self.rows[:2])
            self.assertEqual(result['status'], 'TEMPORAL_BLOCKED')
            self.assertEqual(result['issue']['code'], code)
        for calendar, code in ((None, 'TEMPORAL_FIELD_INVALID'), ('Gregorian', 'TEMPORAL_CALENDAR_UNSUPPORTED'),
                                ('360_day', 'TEMPORAL_CALENDAR_UNSUPPORTED')):
            temporal = self.valid(2020); temporal['calendar'] = calendar
            self.temporal(0, temporal); result, _ = self.read(self.rows[:2])
            self.assertEqual(result['issue']['code'], code)

    def test_middle_failfast_partial_observations_and_future_alias_not_observed(self):
        self.temporal(1, self.valid(2199))
        result, calls = self.read()
        self.assertEqual(result['status'], 'TEMPORAL_BLOCKED')
        self.assertEqual(len(calls), 5)  # model + first3 + secondimage only
        self.assertEqual([r['status'] for r in result['temporal_observations']], ['MATCHED_UNVERIFIED', 'BLOCKED'])
        self.assertEqual([r['status'] for r in result['batch_observation']['rows']],
            ['MATCHED_UNVERIFIED', 'BLOCKED'] + ['NOT_CHECKED'] * 4)
        self.temporal(1, self.valid(2021))
        rows = copy.deepcopy(self.rows[:2]); rows[0]['metadata_ref'] = rows[1]['image_ref']
        result, calls = self.read(rows)
        self.assertEqual(result['status'], 'SCENE_BLOCKED')
        self.assertEqual(len(result['temporal_observations']), 1)
        self.assertEqual(result['temporal_observations'][0]['year'], 2020)
        self.assertEqual(len(calls), 4)

    def test_changed_actual_get_record_is_checked_without_stale_preread(self):
        image_key = version_key(self.rows[0]['image_ref']['id'], self.rows[0]['image_ref']['version'])
        def changed(kind, key, record):
            if kind == 'dataset_versions' and key == image_key:
                record['manifest']['temporal'] = self.valid(2199)
                record['manifest_sha256'] = sha(json.dumps(record['manifest'], sort_keys=True, ensure_ascii=False,
                    allow_nan=False, separators=(',', ':')).encode())
            return record
        result, calls = self.read(self.rows[:2], transform=changed)
        self.assertEqual(result['status'], 'TEMPORAL_BLOCKED')
        self.assertEqual(calls, [('models', 'annual-127'), ('dataset_versions', image_key)])
        self.assertEqual(result['issue']['code'], 'TEMPORAL_YEAR_MISMATCH')

    def test_invalid_global_and_model_failure_never_read_image(self):
        rows = copy.deepcopy(self.rows[:2]); rows[0]['year'] = True
        result, calls = self.read(rows)
        self.assertEqual(result['status'], 'INVALID_INPUT'); self.assertEqual(calls, [])
        self.fixture.manifest['normalization_mode'] = 'global'; self.fixture.bind_model()
        result, calls = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'OUT_OF_SCOPE')
        self.assertEqual(calls, [('models', 'annual-127')]); self.assertEqual(result['temporal_observations'], [])
        checkpoint = self.fixture.model_dir / 'best.pt'; checkpoint.write_bytes(checkpoint.read_bytes() + b'changed')
        result, calls = self.read(self.rows[:2])
        self.assertEqual(result['status'], 'MODEL_BLOCKED')
        self.assertEqual(calls, [('models', 'annual-127')]); self.assertEqual(result['temporal_observations'], [])


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '0ff71266aae84e14fe8620bdafe56725d7fd5c80'
    checks = []
    for name in ('backend/app/ml/pinned_annual_normalization.py', 'backend/app/ml/model_checkpoint_manifest.py',
                 'backend/app/ml/registered_per_scene_files.py', 'backend/app/dataset_registry.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_SAME_GET_REGISTRY_UTC_YEAR_POLICY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        operating_Store_API_registration_checkpoint_reads_or_writes=0, inference_training_calls=0,
        UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Strict internal ASCII uppercase Gregorian known-offset RFC3339 subset; not all RFC3339/calendars.',
          'Verified Registry-declared UTC year window only, not physical acquisition/header/authority/independent scene proof; nested127 temporal flag remains false.',
          'BLOCKED temporal manifest_sha256 may be only a computed candidate digest, not a verified Registry pin.',
          'Same-get record binding prevents this stale preread gap, not all concurrent metadata/filesystem changes or global atomicity.',
          'Inherited Torch/Store resource, approval/ACL/QA/mask/state limitations remain. Internal unwired helper: no API/UI/front/build/browser/full-backend rerun. Prior1184 history is not new. Do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/temporal-normalization-independent-20261018.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
