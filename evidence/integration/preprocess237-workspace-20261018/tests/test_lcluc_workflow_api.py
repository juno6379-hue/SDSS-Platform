"""Isolated FastAPI + TempStore; never imports or posts to operating main."""
import ast
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import threading
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient

from backend.app import lcluc_workflow_api as api
from backend.app import lcluc_workflow as core
import test_lcluc_workflow as fixture_module


class LclucWorkflowApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.LclucWorkflowTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixture_module.LclucWorkflowTests.tearDownClass()

    def setUp(self):
        self.fixture=fixture_module.LclucWorkflowTests('test_actual_cpu_inference_change_report_trace_and_hashed_artifacts')
        self.fixture.setUp();self.store=self.fixture.store;self.root=self.fixture.root
        self.request=self.fixture.request;self.calls=[]
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'backend/app/main.py').read_text(encoding='utf-8'))
        authorized=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='authorized')
        namespace={'os':os,'secrets':secrets,'Request':Request,'Header':Header,'HTTPException':HTTPException}
        exec(compile(ast.Module(body=[authorized],type_ignores=[]),'<isolated-main-auth>','exec'),namespace)
        app=FastAPI(dependencies=[Depends(namespace['authorized'])])
        def get_store():
            self.calls.append(threading.current_thread().name)
            return self.store
        app.include_router(api.create_lcluc_workflow_router(get_store))
        self.env=patch.dict(os.environ,{'GEOAI_API_TOKEN':'fixture-secret'});self.env.start()
        self.client=TestClient(app);self.client.__enter__()
        self.headers={'Authorization':'Bearer fixture-secret'}
        self.identifier=hashlib.sha256(self.request['idempotency_key'].encode()).hexdigest()
        self.url='/v1/lcluc/workflows/'+self.identifier

    def tearDown(self):
        self.client.__exit__(None,None,None);self.env.stop();self.fixture.tearDown()

    def post(self,value=None,**kwargs):
        return self.client.post('/v1/lcluc/workflows',json=self.request if value is None else value,headers=self.headers,**kwargs)

    def get(self,suffix=''):
        return self.client.get(self.url+suffix,headers=self.headers)

    def success(self):
        response=self.post();self.assertEqual(response.status_code,200,response.text)
        result=response.json();self.assertEqual(result['status'],'SUCCEEDED',result)
        return result

    def test_actual_cpu_post_status_report_asset_and_replay_share_verified_snapshot(self):
        record=self.success()
        self.assertEqual(record['trace_id'],self.request['trace_id'])
        self.assertFalse(record['standard_gmais_result']);self.assertFalse(record['scientific_accuracy_validated'])
        with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET must not execute')):
            status=self.get();self.assertEqual(status.status_code,200,status.text)
            self.assertTrue(status.json()['replayed'])
            report=self.get('/report');self.assertEqual(report.status_code,200,report.text)
            self.assertEqual(report.json()['years'],[2020,2021])
            self.assertEqual(report.json()['checkpoint_sha256'],self.request['model_ref']['sha256'])
            for index,item in enumerate(record['artifacts']):
                download=self.get('/assets/'+str(index));self.assertEqual(download.status_code,200,download.text)
                self.assertEqual(hashlib.sha256(download.content).hexdigest(),item['sha256'])
                self.assertIn('attachment;',download.headers['content-disposition'])
                self.assertEqual(download.headers['cache-control'],'no-store')
                self.assertEqual(download.headers['x-content-type-options'],'nosniff')
        replay=self.post();self.assertEqual(replay.status_code,200);self.assertTrue(replay.json()['replayed'])
        self.assertEqual(record['request_snapshot'],replay.json()['request_snapshot'])
        self.assertTrue(all(name.startswith('AnyIO worker') for name in self.calls),self.calls)

    def test_existing_authorized_dependency_guards_all_routes_before_store(self):
        for method,url in (('POST','/v1/lcluc/workflows'),('GET',self.url),('GET',self.url+'/report'),('GET',self.url+'/assets/0')):
            response=self.client.request(method,url,json=self.request if method=='POST' else None)
            self.assertEqual(response.status_code,401)
        self.assertEqual(self.calls,[])

    def test_invalid_strict_json_and_stream_size_do_not_acquire_store(self):
        bad=[b'{"schema_version":1,"schema_version":1}',b'{"x":NaN}',b'{"x":1e999}',b'null',b'\xff']
        for raw in bad:
            response=self.client.post('/v1/lcluc/workflows',content=raw,headers=self.headers)
            self.assertEqual(response.status_code,400,response.text)
            self.assertEqual(response.json()['error']['code'],'INVALID_REQUEST')
        response=self.client.post('/v1/lcluc/workflows',content=iter([b'x'*8192,b'x'*8193]),headers=self.headers)
        self.assertEqual(response.status_code,413);self.assertEqual(self.calls,[])
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_preclaim_gate_blocked_409_has_no_get_record_or_output(self):
        model=self.store.get('models','fixture-model');model['status']='Draft';self.store.put('models',model)
        before=self.store.list(core.KIND)
        response=self.post();self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(response.json()['status'],'BLOCKED');self.assertFalse(response.json()['replayed'])
        self.assertEqual(self.store.list(core.KIND),before);self.assertEqual(self.get().status_code,404)
        self.assertFalse((self.root/'results').exists())

    def test_failed_claim_is_200_historical_failure_and_never_automatic_retry(self):
        execute=api.execute_lcluc_workflow
        def fail(store,request):
            return execute(store,request,_runner=lambda *_:(_ for _ in ()).throw(OSError('private-key-path')))
        with patch.object(api,'execute_lcluc_workflow',side_effect=fail):
            first=self.post();self.assertEqual(first.status_code,200)
            self.assertEqual(first.json()['status'],'FAILED');self.assertNotIn('private',first.text)
        with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET retry')):
            self.assertEqual(self.get().json()['status'],'FAILED')
            self.assertEqual(self.get('/report').status_code,409)
            self.assertEqual(self.get('/assets/0').json()['error']['code'],'WORKFLOW_NOT_SUCCEEDED')
        replay=self.post();self.assertTrue(replay.json()['replayed'])

    def test_idempotency_conflict_and_unknown_identifier(self):
        self.success()
        changed=copy.deepcopy(self.request);changed['trace_id']='other-trace'
        conflict=self.post(changed);self.assertEqual(conflict.status_code,409)
        self.assertEqual(conflict.json()['error']['code'],'IDEMPOTENCY_CONFLICT')
        self.assertEqual(self.client.get('/v1/lcluc/workflows/'+'f'*64,headers=self.headers).status_code,404)
        self.assertEqual(self.client.get('/v1/lcluc/workflows/not-a-hash',headers=self.headers).status_code,400)

    def test_changed_report_or_any_asset_returns_fixed_503_without_writes(self):
        record=self.success();native=self.store.put
        path=self.root/record['artifacts'][0]['path'];path.write_bytes(b'private changed bytes')
        with patch.object(self.store,'put',side_effect=AssertionError('GET write')):
            for suffix in ('','/assets/0'):
                response=self.get(suffix);self.assertEqual(response.status_code,503)
                self.assertEqual(response.json()['error']['code'],'STORED_OUTPUT_CHANGED')
                self.assertNotIn('private',response.text)
        self.assertEqual(native.__self__,self.store)

    def test_invalid_artifact_indices_are_404(self):
        self.success()
        for index in ('-1','01','128','9999','abc'):
            self.assertEqual(self.get('/assets/'+index).status_code,404)

    def test_malformed_record_identity_flags_snapshot_and_cross_namespace_fail_closed(self):
        record=self.success();record.pop('replayed')
        variants=[dict(record,id='f'*64),dict(record,scientific_accuracy_validated=0),dict(record,status='READY'),
                  dict(record,request_snapshot={}),dict(record,extra='private-token')]
        for path in ('../outside.json','results/other/timeseries.json','https://example.invalid/secret',
                     f'results/lcluc-workflows/{"f"*64}/timeseries.json'):
            item=copy.deepcopy(record);item['artifacts'][0]['path']=path;variants.append(item)
        for bad in variants:
            with patch.object(self.store,'get',return_value=bad):
                response=self.get();self.assertEqual(response.status_code,503,response.text)
                self.assertNotIn('private',response.text);self.assertNotIn('example.invalid',response.text)

    def test_api_snapshot_bytes_survive_later_disk_change(self):
        record=self.success();item=record['artifacts'][0]
        raw,_,_=api._artifact(self.root,self.identifier,item,copy_bytes=True)
        (self.root/item['path']).write_bytes(b'after copy')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
        self.assertEqual(self.get('/assets/0').status_code,503)

    def test_native_store_and_producer_exceptions_do_not_leak(self):
        with patch.object(self.store,'get',side_effect=OSError('password private path')):
            response=self.get();self.assertEqual(response.status_code,503);self.assertNotIn('private',response.text)
        with patch.object(api,'execute_lcluc_workflow',side_effect=RuntimeError('token private path')):
            response=self.post();self.assertEqual(response.status_code,503);self.assertNotIn('private',response.text)

    def test_concurrent_post_returns_running_then_failed_with_one_dispatch(self):
        started,release=threading.Event(),threading.Event();calls=[];native=api.execute_lcluc_workflow
        def runner(*_):
            calls.append(1);started.set();release.wait(5);raise RuntimeError('private')
        def execute(store,request):return native(store,request,_runner=runner)
        with patch.object(api,'execute_lcluc_workflow',side_effect=execute),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.post);self.assertTrue(started.wait(5))
            second=self.post();self.assertEqual(second.status_code,200,second.text)
            self.assertEqual(second.json()['status'],'RUNNING');self.assertTrue(second.json()['replayed'])
            release.set();self.assertEqual(first.result().json()['status'],'FAILED')
        self.assertEqual(len(calls),1)

    def test_reader_limits_and_namespace_change_fail_without_execution(self):
        record=self.success()
        with patch.object(api,'MAX_ASSET',1):
            self.assertEqual(self.get('/assets/0').status_code,503)
        native=Path.resolve
        def retarget(path,*args,**kwargs):
            if path.name==self.identifier:return self.root/'other'/path.name
            return native(path,*args,**kwargs)
        with patch.object(Path,'resolve',retarget),patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET execute')):
            self.assertEqual(self.get().status_code,503)

    def test_report_snapshot_json_and_typed_year_binding_reject_malformed_payload(self):
        record=self.success();record.pop('replayed')
        path=self.root/record['report_path'];original=path.read_bytes()
        for raw in (b'{"years":[2020,2021],"years":[2020,2021]}',b'{"number":NaN}',
                    original.replace(b'2020,',b'2020.0,',1)):
            path.write_bytes(raw)
            changed=copy.deepcopy(record)
            for item in changed['artifacts']:
                if item['path']==record['report_path']:item['sha256']=hashlib.sha256(raw).hexdigest()
            with patch.object(self.store,'get',return_value=changed):
                self.assertEqual(self.get('/report').status_code,503)

    def test_download_reads_at_most_limit_plus_one_even_if_file_grows(self):
        record=self.success();item=record['artifacts'][0];path=self.root/item['path']
        path.write_bytes(b'a');item['sha256']=hashlib.sha256(b'a').hexdigest()
        class Growing(io.BytesIO):
            def close(self):self.bytes_read=self.tell()
        stream=Growing(b'0123456789')
        with patch.object(Path,'open',return_value=stream):
            with self.assertRaises(api.ApiIssue) as error:
                api._artifact(self.root,self.identifier,item,copy_bytes=True,maximum=3)
        self.assertEqual(error.exception.code,'STORED_OUTPUT_CHANGED');self.assertEqual(stream.bytes_read,4)


if __name__=='__main__':unittest.main()
