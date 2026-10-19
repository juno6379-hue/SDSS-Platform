import copy
import json
import sqlite3
import unittest
from unittest.mock import patch
import test_execution_binding_capture as fixtures
from app.dataset_registry import resolve_version,canonical_manifest,version_key,register_version
from app.job_inputs import resolve_job_inputs_with_capture
from app.stored_current_binding_preflight import inspect_stored_current_binding_preflight


class StoredCurrentBindingPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ExecutionBindingCaptureTests();self.fixture.setUp()
        self.store,self.ref,self.identity=self.fixture.store,self.fixture.ref,self.fixture.identity
        self.save_job()

    def tearDown(self):self.fixture.tearDown()

    def save_job(self,refs=None):
        refs=[dict(self.ref)] if refs is None else refs
        _,capture=resolve_job_inputs_with_capture(self.store,refs,**self.identity)
        self.job=dict(id=self.identity['job_id'],job_id=self.identity['job_id'],agent_id=self.identity['agent_id'],
                      status={k:self.identity[k] for k in ('job_id','agent_id','trace_id')},
                      request=dict(agent_id=self.identity['agent_id'],execution_context=dict(trace_id=self.identity['trace_id']),input_refs=refs),
                      execution_input_binding_capture=capture)
        self.store.put('gmais_jobs',self.job)

    def run_check(self,job_id='job-test'):
        return inspect_stored_current_binding_preflight(self.store,job_id)

    def test_current_match_single_pass_get_and_no_additional_registry(self):
        with patch.object(self.store,'get',wraps=self.store.get) as get,patch('app.job_inputs.resolve_version',wraps=resolve_version) as resolve:
            result=self.run_check()
        self.assertEqual(result['status'],'MATCH');self.assertEqual(result['resolver_pass_calls'],1)
        self.assertEqual([call.args[0] for call in get.call_args_list],['gmais_jobs','dataset_versions'])
        self.assertEqual(resolve.call_count,1)
        self.assertEqual(result['binding_comparison']['status'],'MATCH')
        self.assertEqual(result['current_resolution_status'],'INTEGRITY_VERIFIED');self.assertEqual(result['current_capture_status'],'RECORDED')
        self.assertEqual(result['current_integrity_verified_count'],1);self.assertEqual(result['current_quality_public_observed_count'],1)
        self.assertTrue(result['current_quality_public_diagnostics_passed']);self.assertEqual(result['current_blocker_count'],0)
        self.assertNotIn('current_files_revalidated',result)
        flags=[v for k,v in result.items() if type(v) is bool and k not in ('store_read_attempted','store_read_observed','current_quality_public_diagnostics_passed')]
        self.assertEqual(len(flags),15);self.assertTrue(all(v is False for v in flags))

    def test_manifest_metadata_rehashed_current_success_still_pin_mismatch(self):
        key=version_key(self.ref['id'],self.ref['version']);record=self.store.get('dataset_versions',key)
        manifest=copy.deepcopy(record['manifest']);manifest['source']['license']='changed metadata'
        manifest,digest=canonical_manifest(manifest)
        self.store.put('dataset_versions',dict(record,manifest=manifest,manifest_sha256=digest))
        result=self.run_check()
        self.assertEqual(result['current_resolution_status'],'INTEGRITY_VERIFIED')
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['binding_comparison']['status'],'BLOCKED')
        self.assertEqual(result['binding_comparison']['issues'][0]['code'],'BINDING_MANIFEST_PIN_MISMATCH')

    def test_quality_acl_blocked_even_when_manifest_pin_matches(self):
        for quality,access in (('RAW','PUBLIC'),('VALIDATED','RESTRICTED')):
            version=quality+access
            register_version(self.store,dict(self.fixture.fixture.manifest,version=version,quality_status=quality,access_class=access))
            self.save_job([dict(self.ref,version=version)])
            result=self.run_check()
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['current_resolution_status'],'BLOCKED')
            self.assertEqual(result['binding_comparison']['status'],'MATCH')
            self.assertFalse(result['current_quality_public_diagnostics_passed']);self.assertEqual(result['current_quality_public_observed_count'],1)

    def test_changed_asset_or_stored_uri_blocks(self):
        self.fixture.fixture.asset.write_bytes(b'changed')
        result=self.run_check();self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['current_capture_status'],'UNAVAILABLE')
        self.fixture.fixture.asset.write_bytes(b'{"contract_fixture":true}')
        job=copy.deepcopy(self.job);job['request']['input_refs'][0]['uri']='other.json';self.store.put('gmais_jobs',job)
        result=self.run_check();self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('INPUT_URI_MISMATCH',[x['code'] for x in result['current_blockers']])

    def test_partial_missing_current_input(self):
        register_version(self.store,dict(self.fixture.fixture.manifest,version='2'))
        self.save_job([dict(self.ref),dict(self.ref,version='2')])
        with self.store.connect() as connection:connection.execute('DELETE FROM records WHERE kind=? AND id=?',('dataset_versions',version_key(self.ref['id'],'2')))
        with patch('app.job_inputs.resolve_version',wraps=resolve_version) as resolve:result=self.run_check()
        self.assertEqual(resolve.call_count,2);self.assertEqual(result['current_input_count'],2)
        self.assertEqual(result['current_integrity_verified_count'],1);self.assertEqual(result['current_quality_public_observed_count'],1)
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['current_capture_status'],'UNAVAILABLE')

    def test_legacy_unavailable_invalid_skip_current_resolver(self):
        from app.execution_binding_capture import unavailable_capture
        for state in ('LEGACY','UNAVAILABLE','INVALID'):
            job=copy.deepcopy(self.job)
            if state=='LEGACY':job.pop('execution_input_binding_capture')
            elif state=='UNAVAILABLE':job['execution_input_binding_capture']=unavailable_capture(None,'CAPTURE_BOUNDARY_FAILURE')
            else:job['agent_id']='wrong'
            self.store.put('gmais_jobs',job)
            with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=AssertionError('resolver')):result=self.run_check()
            self.assertEqual(result['resolver_pass_calls'],0);self.assertEqual(result['current_resolution_status'],'NOT_RUN')
            self.assertEqual(result['status'],'BLOCKED' if state=='INVALID' else 'UNKNOWN')

    def test_all_uris_bounded_before_any_resolver_pass(self):
        for value in ('x'*257,'x\u0085','\ud800','',False):
            job=copy.deepcopy(self.job);job['request']['input_refs'][0]['uri']=value
            self.store.put('gmais_jobs',job) if value!='\ud800' else None
            if value=='\ud800':
                with patch.object(self.store,'get',return_value=job),patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=AssertionError('resolver')):result=self.run_check()
            else:
                with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=AssertionError('resolver')):result=self.run_check()
            self.assertEqual(result['resolver_pass_calls'],0);self.assertEqual(result['status'],'BLOCKED')

    def test_store_errors_missing_and_invalid_literal(self):
        result=self.run_check('missing');self.assertEqual(result['store_status'],'NOT_FOUND');self.assertEqual(result['store_get_calls'],1)
        with patch.object(self.store,'get',side_effect=AssertionError('get')):result=self.run_check('x'*257)
        self.assertEqual(result['store_get_calls'],0)
        for error in (KeyError('internal'),sqlite3.DatabaseError('private'),json.JSONDecodeError('secret','x',0)):
            with patch.object(self.store,'get',side_effect=error):result=self.run_check()
            self.assertEqual(result['store_status'],'RESOURCE_UNAVAILABLE');self.assertNotIn('secret',json.dumps(result))

    def test_resolver_resources_failclosed_programmer_and_process_propagate(self):
        for error in (sqlite3.DatabaseError('private'),ValueError('private'),MemoryError('private')):
            with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=error):result=self.run_check()
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['current_resolution_status'],'RESOURCE_UNAVAILABLE')
        for error in (RuntimeError('bug'),AssertionError('bug'),KeyboardInterrupt(),SystemExit(2)):
            with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=error):
                with self.assertRaises(type(error)):self.run_check()

    def test_current_resolution_bounded_schema_before_snapshot(self):
        pair=resolve_job_inputs_with_capture(self.store,[self.ref],**self.identity)
        for mutate in (lambda r:r.update(ready_for_execution=True),lambda r:r.update(network_requests=False),
                       lambda r:r.update(extra='secret'),lambda r:r.update(scope='x'*1000000),lambda r:r.update(status='x'*1000000),
                       lambda r:r['resolved'][0].update(authorization_verified=True),lambda r:r['resolved'][0].update(unknown={}),
                       lambda r:r.update(resolved=[{}]*65),
                       lambda r:r.update(blockers=[{}]*10000),lambda r:r['resolved'][0].update(blocker_codes=['x']*10000),
                       lambda r:r['resolved'][0].update(blocker_codes=[{}]),lambda r:r['resolved'][0].update(blocker_codes=['x'*1000000])):
            resolution=copy.deepcopy(pair[0]);mutate(resolution)
            with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',return_value=(resolution,pair[1])),patch('app.stored_current_binding_preflight._project_snapshot',side_effect=AssertionError('unbounded snapshot')):
                result=self.run_check()
            self.assertEqual(result['current_resolution_status'],'INVALID')

    def test_capture_invalid_and_unavailable_failclosed(self):
        from app.execution_binding_capture import unavailable_capture
        pair=resolve_job_inputs_with_capture(self.store,[self.ref],**self.identity)
        for capture in (None,dict(pair[1],execution_authorized=True),unavailable_capture(None,'CAPTURE_BOUNDARY_FAILURE')):
            with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',return_value=(pair[0],capture)):result=self.run_check()
            self.assertEqual(result['status'],'BLOCKED');self.assertIsNone(result['binding_comparison'])

    def test_no_put_list_training_or_original_job_registry_asset_changes(self):
        with self.store.connect() as connection:before=connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
        asset=self.fixture.fixture.asset.read_bytes()
        with patch.object(self.store,'put',side_effect=AssertionError('write')),patch.object(self.store,'list',side_effect=AssertionError('list')),patch('app.ml.service.train_model',side_effect=AssertionError('train')):
            result=self.run_check()
        with self.store.connect() as connection:after=connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
        self.assertEqual(before,after);self.assertEqual(asset,self.fixture.fixture.asset.read_bytes())
        encoded=json.dumps(result)
        for raw in ('job-test','lcluc-agent','trace-test','private-location.json',str(self.fixture.fixture.root),'b'*64):self.assertNotIn(raw,encoded)
        with self.assertRaises(TypeError):inspect_stored_current_binding_preflight(self.store,'job-test',supplied={})


if __name__=='__main__':unittest.main()
