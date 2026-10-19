"""Same-get temporal policy on TempStore records; no inference/operating IO."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from app.dataset_registry import version_key
from app.ml import registry_temporal_normalization as api
import test_pinned_annual_normalization as annual_fixtures


class RegistryTemporalNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=annual_fixtures.PinnedAnnualNormalizationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups);self.store=self.fixture.store;self.rows=self.fixture.rows
        for row in self.rows:self.temporal(row['year'],{'start':f"{row['year']}-01-01T00:00:00Z",'end':f"{row['year']}-12-31T23:59:59.999999999Z",'calendar':'gregorian'})

    def temporal(self,year,value):
        row=next(row for row in self.rows if row['year']==year);key=version_key(row['image_ref']['id'],row['image_ref']['version'])
        record=self.store.get('dataset_versions',key);record['manifest']['temporal']=value
        encoded=json.dumps(record['manifest'],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
        record['manifest_sha256']=hashlib.sha256(encoded).hexdigest();self.store.put('dataset_versions',record)

    def inspect(self,**kwargs):
        model=self.fixture.fixture
        args={'store':self.store,'model_ref':model.model_ref,'training_report_sha256':model.report_sha,'requested_years':self.rows[:2]}
        args.update(kwargs);return api.inspect_registry_temporal_normalization(**args)

    def test_two_and_six_actual_batch_one_get_record_per_role_nested_false_and_top_registry_true(self):
        for size in (2,6):
            with patch.object(self.store,'get',wraps=self.store.get) as get:result=self.inspect(requested_years=self.rows[:size])
            self.assertEqual(len(result),13);self.assertEqual(result['status'],'REGISTRY_YEARS_MATCHED_UNVERIFIED')
            self.assertTrue(result['registry_temporal_year_verified']);self.assertTrue(result['artifact_bytes_verified'])
            self.assertEqual(get.call_count,1+3*size);self.assertEqual(len(result['temporal_observations']),size)
            self.assertFalse(result['batch_observation']['temporal_year_verified'])
            self.assertEqual(result['batch_observation']['model_observation_calls'],1)
            for key in ('physical_acquisition_year_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
                self.assertIs(result[key],False)

    def test_utc_offset_local_year_differs_and_start_equal_end_valid_instant(self):
        self.temporal(2020,{'start':'2019-12-31T23:30:00-01:00','end':'2020-01-01T00:30:00Z','calendar':'gregorian'})
        self.assertTrue(self.inspect()['registry_temporal_year_verified'])
        self.temporal(2020,{'start':'2020-01-01T00:30:00+01:00','end':'2020-01-01T01:00:00+01:00','calendar':'gregorian'})
        self.assertEqual(self.inspect()['issue']['code'],'TEMPORAL_YEAR_MISMATCH')

    def test_next_jan1_end_and_cross_year_reject_closed_endpoint_policy(self):
        for start,end in (('2020-01-01T00:00:00Z','2021-01-01T00:00:00Z'),
                          ('2019-12-31T23:59:59.999999999Z','2020-01-01T00:00:00Z')):
            self.temporal(2020,{'start':start,'end':end,'calendar':'gregorian'})
            result=self.inspect();self.assertEqual(result['status'],'TEMPORAL_BLOCKED')
            self.assertEqual(result['issue'],{'code':'TEMPORAL_YEAR_MISMATCH','field':'window','year':2020})
            self.assertEqual([row['status'] for row in result['batch_observation']['rows']],['BLOCKED','NOT_CHECKED'])

    def test_fraction_nanosecond_reversal_not_hidden_by_datetime_microsecond_truncation(self):
        self.temporal(2020,{'start':'2020-01-01T00:00:00.123456789Z','end':'2020-01-01T00:00:00.123456788Z','calendar':'gregorian'})
        result=self.inspect();self.assertEqual(result['issue']['code'],'TEMPORAL_WINDOW_REVERSED')
        self.temporal(2020,{'start':'2020-01-01T00:00:00.123456789Z','end':'2020-01-01T00:00:00.123456789Z','calendar':'gregorian'})
        self.assertTrue(self.inspect()['registry_temporal_year_verified'])

    def test_strict_ascii_rfc3339_subset_calendar_unknown_offset_and_malformed_fields(self):
        invalid=['2020-01-01','2020-01-01T00:00:00','2020-01-01 00:00:00Z','2020-01-01t00:00:00z',
                 '2020-01-01T00:00:60Z','2020-01-01T24:00:00Z','2020-01-01T00:00:00+24:00',
                 '2020-01-01T00:00:00.1234567890Z','２０２０-01-01T00:00:00Z',None,True]
        for value in invalid:
            self.temporal(2020,{'start':value,'end':'2020-12-31T00:00:00Z','calendar':'gregorian'})
            self.assertEqual(self.inspect()['issue']['code'],'TEMPORAL_FIELD_INVALID',repr(value))
        self.temporal(2020,{'start':'2020-01-01T00:00:00-00:00','end':'2020-12-31T00:00:00Z','calendar':'gregorian'})
        self.assertEqual(self.inspect()['issue']['code'],'TEMPORAL_OFFSET_UNKNOWN')
        for calendar,code in ((None,'TEMPORAL_FIELD_INVALID'),('proleptic_gregorian','TEMPORAL_CALENDAR_UNSUPPORTED'),('Gregorian','TEMPORAL_CALENDAR_UNSUPPORTED')):
            self.temporal(2020,{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T00:00:00Z','calendar':calendar})
            self.assertEqual(self.inspect()['issue']['code'],code)

    def test_middle_failfast_precise_proxy_reason_survives_125_sanitization(self):
        self.temporal(2021,{'start':'2021-01-01T00:00:00-00:00','end':'2021-12-31T00:00:00Z','calendar':'gregorian'})
        result=self.inspect(requested_years=self.rows[:3]);nested=result['batch_observation']
        self.assertEqual(result['issue'],{'code':'TEMPORAL_OFFSET_UNKNOWN','field':'start','year':2021})
        self.assertEqual(nested['issue']['code'],'SCENE_OBSERVATION_BLOCKED')
        self.assertEqual(nested['rows'][1]['scene_observation']['issue']['code'],'REGISTRY_RECORD_UNAVAILABLE')
        self.assertEqual([row['status'] for row in nested['rows']],['MATCHED_UNVERIFIED','BLOCKED','NOT_CHECKED'])
        self.assertEqual([row['status'] for row in result['temporal_observations']],['MATCHED_UNVERIFIED','BLOCKED'])
        self.assertFalse(result['registry_temporal_year_verified']);self.assertFalse(result['artifact_bytes_verified'])

    def test_invalid_request_global_and_model_failure_no_image_get(self):
        with patch.object(self.store,'get',side_effect=AssertionError('no I/O')):
            result=self.inspect(requested_years=[]);self.assertEqual(result['status'],'INVALID_INPUT')
        model=self.fixture.fixture;model.manifest['normalization_mode']='global';model.bind_model()
        with patch.object(self.store,'get',wraps=self.store.get) as get:result=self.inspect()
        self.assertEqual(result['status'],'OUT_OF_SCOPE');self.assertEqual(get.call_count,1);self.assertEqual(result['temporal_observations'],[])
        model.checkpoint.write_bytes(b'changed')
        with patch.object(self.store,'get',wraps=self.store.get) as get:result=self.inspect()
        self.assertEqual(result['status'],'MODEL_BLOCKED');self.assertEqual(get.call_count,1)

    def test_temporal_checked_on_exact_returned_record_without_fresh_get_and_detached_copy(self):
        original=self.store.get;image_key=version_key(self.rows[0]['image_ref']['id'],self.rows[0]['image_ref']['version'])
        counts={};captured=[];canonical=api.canonical_manifest
        def getter(kind,key):
            counts[key]=counts.get(key,0)+1
            record=original(kind,key)
            if kind=='dataset_versions' and key==image_key:
                captured.append(record)
                if counts[key]>1:record['manifest']['temporal']['start']='1999-01-01T00:00:00Z'
            return record
        def checked(manifest):
            value=canonical(manifest)
            if captured:captured[0]['manifest']['temporal']['start']='1999-01-01T00:00:00Z'
            return value
        with patch.object(self.store,'get',getter),patch.object(api,'canonical_manifest',checked):result=self.inspect()
        self.assertEqual(result['status'],'REGISTRY_YEARS_MATCHED_UNVERIFIED');self.assertEqual(counts[image_key],1)
        self.assertEqual(captured[0]['manifest']['temporal']['start'],'1999-01-01T00:00:00Z')

    def test_manifest_digest_tamper_and_scene_file_failure_not_misreported_as_temporal_success(self):
        original=self.store.get;key=version_key(self.rows[0]['image_ref']['id'],self.rows[0]['image_ref']['version'])
        def tampered(kind,identifier):
            record=original(kind,identifier)
            if kind=='dataset_versions' and identifier==key:record['manifest']['temporal']['start']='2020-02-01T00:00:00Z'
            return record
        with patch.object(self.store,'get',tampered):result=self.inspect()
        self.assertEqual(result['issue']['code'],'REGISTRY_REFERENCE_CONFLICT');self.assertEqual(result['status'],'TEMPORAL_BLOCKED')
        self.fixture.paths[0][0].write_bytes(b'changed image')
        result=self.inspect();self.assertEqual(result['status'],'SCENE_BLOCKED')
        self.assertEqual(result['temporal_observations'][0]['status'],'MATCHED_UNVERIFIED')
        self.assertFalse(result['registry_temporal_year_verified'])

    def test_inputs_and_db_files_unchanged_no_put_and_nested_127_preserved(self):
        before=copy.deepcopy(self.rows)
        files={p.relative_to(self.fixture.root).as_posix():p.read_bytes() for p in self.fixture.root.rglob('*') if p.is_file()}
        with patch.object(self.store,'put',side_effect=AssertionError('no writes')):result=self.inspect()
        self.assertEqual(before,self.rows);self.assertFalse(result['batch_observation']['temporal_year_verified'])
        self.assertEqual(files,{p.relative_to(self.fixture.root).as_posix():p.read_bytes() for p in self.fixture.root.rglob('*') if p.is_file()})

    def test_invalid_mutable_request_becomes_valid_cannot_trigger_nested_io(self):
        request=[]
        def mutate_then_reject(*args):
            request.extend(copy.deepcopy(self.rows[:2]))
            raise ValueError('original request invalid')
        with patch.object(api,'_request',mutate_then_reject),patch.object(self.store,'get',side_effect=AssertionError('no I/O')):
            result=self.inspect(requested_years=request)
        self.assertEqual(result['status'],'INVALID_INPUT')
        self.assertEqual(result['batch_observation']['status'],'INVALID_INPUT')
        self.assertEqual(result['batch_observation']['model_observation_calls'],0)


if __name__=='__main__':unittest.main()
