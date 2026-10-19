"""Synthetic tiny JSON only: HTTP input, strict projection and worker isolation."""
import asyncio
import copy
import hashlib
import json
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import test_readiness_connectivity_lineage as fixtures
from backend.app import readiness_source_identity_api as api


class ReadinessSourceIdentityAPITests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReadinessConnectivityLineageTests();self.f.setUp()
        self.old=self.f.report;self.oldbytes=self.old.read_bytes()
        self.f.report=self.f.root/api.REPORT_RELATIVE
        self.f.complete_identity();self.f.fresh['blockers']=[{'code':'SYNTHETIC_BLOCKER'}];self.f.write_report()
        self.payload={'report_sha256':self.f.sha(self.f.report),'manifest_sha256':self.f.sha(self.f.manifest),'token':'shared'}
        self.store=SimpleNamespace(root=self.f.root)
        self.app=FastAPI();self.app.include_router(api.create_readiness_source_identity_router(lambda:self.store));self.client=TestClient(self.app)
    def tearDown(self):self.client.close();self.f.tearDown()
    def post(self,payload=None):return self.client.post('/v1/diagnostics/readiness-source-identity',json=payload or self.payload)
    def core(self):return api.inspect_readiness_connectivity_lineage(self.f.root,**{'expected_report_sha256':self.payload['report_sha256'],'expected_manifest_sha256':self.payload['manifest_sha256'],'token':'shared','report_path':self.f.report,'max_members':2000})
    def metadata(self):return api._stored_metadata(self.f.root,self.payload['report_sha256'])
    def test_new_fixed_report_not_old_default_and_allowlisted_projection(self):
        r=self.post();self.assertEqual(r.status_code,200,r.text);v=r.json()
        self.assertEqual(v['counts'],dict(scene_count=3,complete_identity_scene_count=3,saved_blocker_count=1,query_member_count=3,query_active_token_member_count=3,query_zero_patch_scene_count=1,query_eligible_patch_count=2,broad_candidate_link_count=5,broad_unique_raw_row_count=3,refined_candidate_link_count=3,refined_unique_raw_row_count=3,refined_unique_member_count=3))
        self.assertEqual(v['query_token_sha256'],hashlib.sha256(b'shared').hexdigest());self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertEqual(set(v),{'schema_version','status','diagnostic_status','scope','report_sha256','manifest_sha256','query_token_sha256','counts','output_truncated',*api.FALSE_FIELDS})
        self.assertFalse(any(v[k] for k in api.FALSE_FIELDS));self.assertNotIn(str(self.f.root),r.text);self.assertEqual(self.old.read_bytes(),self.oldbytes)
    def test_legacy_absence_and_not_captured_have_null_counts(self):
        original=copy.deepcopy(self.f.fresh)
        for absent in [True,False]:
            self.f.fresh=copy.deepcopy(original)
            if absent:del self.f.fresh['connectivity_diagnostics']['source_identity']
            else:self.f.fresh['connectivity_diagnostics']['source_identity']={'identity_schema_version':1,'identity_capture_status':'NOT_CAPTURED_ERROR','error_type':'RuntimeError','scene_count':3,'scene_identities':None,'source_files_read_or_hashed':False,'source_authenticity_verified':False,'exact_original_row_binding_verified':False,'ready_for_training':False,'scientific_accuracy_validated':False}
            self.f.write_report();self.payload['report_sha256']=self.f.sha(self.f.report);r=self.post()
            self.assertEqual(r.status_code,200,r.text)
            for key in ['complete_identity_scene_count','refined_candidate_link_count','refined_unique_raw_row_count','refined_unique_member_count']:self.assertIsNone(r.json()['counts'][key])
    def test_strict_request_rejection_before_worker(self):
        raw=[b'{"a":1,"a":2}',b'{"token":NaN}',b'\xef\xbb\xbf{}',b'['*10+b'0'+b']'*10,json.dumps(self.payload).encode('utf-16')]
        values=[{**self.payload,'extra':'/secret'},{**self.payload,'report_sha256':True},{**self.payload,'manifest_sha256':'A'*64},{**self.payload,'token':False},{**self.payload,'token':'x'*4097},{**self.payload,'token':'\ud800'}]
        with patch.object(api,'inspect_readiness_connectivity_lineage',side_effect=AssertionError('no worker')):
            for value in raw+[json.dumps(v).encode() for v in values]:
                r=self.client.post('/v1/diagnostics/readiness-source-identity',content=value);self.assertEqual(r.status_code,400);self.assertEqual(r.headers['cache-control'],'no-store')
    def test_body_stream_limit_and_no_client_path(self):
        with patch.object(api,'inspect_readiness_connectivity_lineage',side_effect=AssertionError('no worker')):
            r=self.client.post('/v1/diagnostics/readiness-source-identity',content=iter([b'x'*4096,b'x'*4097]));self.assertEqual(r.status_code,413)
            self.assertEqual(self.post({**self.payload,'path':'other'}).status_code,400)
    def test_pin_conflict_and_errors_do_not_disclose_paths(self):
        self.assertEqual(self.post({**self.payload,'report_sha256':'0'*64}).status_code,409)
        for error,expected in [(ValueError('retargeted E:/secret'),409),(FileNotFoundError('E:/secret'),503),(RuntimeError('E:/secret'),503)]:
            with patch.object(api,'inspect_readiness_connectivity_lineage',side_effect=error):
                r=self.post();self.assertEqual(r.status_code,expected);self.assertNotIn('secret',r.text);self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertEqual(self.post().status_code,200)
    def test_projection_false_flags_typed_counts_and_limits_fail_closed(self):
        core=self.core();meta=self.metadata()
        mutations=[lambda x:x.update(ready_for_training=True),lambda x:x.update(report_scene_count=True),lambda x:x.update(unique_candidate_raw_row_count=100001),lambda x:x['report_members'][0].update(eligible_patches=9007199254740992),lambda x:x.update(report_active_token_member_count=False),lambda x:x.update(source_files_written=True)]
        for mutate in mutations:
            value=copy.deepcopy(core);mutate(value)
            with self.assertRaises(ValueError):api.project_readiness_source_identity(value,meta,self.payload)
    def test_refinement_version_protocol_status_and_cross_counts_fail_closed(self):
        core=self.core();meta=self.metadata()
        mutations=[lambda r:r.update(identity_schema_version=True),lambda r:r.update(path_comparison_protocol='UNKNOWN'),lambda r:r['members'][0].update(refinement_status='NOT_REFINED_IDENTITY_INCOMPLETE'),lambda r:r.update(unique_candidate_raw_row_count=4),lambda r:r['members'][0].update(refined_match_status='NO_DECLARED_METADATA_MATCH')]
        for mutate in mutations:
            value=copy.deepcopy(core);mutate(value['source_identity_refinement'])
            with self.assertRaises(ValueError):api.project_readiness_source_identity(value,meta,self.payload)
        meta['complete']=0
        with self.assertRaises(ValueError):api.project_readiness_source_identity(core,meta,self.payload)
    def test_truncation_preserved_and_missing_member_not_counted(self):
        core=self.core();core['output_truncated']=True
        self.assertTrue(api.project_readiness_source_identity(core,self.metadata(),self.payload)['output_truncated'])
        core['report_members'].pop()
        with self.assertRaises(ValueError):api.project_readiness_source_identity(core,self.metadata(),self.payload)
    def test_metadata_second_read_sha_and_retarget_fail_closed(self):
        with patch.object(api,'_read_bounded',return_value=b'{}'),self.assertRaises(ValueError):self.metadata()
        real=api._confined;calls=0
        def retarget(*args):
            nonlocal calls
            calls+=1
            return real(*args) if calls==1 else self.f.root/'changed.json'
        with patch.object(api,'_confined',side_effect=retarget),self.assertRaises(ValueError):self.metadata()
    def test_worker_exclusive_busy_and_release_after_error(self):
        original=api.inspect_readiness_connectivity_lineage;started=threading.Event();release=threading.Event()
        def slow(*args,**kwargs):started.set();release.wait(5);return original(*args,**kwargs)
        with patch.object(api,'inspect_readiness_connectivity_lineage',side_effect=slow),ThreadPoolExecutor(1) as pool:
            pending=pool.submit(self.post);self.assertTrue(started.wait(3));busy=self.post();self.assertEqual(busy.status_code,429);self.assertTrue(busy.json()['error']['retryable']);self.assertEqual(busy.headers['retry-after'],'1');release.set();self.assertEqual(pending.result(5).status_code,200)
        self.assertEqual(self.post().status_code,200)
    def test_cancelled_request_does_not_release_running_worker(self):
        original=api.inspect_readiness_connectivity_lineage;started=threading.Event();release=threading.Event();finished=threading.Event()
        def slow(*args,**kwargs):
            started.set();release.wait(5)
            try:return original(*args,**kwargs)
            finally:finished.set()
        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test') as client:
                task=asyncio.create_task(client.post('/v1/diagnostics/readiness-source-identity',json=self.payload))
                for _ in range(300):
                    if started.is_set():break
                    await asyncio.sleep(.01)
                self.assertTrue(started.is_set());task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                busy=await client.post('/v1/diagnostics/readiness-source-identity',json=self.payload);self.assertEqual(busy.status_code,429)
                release.set()
                for _ in range(300):
                    if finished.is_set():break
                    await asyncio.sleep(.01)
                await asyncio.sleep(.05)
                self.assertEqual((await client.post('/v1/diagnostics/readiness-source-identity',json=self.payload)).status_code,200)
        with patch.object(api,'inspect_readiness_connectivity_lineage',side_effect=slow):asyncio.run(exercise())
    def test_only_json_reads_no_store_mutation_assess_or_pixel_calls(self):
        before=(self.f.report.read_bytes(),self.f.manifest.read_bytes())
        with patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No assess')),patch('backend.app.data.readiness_connectivity_witness.diagnose_readiness_connectivity',side_effect=AssertionError('No helper')),patch('builtins.open',wraps=open) as opened:
            r=self.post();self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(before,(self.f.report.read_bytes(),self.f.manifest.read_bytes()))
        self.assertTrue(all(str(c.args[0]).endswith('.json') for c in opened.call_args_list))
    def test_openapi_declares_exact_response_contract(self):
        schema=self.app.openapi()['paths']['/v1/diagnostics/readiness-source-identity']['post']
        response=schema['responses']['200']['content']['application/json']['schema']
        self.assertEqual(set(response['properties']['counts']['properties']),api.COUNT_FIELDS)
        self.assertEqual(set(response['required']),set(self.post().json()))
        self.assertFalse(response['additionalProperties'])
        self.assertEqual(schema['requestBody']['content']['application/json']['schema']['additionalProperties'],False)
    def test_get_not_available_and_summary_ascii(self):
        self.assertEqual(self.client.get('/v1/diagnostics/readiness-source-identity').status_code,405)
        self.assertTrue(self.post().content.isascii())

if __name__=='__main__':unittest.main()
