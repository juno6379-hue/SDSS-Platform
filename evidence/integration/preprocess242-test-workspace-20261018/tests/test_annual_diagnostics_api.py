"""Isolated router authentication/transport/concurrency + temporary CPU fixtures."""
import ast
import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import secrets
from threading import BoundedSemaphore, Event, Thread
import time
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from app import annual_diagnostics_api as api
from app.annual_diagnostics_service import _summary
import test_annual_quality_mask_diagnostics as fixtures


TOKEN = 'TEMP_DIAGNOSTIC_TEST_TOKEN'
AUTH = {'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'}


class AnnualDiagnosticsApiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ,{'GEOAI_API_TOKEN':TOKEN}); self.env.start(); self.addCleanup(self.env.stop)
        self.slot = BoundedSemaphore(1); self.guard = patch.object(api,'_SLOT',self.slot); self.guard.start(); self.addCleanup(self.guard.stop)
        self.store = Mock(); self.factory = Mock(return_value=self.store)
        self.app = FastAPI(); self.app.include_router(api.create_annual_diagnostics_router(self.factory))
        self.client = TestClient(self.app); self.addCleanup(self.client.close)

    def post(self,raw=b'{}',headers=AUTH):
        return self.client.post('/v1/lcluc/input-diagnostics',content=raw,headers=headers)

    def assert_error(self,response,status,code):
        self.assertEqual(response.status_code,status)
        self.assertEqual(response.json(),{'schema_version':1,'scope':api.HTTP_SCOPE,'error':{'code':code}})
        self.assertEqual(response.headers['cache-control'],'no-store'); self.assertEqual(response.headers['x-content-type-options'],'nosniff')

    def test_auth_configuration_required_and_wrong_bearer_no_factory_or_service(self):
        with patch.object(api,'read_annual_diagnostic_service',side_effect=AssertionError('service0')):
            for token in ('','   '):
                with patch.dict(os.environ,{'GEOAI_API_TOKEN':token}): self.assert_error(self.post(),503,'AUTH_CONFIGURATION_REQUIRED')
            for headers in ({}, {'Authorization':'Bearer wrong'}, {'Authorization':'bearer '+TOKEN}, {'Authorization':'Bearer '+TOKEN+' '}):
                self.assert_error(self.post(headers=headers),401,'AUTH_REQUIRED')
        self.factory.assert_not_called()

    def test_media_and_size_limits_pre_factory(self):
        self.assert_error(self.post(headers={**AUTH,'Content-Type':'text/plain'}),415,'UNSUPPORTED_MEDIA_TYPE')
        self.assert_error(self.post(b'x'*16385),413,'REQUEST_TOO_LARGE')
        self.assert_error(self.post(headers={**AUTH,'Content-Length':'16385'}),413,'REQUEST_TOO_LARGE')
        self.factory.assert_not_called()

    def test_invalid_service_request_422_no_store_get(self):
        response = self.post(); self.assertEqual(response.status_code,422)
        self.assertEqual(response.json()['status'],'INVALID_REQUEST'); self.store.get.assert_not_called()
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_service_output_status_mapping_schema_and_malformed_fixed503(self):
        value = _summary(); value.update(status='OUTPUT_INVALID',request_sha256='0'*64,blocking_stage='OUTPUT',issue={'code':'OUTPUT_INVALID','year':None})
        with patch.object(api,'read_annual_diagnostic_service',return_value=value):
            self.assertEqual(self.post().status_code,503); self.assertEqual(self.post().json()['status'],'OUTPUT_INVALID')
        for value in ({'SECRET_PATH':'private'}, {**_summary(),'execution_authorized':True},
                      {**_summary(),'schema_version':float('nan')}, {**_summary(),'extra':'private'}):
            with patch.object(api,'read_annual_diagnostic_service',return_value=value):
                self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')
        with patch.object(api,'read_annual_diagnostic_service',side_effect=RuntimeError('SECRET_TOKEN')):
            response = self.post()
        self.assert_error(response,503,'RESOURCE_UNAVAILABLE'); self.assertNotIn('SECRET',response.text)
        self.assertTrue(self.slot.acquire(False)); self.slot.release()

    def test_busy_nonblocking_and_worker_release_after_exception(self):
        started = Event(); release = Event(); results = []
        def slow(*args):
            started.set(); release.wait(10); return _summary()
        with patch.object(api,'read_annual_diagnostic_service',side_effect=slow):
            thread = Thread(target=lambda:results.append(self.post())); thread.start()
            try:
                self.assertTrue(started.wait(5)); response = self.post()
                self.assert_error(response,429,'DIAGNOSTIC_BUSY'); self.assertEqual(response.headers['retry-after'],'1')
            finally:
                release.set(); thread.join(10)
        self.assertFalse(thread.is_alive()); self.assertEqual(results[0].status_code,422)
        self.assertTrue(self.slot.acquire(False)); self.slot.release()

    def test_response_key_budget_and_source_year_must_belong_to_rows(self):
        for key in ('x'*257,'\ud800'):
            with self.assertRaises(ValueError): api._response({key:None})
        source = _summary()
        source.update(status='SOURCE_BLOCKED',request_sha256='0'*64,blocking_stage='ANNUAL',
            issue={'code':'SOURCE_BLOCKED','year':2022},per_year_observations=[
                {'year':year,'status':'NOT_CHECKED','counts':None,'policy_met':None} for year in (2020,2021)])
        with patch.object(api,'read_annual_diagnostic_service',return_value=source):
            self.assert_error(self.post(),503,'RESOURCE_UNAVAILABLE')
        source['issue']['year'] = 2021
        with patch.object(api,'read_annual_diagnostic_service',return_value=source):
            self.assertEqual(self.post().status_code,200)

    def test_actual_temp_two_years_service_and_response_copy(self):
        fixture = fixtures.AnnualQualityMaskDiagnosticsTests(); fixture.setUp()
        try:
            request = {'schema_version':1,'capability':'landcover.input_diagnostics','model_ref':fixture.model.model_ref,
                'training_report_sha256':fixture.model.report_sha,'requested_years':fixture.rows[:2],
                'policy':{'schema_version':1,'minimum_valid_numerator':1,'minimum_valid_denominator':2,'comparison':'greater_than_or_equal'}}
            self.factory.return_value = fixture.store
            with patch.object(fixture.store,'get',wraps=fixture.store.get) as get,patch.object(fixture.store,'put',side_effect=AssertionError('write')):
                response = self.post(json.dumps(request).encode())
            self.assertEqual(response.status_code,200); self.assertEqual(get.call_count,13)
            self.assertEqual(response.json()['status'],'CALLER_POLICY_MET_UNVERIFIED')
            self.assertFalse(response.json()['execution_authorized']); api._validator().validate(response.json())
            self.assertNotIn(str(fixture.store.root),response.text)
        finally: fixture.doCleanups()

    def test_main_ast_only_authorized_import_and_include_added(self):
        root = Path(__file__).resolve().parents[1]
        old = subprocess.run(['git','show','bec226ec460ca2497e092e34c21c64bd9ab0da99:backend/app/main.py'],cwd=root,capture_output=True,check=True).stdout.decode('utf-8-sig')
        current = ast.parse((root/'backend/app/main.py').read_text(encoding='utf-8-sig'))
        removed = []
        for node in list(current.body):
            if isinstance(node,ast.ImportFrom) and node.module == 'annual_diagnostics_api':
                self.assertEqual(len(node.names),1); self.assertEqual(node.names[0].name,'create_annual_diagnostics_router'); removed.append(node); current.body.remove(node)
            elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr == 'include_router':
                if node.value.args and isinstance(node.value.args[0],ast.Call) and isinstance(node.value.args[0].func,ast.Name) and node.value.args[0].func.id == 'create_annual_diagnostics_router':
                    expected = ast.parse('app.include_router(create_annual_diagnostics_router(lambda: store))').body[0]
                    self.assertEqual(ast.dump(node),ast.dump(expected)); removed.append(node); current.body.remove(node)
        old_tree = ast.parse(old)
        old_auth = next(node for node in old_tree.body if isinstance(node,ast.FunctionDef) and node.name == 'authorized')
        current_auth = next(node for node in current.body if isinstance(node,ast.FunctionDef) and node.name == 'authorized')
        expected_auth = copy.deepcopy(old_auth)
        call = next(node for node in ast.walk(expected_auth) if isinstance(node,ast.Call)
            and isinstance(node.func,ast.Attribute) and node.func.attr == 'compare_digest')
        call.args = ast.parse("secrets.compare_digest((authorization or '').encode('utf-8'), f'Bearer {token}'.encode('utf-8'))",mode='eval').body.args
        self.assertEqual(ast.dump(current_auth),ast.dump(expected_auth))
        current.body[current.body.index(current_auth)] = old_auth
        self.assertEqual(len(removed),2); self.assertEqual(ast.dump(current),ast.dump(old_tree))

    def test_actual_main_authorized_dependency_ascii_and_nonascii_safe401(self):
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root/'backend/app/main.py').read_text(encoding='utf-8-sig'))
        function = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == 'authorized')
        namespace = {'Request':Request,'Header':Header,'HTTPException':HTTPException,'os':os,'secrets':secrets}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<isolated-main-authorized>','exec'),namespace)
        app = FastAPI(dependencies=[Depends(namespace['authorized'])]); app.include_router(api.create_annual_diagnostics_router(self.factory))
        with TestClient(app) as client:
            for value in (b'Bearer wrong',b'Bearer \xff'):
                response = client.post('/v1/lcluc/input-diagnostics',content=b'{}',headers={b'authorization':value,b'content-type':b'application/json'})
                self.assertEqual(response.status_code,401); self.assertEqual(set(response.json()),{'detail'})
            self.assertEqual(client.post('/v1/lcluc/input-diagnostics',content=b'{}',headers=AUTH).status_code,422)
            with patch.dict(os.environ,{'GEOAI_API_TOKEN':''}):
                self.assertEqual(client.post('/v1/lcluc/input-diagnostics',content=b'{}',headers=AUTH).status_code,503)


class AsyncRouterBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ,{'GEOAI_API_TOKEN':TOKEN}); self.env.start(); self.addCleanup(self.env.stop)
        self.slot = BoundedSemaphore(1); guard = patch.object(api,'_SLOT',self.slot); guard.start(); self.addCleanup(guard.stop)
        self.factory = Mock(return_value=Mock())
        self.endpoint = api.create_annual_diagnostics_router(self.factory).routes[0].endpoint

    def request(self,messages,headers=None):
        values = iter(messages)
        async def receive(): return next(values)
        rawheaders = [(b'authorization',('Bearer '+TOKEN).encode()),(b'content-type',b'application/json')]
        return Request({'type':'http','method':'POST','path':'/v1/lcluc/input-diagnostics','headers':rawheaders if headers is None else headers},receive)

    async def test_chunked_oversize_disconnect_and_nonascii_auth_safe(self):
        request = self.request([{'type':'http.request','body':b'x'*10000,'more_body':True}, {'type':'http.request','body':b'x'*6385,'more_body':False}])
        response = await self.endpoint(request); self.assertEqual(response.status_code,413)
        response = await self.endpoint(self.request([{'type':'http.disconnect'}])); self.assertEqual(response.status_code,503)
        response = await self.endpoint(self.request([],[(b'authorization',b'Bearer \xff'),(b'content-type',b'application/json')]))
        self.assertEqual(response.status_code,401); self.factory.assert_not_called()

    async def test_cancellation_does_not_free_a_running_worker_slot(self):
        started = Event(); release = Event(); finished = Event()
        def slow(*args):
            started.set(); release.wait(10); finished.set(); return _summary()
        request = self.request([{'type':'http.request','body':b'{}','more_body':False}])
        with patch.object(api,'read_annual_diagnostic_service',side_effect=slow):
            task = asyncio.create_task(self.endpoint(request))
            try:
                for _ in range(500):
                    if started.is_set(): break
                    await asyncio.sleep(.01)
                self.assertTrue(started.is_set()); task.cancel()
                with self.assertRaises(asyncio.CancelledError): await task
                self.assertFalse(self.slot.acquire(False))
            finally: release.set()
            for _ in range(500):
                if finished.is_set() and self.slot.acquire(False):
                    self.slot.release(); break
                await asyncio.sleep(.01)
            else: self.fail('worker did not release')


if __name__ == '__main__':
    unittest.main()
