"""Synthetic format/isolated router regressions; never import the operating app."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from app import gmais_api
from app.schema_formats import create_format_checker
from app.store import Store
from app.workflow_job_request_handoff import _draft_format_checker
from test_workflow_job_request_handoff import full_fixture


VALID = (
    '2024-02-29T23:59:59Z', '2000-02-29t00:00:00z',
    '2026-10-17T00:00:00.123456789Z', '2026-10-17T00:00:00+23:59',
    '2026-10-17T00:00:00-23:59', '2026-10-17T00:00:00-00:00',
)
INVALID = (
    'not-a-date', '2026-02-30T00:00:00Z', '1900-02-29T00:00:00Z',
    '2026-10-17T00:00:00', '2026-10-17T00:00:00+00:60',
    '2026-10-17T00:00:00+01:99', '2026-10-17T00:00:00+24:00',
    '2026-10-17T24:00:00Z', '2026-10-17T23:59:60Z',
    '0000-01-01T00:00:00Z', '2026-10-17 00:00:00Z',
    '2026-10-17T00:00:00Z\n', 'NaN',
)


def job_fixture():
    _, job = full_fixture()
    job.update(agent_id='lcluc-agent', capability_id='landcover.change_detection')
    return job


class SchemaFormatTests(unittest.TestCase):
    def test_supported_zoned_calendar_forms(self):
        checker = create_format_checker()
        for value in VALID:
            with self.subTest(value=value):
                self.assertTrue(checker.conforms(value, 'date-time'))

    def test_invalid_calendar_clock_zone_and_unsupported_forms(self):
        checker = create_format_checker()
        for value in INVALID:
            with self.subTest(value=value):
                self.assertFalse(checker.conforms(value, 'date-time'))

    def test_non_string_format_is_neutral_and_type_keyword_rejects(self):
        checker = create_format_checker()
        validator = Draft202012Validator({'type': 'string', 'format': 'date-time'}, format_checker=checker)
        for value in (None, True, 1, 1.5, {}, []):
            self.assertTrue(checker.conforms(value, 'date-time'))
            self.assertEqual([error.validator for error in validator.iter_errors(value)], ['type'])

    def test_factory_instances_and_global_registry_are_independent(self):
        global_before = dict(FormatChecker.checkers)
        existing = FormatChecker()
        existing_before = dict(existing.checkers)
        first, second = create_format_checker(), create_format_checker()
        self.assertIsNot(first, second)
        self.assertIsNot(first.checkers, second.checkers)
        first.checkers['date-time'] = (lambda value: True, ())
        self.assertFalse(second.conforms(INVALID[0], 'date-time'))
        self.assertEqual(FormatChecker.checkers, global_before)
        self.assertEqual(existing.checkers, existing_before)

    def test_optional_date_time_registration_is_not_required(self):
        absent = {key: value for key, value in FormatChecker.checkers.items() if key != 'date-time'}
        with patch.object(FormatChecker, 'checkers', absent):
            checker = create_format_checker()
            self.assertTrue(checker.conforms(VALID[0], 'date-time'))
            self.assertFalse(checker.conforms(INVALID[1], 'date-time'))
            self.assertNotIn('date-time', FormatChecker.checkers)

    def test_cached_validators_reuse_and_draft_wrapper_do_not_mutate(self):
        job_validator = gmais_api._job_request_validator()
        workflow_validator = gmais_api._workflow_plan_validator()
        job_checker, workflow_checker = job_validator.format_checker, workflow_validator.format_checker
        before = dict(job_checker.checkers), dict(workflow_checker.checkers)
        draft = _draft_format_checker()
        self.assertIsNot(draft, job_checker)
        self.assertIsNot(job_checker, workflow_checker)
        for value in INVALID:
            self.assertFalse(job_checker.conforms(value, 'date-time'))
            self.assertFalse(draft.conforms(value, 'date-time'))
        self.assertIs(gmais_api._job_request_validator(), job_validator)
        self.assertIs(gmais_api._workflow_plan_validator(), workflow_validator)
        self.assertIs(job_validator.format_checker, job_checker)
        self.assertEqual((job_checker.checkers, workflow_checker.checkers), before)

    def test_vendored_job_start_and_end_reject_invalid_date_time(self):
        validator = gmais_api._job_request_validator()
        for field in ('start', 'end'):
            for value in INVALID:
                with self.subTest(field=field, value=value):
                    job = job_fixture()
                    job['time_range'] = {field: value}
                    errors = list(validator.iter_errors(job))
                    self.assertEqual([(list(error.absolute_path), error.validator) for error in errors],
                                     [(['time_range', field], 'format')])

    def test_invalid_submission_returns_existing_400_before_any_store_access(self):
        get_store = Mock(side_effect=AssertionError('invalid draft must not reach Store'))
        app = FastAPI()
        app.include_router(gmais_api.create_router(get_store))
        with TestClient(app) as client:
            for field in ('start', 'end'):
                for value in INVALID:
                    with self.subTest(field=field, value=value):
                        job = job_fixture()
                        job['time_range'] = {field: value}
                        response = client.post('/v1/agents/lcluc-agent/jobs', json=job,
                            headers={'Idempotency-Key': 'isolated-schema-formats'})
                        self.assertEqual(response.status_code, 400, response.text)
                        error = response.json()['error']
                        self.assertEqual(set(error), {'code', 'message', 'trace_id', 'retryable'})
                        self.assertEqual(error['code'], 'INVALID_REQUEST')
                        self.assertEqual(error['trace_id'], 'unknown')
                        self.assertIs(error['retryable'], False)
                        self.assertIn('(time_range.' + field + '):', error['message'])
                        self.assertTrue(error['message'].endswith(repr(value) + " is not a 'date-time'"))
        get_store.assert_not_called()

    def test_valid_submission_preserves_existing_blocked_response_and_records(self):
        job = job_fixture()
        job['time_range'] = {'start': VALID[0], 'end': VALID[2]}
        validator = gmais_api._job_request_validator()
        baseline = validator.evolve(format_checker=FormatChecker())
        outcomes = []
        for selected in (baseline, validator):
            with tempfile.TemporaryDirectory() as temporary:
                store = Store(Path(temporary))
                app = FastAPI()
                app.include_router(gmais_api.create_router(lambda: store))
                with patch('app.gmais_api._job_request_validator', return_value=selected), \
                     patch('app.gmais_api.uuid.uuid4', return_value=SimpleNamespace(hex='1' * 32)), \
                     patch('app.gmais_api._now', return_value='2026-10-17T00:00:00.000Z'), \
                     patch('app.store.now', return_value='2026-10-17T00:00:00.000Z'), TestClient(app) as client:
                    response = client.post('/v1/agents/lcluc-agent/jobs', json=job,
                        headers={'Idempotency-Key': 'isolated-schema-formats-valid'})
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json()['error']['code'], 'MODEL_NOT_READY')
                records = store.list('gmais_jobs')
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]['status']['status'], 'BLOCKED')
                self.assertEqual(records[0]['request'], job)
                self.assertEqual(store.list('gmais_results'), [])
                outcomes.append((response.json(), response.headers['location'], records,
                                 store.list('gmais_idempotency')))
        self.assertEqual(outcomes[0], outcomes[1])

    def test_workflow_schema_and_plan_response_remain_equal_without_format_fields(self):
        workflow, _ = full_fixture()
        original = copy.deepcopy(workflow)
        validator = gmais_api._workflow_plan_validator()
        def has_format(value):
            if isinstance(value, dict):
                return 'format' in value or any(has_format(item) for item in value.values())
            return isinstance(value, list) and any(has_format(item) for item in value)
        self.assertFalse(has_format(validator.schema))
        outcomes = []
        for checker in (FormatChecker(), create_format_checker()):
            with tempfile.TemporaryDirectory() as temporary:
                store = Store(Path(temporary))
                app = FastAPI()
                app.include_router(gmais_api.create_router(lambda: store))
                with patch('app.gmais_api._workflow_plan_validator', return_value=validator.evolve(format_checker=checker)), \
                     patch('app.gmais_api._now', return_value='2026-10-17T00:00:00.000Z'), TestClient(app) as client:
                    response = client.post('/v1/workflows/plan', json=workflow)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['status'], 'BLOCKED')
                self.assertIs(response.json()['execution_started'], False)
                self.assertEqual(store.list('gmais_jobs'), [])
                outcomes.append(response.json())
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(workflow, original)
