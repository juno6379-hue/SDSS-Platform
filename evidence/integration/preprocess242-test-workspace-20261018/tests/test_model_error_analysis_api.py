"""Isolated TempStore + actual writer exports; no main import or model execution."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient
from app import model_error_analysis_api as api
from app.ml.error_analysis import write_training_error_analysis
from app.store import Store


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ModelErrorAnalysisApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = Store(self.root)
        self.directory = self.root / 'models' / 'fixture'
        self.directory.mkdir(parents=True)
        checkpoint = b'opaque test-only checkpoint bytes; never torch-loaded'
        (self.directory / 'best.pt').write_bytes(checkpoint)
        matrix = [[0]*9 for _ in range(9)]
        matrix[0][:2] = [3, 1]
        matrix[1][:2] = [2, 4]
        validation = {'confusion_matrix': matrix, 'loss': .1}
        self.report = {'model_id': 'fixture', 'training_state': 'completed', 'selected_epoch': 1,
            'class_names': ['=formula', 'trees', 'grass', 'flooded', 'crops', 'shrub', 'built', 'bare', 'snow'],
            'checkpoint_sha256': sha(checkpoint), 'reference_kind': 'test_fixture_only',
            'history': [{'epoch': 1, 'val': copy.deepcopy(validation)}, {'epoch': 2, 'val': {'loss': .2}}],
            'selected_validation_metrics': validation, 'test_metrics': {'confusion_matrix': copy.deepcopy(matrix)}}
        self.report['error_analysis'] = write_training_error_analysis(self.report, self.directory, self.root)
        self.model = {'id': 'fixture', 'status': 'Draft', 'checkpoint_path': 'models/fixture/best.pt',
                      'checkpoint_sha256': sha(checkpoint)}
        self.rebind()
        self.request = {'schema_version': 1, 'model_ref': {'id': 'fixture', 'version': ' v1 ', 'sha256': sha(checkpoint)},
                        'training_report_sha256': self.model['training_report_sha256']}
        source = Path(__file__).resolve().parents[1] / 'backend/app/main.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        authorized = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'authorized')
        scope = {'Request': Request, 'Header': Header, 'HTTPException': HTTPException, 'os': os, 'secrets': secrets}
        exec(compile(ast.Module(body=[authorized], type_ignores=[]), str(source), 'exec'), scope)
        app = FastAPI(dependencies=[Depends(scope['authorized'])])
        app.include_router(api.create_model_error_analysis_router(lambda: self.store))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.environment = patch.dict(os.environ, {'GEOAI_API_TOKEN': 'fixture-token'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def rebind(self):
        raw = (json.dumps(self.report, ensure_ascii=False, allow_nan=False)+'\n').encode()
        (self.directory / 'report.json').write_bytes(raw)
        self.model['training_report_sha256'] = sha(raw)
        self.model['model_version_declaration'] = {'schema_version': 1, 'source': 'CALLER_EXPLICIT_REGISTRATION',
            'version': ' v1 ', 'checkpoint_sha256': self.model['checkpoint_sha256'], 'training_report_sha256': sha(raw)}
        self.store.put('models', self.model)
        if hasattr(self, 'request'):
            self.request['training_report_sha256'] = sha(raw)

    def post(self, value=None, suffix='', **kwargs):
        return self.client.post('/v1/models/error-analysis'+suffix, json=self.request if value is None else value,
                                headers={'Authorization': 'Bearer fixture-token'}, **kwargs)

    def test_available_draft_actual_writer_recomputed_null_rates_and_no_store_writes(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(self.store, 'put', side_effect=AssertionError('read only')):
            result = self.post()
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(set(body), {'schema_version', 'scope', 'status', 'issue', 'model_ref', 'training_report_sha256',
                                    'analysis', 'artifacts', 'scientific_accuracy_validated', 'standard_gmais_result'})
        self.assertEqual(body['status'], 'AVAILABLE')
        self.assertIsNone(body['issue'])
        self.assertEqual(body['analysis']['selected_epoch'], 1)
        self.assertEqual(body['analysis']['by_split']['val']['misclassified_pixel_count'], 3)
        self.assertIsNone(body['analysis']['by_split']['test']['classes'][7]['precision'])
        self.assertFalse(body['scientific_accuracy_validated'])
        self.assertFalse(body['standard_gmais_result'])
        self.assertEqual(result.headers['cache-control'], 'no-store')
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_all_three_downloads_are_exact_verified_copies_csv_escape_preserved(self):
        for i, filename in enumerate(api.FILES):
            result = self.post(suffix=f'/assets/{i}')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.content, (self.directory/filename).read_bytes())
            self.assertIn(filename, result.headers['content-disposition'])
        self.assertIn(b"'=formula", self.post(suffix='/assets/1').content)

    def test_missing_declaration_and_artifact_unavailable_no_generation(self):
        del self.model['model_version_declaration']
        self.store.put('models', self.model)
        result = self.post().json()
        self.assertEqual(result['issue'], 'MODEL_VERSION_DECLARATION_UNAVAILABLE')
        self.assertIsNone(result['analysis'])
        self.assertEqual(result['artifacts'], [])
        self.rebind()
        (self.directory/api.FILES[2]).unlink()
        self.assertEqual(self.post().json()['issue'], 'ERROR_ANALYSIS_UNAVAILABLE')
        self.assertEqual(self.post(suffix='/assets/2').status_code, 404)
        self.assertFalse((self.directory/api.FILES[2]).exists())

    def test_missing_error_analysis_is_unavailable_legacy_not_fake_zero(self):
        del self.report['error_analysis']
        self.rebind()
        self.assertEqual(self.post().json()['status'], 'UNAVAILABLE')
        self.assertIsNone(self.post().json()['analysis'])

    def test_auth_and_notfound_and_request_errors_before_store(self):
        self.assertEqual(self.client.post('/v1/models/error-analysis', json=self.request).status_code, 401)
        missing = copy.deepcopy(self.request); missing['model_ref']['id'] = 'absent'
        self.assertEqual(self.post(missing).status_code, 404)
        for i in ('3', '-1', '00', 'private'):
            self.assertEqual(self.post(suffix='/assets/'+i).status_code, 404)
        invalid = [{}, {**self.request, 'schema_version': True}, {**self.request, 'extra': 1}]
        for key, bad in [('id', '../fixture'), ('id', '한글'), ('version', 'latest'), ('version', None), ('sha256', True)]:
            value = copy.deepcopy(self.request); value['model_ref'][key] = bad; invalid.append(value)
        with patch.object(self.store, 'get', side_effect=AssertionError('must not read')):
            for value in invalid:
                self.assertEqual(self.post(value).status_code, 400)

    def test_strict_transport_and_stream_size(self):
        for raw in (b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}', b'{"x":1e999}', b'\xff', b'null'):
            response = self.client.post('/v1/models/error-analysis', content=raw, headers={'Authorization':'Bearer fixture-token'})
            self.assertEqual(response.status_code, 400)
        response = self.client.post('/v1/models/error-analysis', content=b' '*16385, headers={'Authorization':'Bearer fixture-token'})
        self.assertEqual(response.status_code, 413)

    def test_request_pins_and_declaration_conflict(self):
        for key in ('sha256', 'version'):
            value = copy.deepcopy(self.request); value['model_ref'][key] = '0'*64 if key=='sha256' else 'v2'
            self.assertEqual(self.post(value).status_code, 409)
        value = copy.deepcopy(self.request); value['training_report_sha256'] = '0'*64
        self.assertEqual(self.post(value).status_code, 409)
        self.model['model_version_declaration']['checkpoint_sha256'] = '0'*64
        self.store.put('models', self.model)
        self.assertEqual(self.post().status_code, 503)

    def test_checkpoint_report_and_each_asset_tampering_rejected(self):
        for name in ('best.pt', 'report.json', *api.FILES):
            path = self.directory/name; raw = path.read_bytes(); path.write_bytes(raw+b'changed')
            response = self.post(); self.assertEqual(response.status_code, 503, name)
            self.assertNotIn(str(self.root), response.text)
            path.write_bytes(raw)

    def test_rebound_report_does_not_bypass_confusion_epoch_or_flags_verification(self):
        original = copy.deepcopy(self.report)
        mutations = [lambda r:r.update(selected_epoch=True), lambda r:r['history'][0]['val'].update(loss=.2),
                     lambda r:r['error_analysis']['by_split']['val']['classes'][0].update(recall=0),
                     lambda r:r['error_analysis'].update(scientific_accuracy_validated=0),
                     lambda r:r.update(reference_kind={'secret':'path'}),
                     lambda r:r['error_analysis']['artifacts'][1].update(path='models/other/error-analysis-classes.csv')]
        for mutate in mutations:
            self.report=copy.deepcopy(original);mutate(self.report);self.rebind()
            self.assertEqual(self.post().status_code,503)

    def test_limits_and_internal_alias_namespace_rejected(self):
        with patch.object(api,'MAX_CHECKPOINT',1):
            self.assertEqual(self.post().status_code,503)
        with patch.object(api,'MAX_REPORT',1):
            self.assertEqual(self.post().status_code,503)
        for path in ('models/other/best.pt', 'models/fixture/../fixture/best.pt'):
            self.model['checkpoint_path']=path;self.store.put('models',self.model)
            self.assertEqual(self.post().status_code,503)

    def test_windows_relative_checkpoint_and_artifact_paths_supported(self):
        self.model['checkpoint_path']='models\\fixture\\best.pt'
        for item in self.report['error_analysis']['artifacts']:
            item['path']=item['path'].replace('/','\\')
        self.rebind()
        self.assertEqual(self.post().status_code,200)

    def test_copied_snapshot_bytes_detached_from_later_file_changes(self):
        response,payloads=api.read_model_error_analysis(self.store,self.request)
        original=payloads[1]
        (self.directory/api.FILES[1]).write_bytes(b'later mutation')
        self.assertEqual(payloads[1],original)
        self.assertEqual(sha(original),response['artifacts'][1]['sha256'])
        self.assertEqual(self.post().status_code,503)

    def test_concurrent_readers_never_write_or_generate(self):
        with patch.object(self.store,'put',side_effect=AssertionError('write')):
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda _:api.read_model_error_analysis(self.store,self.request),range(8)))
        self.assertTrue(all(result[0]==results[0][0] and result[1]==results[0][1] for result in results))

    def test_internal_symlink_or_junction_classification_fails_closed(self):
        # Windows creating symlinks needs privileges; the platform predicates are
        # exercised without changing filesystem policy or requiring elevation.
        original=Path.is_symlink
        def classified(path):
            return path==self.directory or original(path)
        with patch.object(Path,'is_symlink',classified):
            self.assertEqual(self.post().status_code,503)
        if hasattr(Path,'is_junction'):
            original_junction=Path.is_junction
            with patch.object(Path,'is_junction',lambda path:path==self.directory or original_junction(path)):
                self.assertEqual(self.post().status_code,503)


if __name__=='__main__':
    unittest.main()
