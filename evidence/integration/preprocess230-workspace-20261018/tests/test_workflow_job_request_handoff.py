import copy
import json
import math
import unittest
from unittest.mock import patch

from app.workflow_job_request_handoff import compare_workflow_job_request_handoff as compare, _bounded_json
from app.workflow_node_input_handoff import _digest
from test_workflow_node_input_handoff import fixture


def full_fixture():
    workflow, metadata = fixture()
    job = dict(schema_version='0.2.0', **metadata,
        aoi=dict(bbox=[106.1, -6.8, 106.2, -6.7], crs='EPSG:4326'),
        requested_outputs=['COG'], parameters={'threshold': 0.5, 'enabled': True})
    job['execution_context'].update(purpose='private-purpose', environment='development')
    return workflow, job


class WorkflowJobRequestHandoffTests(unittest.TestCase):
    def run_compare(self, job=None, workflow=None, pin=None):
        w, j = full_fixture()
        w = w if workflow is None else workflow
        return compare(w, _digest(w) if pin is None else pin, 'private-node', j if job is None else job)

    def test_match_schema_decimal_bbox_immutable_and_private(self):
        w,j = full_fixture(); before = copy.deepcopy((w,j))
        r = self.run_compare(j,w)
        self.assertEqual(r['status'], 'MATCH'); self.assertEqual((w,j),before)
        self.assertTrue(r['full_job_schema_validated']); self.assertTrue(r['bbox_numeric_order_validated'])
        self.assertEqual(r['full_job_request_sha256'],_digest(j))
        self.assertEqual(r['comparator_calls'],1); self.assertIsNone(r['schema_files_read'])
        encoded=json.dumps(r)
        for value in ('private-purpose','private-trace','private-node','private-dataset','file:///private'):
            self.assertNotIn(value,encoded)
        for key in ('database_calls','registry_calls','source_files_read','source_files_written','network_requests','executor_calls','resolver_calls'):
            self.assertIs(type(r[key]),int); self.assertEqual(r[key],0)
        for key in ('complete_job_validated','execution_authorized','aoi_verified','requested_outputs_verified','agent_capability_verified','model_verified','full_job_pin_verified','full_job_origin_verified'):
            self.assertIs(r[key],False)

    def test_required_top_and_context_schema_fields(self):
        for key in ('aoi','requested_outputs','execution_context','schema_version','input_refs'):
            w,j=full_fixture(); del j[key]
            r=self.run_compare(j,w); self.assertEqual(r['issues'],[{'code':'FULL_JOB_SCHEMA_INVALID'}]); self.assertEqual(r['comparator_calls'],0)
        for key in ('purpose','environment','trace_id'):
            w,j=full_fixture(); del j['execution_context'][key]
            self.assertEqual(self.run_compare(j,w)['validator_status'],'INVALID')

    def test_unknown_shape_environment_and_format_rejected(self):
        for mutate in (lambda j:j.update(unknown=True),lambda j:j['execution_context'].update(unknown='secret'),
                lambda j:j['execution_context'].update(environment='unknown'),
                lambda j:j.update(time_range={'start':'not-a-date'})):
            w,j=full_fixture(); mutate(j)
            self.assertEqual(self.run_compare(j,w)['validator_status'],'INVALID')
        w,j=full_fixture(); j['time_range']={'start':'2026-10-17T00:00:00Z'}
        self.assertEqual(self.run_compare(j,w)['status'],'MATCH')

    def test_bbox_bool_nonfinite_and_order(self):
        for bbox in ([True,-6.8,106.2,-6.7],[106,-6,105,-5],[106,-5,107,-6], [106,-6,math.nan,-5],[106,-6,math.inf,-5]):
            w,j=full_fixture(); j['aoi']['bbox']=bbox
            self.assertEqual(self.run_compare(j,w)['status'],'BLOCKED')
        w,j=full_fixture(); j['aoi']['bbox']=[106,-6,107,-5]
        self.assertEqual(self.run_compare(j,w)['status'],'MATCH')

    def test_full_hash_includes_uncompared_aoi_output_context_parameters(self):
        base=self.run_compare()
        for mutate in (lambda j:j['aoi'].update(crs='EPSG:32748'),lambda j:j.update(requested_outputs=['JSON']),
                lambda j:j['parameters'].update(threshold=.7),lambda j:j['execution_context'].update(purpose='other')):
            w,j=full_fixture(); mutate(j); r=self.run_compare(j,w)
            self.assertEqual(r['status'],'MATCH'); self.assertNotEqual(r['full_job_request_sha256'],base['full_job_request_sha256'])
            self.assertEqual(r['extracted_metadata_sha256'],base['extracted_metadata_sha256'])
        w,j=full_fixture(); reversed_job=dict(reversed(list(j.items())))
        self.assertEqual(self.run_compare(reversed_job,w)['full_job_request_sha256'],base['full_job_request_sha256'])

    def test_metadata_agent_trace_inputs_and_presence_drift(self):
        for mutate in (lambda j:j.update(agent_id='changed'),lambda j:j.update(capability_id='changed'),
                lambda j:j['execution_context'].update(trace_id='changed'),lambda j:j['input_refs'][0].update(sha256='b'*64),
                lambda j:j['input_refs'][0].pop('uri'),lambda j:j['input_refs'][0].pop('role')):
            w,j=full_fixture(); mutate(j); r=self.run_compare(j,w)
            self.assertEqual(r['status'],'BLOCKED'); self.assertEqual(r['comparator_calls'],1)
        w,j=full_fixture()
        for field in ('uri','role'):
            del w['nodes'][0]['input_bindings'][0][field]; del j['input_refs'][0][field]
        self.assertEqual(self.run_compare(j,w)['status'],'MATCH')

    def test_optional_workflow_run_id_never_filled(self):
        w,j=full_fixture(); r=self.run_compare(j,w)
        self.assertNotIn('workflow_run_id',j['execution_context']); self.assertEqual(r['status'],'MATCH')
        j['execution_context']['workflow_run_id']=w['workflow_run_id']
        self.assertEqual(self.run_compare(j,w)['status'],'MATCH')
        j['execution_context']['workflow_run_id']='changed'
        self.assertEqual(self.run_compare(j,w)['issues'],[{'code':'WORKFLOW_RUN_ID_MISMATCH'}])

    def test_bounds_cycles_depth_large_int_nonbuiltin_and_aggregate_bytes(self):
        class BadDict(dict): pass
        cycle={}; cycle['self']=cycle
        deep={}; cursor=deep
        for _ in range(26): cursor['next']={}; cursor=cursor['next']
        for bad in (cycle,deep,BadDict(),{'x':10**10000},{'x':'x'*4097},{'x':(1,2)},{1:'key'}, {'x':'\ud800'}, {'x':list(range(17000))}, {'x':['a'*4000]*132}):
            w,j=full_fixture(); j['parameters']=bad
            with patch('app.workflow_job_request_handoff._job_request_validator',side_effect=AssertionError('must not load schema')):
                r=self.run_compare(j,w)
            self.assertEqual(r['issues'],[{'code':'FULL_JOB_JSON_BOUNDS_INVALID'}]); self.assertFalse(r['validator_attempted'])
        self.assertTrue(_bounded_json({'bool':True,'null':None,'n':.5}))

    def test_workflow_bound_precedes_validator(self):
        w,j=full_fixture(); w['policy']['extra']='x'*4097
        with patch('app.workflow_job_request_handoff._job_request_validator',side_effect=AssertionError('must not load')):
            self.assertEqual(self.run_compare(j,w)['issues'],[{'code':'WORKFLOW_JSON_BOUNDS_INVALID'}])

    def test_pin_drift_empty_refs_and_latest_are_blocked(self):
        self.assertEqual(self.run_compare(pin='b'*64)['metadata_comparison']['issues'][0]['code'],'WORKFLOW_PIN_MISMATCH')
        w,j=full_fixture(); j['input_refs'][0]['version']='latest'
        self.assertEqual(self.run_compare(j,w)['status'],'BLOCKED')
        j['input_refs']=[]; self.assertEqual(self.run_compare(j,w)['validator_status'],'INVALID')
        w,j=full_fixture(); j['model_ref']={'id':'model','version':'current','sha256':'a'*64}
        self.assertEqual(self.run_compare(j,w)['issues'],[{'code':'MODEL_VERSION_NOT_PINNED'}])
        for field in ('id','version','role'):
            j['model_ref']={'id':'model','version':'v1','sha256':'a'*64,field:'   '}
            self.assertEqual(self.run_compare(j,w)['issues'],[{'code':'MODEL_REFERENCE_INVALID'}])

    def test_schema_resource_error_private_but_programmer_and_base_exceptions_propagate(self):
        for error in (OSError('private/path'),RuntimeError('GMAIS v0.2 job-request \uc6d0\ubb38 schema\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.'),MemoryError('private')):
            with patch('app.workflow_job_request_handoff._job_request_validator',side_effect=error):
                r=self.run_compare(); self.assertEqual(r['validator_status'],'RESOURCE_UNAVAILABLE')
                self.assertNotIn('private',json.dumps(r))
        for error in (RuntimeError('programmer'),AssertionError('programmer'),KeyboardInterrupt()):
            with patch('app.workflow_job_request_handoff._job_request_validator',side_effect=error):
                with self.assertRaises(type(error)): self.run_compare()
        class BrokenValidator:
            def evolve(self, **kwargs): return self
            def iter_errors(self,value): raise RuntimeError('programmer')
        with patch('app.workflow_job_request_handoff._job_request_validator',return_value=BrokenValidator()):
            with self.assertRaises(RuntimeError): self.run_compare()

    def test_schema_cold_load_is_only_schema_read_no_submission(self):
        from pathlib import Path
        from app.gmais_api import _job_request_validator
        _job_request_validator.cache_clear(); paths=[]; original=Path.read_text
        def read(path,*args,**kwargs):
            paths.append(path.as_posix()); return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read), patch('app.gmais_api._validate_job',side_effect=AssertionError('no fake submit')):
            r=self.run_compare()
        self.assertEqual(r['status'],'MATCH'); self.assertEqual(len(paths),1)
        self.assertTrue(paths[0].endswith('/contracts/upstream/GMAIS-v0.2/schemas/job-request.schema.json'))
        self.assertIsNone(r['schema_files_read'])

    def test_detached_format_checker_keeps_cached_checker_unchanged(self):
        from app.gmais_api import _job_request_validator
        cached = _job_request_validator()
        checker = cached.format_checker
        before = dict(checker.checkers)
        for value in ('not-a-date', '2026-02-30T00:00:00Z', '2026-10-17T00:00:00',
                      '2026-10-17T00:00:60Z', '2026-10-17T00:00:00+99:00', '2026-10-17T00:00:00+00:60',
                      '2026-10-17T00:00:00+01:99'):
            w,j=full_fixture(); j['time_range']={'start':value}
            self.assertEqual(self.run_compare(j,w)['validator_status'],'INVALID')
        for value in ('2026-10-17T00:00:00Z', '2026-10-17t09:00:00.123456+09:00'):
            w,j=full_fixture(); j['time_range']={'start':value}
            self.assertEqual(self.run_compare(j,w)['status'],'MATCH')
        self.assertIs(cached.format_checker,checker)
        self.assertEqual(checker.checkers,before)

    def test_actual_factory_missing_schema_maps_to_safe_resource(self):
        from app.gmais_api import _job_request_validator
        _job_request_validator.cache_clear()
        with patch('app.gmais_api.Path.is_file',return_value=False):
            result=self.run_compare()
        self.assertEqual(result['issues'],[{'code':'RESOURCE_UNAVAILABLE'}])
        self.assertEqual(result['validator_status'],'RESOURCE_UNAVAILABLE')
        _job_request_validator.cache_clear()
        self.assertEqual(self.run_compare()['status'],'MATCH')

    def test_exact_one_comparator_call_and_original_metadata(self):
        from app.workflow_node_input_handoff import compare_workflow_node_input_handoff
        with patch('app.workflow_job_request_handoff.compare_workflow_node_input_handoff',wraps=compare_workflow_node_input_handoff) as spy:
            r=self.run_compare(); self.assertEqual(spy.call_count,1)
            self.assertEqual(spy.call_args.args[3]['input_refs'],full_fixture()[1]['input_refs'])
            self.assertEqual(r['metadata_comparison']['proposed_metadata_sha256'],r['extracted_metadata_sha256'])


if __name__ == '__main__': unittest.main()
