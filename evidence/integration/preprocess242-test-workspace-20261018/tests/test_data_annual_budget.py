"""병렬 작업에도 총 예산과 대상 주 범위가 유지되는지 검증한다."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).resolve().parents[1]/'scripts/collect_first_group_annual.py'
spec=importlib.util.spec_from_file_location('annual_budget',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AnnualBudgetTests(unittest.TestCase):
    def config(self):
        return {'aois':[{'id':name} for name in sorted(module.PROVINCES)],'years':list(range(2020,2026)),
                'max_total_bytes':2*1024**3,'prior_download_budget_bytes':230000000}

    def test_concurrent_allowances_cannot_exceed_total(self):
        plan=module.build_plan(self.config(),Path('test-output'),additional_prior=18000000)
        self.assertLessEqual(plan['prior_budget_bytes']+sum(t['reserved_transfer_allowance'] for t in plan['tasks']),plan['maximum_total_bytes'])
        ids=[a['id'] for t in plan['tasks'] for a in t['config']['aois']]
        self.assertEqual(set(ids),module.PROVINCES)
        self.assertEqual(len(ids),6)
        self.assertTrue(all(len(t['config']['bands'])==6 for t in plan['tasks']))

    def test_exhausted_budget_and_wrong_province_are_rejected(self):
        config=self.config()
        with self.assertRaises(ValueError):
            module.build_plan(config,Path('test-output'),additional_prior=2*1024**3)
        config['aois'][0]={'id':'central_java'}
        with self.assertRaises(ValueError):
            module.build_plan(config,Path('test-output'))

    def test_resume_rejects_modified_budget_file(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()
            plan=module.build_plan(self.config(),output)
            for task in plan['tasks']:
                Path(task['config_path']).write_text(json.dumps(task['config']),encoding='utf-8')
            module.validate_plan(plan,output)
            task=plan['tasks'][0]
            changed={**task['config'],'max_total_bytes':4*1024**3}
            Path(task['config_path']).write_text(json.dumps(changed),encoding='utf-8')
            with self.assertRaises(ValueError):
                module.validate_plan(plan,output)

    def test_provider_429_is_propagated_to_coordinator(self):
        result=module.rate_limit_evidence({'scenes':[{'aoi':'west_java','year':'2020','error':{'http_status':429,'retry_after':'60','server_host':'planetarycomputer.microsoft.com'}}]})
        self.assertEqual(result['http_status'],429)
        self.assertEqual(result['retry_after'],'60')
        self.assertEqual(result['request_host'],'planetarycomputer.microsoft.com')
        self.assertIsNone(module.rate_limit_evidence({'scenes':[{'error':{'http_status':404}}]}))
        state={'last_rate_limit':{'reason':'provider_http_429','request_host':'example.test','retry_after':'120'}}
        self.assertEqual(module.rate_limit_evidence(None,state)['retry_after'],'120')
        self.assertEqual(module.rate_limit_evidence({'batch_circuit_breaker':state['last_rate_limit']})['request_host'],'example.test')


if __name__=='__main__':
    unittest.main()
