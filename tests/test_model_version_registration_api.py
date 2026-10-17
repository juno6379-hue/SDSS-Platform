"""Actual main AST route/auth fragments in an isolated app; never import main."""
import ast
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from threading import RLock
import unittest
from unittest.mock import patch

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient

from app import experiment_registry
import test_model_version_declaration as fixtures


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'backend/app/main.py'
ORIGINAL = ROOT / 'evidence/integration/model-version-api-original-main-20261017.py'
ORIGINAL_SHA = '11dfe9aafe9c419381650349eb2572b9625e5a243ec07f76a28e5ad79a639be9'
PATH = '/api/models/register-experiment'


def fragments(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ('authorized', 'register_completed_experiment'):
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'app' for target in node.targets):
            selected.append(node)
    if len(selected) != 3:
        raise AssertionError('Actual main auth/app/route fragments must remain unambiguous')
    return selected


def normalize_authorized_comparison(node):
    """137 allows only the exact UTF-8 argument change; keep all other AST."""
    calls = [item for item in ast.walk(node) if isinstance(item, ast.Call)
             and isinstance(item.func, ast.Attribute) and isinstance(item.func.value, ast.Name)
             and item.func.value.id == 'secrets' and item.func.attr == 'compare_digest']
    expected = ast.parse("secrets.compare_digest((authorization or '').encode('utf-8'), f'Bearer {token}'.encode('utf-8'))", mode='eval').body
    if len(calls) != 1 or ast.dump(calls[0]) != ast.dump(expected):
        raise AssertionError('Only the exact authorized UTF-8 comparison is allowed')
    original = ast.parse("secrets.compare_digest(authorization or '', f'Bearer {token}')", mode='eval').body
    calls[0].args = original.args
    return node


class RecordingLock:
    def __init__(self):
        self.inner = RLock()
        self.active = 0
        self.entries = 0
        self.exits = 0

    def __enter__(self):
        self.inner.acquire(); self.active += 1; self.entries += 1
        return self

    def __exit__(self, *args):
        self.active -= 1; self.exits += 1; self.inner.release()


def isolated_app(source, store, lock):
    namespace = dict(__name__='app._isolated_model_version_api', __package__='app',
        Body=Body, Depends=Depends, FastAPI=FastAPI, Header=Header,
        HTTPException=HTTPException, Request=Request, os=os, secrets=secrets,
        store=store, registry_lock=lock)
    code = compile(ast.Module(body=fragments(source), type_ignores=[]), str(source), 'exec')
    exec(code, namespace)
    return namespace['app']


class ModelVersionRegistrationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA:
            raise AssertionError('Original main API source evidence changed')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.files = fixtures.ModelVersionDeclarationTests()
        self.report, self.checkpoint = self.files.fixture(self.root)
        self.store = fixtures.RecordingStore(self.root)
        self.lock = RecordingLock()
        self.client = TestClient(isolated_app(MAIN, self.store, self.lock))
        self.env = patch.dict(os.environ, {'GEOAI_API_TOKEN': ''})
        self.env.start()

    def tearDown(self):
        self.client.close(); self.env.stop(); self.temporary.cleanup()

    def test_original_auth_app_and_route_metadata_are_unchanged(self):
        before, after = fragments(ORIGINAL), fragments(MAIN)
        normalize_authorized_comparison(after[0])
        self.assertEqual([ast.dump(node) for node in before[:2]], [ast.dump(node) for node in after[:2]])
        old_route, new_route = before[-1], after[-1]
        self.assertEqual([ast.dump(node) for node in old_route.decorator_list],
                         [ast.dump(node) for node in new_route.decorator_list])
        self.assertEqual(ast.dump(old_route.args), ast.dump(new_route.args))
        self.assertEqual([ast.dump(node) for node in old_route.body[-1].handlers],
                         [ast.dump(node) for node in new_route.body[-1].handlers])

    def test_omitted_real_registration_exact_old_response_records_and_order(self):
        outcomes = []
        for source in (ORIGINAL, MAIN):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); report, _ = self.files.fixture(root)
                store = fixtures.RecordingStore(root); lock = RecordingLock()
                with TestClient(isolated_app(source, store, lock)) as client, \
                     patch('app.store.now', return_value='2026-10-17T00:00:00Z'):
                    response = client.post(PATH, json={'report_path': str(report)})
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual((lock.entries, lock.exits, lock.active), (1, 1, 0))
                self.assertNotIn('model_version_declaration', response.json()['model'])
                outcomes.append((response.content, dict(response.headers), self.files.stored_bytes(store), store.puts))
        self.assertEqual(outcomes[0], outcomes[1])

    def test_present_null_raw_version_and_omitted_kwargs_inside_lock(self):
        for body, expected_kwargs in (({'report_path': 'missing'}, {}),
                                    ({'report_path': 'missing', 'model_version': None}, {'model_version': None}),
                                    ({'report_path': 'missing', 'model_version': ' v1 '}, {'model_version': ' v1 '})):
            calls = []
            def record(*args, **kwargs):
                self.assertEqual(self.lock.active, 1)
                calls.append((args, kwargs)); return {'isolated_mock': True}
            with patch.object(experiment_registry, 'register_experiment', side_effect=record):
                response = self.client.post(PATH, json=body)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(calls, [((self.store, 'missing'), expected_kwargs)])
            self.assertEqual(self.lock.active, 0)

    def test_explicit_real_registration_exact5_hashes_draft_false_and_files_unchanged(self):
        before = self.files.file_hashes(self.root)
        response = self.client.post(PATH, json={'report_path': str(self.report), 'model_version': ' caller-v2 ',
            'status': 'Approved', 'independent_evaluation': True, 'dataset_version': 'injected', 'overwrite': True})
        self.assertEqual(response.status_code, 201, response.text)
        model, dataset = response.json()['model'], response.json()['dataset']
        self.assertEqual(model['model_version_declaration'], {
            'schema_version': 1, 'source': 'CALLER_EXPLICIT_REGISTRATION', 'version': ' caller-v2 ',
            'checkpoint_sha256': hashlib.sha256(self.checkpoint.read_bytes()).hexdigest(),
            'training_report_sha256': hashlib.sha256((self.checkpoint.parent / 'report.json').read_bytes()).hexdigest()})
        self.assertEqual(model['status'], 'Draft')
        self.assertIs(model['independent_evaluation'], False)
        self.assertIs(model['scientific_accuracy_validated'], False)
        self.assertEqual(model['dataset_version'], 'v1')
        self.assertNotIn('model_version', model)
        self.assertNotIn('model_version_declaration', dataset)
        self.assertEqual(self.files.file_hashes(self.root), before)
        self.assertEqual([kind for kind, _ in self.store.puts], ['datasets', 'models'])

    def test_invalid_explicit_values_existing422_detail_before_any_put(self):
        before = self.files.file_hashes(self.root)
        for value in (None, True, 1, '', ' ', 'latest', ' CURRENT ', 'x\x00', '\ud800', 'x' * 257):
            response = self.client.post(PATH, content=json.dumps({'report_path': str(self.report), 'model_version': value}),
                headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(set(response.json()), {'detail'})
            self.assertIs(type(response.json()['detail']), str)
            self.assertEqual(self.store.puts, [])
            self.assertEqual(self.lock.active, 0)
        self.assertEqual(self.files.file_hashes(self.root), before)
        self.assertEqual(self.files.stored_bytes(self.store), [])

    def test_conflict_and_duplicate_ids_still422_without_new_puts(self):
        for trained in ({'model_version': 'other'}, {'model_version': None}, {'model_version_declaration': None}):
            value = json.loads(self.report.read_text()); value['training'].update(trained)
            self.report.write_text(json.dumps(value))
            (self.checkpoint.parent / 'report.json').write_text(json.dumps(value['training']))
            response = self.client.post(PATH, json={'report_path': str(self.report), 'model_version': 'v1'})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(self.store.puts, [])
            for key in trained: value['training'].pop(key)
            self.report.write_text(json.dumps(value))
            (self.checkpoint.parent / 'report.json').write_text(json.dumps(value['training']))
        first = self.client.post(PATH, json={'report_path': str(self.report), 'model_version': 'v1'})
        self.assertEqual(first.status_code, 201)
        self.store.puts.clear(); before = self.files.stored_bytes(self.store)
        second = self.client.post(PATH, json={'report_path': str(self.report), 'model_version': 'v2', 'overwrite': True})
        self.assertEqual(second.status_code, 422)
        self.assertEqual(self.store.puts, [])
        self.assertEqual(self.files.stored_bytes(self.store), before)

    def test_prior_missing_path_and_checkpoint_errors_preserved_before_version(self):
        for payload in ({'report_path': 'missing', 'model_version': None},
                        {'report_path': str(self.report), 'model_version': 'latest'}):
            if payload['report_path'] != 'missing': self.checkpoint.write_bytes(b'changed')
            expected = self.client.post(PATH, json={'report_path': payload['report_path']})
            actual = self.client.post(PATH, json=payload)
            self.assertEqual(actual.status_code, 422)
            self.assertEqual(actual.content, expected.content)
            self.assertEqual(self.store.puts, [])

    def test_ignored_unknown_extras_do_not_expand_registration_kwargs(self):
        body = {'report_path': 'fixture', 'status': 'Approved', 'approval_ref': 'injected',
                'dataset_version': 'v999', 'overwrite': True, 'unrelated': {}}
        with patch.object(experiment_registry, 'register_experiment', return_value={'isolated_mock': True}) as spy:
            response = self.client.post(PATH, json=body)
        self.assertEqual(response.status_code, 201)
        spy.assert_called_once_with(self.store, 'fixture')

    def test_auth_denies_before_lock_or_register_and_accepts_existing_bearer_policy(self):
        with patch.dict(os.environ, {'GEOAI_API_TOKEN': 'isolated-test-token'}), \
             patch.object(experiment_registry, 'register_experiment', return_value={'isolated_mock': True}) as spy:
            body = {'report_path': 'fixture', 'model_version': 'v1'}
            for headers in ({}, {'Authorization': 'Bearer wrong'}):
                response = self.client.post(PATH, json=body, headers=headers)
                self.assertEqual(response.status_code, 401)
            self.assertEqual(self.lock.entries, 0); spy.assert_not_called()
            response = self.client.post(PATH, json=body, headers={'Authorization': 'Bearer isolated-test-token'})
            self.assertEqual(response.status_code, 201)
            spy.assert_called_once_with(self.store, 'fixture', model_version='v1')

    def test_existing_exception_tuple_converts422_and_releases_lock(self):
        for exception in (ValueError('fixture'), OSError('fixture'), KeyError('fixture'), TypeError('fixture')):
            with patch.object(experiment_registry, 'register_experiment', side_effect=exception):
                response = self.client.post(PATH, json={'report_path': 'fixture', 'model_version': 'v1'})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {'detail': str(exception)})
            self.assertEqual(self.lock.active, 0)
        self.assertEqual(self.lock.entries, self.lock.exits)

    def test_non_object_and_missing_body_keep_fastapi422_before_route(self):
        for kwargs in ({'json': []}, {'content': ''}):
            response = self.client.post(PATH, **kwargs)
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.lock.entries, 0)
        self.assertEqual(self.store.puts, [])
