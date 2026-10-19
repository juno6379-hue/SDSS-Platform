"""Caller threshold tests: actual temporary integration and pure boundary fixtures."""
import copy
import unittest
from unittest.mock import patch

from app.ml import annual_mask_policy as api
import test_annual_quality_mask_diagnostics as fixtures


def policy(n=1,d=2):
    return {'schema_version':1,'minimum_valid_numerator':n,'minimum_valid_denominator':d,'comparison':'greater_than_or_equal'}


def parent(rows,counts=None):
    values = {'valid_pixels':1,'invalid_pixels':2,'total_pixels':3} if counts is None else counts
    return {'status':'ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED','issue':None,'artifact_bytes_verified':True,
        'mask_values_verified':True,'registry_manifest_join_verified':True,'mask_observations':[
            {'year':row['year'],'status':'MATCHED_UNVERIFIED','registry_manifest_join_verified':True,'issue':None,
             'mask_observation':{'status':'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED','mask_declaration_verified':True,
                 'mask_values_verified':True,'artifact_bytes_verified':True,'counts':copy.deepcopy(values)}} for row in rows]}


class AnnualMaskPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fixtures.AnnualQualityMaskDiagnosticsTests(); cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups)

    def inspect(self,rows=None,value=None):
        f = self.fixture
        return api.inspect_annual_mask_policy(f.store,f.model.model_ref,f.model.report_sha,
            f.rows[:2] if rows is None else rows,policy() if value is None else value)

    def test_actual_two_six_rows_exact20_no_extra_io_counts_or_model_load(self):
        f = self.fixture
        for count in (2,6):
            with patch.object(f.store,'get',wraps=f.store.get) as get:
                result = self.inspect(f.rows[:count])
            self.assertEqual(get.call_count,1+6*count); self.assertEqual(len(result),20)
            self.assertEqual(result['status'],'CALLER_POLICY_MET_UNVERIFIED')
            self.assertEqual(result['annual_observation_calls'],1); self.assertTrue(result['caller_policy_evaluated'])
            self.assertTrue(result['caller_policy_met']); self.assertTrue(result['artifact_bytes_verified'])
            self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))

    def test_policy_and_last_row_invalid_all_rejected_pre_io(self):
        invalid = [None,{},True,policy(-1,2),policy(2,1),policy(0,0),policy(1,1000001)]
        for key,value in (('schema_version',True),('minimum_valid_numerator',True),('minimum_valid_denominator',False),
                          ('minimum_valid_numerator',.5),('minimum_valid_denominator','2'),('comparison','>=')):
            bad = policy(); bad[key] = value; invalid.append(bad)
        invalid.append({**policy(),'extra':0})
        with patch.object(self.fixture.store,'get',side_effect=AssertionError('IO')):
            for bad in invalid:
                result = api.inspect_annual_mask_policy(self.fixture.store,self.fixture.model.model_ref,self.fixture.model.report_sha,self.fixture.rows,bad)
                self.assertEqual(result['status'],'INVALID_INPUT'); self.assertEqual(result['annual_observation_calls'],0)
            rows = copy.deepcopy(self.fixture.rows); rows[-1]['mask_ref'] = None
            self.assertEqual(self.inspect(rows)['status'],'INVALID_INPUT')

    def test_integer_exact_boundary_no_rounding_all_years_evaluated(self):
        rows = self.fixture.rows[:3]; fake = parent(rows)
        for n,d,met in ((1,3,True),(333333,1000000,True),(333334,1000000,False),(0,1,True),(1,1,False)):
            with patch.object(api,'inspect_annual_quality_mask_diagnostics',return_value=fake):
                result = self.inspect(rows,policy(n,d))
            self.assertEqual(result['caller_policy_met'],met)
            self.assertEqual([v['status'] for v in result['per_year_observations']],['MET' if met else 'NOT_MET']*3)
            self.assertTrue(result['caller_policy_evaluated']); self.assertEqual(result['artifact_bytes_verified'],met)

    def test_allzero_threshold_zero_pass_positive_threshold_fails(self):
        fake = parent(self.fixture.rows[:2],{'valid_pixels':0,'invalid_pixels':256,'total_pixels':256})
        for n,met in ((0,True),(1,False)):
            with patch.object(api,'inspect_annual_quality_mask_diagnostics',return_value=fake):
                result = self.inspect(value=policy(n,1000000))
            self.assertEqual(result['caller_policy_met'],met)
            self.assertTrue(result['parent_annual_observation']['artifact_bytes_verified'])

    def test_all_counts_prevalidated_no_partial_policy_evaluation(self):
        invalid = [None,{}, {'valid_pixels':0,'invalid_pixels':0,'total_pixels':0},
            {'valid_pixels':1,'invalid_pixels':0,'total_pixels':1024**2+1},
            {'valid_pixels':True,'invalid_pixels':2,'total_pixels':3},
            {'valid_pixels':1,'invalid_pixels':1,'total_pixels':3},
            {'valid_pixels':-1,'invalid_pixels':4,'total_pixels':3},
            {'valid_pixels':1.,'invalid_pixels':2,'total_pixels':3},
            {'valid_pixels':'1','invalid_pixels':2,'total_pixels':3},
            {'valid_pixels':1,'invalid_pixels':2,'total_pixels':3,'extra':0}]
        for bad in invalid:
            fake = parent(self.fixture.rows[:2]); fake['mask_observations'][1]['mask_observation']['counts'] = bad
            with patch.object(api,'inspect_annual_quality_mask_diagnostics',return_value=fake): result = self.inspect()
            self.assertEqual(result['status'],'POLICY_INPUT_BLOCKED'); self.assertFalse(result['caller_policy_evaluated'])
            self.assertTrue(all(v['status']=='NOT_CHECKED' and v['counts'] is None for v in result['per_year_observations']))

    def test_parent_year_status_join_and_fullflags_strict_true(self):
        for key,value in (('year',True),('year',1999),('status','BLOCKED'),('registry_manifest_join_verified',1)):
            fake = parent(self.fixture.rows[:2]); fake['mask_observations'][0][key] = value
            with patch.object(api,'inspect_annual_quality_mask_diagnostics',return_value=fake): result = self.inspect()
            self.assertEqual(result['status'],'POLICY_INPUT_BLOCKED')
        for key in ('artifact_bytes_verified','mask_values_verified','registry_manifest_join_verified'):
            fake = parent(self.fixture.rows[:2]); fake[key] = 1
            with patch.object(api,'inspect_annual_quality_mask_diagnostics',return_value=fake): result = self.inspect()
            self.assertEqual(result['status'],'POLICY_INPUT_BLOCKED')

    def test_first_deficit_issue_but_every_year_evaluated_and_nested_unchanged(self):
        rows = self.fixture.rows[:3]; fake = parent(rows)
        fake['mask_observations'][1]['mask_observation']['counts'] = {'valid_pixels':3,'invalid_pixels':0,'total_pixels':3}
        before = copy.deepcopy(fake)
        with patch.object(api,'inspect_annual_quality_mask_diagnostics',return_value=fake): result = self.inspect(rows,policy(1,2))
        self.assertEqual(result['issue']['year'],2020); self.assertEqual(result['status'],'CALLER_POLICY_NOT_MET')
        self.assertEqual([v['policy_met'] for v in result['per_year_observations']],[False,True,False])
        self.assertEqual(fake,before); self.assertIs(result['parent_annual_observation'],fake)
        result['per_year_observations'][0]['counts']['valid_pixels'] = 100
        self.assertEqual(fake,before)

    def test_request_policy_snapshot_and_fixed_stage_error(self):
        value = policy(1,3); rows = copy.deepcopy(self.fixture.rows[:2]); fake = parent(rows)
        def mutate(*args):
            rows[0]['year'] = 1900; value['minimum_valid_numerator'] = 3
            return fake
        with patch.object(api,'inspect_annual_quality_mask_diagnostics',side_effect=mutate): result = self.inspect(rows,value)
        self.assertTrue(result['caller_policy_met']); self.assertEqual(result['policy']['minimum_valid_numerator'],1)
        self.assertEqual(result['per_year_observations'][0]['year'],2020)
        with patch.object(api,'inspect_annual_quality_mask_diagnostics',side_effect=RuntimeError('SECRET')):
            result = self.inspect()
        self.assertNotIn('SECRET',str(result)); self.assertEqual(result['status'],'ANNUAL_DIAGNOSTICS_BLOCKED')


if __name__ == '__main__':
    unittest.main()
