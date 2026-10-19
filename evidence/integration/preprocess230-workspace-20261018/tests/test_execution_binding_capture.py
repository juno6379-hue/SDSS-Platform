import builtins
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch
from app.execution_binding_capture import build_submission_binding_capture
from app.execution_input_binding import compare_execution_input_bindings
from app.job_inputs import resolve_job_inputs, resolve_job_inputs_with_capture
from app.dataset_registry import register_version, resolve_version, version_key
import test_job_inputs as fixtures


class ExecutionBindingCaptureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.JobInputTests(); self.fixture.setUp()
        self.store, self.ref = self.fixture.store, self.fixture.ref
        self.identity = dict(job_id='job-test',agent_id='lcluc-agent',trace_id='trace-test',captured_at='2026-10-17T00:00:00Z')

    def tearDown(self): self.fixture.tearDown()

    def pair(self, refs=None, **kwargs):
        return resolve_job_inputs_with_capture(self.store, [copy.deepcopy(self.ref)] if refs is None else refs,
                                              **dict(self.identity, **kwargs))

    def test_same_pass_verified_pin_and_no_extra_reads(self):
        with patch('app.job_inputs.resolve_version', wraps=resolve_version) as resolver:
            old = resolve_job_inputs(self.store,[self.ref]); self.assertEqual(resolver.call_count,1)
            result,capture = self.pair(); self.assertEqual(resolver.call_count,2)
        self.assertEqual(result,old); self.assertEqual(capture['status'],'RECORDED')
        record=self.store.get('dataset_versions',version_key('fixture','1'))
        row=capture['expected_envelope']['bindings'][0]
        self.assertEqual(row['manifest_sha256'],record['manifest_sha256'])
        self.assertNotEqual(row['manifest_sha256'],row['sha256'])
        self.assertEqual(compare_execution_input_bindings(capture['expected_envelope'],capture['expected_envelope'])['status'],'MATCH')
        for key in ('additional_registry_queries','additional_artifact_reads','additional_database_writes'): self.assertEqual(capture[key],0)

    def test_old_public_call_does_not_import_capture(self):
        with patch('app.execution_binding_capture.build_submission_binding_capture',side_effect=AssertionError('capture called')):
            self.assertEqual(resolve_job_inputs(self.store,[self.ref])['status'],'INTEGRITY_VERIFIED')

    def test_restricted_and_quality_blocked_can_record_metadata_without_approval(self):
        for access,quality in (('RESTRICTED','VALIDATED'),('PUBLIC','RAW'),('PUBLIC','REJECTED')):
            version=access+quality
            register_version(self.store,dict(self.fixture.manifest,version=version,access_class=access,quality_status=quality))
            refs=[dict(self.ref,version=version)]
            old=resolve_job_inputs(self.store,refs); result,capture=self.pair(refs)
            self.assertEqual(result,old); self.assertEqual(result['status'],'BLOCKED')
            self.assertEqual(capture['status'],'RECORDED')
            for key in ('execution_authorized','ready_for_execution','ready_for_training','scientific_approval','acl_verified',
                        'registry_verified','training_authorized','pixels_verified','toc_tou_protected','executor_connected',
                        'artifact_bytes_verified','manifest_bytes_verified'): self.assertIs(capture[key],False)

    def test_partial_missing_conflict_and_uri_mismatch_whole_unavailable(self):
        cases=[[self.ref,dict(self.ref,id='missing')], [self.ref,dict(self.ref,sha256='a'*64)],
               [dict(self.ref,uri='other.json')], [dict(self.ref,version='latest')]]
        for refs in cases:
            old=resolve_job_inputs(self.store,refs); result,capture=self.pair(refs)
            self.assertEqual(result,old); self.assertEqual(capture['status'],'UNAVAILABLE')
            self.assertIsNone(capture['expected_envelope']);self.assertIsNone(capture['expected_bindings_sha256'])

    def test_refs_unsupported_capture_only_legacy_still_runs(self):
        for refs in (None,[],{},[self.ref]*65):
            old=resolve_job_inputs(self.store,refs); result,capture=self.pair(refs if refs is not None else [])
            if refs is not None:self.assertEqual(result,old)
            self.assertEqual(capture['status'],'UNAVAILABLE')

    def test_original_order_role_absence_and_distinct_versions(self):
        register_version(self.store,dict(self.fixture.manifest,version='2'))
        refs=[dict(self.ref,version='2',role='T2'),dict(self.ref)]
        result,capture=self.pair(refs)
        rows=capture['expected_envelope']['bindings']
        self.assertEqual([r['version'] for r in rows],['2','1'])
        self.assertEqual([r['input_index'] for r in rows],[0,1])
        self.assertEqual(rows[0]['role'],'T2');self.assertNotIn('role',rows[1])
        self.assertNotIn('uri',json.dumps(capture))

    def test_input_and_record_mutation_detached(self):
        refs=[dict(self.ref,role='T1')]; before=copy.deepcopy(refs)
        result,capture=self.pair(refs)
        refs[0]['role']='later'; refs[0]['sha256']='e'*64
        self.assertEqual(capture['expected_envelope']['bindings'][0]['role'],'T1')
        capture['expected_envelope']['bindings'][0]['sha256']='f'*64
        self.assertEqual(result['resolved'][0]['sha256'],before[0]['sha256'])
        self.assertEqual(self.store.get('dataset_versions',version_key('fixture','1'))['manifest']['sha256'],before[0]['sha256'])

    def test_capture_failure_does_not_change_resolution(self):
        old=resolve_job_inputs(self.store,[self.ref])
        def fail(rows,**kwargs):
            rows[0]['sha256']='e'*64
            raise ValueError('secret raw path')
        with patch('app.execution_binding_capture.build_submission_binding_capture',side_effect=fail):
            result,capture=self.pair()
        self.assertEqual(result,old);self.assertEqual(capture['status'],'UNAVAILABLE')
        self.assertNotIn('secret',json.dumps(capture))

    def test_optional_import_failure_isolated(self):
        original=builtins.__import__
        def importing(name,*args,**kwargs):
            if name=='execution_binding_capture':raise ImportError('private location')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=importing): result,capture=self.pair()
        self.assertEqual(result['status'],'INTEGRITY_VERIFIED');self.assertEqual(capture['status'],'UNAVAILABLE')

    def test_process_exits_and_old_unhandled_errors_propagate(self):
        for error in (KeyboardInterrupt(),SystemExit(2)):
            with patch('app.execution_binding_capture.build_submission_binding_capture',side_effect=error):
                with self.assertRaises(type(error)):self.pair()
        with patch('app.job_inputs.resolve_version',side_effect=RuntimeError('legacy unhandled')):
            with self.assertRaises(RuntimeError):self.pair()
            with self.assertRaises(RuntimeError):resolve_job_inputs(self.store,[self.ref])

    def test_registry_failures_and_capture_pin_errors_preserve_old(self):
        for error in (sqlite3.DatabaseError('secret'),ValueError('secret')):
            with patch('app.job_inputs.resolve_version',side_effect=error):
                old=resolve_job_inputs(self.store,[self.ref]);result,capture=self.pair()
            self.assertEqual(result,old);self.assertEqual(capture['status'],'UNAVAILABLE')
        original=resolve_version(self.store,'fixture','1',self.ref['sha256'])
        for pin in (None,True,'A'*64,'a'*65):
            with patch('app.job_inputs.resolve_version',return_value=dict(original,manifest_sha256=pin)):
                old=resolve_job_inputs(self.store,[self.ref]);result,capture=self.pair()
            self.assertEqual(result,old);self.assertEqual(capture['status'],'UNAVAILABLE')
        damaged=dict(original);damaged.pop('manifest_sha256')
        with patch('app.job_inputs.resolve_version',return_value=damaged):
            result,capture=self.pair()
        self.assertEqual(result['status'],'INTEGRITY_VERIFIED');self.assertEqual(capture['status'],'UNAVAILABLE')

    def test_capture_limits_identity_and_timestamp(self):
        for key,value in (('job_id',True),('agent_id','x'*257),('trace_id','\ud800'),
                          ('captured_at','2026-01-01'),('captured_at',None)):
            result,capture=self.pair(**{key:value})
            self.assertEqual(result['status'],'INTEGRITY_VERIFIED');self.assertEqual(capture['status'],'UNAVAILABLE')
        refs=[dict(self.ref,role='x'*257)]
        old=resolve_job_inputs(self.store,refs);result,capture=self.pair(refs)
        self.assertEqual(result,old);self.assertEqual(capture['status'],'UNAVAILABLE')

    def test_pure_builder_no_io_and_typed_row(self):
        row=dict(input_index=0,**self.ref,manifest_sha256='b'*64,integrity_verified=True)
        before=copy.deepcopy(row)
        with patch('builtins.open',side_effect=AssertionError('pure IO')):
            capture=build_submission_binding_capture([row],**self.identity)
        self.assertEqual(capture['status'],'RECORDED');self.assertEqual(row,before)
        for key,value in (('integrity_verified',1),('input_index',False),('manifest_sha256',None)):
            invalid=dict(row,**{key:value})
            self.assertEqual(build_submission_binding_capture([invalid],**self.identity)['status'],'UNAVAILABLE')

    def test_no_writes_or_manifest_uri_leak(self):
        before={p.name:p.read_bytes() for p in self.fixture.root.iterdir() if p.is_file()}
        with patch.object(self.store,'put',side_effect=AssertionError('write')):
            result,capture=self.pair([dict(self.ref,uri=self.fixture.asset.name)])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.fixture.root.iterdir() if p.is_file()})
        encoded=json.dumps(capture)
        for secret in (self.fixture.asset.name,str(self.fixture.root),'artifact_uri','quality_report_ref'):
            self.assertNotIn(secret,encoded)


    def test_api_stores_only_extension_and_replay_never_recaptures(self):
        import test_gmais_api as api_fixtures
        api = api_fixtures.GmaisApiTests(); api.setUp()
        try:
            payload=api.request();api.register_input_fixture(payload)
            store=api_fixtures.main.store
            with patch.object(store,'put',wraps=store.put) as put, patch('app.job_inputs.resolve_version',wraps=resolve_version) as resolver:
                response,status=api.submit_blocked('capture-contract',payload)
                self.assertEqual(put.call_count,2);self.assertEqual(resolver.call_count,1)
            job=store.get('gmais_jobs',status['job_id'])
            self.assertEqual(job['execution_input_binding_capture']['status'],'RECORDED')
            self.assertNotIn('execution_input_binding_capture',response.json()['error']['details'])
            self.assertNotIn('execution_input_binding_capture',status)
            before=copy.deepcopy(job)
            with patch.object(store,'put',side_effect=AssertionError('replay wrote')), patch('app.job_inputs.resolve_job_inputs_with_capture',side_effect=AssertionError('replay capture')):
                replay=api.client.post('/v1/agents/lcluc-agent/jobs',json=payload,headers={'Idempotency-Key':'capture-contract'})
                self.assertEqual(replay.json(),response.json())
                self.assertEqual(api.client.get('/v1/jobs/'+status['job_id']).json(),status)
            self.assertEqual(store.get('gmais_jobs',status['job_id']),before)
            legacy=copy.deepcopy(job);legacy.pop('execution_input_binding_capture');store.put('gmais_jobs',legacy)
            with patch.object(store,'put',side_effect=AssertionError('backfill')),patch('app.job_inputs.resolve_job_inputs_with_capture',side_effect=AssertionError('legacy replay capture')):
                api.client.post('/v1/agents/lcluc-agent/jobs',json=payload,headers={'Idempotency-Key':'capture-contract'})
            self.assertNotIn('execution_input_binding_capture',store.get('gmais_jobs',status['job_id']))
        finally:api.tearDown()

    def test_api_capture_failure_preserves_http_and_jobstatus(self):
        import test_gmais_api as api_fixtures
        from types import SimpleNamespace
        bodies=[];jobs=[]
        for fail in (False,True):
            api=api_fixtures.GmaisApiTests();api.setUp()
            try:
                payload=api.request();api.register_input_fixture(payload)
                original=build_submission_binding_capture
                def builder(*args,**kwargs):
                    if fail:raise RuntimeError('private exception')
                    return original(*args,**kwargs)
                with patch('app.gmais_api.uuid.uuid4',return_value=SimpleNamespace(hex='fixed')),patch('app.gmais_api._now',return_value=self.identity['captured_at']),patch('app.store.now',return_value=self.identity['captured_at']),patch('app.execution_binding_capture.build_submission_binding_capture',side_effect=builder):
                    response,status=api.submit_blocked('capture-failure-contract',payload)
                bodies.append(response.json());job=api_fixtures.main.store.get('gmais_jobs',status['job_id'])
                capture=job.pop('execution_input_binding_capture')
                self.assertEqual(capture['status'],'UNAVAILABLE' if fail else 'RECORDED')
                jobs.append(job)
            finally:api.tearDown()
        self.assertEqual(bodies[0],bodies[1]);self.assertEqual(jobs[0],jobs[1])


if __name__=='__main__':unittest.main()
