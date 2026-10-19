"""표적 계획의 명시 SCL 선별 강화: 실제 Temp 파일, 네트워크 Mock."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import from_origin

import test_targeted_bare_plan as fixtures
from app.data.targeted_bare_plan import prepare_targeted_bare_jobs
from scripts import collect_samples as collector


class TargetedCandidateQualityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.TargetedBarePlanTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def prepare(self,value):
        self.fixture.plan['policy']['minimum_candidate_valid_fraction']=value
        return self.fixture.run_plan()

    def test_omitted_field_preserves_complete_existing_banten_job_and_key(self):
        # Existing175 test checks every job/config field and both canonical SHA values.
        self.fixture.test_existing_banten_complete_job_and_key_contract_remains_unchanged()
        self.assertEqual(self.fixture.run_plan()['job_proposals'][0]['config']['candidate_valid_fraction'],.65)

    def test_explicit_finite_range_is_forwarded_and_only_candidate_config_changes(self):
        original_plan=copy.deepcopy(self.fixture.plan)
        original_job=self.fixture.run_plan()['job_proposals'][0]
        for value in (.8,.9,1.0,1):
            with self.subTest(value=value):
                self.fixture.plan=copy.deepcopy(original_plan)
                out=self.prepare(value)
                self.assertEqual(out['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',out)
                job=out['job_proposals'][0]
                expected=copy.deepcopy(original_job['config']);expected['candidate_valid_fraction']=value
                self.assertEqual(job['config'],expected)
                self.assertEqual(job['config_sha256'],hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest())
                self.assertEqual(job['split'],'val')
                self.assertEqual(job['nominal_patches'],1)
                self.assertEqual(job['geometry'],original_job['geometry'])
                self.assertFalse(out['execution_supported'])
                digest=hashlib.sha256(json.dumps(self.fixture.plan,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
                self.assertEqual(job['key'],f'target256-bare-banten-2020-local-a-{digest[:12]}')
                self.assertNotEqual(job['key'],original_job['key'])

    def test_invalid_field_or_extra_policy_is_rejected_before_pinned_file_reads(self):
        original=copy.deepcopy(self.fixture.plan)
        for value in (True,False,None,'0.8',.65,.799999,-1,1.000001,float('nan'),float('inf'),float('-inf'),[],{}):
            with self.subTest(value=value):
                self.fixture.plan=copy.deepcopy(original)
                self.fixture.plan['policy']['minimum_candidate_valid_fraction']=value
                with patch('app.data.targeted_bare_plan._snapshot',side_effect=AssertionError('입력 파일 읽기 금지')) as read:
                    out=self.fixture.run_plan()
                self.assertEqual(out['status'],'BLOCKED')
                self.assertEqual(out['job_proposals'],[])
                read.assert_not_called()
        self.fixture.plan=copy.deepcopy(original)
        self.fixture.plan['policy'].update(minimum_candidate_valid_fraction=.8,unexpected=True)
        with patch('app.data.targeted_bare_plan._snapshot') as read:
            self.assertEqual(self.fixture.run_plan()['issue'],'POLICY_INVALID')
        read.assert_not_called()

    def test_explicit_policy_preserves_inputs_and_actual_local_fixture_bytes(self):
        self.fixture.plan['policy']['minimum_candidate_valid_fraction']=.8
        original=copy.deepcopy((self.fixture.plan,self.fixture.base))
        before={p:p.read_bytes() for p in self.fixture.root.rglob('*') if p.is_file()}
        self.assertEqual(self.fixture.run_plan()['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED')
        self.assertEqual(original,(self.fixture.plan,self.fixture.base))
        self.assertEqual(before,{p:p.read_bytes() for p in self.fixture.root.rglob('*') if p.is_file()})

    def test_existing_collect_windows_passes_explicit_minimum_to_selector(self):
        job=self.prepare(.8)['job_proposals'][0]
        config=copy.deepcopy(job['config'])
        config.update(collection='sentinel-2-l2a',periods={'2020':{'start_date':'2020-06-01','end_date':'2020-09-30'}})
        directory=self.fixture.root/'dispatch'
        with (patch.object(collector.service,'search_stac',return_value={'items':[{'id':'synthetic','cloud_cover':0}]}),
              patch.object(collector,'select_quality_candidate',return_value=(None,None,[])) as select,
              patch.object(collector.service,'read_cog_window',side_effect=AssertionError('원격 읽기 금지')) as remote):
            report=collector.collect_windows(config,directory,execute=True)
        select.assert_called_once()
        self.assertEqual(select.call_args.args[-1],.8)
        self.assertEqual(report['scenes'][0]['status'],'quality_insufficient')
        remote.assert_not_called()
        self.assertFalse(report['learning_ready'])

    def test_actual_selector_rejects_low_scl_then_tries_next_candidate(self):
        items=[{'id':name,'cloud_cover':index,'assets':{'SCL':{'href':name}},'license':'TESTED_SYNTHETIC'}
               for index,name in enumerate(('low','clear'))]
        profile={'driver':'GTiff','count':1,'dtype':'uint8','width':128,'height':128,
                 'crs':CRS.from_epsg(32748),'transform':from_origin(500000,9300000,20,20)}
        low=np.full((1,128,128),9,dtype='uint8');low[0].flat[:11082]=4
        clear=np.full((1,128,128),4,dtype='uint8')
        calls=[]
        def fetch(url,bbox,pixels):
            calls.append(url)
            return (low if url=='low' else clear),profile
        for minimum,expected in ((.65,'low'),(.8,'clear')):
            directory=self.fixture.root/f'qa-{minimum}';directory.mkdir()
            chosen,_,audit=collector.select_quality_candidate(items,fetch,{'bbox':[105,-7,105.1,-6.9]},256,directory,self.fixture.root,minimum)
            self.assertEqual(chosen['id'],expected)
            self.assertEqual(audit[0]['minimum_fraction'],minimum)
            if minimum==.8:
                self.assertEqual([row['status'] for row in audit],['quality_insufficient','eligible'])
                self.assertEqual(calls[-2:],['low','clear'])


if __name__=='__main__':
    unittest.main()
