"""Actual route/auth/record AST with TempStore; no operating main import."""
import ast
import builtins
import hashlib
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient

from app import model_registration_provenance as provenance
from app import experiment_registry
from app.store import Store
import test_model_registration_provenance as fixtures


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'backend/app/main.py'
ORIGINAL = ROOT / 'evidence/integration/model-provenance-api-original-main-20261017.py'
ORIGINAL_SHA = 'bae2e9d6592054d946a9e90549ee84d154737a8626d16a1b273108eb768c92c8'
ROUTE_NAME = 'model_registration_provenance'
PATH = '/api/models/private-model/registration-provenance'
MESSAGE = '등록 선언 관측을 완료할 수 없습니다.'


def tree(path):
    return ast.parse(path.read_text(encoding='utf-8-sig'))


def isolated_app(source, store):
    body = []
    for node in tree(source).body:
        if isinstance(node, ast.FunctionDef) and node.name in ('authorized', 'record', 'models', ROUTE_NAME):
            body.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'app' for target in node.targets):
            body.append(node)
    namespace = dict(__name__='app._isolated_model_provenance_api', __package__='app',
        Depends=Depends, FastAPI=FastAPI, Header=Header, HTTPException=HTTPException,
        Request=Request, os=os, secrets=secrets, store=store)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['app']


class RecordingStore(Store):
    def __init__(self, root):
        self.accesses = []
        super().__init__(root)

    def get(self, kind, identifier):
        self.accesses.append(('get', kind, identifier))
        return super().get(kind, identifier)

    def put(self, kind, value):
        self.accesses.append(('put', kind))
        return super().put(kind, value)

    def list(self, kind):
        self.accesses.append(('list', kind))
        return super().list(kind)


class ModelRegistrationProvenanceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA:
            raise AssertionError('Original main source evidence changed')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = RecordingStore(Path(self.temporary.name))
        self.client = TestClient(isolated_app(MAIN, self.store))
        self.env = patch.dict(os.environ, {'GEOAI_API_TOKEN': ''})
        self.env.start()

    def tearDown(self):
        self.client.close(); self.env.stop(); self.temporary.cleanup()

    def records(self):
        with self.store.connect() as connection:
            return connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()

    def save(self, record):
        self.store.put('models', record)
        self.store.accesses.clear()

    def test_only_new_route_ast_added_all_existing_main_nodes_unchanged(self):
        before, after = tree(ORIGINAL), tree(MAIN)
        added = [node for node in after.body if isinstance(node, ast.FunctionDef) and node.name == ROUTE_NAME]
        self.assertEqual(len(added), 1)
        after.body = [node for node in after.body if node not in added]
        self.assertEqual(ast.dump(after), ast.dump(before))

    def test_all_five_states_are_200_exact_helper_response_get_once_write_zero(self):
        cases = []
        absent = {'id': 'private-model', 'dataset_version': 'v1'}; cases.append(('ABSENT', absent))
        invalid = fixtures.fixture(); invalid['model_version_declaration'] = None; cases.append(('INVALID', invalid))
        conflict = fixtures.fixture(); conflict['checkpoint_sha256'] = 'c' * 64; cases.append(('RECORD_CONFLICT', conflict))
        unknown = fixtures.fixture(); del unknown['training_report_sha256']; cases.append(('PARENT_BINDING_UNKNOWN', unknown))
        cases.append(('CONSISTENT_UNVERIFIED', fixtures.fixture()))
        for status, record in cases:
            self.save(record); before = self.records()
            response = self.client.get(PATH)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), provenance.inspect_model_registration_provenance(record))
            self.assertEqual(response.json()['status'], status)
            self.assertEqual(set(response.json()), fixtures.KEYS)
            for flag in fixtures.FLAGS: self.assertIs(response.json()[flag], False)
            self.assertEqual(self.store.accesses, [('get', 'models', 'private-model')])
            self.assertEqual(self.records(), before)

    def test_existing_models_list_body_and_headers_preserved(self):
        self.save(fixtures.fixture())
        with TestClient(isolated_app(ORIGINAL, self.store)) as original:
            expected = original.get('/api/models')
        actual = self.client.get('/api/models')
        self.assertEqual((actual.status_code, actual.content, dict(actual.headers)),
                         (expected.status_code, expected.content, dict(expected.headers)))

    def test_missing_model_preserves_404_fixed_detail_and_no_helper_or_write(self):
        with patch.object(provenance, 'inspect_model_registration_provenance', side_effect=AssertionError('not called')) as helper:
            response = self.client.get(PATH)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': '항목이 없습니다.'})
        helper.assert_not_called()
        self.assertEqual(self.store.accesses, [('get', 'models', 'private-model')])
        self.assertEqual(self.records(), [])

    def test_auth_denies_before_store_and_retains_existing_bearer_policy(self):
        self.save(fixtures.fixture())
        with patch.dict(os.environ, {'GEOAI_API_TOKEN': 'isolated-test-token'}):
            for headers in ({}, {'Authorization': 'Bearer wrong'}):
                response = self.client.get(PATH, headers=headers)
                self.assertEqual(response.status_code, 401)
            self.assertEqual(self.store.accesses, [])
            response = self.client.get(PATH, headers={'Authorization': 'Bearer isolated-test-token'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.store.accesses, [('get', 'models', 'private-model')])

    def test_store_exceptions_are_fixed503_with_no_private_details(self):
        for exception in (OSError('C:/private/checkpoint.pt'), ValueError('private-model'),
                          TypeError('secret'), RuntimeError('private-dataset'), MemoryError('private-memory')):
            with patch.object(self.store, 'get', side_effect=exception) as get:
                response = self.client.get(PATH)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {'detail': MESSAGE})
            get.assert_called_once_with('models', 'private-model')
        self.assertEqual(self.records(), [])

    def test_helper_exceptions_are_fixed503_and_existing_http_exception_is_preserved(self):
        self.save(fixtures.fixture()); before = self.records()
        for exception in (ValueError('C:/private/report.json'), RuntimeError('secret'), MemoryError('private-memory')):
            with patch.object(provenance, 'inspect_model_registration_provenance', side_effect=exception):
                response = self.client.get(PATH)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {'detail': MESSAGE})
        with patch.object(provenance, 'inspect_model_registration_provenance', side_effect=HTTPException(409, 'isolated-existing-http')):
            response = self.client.get(PATH)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {'detail': 'isolated-existing-http'})
        self.assertEqual(self.records(), before)
        self.assertTrue(all(item[0] == 'get' for item in self.store.accesses))

    def test_local_import_error_is_also_safe503_before_store(self):
        original_import = builtins.__import__
        def fail_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'model_registration_provenance' and level == 1:
                raise ImportError('C:/private/source-path.py')
            return original_import(name, globals, locals, fromlist, level)
        with patch('builtins.__import__', side_effect=fail_import):
            response = self.client.get(PATH)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'detail': MESSAGE})
        self.assertEqual(self.store.accesses, [])

    def test_no_checkpoint_report_source_write_network_or_registration_calls(self):
        record = fixtures.fixture()
        record.update(checkpoint_path='file:///private-checkpoint', status='Approved',
                      independent_evaluation=True, scientific_accuracy_validated=True)
        self.save(record); before = self.records()
        with TestClient(self.client.app) as client, \
             patch.object(Path, 'open', side_effect=AssertionError('no artifact open')), \
             patch.object(experiment_registry, 'digest', side_effect=AssertionError('no rehash')), \
             patch.object(experiment_registry, 'register_experiment', side_effect=AssertionError('no registration')), \
             patch.object(Store, 'put', side_effect=AssertionError('no write')), \
             patch('socket.create_connection', side_effect=AssertionError('no outbound connection')):
            response = client.get(PATH)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'CONSISTENT_UNVERIFIED')
        for flag in fixtures.FLAGS: self.assertIs(response.json()[flag], False)
        for secret in ('private-model', 'file:///private', ' v2 ', 'a' * 64, 'b' * 64): self.assertNotIn(secret, response.text)
        self.assertEqual(self.store.accesses, [('get', 'models', 'private-model')])
        self.assertEqual(self.records(), before)
