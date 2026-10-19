"""작은 합성 4JSON/HTTP만 사용. 원본·후보manifest/영상/QA/DB IO 없음."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
import test_candidate_readiness_qa as fixtures
from backend.app.ml import candidate_qa_comparison as core
from backend.app import candidate_qa_comparison_api as api


class CandidateQAComparisonTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.CandidateReadinessQATests();self.f.setUp();self.root=self.f.data
        with patch.object(fixtures.module,'run',side_effect=self.f.fake_run):self.qa=self.f.assess()
        self.stage=copy.deepcopy(self.f.stage);self.old=self.f.report();self.new=self.f.report()
        self.old.pop('connectivity_diagnostics');self.old['input_manifests']=[{'path':'source.json','sha256':'1'*64}]
        self.old['blockers']=[{'code':'SHARED_SOURCE_CROSSES_FIXED_SPLIT','detail':'/secret/source'}]+[{'code':'REFERENCE_CLASS_IMBALANCE'}]*3+[{'code':'CLASS_COVERAGE'}]
        self.new['blockers']=[{'code':'REFERENCE_CLASS_IMBALANCE'}]*3+[{'code':'CLASS_COVERAGE'}]
        self.old['patch_counts_by_split']={'train':2,'val':2,'test':2};self.new['patch_counts_by_split']={'train':2,'val':1,'test':2}
        for report in (self.old,self.new):
            report['input_signature']['class_names'][7]='bare'
            report['class_counts_by_split']={s:[0]*7+[n,0] for s,n in [('train',1418),('val',209),('test',1025)]}
            report['class_patch_counts_by_split']={s:[0]*9 for s in ['train','val','test']}
        self.stage.update(source_row_count=7,candidate_row_count=5,projected_after={'eligible_patches_by_split':copy.deepcopy(self.new['patch_counts_by_split']),'eligible_total':5,'eligible_by_province_year':{'south_sulawesi/2021':2,'banten/2021':1,'west_java/2021':2}})
        staged='first-group-candidate-qa-stage-20261017/candidate.json';self.stage['staged_candidate']['path']=staged;self.new['input_manifests'][0]['path']=staged
        capture=self.new['connectivity_diagnostics'];capture.update(gate_components_match=True,scene_count=5,supplied_eligible_patch_sum=5,manifest_input_references=copy.deepcopy(self.new['input_manifests']))
        self.documents={'original_report_sha256':self.old,'candidate_report_sha256':self.new,'qa_receipt_sha256':self.qa,'staging_receipt_sha256':self.stage}
        self.paths={k:self.root/v for k,v in core.FIXED_PATHS.items()}
        self.write('original_report_sha256');self.write('candidate_report_sha256')
        self.stage['input_pins']['readiness']=self.sha(self.paths['original_report_sha256']);self.write('staging_receipt_sha256')
        self.qa['inputs']['old_readiness']={'path':str(self.paths['original_report_sha256']),'sha256':self.sha(self.paths['original_report_sha256']),'bytes':self.paths['original_report_sha256'].stat().st_size}
        self.qa['inputs']['staging_receipt']={'path':str(self.paths['staging_receipt_sha256']),'sha256':self.sha(self.paths['staging_receipt_sha256']),'bytes':self.paths['staging_receipt_sha256'].stat().st_size}
        self.qa['inputs']['candidate']['path']=str(self.root/staged)
        self.qa['readiness_report']={'name':'readiness.json','sha256':self.sha(self.paths['candidate_report_sha256']),'bytes':self.paths['candidate_report_sha256'].stat().st_size}
        self.qa.update(saved_blockers=copy.deepcopy(self.new['blockers']),patch_counts_by_split=copy.deepcopy(self.new['patch_counts_by_split']));self.write('qa_receipt_sha256')
        self.pins={k:self.sha(p) for k,p in self.paths.items()};self.refs={k:{'path':str(p),'bytes':p.stat().st_size} for k,p in self.paths.items()}
        self.app=FastAPI();self.app.include_router(api.create_candidate_qa_comparison_router(lambda:SimpleNamespace(root=self.root)));self.client=TestClient(self.app)
    def tearDown(self):self.client.close();self.f.tearDown()
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def write(self,k):self.paths[k].parent.mkdir(parents=True,exist_ok=True);self.paths[k].write_text(json.dumps(self.documents[k],ensure_ascii=False),encoding='utf-8')
    def project(self,docs=None):return core.project_candidate_qa(docs or self.documents,self.pins,self.refs,data_root_literal=str(self.root))
    def post(self,pins=None):return self.client.post('/v1/diagnostics/candidate-readiness-comparison',json=pins or self.pins)
    def test_summary_counter_rows_bare_and_all_false_projection(self):
        result=self.project();self.assertEqual(result['original']['eligible_patch_count'],6);self.assertEqual(result['candidate']['eligible_patch_count'],5)
        self.assertEqual(result['original']['blocker_count'],5);self.assertEqual(result['candidate']['blocker_count'],4)
        frequencies={x['code']:x for x in result['blocker_frequencies']};self.assertEqual(frequencies['REFERENCE_CLASS_IMBALANCE']['original_count'],3);self.assertEqual(frequencies['REFERENCE_CLASS_IMBALANCE']['candidate_count'],3)
        self.assertIsNone(result['row_counts']['original_report_physical_scene_count']);self.assertEqual(result['row_counts']['source_rows_declared'],7);self.assertEqual(result['row_counts']['candidate_appended_scene_count'],5)
        self.assertTrue(result['shared_source_blocker']['original_observed']);self.assertFalse(result['shared_source_blocker']['candidate_observed']);self.assertFalse(result['shared_source_blocker']['absence_proves_independence'])
        self.assertEqual(result['bare_class']['original_pixels_by_split'],{'train':1418,'val':209,'test':1025});self.assertTrue(result['bare_class']['candidate_shortage_observed']);self.assertTrue(all(result[k] is False for k in core.FALSE_FIELDS))
    def test_pure_projection_is_input_immutable_without_io_or_assess(self):
        before=copy.deepcopy(self.documents)
        with patch('pathlib.Path.open',side_effect=AssertionError('No IO')),patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No QA')):self.project()
        self.assertEqual(before,self.documents)
    def test_policy_signature_stage_qa_schema_false_flags_and_typed_counts(self):
        changes=[lambda d:d['candidate_report_sha256']['policy'].update(seed=True),lambda d:d['candidate_report_sha256']['input_signature'].update(label_source='other'),lambda d:d['qa_receipt_sha256'].update(extra=True),lambda d:d['staging_receipt_sha256'].update(qa_performed=0),lambda d:d['qa_receipt_sha256'].update(execution_authorized=True),lambda d:d['candidate_report_sha256']['patch_counts_by_split'].update(val=True),lambda d:d['qa_receipt_sha256'].update(proposed_refund_bytes=False),lambda d:d['staging_receipt_sha256'].update(candidate_row_count=True)]
        for change in changes:
            docs=copy.deepcopy(self.documents);change(docs)
            with self.assertRaises(ValueError):self.project(docs)
    def test_source_role_pin_path_size_and_receipt_report_crossbinding(self):
        changes=[lambda d:d['original_report_sha256']['input_manifests'][0].update(sha256='0'*64),lambda d:d['staging_receipt_sha256']['input_pins'].update(readiness='0'*64),lambda d:d['qa_receipt_sha256']['inputs']['candidate'].update(sha256='0'*64),lambda d:d['qa_receipt_sha256']['inputs']['old_readiness'].update(bytes=True),lambda d:d['qa_receipt_sha256']['inputs']['staging_receipt'].update(path='other.json'),lambda d:d['qa_receipt_sha256']['readiness_report'].update(sha256='0'*64),lambda d:d['staging_receipt_sha256']['staged_candidate'].update(path='../escape'),lambda d:d['staging_receipt_sha256']['verified_package_outputs']['candidate'].update(bytes=1)]
        for change in changes:
            docs=copy.deepcopy(self.documents);change(docs)
            with self.assertRaises(ValueError):self.project(docs)
    def test_qa_saved_counts_blockers_capture_and_scene_scope_consistency(self):
        changes=[lambda d:d['qa_receipt_sha256'].update(saved_blockers=[]),lambda d:d['qa_receipt_sha256']['patch_counts_by_split'].update(val=2),lambda d:d['qa_receipt_sha256'].update(connectivity_capture_status='FAILED_DIAGNOSTIC'),lambda d:d['candidate_report_sha256']['connectivity_diagnostics'].update(scene_count=6),lambda d:d['candidate_report_sha256']['connectivity_diagnostics'].update(source_files_read=True),lambda d:d['original_report_sha256'].update(scene_count=7)]
        for change in changes:
            docs=copy.deepcopy(self.documents);change(docs)
            with self.assertRaises(ValueError):self.project(docs)
    def test_failed_capture_null_and_bare_shortage_computed_not_assumed(self):
        docs=copy.deepcopy(self.documents);docs['candidate_report_sha256']['connectivity_diagnostics'].update(capture_status='FAILED_DIAGNOSTIC',scene_count=None);docs['qa_receipt_sha256']['connectivity_capture_status']='FAILED_DIAGNOSTIC';result=self.project(docs)
        self.assertIsNone(result['row_counts']['candidate_appended_scene_count']);self.assertEqual(result['row_counts']['candidate_capture_scope'],'NOT_CAPTURED')
        for s in ['train','val','test']:docs['candidate_report_sha256']['class_patch_counts_by_split'][s][7]=1
        self.assertTrue(self.project(docs)['bare_class']['candidate_shortage_observed'])
    def test_huge_integer_float_bool_and_blocker_code_privacy_rejected(self):
        for value in [True,1.0,10**400]:
            docs=copy.deepcopy(self.documents);docs['candidate_report_sha256']['class_counts_by_split']['val'][7]=value
            with self.assertRaises(ValueError):self.project(docs)
        docs=copy.deepcopy(self.documents);docs['candidate_report_sha256']['blockers'][0]['code']='E:/secret/path'
        with self.assertRaises(ValueError):self.project(docs)
    def test_signature_required_class_range_capture_false_and_bare_bounds(self):
        changes=[lambda d:d['candidate_report_sha256']['policy'].update(required_classes=[7,7]),lambda d:d['candidate_report_sha256']['policy'].update(required_classes=[7,9]),lambda d:d['candidate_report_sha256']['input_signature'].pop('label_source'),lambda d:d['candidate_report_sha256']['input_signature'].update(band_indices=[True,2,3,4,5,6]),lambda d:d['candidate_report_sha256']['connectivity_diagnostics'].update(training_executed=True),lambda d:d['candidate_report_sha256']['connectivity_diagnostics'].update(gate_components_match=False),lambda d:d['candidate_report_sha256']['class_patch_counts_by_split']['val'].__setitem__(7,2),lambda d:d['candidate_report_sha256']['class_counts_by_split']['val'].__setitem__(7,65537)]
        for change in changes:
            docs=copy.deepcopy(self.documents);change(docs)
            with self.assertRaises(ValueError):self.project(docs)
    def test_code_counter_budget_and_empty_blocked_report_refused(self):
        docs=copy.deepcopy(self.documents);docs['candidate_report_sha256']['blockers']=[{'code':'DIAGNOSTIC_'+str(i)} for i in range(33)];docs['qa_receipt_sha256']['saved_blockers']=copy.deepcopy(docs['candidate_report_sha256']['blockers'])
        with self.assertRaises(ValueError):self.project(docs)
        docs=copy.deepcopy(self.documents);docs['candidate_report_sha256']['blockers']=[]
        with self.assertRaises(ValueError):self.project(docs)
    def test_reader_change_after_initial_four_inputs_rejected(self):
        original=core.BoundedJSONIO.read;calls=0
        def changed(io,*args):
            nonlocal calls
            result=original(io,*args);calls+=1
            if calls==4:
                path=self.paths['candidate_report_sha256'];path.write_bytes(path.read_bytes()+b' ')
            return result
        with patch.object(core.BoundedJSONIO,'read',changed),self.assertRaises(ValueError):core.compare_candidate_qa(self.root,self.pins)
    def test_reader_opens_only_fixed_four_jsons_and_preserves_bytes(self):
        before={p:p.read_bytes() for p in self.paths.values()};allowed={p.resolve() for p in self.paths.values()};original=Path.open;opened=[]
        def guard(path,*args,**kwargs):self.assertIn(path.resolve(),allowed);opened.append(path.resolve());return original(path,*args,**kwargs)
        with patch('pathlib.Path.open',guard),patch('backend.app.ml.readiness.assess',side_effect=AssertionError('No assess')):result=core.compare_candidate_qa(self.root,self.pins)
        self.assertEqual(set(opened),allowed);self.assertEqual(len(opened),8);self.assertEqual(before,{p:p.read_bytes() for p in before});self.assertNotIn(str(self.root),json.dumps(result))
    def test_reader_caps_strict_json_pin_and_stale(self):
        with patch.dict(core.CAPS,{'candidate_report_sha256':1}),patch('pathlib.Path.open',side_effect=AssertionError('No content')),self.assertRaises(ValueError):core.compare_candidate_qa(self.root,self.pins)
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'['*33+b'0'+b']'*33,json.dumps({'q':'"'}).encode('utf-16')]:
            self.paths['qa_receipt_sha256'].write_bytes(raw);pins={**self.pins,'qa_receipt_sha256':self.sha(self.paths['qa_receipt_sha256'])}
            with self.assertRaises(ValueError):core.compare_candidate_qa(self.root,pins)
    def test_api_exact_minimal_success_schema_and_no_store(self):
        r=self.post();self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.headers['cache-control'],'no-store');self.assertEqual(r.json(),self.project());self.assertNotIn('/secret',r.text);self.assertNotIn(str(self.root),r.text)
        schema=self.app.openapi()['paths']['/v1/diagnostics/candidate-readiness-comparison']['post']['responses']['200']['content']['application/json']['schema'];self.assertEqual(set(schema['required']),set(r.json()));self.assertFalse(schema['additionalProperties'])
    def test_api_invalid_requests_before_reader_and_stream_cap(self):
        bad=[{**self.pins,'extra':'path'},{**self.pins,'original_report_sha256':True},{**self.pins,'candidate_report_sha256':'A'*64}]
        raw=[b'{"x":1,"x":2}',b'{"x":NaN}',json.dumps(self.pins).encode('utf-16'),b'['*9+b'0'+b']'*9]+[json.dumps(d).encode() for d in bad]
        with patch.object(api,'compare_candidate_qa',side_effect=AssertionError('No reader')):
            for body in raw:self.assertEqual(self.client.post('/v1/diagnostics/candidate-readiness-comparison',content=body).status_code,400)
            self.assertEqual(self.client.post('/v1/diagnostics/candidate-readiness-comparison',content=iter([b'x'*1024,b'x'*1025])).status_code,413)
    def test_api_pin_error_privacy_and_recovery(self):
        self.assertEqual(self.post({**self.pins,'original_report_sha256':'0'*64}).status_code,409)
        for error,status in [(ValueError('retargeted E:/secret'),409),(FileNotFoundError('E:/secret'),503)]:
            with patch.object(api,'compare_candidate_qa',side_effect=error):
                r=self.post();self.assertEqual(r.status_code,status);self.assertNotIn('secret',r.text);self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertEqual(self.post().status_code,200)
    def test_api_busy_worker_lock_and_recovery(self):
        original=api.compare_candidate_qa;started=threading.Event();release=threading.Event()
        def slow(*args):started.set();release.wait(5);return original(*args)
        with patch.object(api,'compare_candidate_qa',side_effect=slow),ThreadPoolExecutor(1) as pool:
            future=pool.submit(self.post);self.assertTrue(started.wait(3));r=self.post();self.assertEqual(r.status_code,429);self.assertTrue(r.json()['error']['retryable']);self.assertEqual(r.headers['retry-after'],'1');release.set();self.assertEqual(future.result(5).status_code,200)
    def test_api_cancelled_request_keeps_worker_busy_until_finished(self):
        original=api.compare_candidate_qa;started=threading.Event();release=threading.Event();finished=threading.Event()
        def slow(*args):
            started.set();release.wait(5)
            try:return original(*args)
            finally:finished.set()
        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test') as client:
                task=asyncio.create_task(client.post('/v1/diagnostics/candidate-readiness-comparison',json=self.pins))
                for _ in range(300):
                    if started.is_set():break
                    await asyncio.sleep(.01)
                self.assertTrue(started.is_set());task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                self.assertEqual((await client.post('/v1/diagnostics/candidate-readiness-comparison',json=self.pins)).status_code,429);release.set()
                for _ in range(300):
                    if finished.is_set():break
                    await asyncio.sleep(.01)
                await asyncio.sleep(.05);self.assertEqual((await client.post('/v1/diagnostics/candidate-readiness-comparison',json=self.pins)).status_code,200)
        with patch.object(api,'compare_candidate_qa',side_effect=slow):asyncio.run(exercise())

if __name__=='__main__':unittest.main()
