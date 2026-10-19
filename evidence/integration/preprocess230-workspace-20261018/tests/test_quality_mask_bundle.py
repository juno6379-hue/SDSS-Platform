"""Pure bundle drafts plus explicitly completed Temp consumer registration."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import quality_mask_bundle as api
from app.dataset_registry import canonical_manifest, register_version
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.store import Store
import test_registered_quality_mask_grid as fixtures


class QualityMaskBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fixtures.RegisteredQualityMaskGridTests(); cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups)

    def setUp(self):
        f = self.fixture.fixture
        self.image = copy.deepcopy(f.manifests[0]); self.mask = copy.deepcopy(f.manifests[2])
        self.mask['source']['mask_semantics'] = {'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
        self.identity = {'id':'quality','version':' v1 ','artifact_uri':'quality.json'}

    def prepare(self):
        return api.prepare_quality_mask_bundle(self.image,self.mask,self.identity)

    def test_exact22_envelope_patch7_bytes_sha_metadata_required_and_ten_false(self):
        result = self.prepare()
        self.assertEqual(len(result),22); self.assertEqual(result['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        self.assertEqual(set(result['report_envelope']),{'schema_version','scope','image_ref','mask_ref','quality_status'})
        self.assertEqual(len(result['report_manifest_patch']),7)
        self.assertEqual(result['report_metadata_required'],['source','spatial','temporal','quality_status','access_class'])
        self.assertEqual(result['report_bytes'],json.dumps(result['report_envelope'],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode())
        self.assertEqual(result['report_sha256'],hashlib.sha256(result['report_bytes']).hexdigest())
        self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))
        for field in api.REQUIRED_REPORT_METADATA: self.assertNotIn(field,result['report_manifest_patch'])
        self.assertEqual(result['fixed_refs']['quality_report_ref']['version'],' v1 ')

    def test_pure_call_no_files_store_network_model_import_and_inputs_detached(self):
        before = copy.deepcopy((self.image,self.mask,self.identity))
        with (patch('builtins.open',side_effect=AssertionError('no open')),
              patch.object(Path,'stat',side_effect=AssertionError('no stat')),
              patch.object(Path,'resolve',side_effect=AssertionError('no resolve')),
              patch.object(Store,'get',side_effect=AssertionError('no get')),
              patch.object(Store,'put',side_effect=AssertionError('no put')),
              patch('app.dataset_registry.canonical_manifest',side_effect=AssertionError('no cold schema'))):
            result = self.prepare()
        self.assertEqual(result['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        self.assertEqual((self.image,self.mask,self.identity),before)
        result['image_manifest_draft']['source']['institution'] = 'changed'
        result['mask_manifest_draft']['source']['mask_semantics']['valid_value'] = 100
        result['fixed_refs']['image_ref']['id'] = 'changed'
        self.assertEqual((self.image,self.mask,self.identity),before)

    def test_raw_staged_only_no_access_or_quality_promotion(self):
        for image_quality in ('RAW','STAGED'):
            for mask_quality in ('RAW','STAGED'):
                self.image['quality_status'] = image_quality; self.mask['quality_status'] = mask_quality
                self.mask['access_class'] = 'RESTRICTED'
                result = self.prepare(); self.assertEqual(result['report_envelope']['quality_status'],image_quality)
                self.assertEqual(result['mask_manifest_draft']['access_class'],'RESTRICTED')
        for value in ('STANDARDIZED','VALIDATED','REJECTED',None,True):
            self.mask['quality_status'] = value
            self.assertEqual(self.prepare()['status'],'BLOCKED')

    def test_explicit_semantics_missing_extra_bool_or_scl_never_inferred(self):
        for semantics in (None,{}, {'schema_version':True,'kind':'binary_validity','valid_value':1,'invalid_value':0},
            {'schema_version':1,'kind':'binary_validity','valid_value':True,'invalid_value':False},
            {'schema_version':1,'kind':'SCL','valid_value':1,'invalid_value':0},
            {'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0,'extra':0}):
            self.mask['source'].pop('mask_semantics',None)
            if semantics is not None: self.mask['source']['mask_semantics'] = semantics
            self.assertEqual(self.prepare()['issue']['code'],'MASK_SEMANTICS_INVALID')

    def test_report_reference_conflict_safe_relative_paths_and_distinct_keys(self):
        for path in ('../report.json','/report.json','https://x/report','C:\\report.json','a//b.json','a/./b.json','a./b.json','a /b.json'):
            self.identity['artifact_uri'] = path
            self.assertEqual(self.prepare()['status'],'BLOCKED')
        self.identity['artifact_uri'] = self.image['artifact_uri']
        self.assertEqual(self.prepare()['issue']['code'],'REFERENCE_CONFLICT')
        self.identity['artifact_uri'] = 'other.json'
        self.assertEqual(self.prepare()['issue']['code'],'QUALITY_REPORT_REF_CONFLICT')
        self.identity['artifact_uri'] = 'quality.json'; self.identity['id'] = self.image['dataset_id']
        self.assertEqual(self.prepare()['issue']['code'],'REFERENCE_CONFLICT')

    def test_normalized_path_equality_preserves_explicit_original_and_image_mask_alias(self):
        self.image['quality_report_ref'] = 'reports\\quality.json'; self.identity['artifact_uri'] = 'reports/quality.json'
        result = self.prepare(); self.assertEqual(result['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        self.assertEqual(result['image_manifest_draft']['quality_report_ref'],'reports/quality.json')
        self.mask['artifact_uri'] = self.image['artifact_uri']; self.mask['sha256'] = self.image['sha256']
        self.assertEqual(self.prepare()['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        self.assertFalse(self.prepare()['artifact_bytes_verified'])

    def test_strict_builtin_bounded_tree_and_optional_mask_quality_ref(self):
        for value in (float('nan'),float('inf'),2**53,'\ud800'):
            self.mask['source']['extra'] = value
            self.assertEqual(self.prepare()['status'],'BLOCKED')
        self.mask['source'].pop('extra')
        cycle = {}; cycle['same'] = cycle; self.mask['source']['extra'] = cycle
        self.assertEqual(self.prepare()['status'],'BLOCKED'); self.mask['source'].pop('extra')
        for value in (123,True,'../not-safe.json'):
            self.mask['quality_report_ref'] = value
            self.assertEqual(self.prepare()['status'],'BLOCKED')
        self.mask.pop('quality_report_ref',None)
        deep = {}
        for _ in range(18): deep = {'child':deep}
        self.mask['source']['extra'] = deep; self.assertEqual(self.prepare()['status'],'BLOCKED')
        self.mask['source']['extra'] = 'x'*4097; self.assertEqual(self.prepare()['status'],'BLOCKED')
        class Custom(dict): pass
        self.assertEqual(api.prepare_quality_mask_bundle(Custom(self.image),self.mask,self.identity)['status'],'BLOCKED')

    def test_manifest_subset_shapes_types_dates_and_upstream_compatible_drafts(self):
        for value in (None,'',True):
            old = self.image['source']['institution']; self.image['source']['institution'] = value
            self.assertEqual(self.prepare()['status'],'BLOCKED'); self.image['source']['institution'] = old
        for bbox in ([True,0,1,2],[100,-10,90,0],[100,-91,110,0],[100,0,float('nan'),1]):
            old = self.image['spatial']['bbox']; self.image['spatial']['bbox'] = bbox
            self.assertEqual(self.prepare()['status'],'BLOCKED'); self.image['spatial']['bbox'] = old
        self.image['temporal']['start'] = '2020-02-30T00:00:00Z'; self.assertEqual(self.prepare()['status'],'BLOCKED')
        self.image['temporal']['start'] = '2020-01-01T00:00:00Z'
        result = self.prepare()
        for manifest in (result['image_manifest_draft'],result['mask_manifest_draft']): canonical_manifest(manifest)
        with self.assertRaises(ValueError): canonical_manifest(result['report_manifest_patch'])

    def test_explicit_caller_report_metadata_temp_register_and_131_133_consume(self):
        result = self.prepare(); self.assertEqual(result['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); store = Store(root)
            for manifest,index in ((result['image_manifest_draft'],0),(result['mask_manifest_draft'],2)):
                (root/manifest['artifact_uri']).write_bytes(self.fixture.fixture.paths[index].read_bytes())
            (root/result['report_manifest_patch']['artifact_uri']).write_bytes(result['report_bytes'])
            caller = {'source':{'institution':'EXPLICIT_TEST_REPORT_CALLER','product':'EXPLICIT_TEST_REPORT','license':'TEST_ONLY'},
                'spatial':{'crs':'EPSG:4326','bbox':[100,-10,110,0]},
                'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T00:00:00Z','calendar':'gregorian'},
                'quality_status':'RAW','access_class':'PUBLIC'}
            complete_report = {**caller,**result['report_manifest_patch']}
            for manifest in (result['image_manifest_draft'],result['mask_manifest_draft'],complete_report): register_version(store,manifest)
            refs = result['fixed_refs']; args = [store,refs['image_ref'],refs['quality_report_ref'],refs['mask_ref']]
            self.assertTrue(read_registered_quality_mask_files(*args)['artifact_bytes_verified'])
            observed = inspect_registered_binary_mask_values(*args)
            self.assertTrue(observed['mask_values_verified']); self.assertEqual(observed['counts']['total_pixels'],256)
            self.assertFalse(observed['quality_mask_verified'])


if __name__ == '__main__':
    unittest.main()
