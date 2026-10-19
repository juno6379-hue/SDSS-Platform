"""Bounded service transport, safe projections and temporary real integrations."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from app import annual_diagnostics_service as api
from app.ml.annual_mask_policy import inspect_annual_mask_policy
import test_annual_quality_mask_diagnostics as fixtures


class AnnualDiagnosticsServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fixtures.AnnualQualityMaskDiagnosticsTests(); cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups)
        root = Path(__file__).resolve().parents[1] / 'contracts/internal'
        cls.request_schema = json.loads((root/'lcluc-annual-diagnostics-request.schema.json').read_text())
        cls.response_schema = json.loads((root/'lcluc-annual-diagnostics-response.schema.json').read_text())
        Draft202012Validator.check_schema(cls.request_schema); Draft202012Validator.check_schema(cls.response_schema)
        f = cls.fixture
        cls.parent = inspect_annual_mask_policy(f.store,f.model.model_ref,f.model.report_sha,f.rows[:2],cls.policy())

    @staticmethod
    def policy():
        return {'schema_version':1,'minimum_valid_numerator':1,'minimum_valid_denominator':2,'comparison':'greater_than_or_equal'}

    def request(self,count=2):
        f = self.fixture
        return {'schema_version':1,'capability':'landcover.input_diagnostics','model_ref':copy.deepcopy(f.model.model_ref),
            'training_report_sha256':f.model.report_sha,'requested_years':copy.deepcopy(f.rows[:count]),'policy':self.policy()}

    def read(self,value=None,raw=None):
        return api.read_annual_diagnostic_service(self.fixture.store,
            json.dumps(self.request() if value is None else value,ensure_ascii=False).encode() if raw is None else raw)

    def validate(self,result):
        Draft202012Validator(self.response_schema).validate(result)

    def test_actual_two_six_service_calls_one135_no_extra_io_and_schema(self):
        for size in (2,6):
            request = self.request(size); Draft202012Validator(self.request_schema).validate(request)
            with (patch.object(self.fixture.store,'get',wraps=self.fixture.store.get) as get,
                  patch.object(api,'inspect_annual_mask_policy',wraps=api.inspect_annual_mask_policy) as core):
                result = self.read(request)
            self.assertEqual(get.call_count,1+6*size); core.assert_called_once(); self.validate(result)
            self.assertEqual(len(result),19); self.assertEqual(result['status'],'CALLER_POLICY_MET_UNVERIFIED')
            self.assertTrue(result['caller_policy_met']); self.assertIsNone(result['blocking_stage'])
            self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))
            for forbidden in ('parent_annual_observation','registry_bindings','artifact_uri','checkpoint_manifest'):
                self.assertNotIn(forbidden,json.dumps(result))

    def test_strict_bytes_limits_json_integer_depth_nodes_unicode_no_store(self):
        raw = json.dumps(self.request()).encode()
        invalid = [b'',b'[]',b'\xff',b'{} '*6000,b'{"a":NaN}',b'{"a":Infinity}',b'{"a":1e999}',b'{"a":1.0}',
            b'{"a":12345678901234567}',b'{"a":9007199254740992}',b'{"a":"\\ud800"}',b'{"\\ud800":1}',
            b'{"a":1,"a":2}',b'['*17+b'0'+b']'*17,b'{"a":['+b'0,'*4096+b'0]}',
            b'{"a":"'+b'x'*513+b'"}',raw.replace(b'"schema_version": 1',b'"schema_version": 1.0',1)]
        with patch.object(self.fixture.store,'get',side_effect=AssertionError('no IO')):
            for value in invalid:
                result = self.read(raw=value); self.assertEqual(result['status'],'INVALID_REQUEST')
                self.assertIsNone(result['request_sha256']); self.validate(result)
            self.assertEqual(api.read_annual_diagnostic_service(self.fixture.store,'not bytes')['status'],'INVALID_REQUEST')

    def test_exact_request_alias_bool_extra_and_last_row_rejected_pre_core(self):
        invalid = []
        for key,value in (('schema_version',True),('capability','landcover.execute'),('extra','secret')):
            item = self.request(); item[key] = value; invalid.append(item)
        item = self.request(); item['model_ref']['version'] = ' current '; invalid.append(item)
        item = self.request(6); item['requested_years'][-1]['mask_ref'] = None; invalid.append(item)
        with patch.object(api,'inspect_annual_mask_policy',side_effect=AssertionError('core0')):
            for item in invalid:
                self.assertEqual(self.read(item)['status'],'INVALID_REQUEST')

    def test_canonical_fingerprint_key_order_whitespace_and_original_unicode(self):
        request = self.request()
        expected = hashlib.sha256(api._canonical(request)).hexdigest()
        with patch.object(api,'inspect_annual_mask_policy',return_value=copy.deepcopy(self.parent)):
            a = self.read(request)
            b = self.read(raw=json.dumps(dict(reversed(list(request.items()))),indent=2).encode())
        self.assertEqual(a['request_sha256'],expected); self.assertEqual(b['request_sha256'],expected)
        request['requested_years'][0]['mask_ref']['id'] = '원형 참조 '
        with patch.object(api,'inspect_annual_mask_policy',return_value=copy.deepcopy(self.parent)):
            result = self.read(request)
        self.assertEqual(result['request_sha256'],hashlib.sha256(api._canonical(request)).hexdigest())

    def test_source_blocked_issues_never_echo_private_paths_and_schema(self):
        for status,stage in (('ANNUAL_DIAGNOSTICS_BLOCKED','ANNUAL'),('POLICY_INPUT_BLOCKED','COUNTS')):
            parent = copy.deepcopy(self.parent)
            parent.update(status=status,caller_policy_evaluated=False,caller_policy_met=False,artifact_bytes_verified=False,
                issue={'code':'SECRET_PATH','field':'C:/private/path','year':2021})
            for row in parent['per_year_observations']:
                row.update(status='NOT_CHECKED',counts=None,policy_met=None)
            with patch.object(api,'inspect_annual_mask_policy',return_value=parent): result = self.read()
            self.assertEqual(result['status'],'SOURCE_BLOCKED'); self.assertEqual(result['blocking_stage'],stage)
            self.assertEqual(result['issue'],{'code':'SOURCE_BLOCKED','year':2021}); self.validate(result)
            self.assertNotIn('private',json.dumps(result)); self.assertNotIn('SECRET',json.dumps(result))

    def test_policy_not_met_projection_recomputes_all_rows_and_first_issue(self):
        parent = copy.deepcopy(self.parent)
        for row in parent['per_year_observations']:
            row.update(status='NOT_MET',counts={'valid_pixels':0,'invalid_pixels':256,'total_pixels':256},policy_met=False)
        parent.update(status='CALLER_POLICY_NOT_MET',caller_policy_met=False,artifact_bytes_verified=False,
            issue={'code':'ANY_SOURCE_TEXT','field':'private','year':2020})
        with patch.object(api,'inspect_annual_mask_policy',return_value=parent): result = self.read()
        self.assertEqual(result['status'],'CALLER_POLICY_NOT_MET'); self.assertEqual(result['issue']['code'],'CALLER_POLICY_NOT_MET')
        self.assertTrue(result['caller_policy_evaluated']); self.assertFalse(result['artifact_bytes_verified']); self.validate(result)

    def test_unsafe_parent_rows_flags_policy_counts_status_return_output_invalid(self):
        variants = []
        for key,value in (('schema_version',True),('scope','SECRET'),('execution_authorized',True),
                          ('artifact_bytes_verified',1),('status','SECRET'),('annual_observation_calls',True)):
            parent = copy.deepcopy(self.parent); parent[key] = value; variants.append(parent)
        for key,value in (('year',True),('status','SECRET'),('policy_met',1),('counts',{'valid_pixels':True,'invalid_pixels':255,'total_pixels':256})):
            parent = copy.deepcopy(self.parent); parent['per_year_observations'][0][key] = value; variants.append(parent)
        parent = copy.deepcopy(self.parent); parent['policy']['minimum_valid_numerator'] = 0; variants.append(parent)
        parent = copy.deepcopy(self.parent); parent['issue'] = {'code':'SECRET','field':'path','year':1899}; variants.append(parent)
        for parent in variants:
            with patch.object(api,'inspect_annual_mask_policy',return_value=parent): result = self.read()
            self.assertEqual(result['status'],'OUTPUT_INVALID'); self.validate(result)
            self.assertEqual(result['per_year_observations'],[]); self.assertNotIn('SECRET',json.dumps(result))
        with patch.object(api,'inspect_annual_mask_policy',side_effect=RuntimeError('SECRET')):
            result = self.read()
        self.assertEqual(result['status'],'OUTPUT_INVALID'); self.assertNotIn('SECRET',json.dumps(result))

    def test_runtime_stricter_than_json_schema_integer_and_cross_field_rules(self):
        request = self.request(); request['schema_version'] = 1.0
        Draft202012Validator(self.request_schema).validate(request)
        self.assertEqual(self.read(request)['status'],'INVALID_REQUEST')
        request = self.request(); request['policy']['minimum_valid_numerator'] = 2; request['policy']['minimum_valid_denominator'] = 1
        Draft202012Validator(self.request_schema).validate(request)
        self.assertEqual(self.read(request)['status'],'INVALID_REQUEST')
        unsafe = api._summary(); unsafe['unexpected'] = 'SECRET'
        self.assertFalse(Draft202012Validator(self.response_schema).is_valid(unsafe))

    def test_core_arguments_cannot_change_fingerprint_or_verification_snapshot(self):
        request = self.request(); expected = hashlib.sha256(api._canonical(request)).hexdigest()
        def mutate(store,ref,sha,rows,policy):
            ref['id'] = 'altered'; rows[0]['year'] = 1900; policy['minimum_valid_numerator'] = 0
            return copy.deepcopy(self.parent)
        with patch.object(api,'inspect_annual_mask_policy',side_effect=mutate): result = self.read(request)
        self.assertEqual(result['status'],'CALLER_POLICY_MET_UNVERIFIED')
        self.assertEqual(result['request_sha256'],expected); self.assertEqual(result['per_year_observations'][0]['year'],2020)

    def test_status_subclass_cannot_echo_sensitive_text_or_run_equality(self):
        calls = []
        class UnsafeStatus(str):
            def __eq__(self,other):
                calls.append(other); return True
        parent = copy.deepcopy(self.parent)
        parent['per_year_observations'][0]['status'] = UnsafeStatus('SECRET_PATH')
        with patch.object(api,'inspect_annual_mask_policy',return_value=parent): result = self.read()
        self.assertEqual(result['status'],'OUTPUT_INVALID'); self.assertEqual(calls,[])
        self.assertNotIn('SECRET',json.dumps(result)); self.validate(result)

    def test_parser_escaped_quotes_backslashes_and_brackets_are_not_depth(self):
        for text in ('quoted " then ' + '{'*30, 'backslash \\ then quoted " and }]', 'ends with \\'):
            raw = json.dumps({'text':text}).encode()
            self.assertEqual(api._parse(raw),{'text':text})
        with self.assertRaises(ValueError): api._parse(b'{"text":"unclosed\\"}')


if __name__ == '__main__':
    unittest.main()
