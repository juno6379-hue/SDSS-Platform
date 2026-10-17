"""저장 Job snapshot과 분리된 현재 계보·합산 예산·비쓰기 HTTP companion 시험."""
import copy
import json
import os
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import test_dataset_lineage as fixtures
import test_gmais_api as app_fixtures
from app.job_lineage import validate_job_lineage
from app.job_lineage_api import create_job_lineage_router


class JobLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DatasetLineageTests(); self.fixture.setUp()
        self.store = self.fixture.store
        self.ref = self.fixture.dataset('job-root')
        self.job = {'id':'job-current-fixture','job_id':'job-current-fixture','agent_id':'lcluc-agent',
            'status':{'schema_version':'0.2.0','job_id':'job-current-fixture','agent_id':'lcluc-agent',
                'trace_id':'trace-current-fixture','status':'BLOCKED','submitted_at':'2026-10-17T00:00:00Z','progress':0},
            'request':{'agent_id':'lcluc-agent','execution_context':{'trace_id':'trace-current-fixture'},
                       'input_refs':[dict(self.ref,uri='PRIVATE-REQUEST-URI',role='PRIVATE-ROLE')]},
            'input_resolution':{'PRIVATE-STORED-SNAPSHOT':'unchanged'}}
        self.save()
        app = FastAPI(); app.include_router(create_job_lineage_router(lambda:self.store))
        self.client = TestClient(app)
        self.uri = '/v1/jobs/job-current-fixture/lineage-validation'
        self.original_store = app_fixtures.main.store; app_fixtures.main.store = self.store
        self.main_client = TestClient(app_fixtures.main.app)
        self.auth = patch.dict(os.environ, {'GEOAI_API_TOKEN':''}); self.auth.start()

    def tearDown(self):
        self.auth.stop(); self.main_client.close(); self.client.close()
        app_fixtures.main.store = self.original_store; self.fixture.tearDown()

    def save(self):
        self.store.put('gmais_jobs', copy.deepcopy(self.job))

    def inspect(self, **limits):
        before = self.fixture.files(self.store)
        with patch.object(self.store,'put',side_effect=AssertionError('진단이 Job을 변경했습니다.')):
            result = validate_job_lineage(self.store, self.job['id'], **limits)
        self.assertEqual(before,self.fixture.files(self.store))
        for field in ('execution_authorized','authorization_verified','scientific_approval'):
            self.assertIs(result[field],False)
        for secret in ('PRIVATE-REQUEST-URI','PRIVATE-ROLE','PRIVATE-STORED-SNAPSHOT','PRIVATE-ASSET',str(self.store.root)):
            self.assertNotIn(secret,json.dumps(result))
        return result

    def test_current_check_does_not_depend_on_or_modify_stored_snapshot(self):
        result = self.inspect()
        self.assertTrue(result['available']); self.assertTrue(result['lineage_integrity_verified'])
        self.assertEqual(result['status'],'INTEGRITY_VERIFIED')
        self.assertEqual(result['reason'],'CURRENT_LINEAGE_CHECKED')
        self.assertEqual(self.store.get('gmais_jobs',self.job['id'])['input_resolution'],self.job['input_resolution'])
        self.assertEqual(result['limits']['node_checks_performed'],1)

    def test_duplicate_roots_reuse_diagnostics_and_preserve_binding_indices(self):
        self.job['request']['input_refs']=[dict(self.ref,role='T1'),dict(self.ref,role='T2')]; self.save()
        import app.job_lineage as module
        with patch('app.job_lineage.verify_dataset_lineage',wraps=module.verify_dataset_lineage) as verify:
            with patch.object(self.store,'get',wraps=self.store.get) as read:
                result=self.inspect()
        self.assertEqual(verify.call_count,1)
        self.assertEqual(sum(call.args[0]=='gmais_jobs' for call in read.call_args_list),1)
        self.assertEqual([row['input_index'] for row in result['bindings']],[0,1])
        self.assertEqual([row['diagnostic_index'] for row in result['bindings']],[0,0])
        self.assertEqual([row['reused'] for row in result['bindings']],[False,True])
        self.assertEqual(result['limits']['node_checks_performed'],1)

    def test_total_budget_stops_new_roots_but_allows_cached_root_after_exhaustion(self):
        other=self.fixture.dataset('job-other')
        self.job['request']['input_refs']=[self.ref,other,self.ref]; self.save()
        import app.job_lineage as module
        with patch('app.job_lineage.verify_dataset_lineage',wraps=module.verify_dataset_lineage) as verify:
            result=self.inspect(max_total_nodes=1,max_nodes_per_root=1)
        self.assertEqual(verify.call_count,1)
        self.assertEqual(result['reason'],'CHECK_LIMIT_REACHED'); self.assertTrue(result['available'])
        self.assertEqual([row['checked'] for row in result['bindings']],[True,False,True])
        self.assertIsNone(result['bindings'][1]['diagnostic_index'])
        self.assertTrue(result['bindings'][2]['reused'])
        self.assertEqual(result['limits']['node_checks_performed'],1)
        self.assertFalse(result['lineage_integrity_verified'])

    def test_remaining_global_budget_is_passed_into_partial_root_traversal(self):
        leaf=self.fixture.dataset('job-leaf'); parent=self.fixture.dataset('job-parent',parents=[leaf])
        root=self.fixture.dataset('job-wide',parents=[parent])
        self.job['request']['input_refs']=[root,self.ref]; self.save()
        result=self.inspect(max_total_nodes=2)
        self.assertEqual(result['reason'],'CHECK_LIMIT_REACHED')
        self.assertEqual(result['limits']['node_checks_performed'],2)
        self.assertEqual(result['diagnostics'][0]['limits']['max_nodes'],2)
        self.assertIn('LINEAGE_NODE_LIMIT',{item['code'] for item in result['blockers']})
        self.assertFalse(result['bindings'][1]['checked'])

    def test_shared_ancestors_across_distinct_roots_are_counted_as_repeated_work(self):
        common=self.fixture.dataset('job-common')
        a=self.fixture.dataset('job-a',parents=[common]); b=self.fixture.dataset('job-b',parents=[common])
        self.job['request']['input_refs']=[a,b]; self.save()
        result=self.inspect()
        self.assertEqual(result['limits']['unique_roots_checked'],2)
        self.assertEqual(result['limits']['node_checks_performed'],4)

    def test_preflight_caps_preserve_trace_and_do_not_clone_large_ref_list(self):
        class NoCopy(dict):
            def __deepcopy__(self,memo):
                raise AssertionError('상한 초과 참조를 복제했습니다.')
        record=copy.deepcopy(self.job)
        record['request']['input_refs']=[NoCopy(self.ref) for _ in range(65)]
        with patch.object(self.store,'get',return_value=record), patch('app.job_lineage.verify_dataset_lineage',side_effect=AssertionError('상한 초과 검사')):
            result=validate_job_lineage(self.store,self.job['id'])
        self.assertEqual(result['trace_id'],'trace-current-fixture')
        self.assertEqual(result['reason'],'CHECK_LIMIT_REACHED'); self.assertFalse(result['available'])
        self.assertEqual(result['bindings'],[]); self.assertEqual(result['diagnostics'],[])
        self.job['request']['input_refs']=[dict(self.ref,id='unregistered-'+str(index)) for index in range(33)]; self.save()
        with patch('app.job_lineage.verify_dataset_lineage',side_effect=AssertionError('상한 초과 검사')):
            result=self.inspect()
        self.assertEqual(result['trace_id'],'trace-current-fixture')
        self.assertIn('JOB_UNIQUE_ROOT_LIMIT',{item['code'] for item in result['blockers']})

    def test_conflicting_fixed_hashes_are_structurally_blocked_without_fake_file_checks(self):
        self.job['request']['input_refs']=[self.ref,dict(self.ref,sha256='a'*64)]; self.save()
        with patch('app.job_lineage.verify_dataset_lineage',side_effect=AssertionError('상충 입력 검사')):
            result=self.inspect()
        self.assertTrue(result['available']); self.assertFalse(result['current_assets_revalidated'])
        self.assertEqual(result['diagnostics'],[])
        self.assertEqual([item['input_index'] for item in result['blockers']],[0,1])

    def test_missing_dynamic_and_acl_lineage_blockers_remain_non_approving(self):
        hidden=self.fixture.dataset('job-undisclosed')
        restricted=self.fixture.dataset('job-private',parents=[hidden],access='RESTRICTED')
        cases=[(dict(self.ref,id='job-missing'),'DATASET_VERSION_NOT_FOUND'),
               (dict(self.ref,version='latest'),'LINEAGE_REF_NOT_PINNED'),
               (restricted,'LINEAGE_ACL_NOT_IMPLEMENTED')]
        for ref,code in cases:
            with self.subTest(code=code):
                self.job['request']['input_refs']=[ref]; self.save()
                result=self.inspect()
                self.assertIn(code,{item['code'] for item in result['blockers']})
                self.assertFalse(result['lineage_integrity_verified'])
                self.assertNotIn(hidden['id'],json.dumps(result))

    def test_legacy_bad_request_and_identity_mismatch_do_not_run_lineage(self):
        original=copy.deepcopy(self.job)
        mutations=[('LEGACY_REQUEST_NOT_RECORDED',lambda job:job.pop('request')),
                   ('JOB_REQUEST_INVALID',lambda job:job.update(request=None)),
                   ('JOB_REQUEST_INVALID',lambda job:job['request']['execution_context'].update(trace_id='PRIVATE-WRONG-TRACE')),
                   ('JOB_REQUEST_INVALID',lambda job:job['status'].update(job_id='wrong')),
                   ('JOB_REQUEST_INVALID',lambda job:job['request'].update(input_refs=[])),
                   ('JOB_REQUEST_INVALID',lambda job:job['request']['input_refs'][0].update(sha256='bad'))]
        for reason,mutate in mutations:
            with self.subTest(reason=reason):
                self.job=copy.deepcopy(original); mutate(self.job); self.save()
                with patch('app.job_lineage.verify_dataset_lineage',side_effect=AssertionError('유효하지 않은 Job 검사')):
                    result=self.inspect()
                self.assertEqual(result['reason'],reason); self.assertFalse(result['available'])
                self.assertNotIn('PRIVATE-WRONG-TRACE',json.dumps(result))

    def test_asset_change_is_current_failure_while_job_and_snapshot_stay_unchanged(self):
        original=self.store.get('gmais_jobs',self.job['id'])
        self.assertTrue(self.inspect()['lineage_integrity_verified'])
        (self.store.root/'PRIVATE-ASSET-job-root-1.bin').write_bytes(b'changed current asset')
        result=self.inspect()
        self.assertFalse(result['lineage_integrity_verified'])
        self.assertEqual(self.store.get('gmais_jobs',self.job['id']),original)

    def test_http_companion_contract_no_store_missing_and_safe_runtime_errors(self):
        before=self.fixture.files(self.store)
        response=self.client.get(self.uri)
        self.assertEqual(response.status_code,200)
        body=response.json()
        self.assertEqual(body['extension'],'greenblue.job-lineage-validation.rfc1')
        self.assertEqual(body['evaluation_scope'],'CURRENT_TRANSITIVE_LINEAGE_NOT_SUBMISSION_SNAPSHOT')
        self.assertTrue(body['available']); self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(before,self.fixture.files(self.store))
        missing=self.client.get('/v1/jobs/not-existing/lineage-validation')
        self.assertEqual(missing.status_code,404)
        app_fixtures.GmaisApiTests().validate('error.schema.json',missing.json())
        with patch('app.job_lineage_api.validate_job_lineage',side_effect=KeyError('PRIVATE-INTERNAL-KEY')):
            failed=self.client.get(self.uri)
        self.assertEqual(failed.status_code,503); self.assertNotIn('PRIVATE-INTERNAL-KEY',failed.text)
        app_fixtures.GmaisApiTests().validate('error.schema.json',failed.json())

    def test_actual_main_auth_status_and_submission_snapshot_are_preserved(self):
        status=self.main_client.get('/v1/jobs/'+self.job['id']).json()
        stored=self.store.get('gmais_jobs',self.job['id'])
        with patch.dict(os.environ,{'GEOAI_API_TOKEN':'temporary-job-lineage-token'}):
            self.assertEqual(self.main_client.get(self.uri).status_code,401)
            response=self.main_client.get(self.uri,headers={'Authorization':'Bearer temporary-job-lineage-token'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.main_client.get('/v1/jobs/'+self.job['id']).json(),status)
        app_fixtures.GmaisApiTests().validate('job-status.schema.json',status)
        self.assertEqual(self.store.get('gmais_jobs',self.job['id']),stored)
        for kind in ('jobs','gmais_results','traces','gmais_traces','workflow_runs','analyses','models'):
            self.assertEqual(self.store.list(kind),[])
