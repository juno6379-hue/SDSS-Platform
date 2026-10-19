"""Explicit report metadata and untrusted producer boundary; temporary consumers."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import quality_report_completion as api
from app.data.quality_mask_bundle import prepare_quality_mask_bundle
from app.dataset_registry import canonical_manifest, register_version
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store
import test_quality_mask_bundle as fixtures


class QualityReportCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.QualityMaskBundleTests.setUpClass()
        cls.addClassCleanup(fixtures.QualityMaskBundleTests.doClassCleanups)

    def setUp(self):
        self.fixture = fixtures.QualityMaskBundleTests(); self.fixture.setUp()
        self.image = self.fixture.image; self.mask = self.fixture.mask; self.identity = self.fixture.identity
        self.metadata = {'source':{'institution':'EXPLICIT_REPORT_CALLER','product':'REPORT_NOT_IMAGE_PRODUCT','license':'TEST_ONLY'},
            'spatial':{'crs':'EPSG:4326','bbox':[100,-10,110,0]},
            'temporal':{'start':'2021-01-01T00:00:00Z','end':'2021-12-31T00:00:00Z','calendar':'gregorian'},
            'quality_status':'STAGED','access_class':'PUBLIC'}

    def complete(self):
        return api.complete_quality_report(self.image,self.mask,self.identity,self.metadata)

    def test_exact21_complete12keys_caller_metadata_preserved_bytes_same_and_false(self):
        bundle = prepare_quality_mask_bundle(self.image,self.mask,self.identity)
        with patch.object(api,'prepare_quality_mask_bundle',wraps=api.prepare_quality_mask_bundle) as producer:
            result = self.complete()
        producer.assert_called_once(); self.assertEqual(len(result),21)
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        self.assertEqual(len(result['report_manifest_draft']),12)
        self.assertEqual(result['report_bytes'],bundle['report_bytes']); self.assertEqual(result['report_sha256'],bundle['report_sha256'])
        self.assertEqual(result['report_manifest_draft']['source'],self.metadata['source'])
        self.assertEqual(result['report_manifest_draft']['temporal'],self.metadata['temporal'])
        self.assertEqual(result['report_manifest_draft']['quality_status'],'STAGED')
        self.assertEqual(result['report_envelope']['quality_status'],'RAW')
        self.assertTrue(all(result[field] is False for field in api.FALSE_FIELDS))
        canonical_manifest(result['report_manifest_draft'])

    def test_exact5_metadata_invalid_values_zero_producer_calls(self):
        bad = [None,{}, {**self.metadata,'dataset_id':'collision'}, {**self.metadata,'quality_status':'VALIDATED'},
            {**self.metadata,'access_class':'OPEN'}, {**self.metadata,'source':{}},
            {**self.metadata,'spatial':{'crs':'EPSG:4326','bbox':[True,0,1,2]}},
            {**self.metadata,'temporal':{'start':'2021-02-30T00:00:00Z','end':'2021-12-31T00:00:00Z','calendar':'gregorian'}}]
        for metadata in bad:
            with patch.object(api,'prepare_quality_mask_bundle',side_effect=AssertionError('invalid metadata no prepare')) as producer:
                result = api.complete_quality_report(self.image,self.mask,self.identity,metadata)
            producer.assert_not_called(); self.assertEqual(result['status'],'BLOCKED')
            self.assertIsNone(result['report_manifest_draft']); self.assertIsNone(result['report_bytes'])

    def test_untrusted_producer_exactshape_flags_bytes_sha_ref_patch_and_metadata_tamper(self):
        baseline = prepare_quality_mask_bundle(self.image,self.mask,self.identity)
        variants = []
        for key,value in (('schema_version',True),('scope','PRIVATE'),('status','BLOCKED'),('issue',{'code':'PRIVATE','field':'/secret'}),
                          ('execution_authorized',0),('registry_registered',True),('report_bytes',b'changed'),
                          ('report_sha256','0'*64),('extra','PRIVATE'),('report_metadata_required',[])):
            parent = copy.deepcopy(baseline); parent[key] = value; variants.append(parent)
        for mutate in (lambda p:p['fixed_refs']['image_ref'].update(version='different'),
                       lambda p:p['report_manifest_patch']['lineage'].reverse(),
                       lambda p:p['report_manifest_patch'].update(source={'institution':'invented'}),
                       lambda p:p['image_manifest_draft'].update(quality_report_ref='private'),
                       lambda p:p['mask_manifest_draft']['source']['mask_semantics'].update(valid_value=True)):
            parent = copy.deepcopy(baseline); mutate(parent); variants.append(parent)
        for parent in variants:
            with patch.object(api,'prepare_quality_mask_bundle',return_value=parent): result = self.complete()
            self.assertEqual(result['issue'],{'code':'PREPARATION_OUTPUT_INVALID','field':'bundle'})
            self.assertIsNone(result['report_bytes']); self.assertIsNone(result['fixed_refs']); self.assertNotIn('PRIVATE',json.dumps(result))

    def test_producer_mutation_inputs_and_custom_equality_cannot_change_expected(self):
        original = api.prepare_quality_mask_bundle
        def mutate(image,mask,identity):
            result = original(image,mask,identity)
            image['source']['institution'] = 'changed'; identity['id'] = 'changed'
            return result
        before = copy.deepcopy((self.image,self.mask,self.identity,self.metadata))
        with patch.object(api,'prepare_quality_mask_bundle',side_effect=mutate): result = self.complete()
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        self.assertEqual((self.image,self.mask,self.identity,self.metadata),before)
        calls = []
        class Unsafe(str):
            def __eq__(self,other): calls.append(other); return True
        parent = original(self.image,self.mask,self.identity); parent['scope'] = Unsafe('PRIVATE')
        with patch.object(api,'prepare_quality_mask_bundle',return_value=parent): result = self.complete()
        self.assertEqual(result['issue']['code'],'PREPARATION_OUTPUT_INVALID'); self.assertEqual(calls,[])

    def test_no_io_deep_detached_outputs_and_negative_zero_exactness(self):
        before = copy.deepcopy((self.image,self.mask,self.identity,self.metadata))
        with (patch('builtins.open',side_effect=AssertionError('open')),
              patch.object(Path,'stat',side_effect=AssertionError('stat')),
              patch.object(Path,'resolve',side_effect=AssertionError('resolve')),
              patch.object(Store,'get',side_effect=AssertionError('get')),
              patch.object(Store,'put',side_effect=AssertionError('put')),
              patch('app.dataset_registry.canonical_manifest',side_effect=AssertionError('cold schema'))):
            result = self.complete()
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        result['report_manifest_draft']['source']['institution'] = 'changed'
        result['image_manifest_draft']['source']['product'] = 'changed'
        self.assertEqual((self.image,self.mask,self.identity,self.metadata),before)
        self.image['spatial']['bbox'][0] = -0.0
        parent = prepare_quality_mask_bundle(self.image,self.mask,self.identity)
        parent['image_manifest_draft']['spatial']['bbox'][0] = 0.0
        with patch.object(api,'prepare_quality_mask_bundle',return_value=parent): result = self.complete()
        self.assertEqual(result['issue']['code'],'PREPARATION_OUTPUT_INVALID')

    def test_metadata_strict_tree_cycle_nan_bigint_surrogate_and_subclasses(self):
        for value in (float('nan'),float('inf'),2**53,'\ud800'):
            self.metadata['source']['extra'] = value
            self.assertEqual(self.complete()['status'],'BLOCKED')
        self.metadata['source'].pop('extra')
        cycle = {}; cycle['self'] = cycle; self.metadata['source']['extra'] = cycle
        self.assertEqual(self.complete()['status'],'BLOCKED'); self.metadata['source'].pop('extra')
        class Custom(dict): pass
        self.assertEqual(api.complete_quality_report(self.image,self.mask,self.identity,Custom(self.metadata))['status'],'BLOCKED')

    def test_verified_report_bytes_snapshot_not_mutable_parent_reread(self):
        parent = prepare_quality_mask_bundle(self.image,self.mask,self.identity)
        original_bytes = parent['report_bytes']; same = api._same
        def poison(actual,expected):
            verified = same(actual,expected)
            if type(expected) is dict and expected.get('scope') == 'UNREGISTERED_QUALITY_MASK_BUNDLE_PREPARATION_ONLY' and verified:
                actual['report_bytes'] = b'POISON_AFTER_VALIDATION'
            return verified
        with patch.object(api,'prepare_quality_mask_bundle',return_value=parent),patch.object(api,'_same',side_effect=poison):
            result = self.complete()
        self.assertEqual(parent['report_bytes'],b'POISON_AFTER_VALIDATION')
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        self.assertEqual(result['report_bytes'],original_bytes)

    def test_report_quality_access_caller_declarations_not_rank_policy(self):
        self.image['access_class'] = 'RESTRICTED'; self.metadata['access_class'] = 'PUBLIC'
        result = self.complete()
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        self.assertEqual(result['image_manifest_draft']['access_class'],'RESTRICTED')
        self.assertEqual(result['report_manifest_draft']['access_class'],'PUBLIC')
        self.assertFalse(result['registry_registered']); self.assertFalse(result['quality_report_verified'])

    def test_actual_temp_complete_report_registry_and_131_133_consumer(self):
        result = self.complete()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); store = Store(root)
            source = self.fixture.fixture.fixture
            for manifest,index in ((result['image_manifest_draft'],0),(result['mask_manifest_draft'],2)):
                (root/manifest['artifact_uri']).write_bytes(source.paths[index].read_bytes())
            (root/result['report_manifest_draft']['artifact_uri']).write_bytes(result['report_bytes'])
            for manifest in (result['image_manifest_draft'],result['mask_manifest_draft'],result['report_manifest_draft']):
                register_version(store,manifest)
            refs = result['fixed_refs']; args = [store,refs['image_ref'],refs['quality_report_ref'],refs['mask_ref']]
            self.assertTrue(read_registered_quality_mask_files(*args)['artifact_bytes_verified'])
            observed = inspect_registered_binary_mask_values(*args)
            self.assertTrue(observed['mask_values_verified']); self.assertFalse(observed['scientific_accuracy_validated'])


if __name__ == '__main__': unittest.main()
