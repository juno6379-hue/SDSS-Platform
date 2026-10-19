"""265 양방향 정책 결속·portable fixture 무결성. Temp/fake provider 전용."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import collect_samples as collector
import selection265_fixtures as fixture_loader
import test_deficit_metadata_selection260 as prior_tests


class Selection265Tests(unittest.TestCase):
    def setUp(self):
        # 기존 fixture 계약을 합성으로 구성하되 TestCase를 이 모듈에 import하지 않는다.
        self.fixture = prior_tests.MetadataSelectionTests(methodName='runTest')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def test_marked_config_requires_callback_and_rejects_unknown_boolean_none(self):
        for marker in ('DEFICIT_AOI_BBOX_CONTAINS_V1','UNKNOWN',True,False,None,0,{},[]):
            for callback in (None,Mock()):
                if marker == 'DEFICIT_AOI_BBOX_CONTAINS_V1' and callback is not None:continue
                config=self.fixture.config();config['candidate_metadata_policy']=marker
                with self.subTest(marker=marker,callback=callback),tempfile.TemporaryDirectory() as directory, \
                     patch.object(collector.service,'search_stac') as search, \
                     patch.object(collector.service,'read_cog_window') as pixels:
                    with self.assertRaisesRegex(ValueError,'CENTER_METADATA_CALLBACK_INVALID'):
                        collector.collect_windows(config,Path(directory),True,candidate_metadata_filter=callback)
                    search.assert_not_called();pixels.assert_not_called()
                    if callback is not None:callback.assert_not_called()

    def test_callback_requires_marker_and_exact_1024_search_bounds_before_network(self):
        for change in ('missing_marker','window256','search21','noncallable'):
            config=self.fixture.config();callback=self.fixture.guard.filter_candidate_pool
            if change=='missing_marker':del config['candidate_metadata_policy']
            if change=='window256':config['window_size']=256
            if change=='search21':config['search_limit']=21
            if change=='noncallable':callback=False
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory, \
                 patch.object(collector.service,'search_stac') as search:
                with self.assertRaisesRegex(ValueError,'CENTER_METADATA_CALLBACK_INVALID'):
                    collector.collect_windows(config,Path(directory),True,candidate_metadata_filter=callback)
                search.assert_not_called()

    def test_unmarked_default_256_report_is_exact_legacy_and_no_network(self):
        config=self.fixture.config(1);config['window_size']=256;del config['candidate_metadata_policy']
        before=copy.deepcopy(config);reports=[]
        for module in (fixture_loader.load_legacy('collector'),collector):
            with tempfile.TemporaryDirectory() as directory,patch.object(collector.service,'search_stac') as search:
                reports.append(module.collect_windows(config,Path(directory),False))
                search.assert_not_called()
        self.assertEqual(reports[0],reports[1]);self.assertEqual(before,config)

    def test_exact_marked_callable_path_still_filters_all_before_scl(self):
        row=self.fixture.item();row['bbox']=None
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(collector.service,'search_stac',return_value=self.fixture.response([row])) as search, \
             patch.object(collector.service,'read_cog_window') as pixels:
            report=collector.collect_windows(self.fixture.config(),Path(directory),True,
                collection_guard=self.fixture.guard,candidate_metadata_filter=self.fixture.guard.filter_candidate_pool)
        self.assertEqual(search.call_count,1);pixels.assert_not_called()
        self.assertEqual(report['scenes'][0]['status'],'metadata_coverage_insufficient')

    def test_fixture_manifest_missing_mutated_and_fixture_missing_mutated_fail_without_fallback(self):
        for mutation in ('missing_manifest','mutated_manifest','missing_guard','mutated_guard',
                         'missing_collector','mutated_collector'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'fixtures';shutil.copytree(fixture_loader.FIXTURES,root)
                role='collector' if mutation.endswith('collector') else 'guard'
                filename='manifest.json' if mutation.endswith('manifest') else role+'.py.fixture'
                path=root/filename
                if mutation.startswith('missing'):path.unlink()
                else:
                    raw=path.read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:])
                with self.assertRaisesRegex(ValueError,'SELECTION265_FIXTURE_'):
                    fixture_loader.load_legacy(role,fixture_root=root)

    def test_fixture_sha_and_bytes_are_exact_historical_contract(self):
        import hashlib
        manifest=json.loads((fixture_loader.FIXTURES/'manifest.json').read_bytes())
        self.assertEqual(manifest['roles']['guard']['bytes'],22548)
        self.assertEqual(manifest['roles']['collector']['bytes'],47009)
        for role,sha in [('guard','a90ba9a70bb0b0eecf529a10961e12edd1d9519b881913eed2e997c52c182071'),
                         ('collector','68d4b986b5500cb19eb810c5b086f668fc698d124551a268c190cdf5a5211301')]:
            raw=(fixture_loader.FIXTURES/manifest['roles'][role]['filename']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),sha)
            self.assertEqual(manifest['roles'][role]['sha256'],sha)
            fixture_loader.load_legacy(role)


if __name__=='__main__':unittest.main()
