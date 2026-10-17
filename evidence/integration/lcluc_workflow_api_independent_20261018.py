"""Independent adversarial boundary checks; synthetic TempStore only."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app import lcluc_workflow_api as api
from test_lcluc_workflow import LclucWorkflowTests

ROOT = Path(__file__).resolve().parents[2]
PATH = '/v1/lcluc/workflows'

class IndependentApiChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): LclucWorkflowTests.setUpClass()
    @classmethod
    def tearDownClass(cls): LclucWorkflowTests.tearDownClass()
    def setUp(self):
        self.fixture = LclucWorkflowTests(); self.fixture.setUp()
        self.store = self.fixture.store
        self.app = FastAPI(); self.app.include_router(api.create_lcluc_workflow_router(lambda:self.store))
        self.client = TestClient(self.app)
    def tearDown(self):
        self.client.close(); self.fixture.tearDown()
    def run_fixture(self):
        response = self.client.post(PATH,json=self.fixture.request)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'SUCCEEDED')
        return response.json()
    def rows(self):
        with self.store.connect() as conn:
            return conn.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
    def test_main_exact_two_new_nodes_preserves_entire_previous_module(self):
        baseline=ROOT/'evidence/integration/lcluc-workflow-api-original-main.py-20261018.py'
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest(),'4c4a0d1b96bf2472ee01a2af6597aea221b8cae07a9d9932fbd7d6c16f665e4a')
        before=ast.parse(baseline.read_text(encoding='utf-8-sig'))
        after=ast.parse((ROOT/'backend/app/main.py').read_text(encoding='utf-8-sig'))
        for expected in ast.parse('from .lcluc_workflow_api import create_lcluc_workflow_router\napp.include_router(create_lcluc_workflow_router(lambda: store))\n').body:
            matches=[n for n in after.body if ast.dump(n)==ast.dump(expected)]
            self.assertEqual(len(matches),1); after.body.remove(matches[0])
        self.assertEqual(ast.dump(before),ast.dump(after))
    def test_all_get_paths_never_execute_and_leave_database_unchanged(self):
        receipt=self.run_fixture(); identifier=receipt['id']; before=self.rows()
        with patch.object(api,'execute_lcluc_workflow',side_effect=AssertionError('GET must not execute')):
            for suffix in ('','/report','/assets/0','/assets/00','/assets/-1','/assets/128'):
                response=self.client.get(PATH+'/'+identifier+suffix)
                self.assertIn(response.status_code,(200,404),response.text)
        self.assertEqual(before,self.rows())
    def test_old_success_read_is_not_current_model_approval(self):
        receipt=self.run_fixture(); model=copy.deepcopy(self.fixture.model);model['status']='Draft';self.store.put('models',model)
        before=self.rows()
        response=self.client.get(PATH+'/'+receipt['id'])
        self.assertEqual(response.status_code,200,response.text)
        self.assertIs(response.json()['replayed'],True)
        self.assertIs(response.json()['scientific_accuracy_validated'],False)
        self.assertEqual(before,self.rows())
    def test_backslash_record_paths_roundtrip_without_changing_stored_bytes(self):
        receipt=self.run_fixture(); record=self.store.get(api.KIND,receipt['id'])
        record['report_path']=record['report_path'].replace('/','\\')
        for artifact in record['artifacts']:artifact['path']=artifact['path'].replace('/','\\')
        self.store.put(api.KIND,record);before=self.rows()
        self.assertEqual(self.client.get(PATH+'/'+receipt['id']).status_code,200)
        self.assertEqual(self.client.get(PATH+'/'+receipt['id']+'/report').status_code,200)
        self.assertEqual(before,self.rows())
    def test_download_and_report_refuse_changed_bytes_preserve_receipt(self):
        receipt=self.run_fixture(); before=self.rows()
        index=next(i for i,a in enumerate(receipt['artifacts']) if a['path']==receipt['report_path'])
        report=self.fixture.root/receipt['report_path'];report.write_bytes(report.read_bytes()+b' ')
        for suffix in ('','/report','/assets/'+str(index)):
            response=self.client.get(PATH+'/'+receipt['id']+suffix)
            self.assertEqual(response.status_code,503,response.text)
            self.assertFalse(response.json()['error']['retryable'])
        self.assertEqual(before,self.rows())
    def test_duplicate_request_rejection_never_acquires_store(self):
        app=FastAPI();app.include_router(api.create_lcluc_workflow_router(lambda: (_ for _ in ()).throw(AssertionError('store acquired'))))
        with TestClient(app) as client:
            for raw in (b'{"schema_version":1,"schema_version":1}',b'NaN',b'{}',b'[]'):
                self.assertEqual(client.post(PATH,content=raw).status_code,400)

if __name__=='__main__':unittest.main(verbosity=2)
