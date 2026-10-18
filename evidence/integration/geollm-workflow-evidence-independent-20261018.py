"""Temp CPU fixture and GET-only independent checks; never operating Store/main import."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.testclient import TestClient
import numpy as np
import rasterio
import torch

from backend.app import lcluc_workflow as core
from backend.app import lcluc_workflow_api as api
from backend.app.dataset_registry import register_version
from backend.app.ml.network import TinyUNet
from backend.app.store import now
from test_lcluc_workflow import LclucWorkflowTests

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'c07602a203907e99ac94e4008b94a783719f01de'
TOKEN = 'LOCAL_WORKFLOW_EVIDENCE_147_ONLY'
SCOPE = 'TESTED_SYNTHETIC_GENERATED_RASTERS_HAND_SET_UNTRAINED_NETWORK_MOCK_APPROVAL_NO_LLM_RAG'
KEYS = {'succeeded':'workflow-evidence-147-succeeded','running':'workflow-evidence-147-running','failed':'workflow-evidence-147-failed'}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def identifier(state): return sha(KEYS[state].encode())


def build_fixture():
    """One actual local workflow, three tiny CPU raster inferences; no training."""
    fixture = LclucWorkflowTests()
    fixture.setUpClass(); fixture.setUp()
    try:
        model = TinyUNet(3)
        with torch.no_grad():
            for parameter in model.parameters(): parameter.zero_()
            model.enc1[0].weight[0,0,1,1] = 1
            model.enc1[2].weight[0,0,1,1] = 1
            model.dec1[0].weight[0,16,1,1] = 1
            model.dec1[2].weight[0,0,1,1] = 1
            model.head.bias[1] = .01005
            model.head.weight[2,0,0,0] = 1
        manifest = {**fixture.signature,'fixture_only':'HAND_SET_UNTRAINED_NETWORK_MOCK_ADMISSION_NOT_SCIENTIFIC_APPROVAL'}
        torch.save({'architecture':'tiny_unet','state_dict':model.state_dict(),'manifest':manifest},fixture.checkpoint)
        digest = fixture.sha(fixture.checkpoint)
        fixture.model.update(name='TESTED SYNTHETIC Workflow evidence 147',
            fixture_only='GENERATED_RASTERS_UNTRAINED_WEIGHTS_MOCK_APPROVAL_NOT_OPERATING')
        fixture.model['checkpoint_sha256'] = digest
        fixture.model['evaluation']['checkpoint_sha256'] = digest
        fixture.model['model_version_declaration']['checkpoint_sha256'] = digest
        fixture.store.put('models',fixture.model)
        fixture.request['model_ref']['sha256'] = digest
        fixture.request.update(idempotency_key=KEYS['succeeded'],trace_id='trace-workflow-evidence-147')
        image = fixture.root/'image-2022.tif'
        with rasterio.open(fixture.root/'image-2021.tif') as source:
            with rasterio.open(image,'w',**source.profile) as target:
                target.write(source.read()); target.descriptions = source.descriptions
        quality = fixture.root/'quality-2022.json'
        quality.write_text('{"fixture_only":"MOCK_VALIDATED_METADATA_NOT_QA_APPROVAL"}',encoding='utf-8')
        entry = copy.deepcopy(fixture.input_manifests[-1])
        entry.update(dataset_id='fixture-input-2022',sha256=fixture.sha(image),artifact_uri=image.name,quality_report_ref=quality.name)
        entry['temporal'] = {'start':'2022-01-01T00:00:00Z','end':'2022-12-31T00:00:00Z','calendar':'gregorian'}
        register_version(fixture.store,entry)
        fixture.request['images'].append({'year':2022,'input_ref':{'id':entry['dataset_id'],'version':'v1','sha256':entry['sha256']},
            'quality_report_sha256':fixture.sha(quality)})
        receipt = core.execute_lcluc_workflow(fixture.store,fixture.request)
        assert receipt['status'] == 'SUCCEEDED',receipt
        report_raw = (fixture.root/receipt['report_path']).read_bytes()
        report = json.loads(report_raw)
        assert report['changes']['2020-2021']['vector_feature_count'] == 1
        assert report['changes']['2021-2022']['vector_feature_count'] == 0
        # Constructed historical records are clearly distinct from actual execution.
        for state in ('running','failed'):
            request = copy.deepcopy(fixture.request)
            request.update(idempotency_key=KEYS[state],trace_id='trace-workflow-evidence-147-'+state)
            request,digest = core._request(request)
            record = {'schema_version':1,'scope':'LOCAL_LCLUC_WORKFLOW_ONLY','id':identifier(state),
                'trace_id':request['trace_id'],'request_sha256':digest,
                'request_snapshot':{k:v for k,v in request.items() if k != 'idempotency_key'},
                'status':state.upper(),'created_at':now(),'issue':None,'artifacts':[],
                'scientific_accuracy_validated':False,'standard_gmais_result':False}
            if state == 'failed': record.update(finished_at=now(),issue='LOCAL_EXECUTION_FAILED')
            fixture.store.put(core.KIND,record)
        return fixture,{'scope':SCOPE,'request':fixture.request,'receipt':receipt,'report':report,
            'report_sha256':sha(report_raw),'identifiers':{state:identifier(state) for state in KEYS},
            'fixture_creation':{'actual_local_workflow_calls':1,'tiny_raster_cpu_inference_calls':3,
                'training_calls':0,'operating_inference_calls':0,'running_failed_rows':'CONSTRUCTED_HISTORICAL_METADATA_ONLY'}}
    except BaseException:
        fixture.tearDown(); fixture.tearDownClass(); raise


def close_fixture(fixture):
    fixture.tearDown(); fixture.tearDownClass()


class EvidenceReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture,cls.data = build_fixture()
        cls.root = cls.fixture.root
        os.environ['GEOAI_API_TOKEN'] = TOKEN
        tree = ast.parse((ROOT/'backend/app/main.py').read_text(encoding='utf-8'))
        authorized = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == 'authorized')
        namespace = {'os':os,'secrets':secrets,'Request':Request,'Header':Header,'HTTPException':HTTPException}
        exec(compile(ast.Module(body=[authorized],type_ignores=[]),'<current-main-auth-isolated>','exec'),namespace)
        app = FastAPI(dependencies=[Depends(namespace['authorized'])])
        app.include_router(api.create_lcluc_workflow_router(lambda:cls.fixture.store))
        cls.client = TestClient(app); cls.client.__enter__()
        cls.headers = {'Authorization':'Bearer '+TOKEN}

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None); close_fixture(cls.fixture)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix():sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}

    def url(self,state='succeeded',suffix=''):
        return '/v1/lcluc/workflows/'+self.data['identifiers'][state]+suffix

    def get(self,state='succeeded',suffix=''):
        return self.client.get(self.url(state,suffix),headers=self.headers)

    def test_01_authenticated_status_raw_report_sha_trace_model_years_pairs_no_writes(self):
        before = self.snapshot()
        with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET execution forbidden')),patch.object(self.fixture.store,'put',side_effect=AssertionError('GET write forbidden')):
            status = self.get(); report = self.get(suffix='/report')
        self.assertEqual(status.status_code,200,status.text); self.assertEqual(report.status_code,200,report.text)
        receipt = status.json(); self.assertTrue(receipt['replayed']); self.assertEqual(receipt['id'],identifier('succeeded'))
        self.assertEqual(receipt['trace_id'],self.data['request']['trace_id'])
        self.assertEqual(receipt['request_snapshot']['model_ref'],self.data['request']['model_ref'])
        self.assertFalse(receipt['standard_gmais_result']); self.assertFalse(receipt['scientific_accuracy_validated'])
        item = next(a for a in receipt['artifacts'] if a['path'].replace('\\','/') == receipt['report_path'].replace('\\','/'))
        self.assertEqual(sha(report.content),item['sha256']); self.assertEqual(sha(report.content),self.data['report_sha256'])
        value = report.json(); self.assertEqual(value['years'],[2020,2021,2022])
        self.assertEqual(value['checkpoint_sha256'],receipt['request_snapshot']['model_ref']['sha256'])
        self.assertEqual(set(value['changes']),{'2020-2021','2021-2022','2020-2022'})
        self.assertEqual(value['changes']['2020-2021']['vector_feature_count'],1)
        self.assertEqual(value['changes']['2021-2022']['vector_feature_count'],0)
        self.assertEqual(status.headers['cache-control'],'no-store'); self.assertEqual(report.headers['x-content-type-options'],'nosniff')
        self.assertEqual(self.snapshot(),before)

    def test_02_authentication_before_store_and_missing_record(self):
        before = self.snapshot()
        with patch.object(self.fixture.store,'get',side_effect=AssertionError('unauthorized Store read')) as read:
            for suffix in ('','/report','/assets/0'):
                self.assertEqual(self.client.get(self.url(suffix=suffix)).status_code,401)
                self.assertEqual(self.client.get(self.url(suffix=suffix),headers={'Authorization':'Bearer wrong'}).status_code,401)
            read.assert_not_called()
        response = self.client.get('/v1/lcluc/workflows/'+'f'*64,headers=self.headers)
        self.assertEqual(response.status_code,404); self.assertEqual(response.json()['error']['code'],'NOT_FOUND')
        self.assertEqual(self.snapshot(),before)

    def test_03_running_failed_are_historical_only_report409_no_dispatch(self):
        before = self.snapshot()
        with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('no resume/retry')),patch.object(self.fixture.store,'put',side_effect=AssertionError('no writes')):
            for state in ('running','failed'):
                response = self.get(state); self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()['status'],state.upper()); self.assertTrue(response.json()['replayed'])
                self.assertEqual(response.json()['artifacts'],[])
                for suffix in ('/report','/assets/0'):
                    response = self.get(state,suffix); self.assertEqual(response.status_code,409)
                    self.assertEqual(response.json()['error']['code'],'WORKFLOW_NOT_SUCCEEDED')
        self.assertEqual(self.snapshot(),before)

    def test_04_tamper_fixed503_and_no_secret_or_new_write(self):
        path = self.root/self.data['receipt']['report_path']; raw = path.read_bytes()
        path.write_bytes(b'{"private":"SECRET_TEST_TAMPER"}')  # Explicit Temp fault, not API mutation.
        try:
            before = self.snapshot()
            with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('no dispatch')),patch.object(self.fixture.store,'put',side_effect=AssertionError('no write')):
                for suffix in ('','/report'):
                    response = self.get(suffix=suffix); self.assertEqual(response.status_code,503)
                    self.assertEqual(response.json()['error']['code'],'STORED_OUTPUT_CHANGED')
                    self.assertNotIn('SECRET_TEST_TAMPER',response.text)
            self.assertEqual(self.snapshot(),before)
        finally: path.write_bytes(raw)

    def test_05_all_assets_pinned_snapshot_and_same_workflow_paths(self):
        before = self.snapshot(); receipt = self.get().json()
        with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET no dispatch')):
            for index,item in enumerate(receipt['artifacts']):
                response = self.get(suffix='/assets/'+str(index)); self.assertEqual(response.status_code,200)
                self.assertEqual(sha(response.content),item['sha256'])
                self.assertTrue(item['path'].replace('\\','/').startswith('results/lcluc-workflows/'+receipt['id']+'/'))
        self.assertEqual(self.snapshot(),before)

    def test_06_historical_success_is_not_current_model_approval(self):
        original = self.fixture.store.get('models','fixture-model'); changed = copy.deepcopy(original)
        changed['status'] = 'Draft'; self.fixture.store.put('models',changed)  # Temp-only state injection.
        try:
            before = self.snapshot()
            with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET cannot approve/execute')):
                self.assertEqual(self.get().json()['status'],'SUCCEEDED'); self.assertEqual(self.get(suffix='/report').status_code,200)
            self.assertEqual(self.snapshot(),before)
        finally: self.fixture.store.put('models',original)

    def test_07_existing_backend_bytes_match_pinned_git(self):
        for relative in ('backend/app/lcluc_workflow.py','backend/app/lcluc_workflow_api.py','backend/app/main.py',
                         'backend/app/ml/service.py','backend/app/ml/network.py','frontend/src/lclucWorkflowAdapter.ts'):
            old = subprocess.run(['git','show',BASELINE+':'+relative],cwd=ROOT,capture_output=True,check=True).stdout
            self.assertEqual((ROOT/relative).read_bytes(),old,relative)


def main():
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceReadTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    files = ('backend/app/lcluc_workflow.py','backend/app/lcluc_workflow_api.py','backend/app/main.py','frontend/src/lclucWorkflowAdapter.ts')
    proof = {'schema_version':1,'scope':SCOPE,'baseline_commit':BASELINE,'tests':result.testsRun,
        'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'skipped':len(result.skipped),
        'failures':len(result.failures),'errors':len(result.errors),'seconds':time.perf_counter()-start,
        'fixture_creation':EvidenceReadTests.data['fixture_creation'] if hasattr(EvidenceReadTests,'data') else None,
        'fixture_identifiers':{state:identifier(state) for state in KEYS},'operating_store_access':0,
        'GET_execution_calls':0,'GET_store_put_calls':0,'LLM_calls':0,'RAG_calls':0,'training_calls':0,
        'auth_scope':'CURRENT_AUTH_AST_ISOLATED_FASTAPI_WITH_EXISTING_116_ROUTER_NOT_FULL_MAIN_SERVER',
        'backend_source_sha256':{relative:sha((ROOT/relative).read_bytes()) for relative in files},
        'frontend_frozen_source_sha256':{},
        'limits':['Synthetic generated rasters, hand-set untrained weights and fabricated admission metadata are not scientific or institutional approval.',
            'The actual fixture executes one local workflow and three tiny CPU raster inferences; operating inference is zero.',
            'RUNNING/FAILED records are constructed historical metadata fixtures; GET does not execute, retry or resume.',
            'Observed GET DB/files are unchanged; explicit tamper/model-state setup writes are separate.',
            'Actual main server browser verification is a separate Root task; no LLM inference, RAG retrieval, official corpus or operating result validation.']}
    (ROOT/'evidence/integration/geollm-workflow-evidence-independent-20261018.json').write_text(
        json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': raise SystemExit(main())
