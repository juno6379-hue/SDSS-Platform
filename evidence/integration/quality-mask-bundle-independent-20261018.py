"""Independent138: pure preparation vs actual temporary registered consumption."""
import ast
from contextlib import contextmanager, ExitStack
import copy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.data import quality_mask_bundle as api
from app.dataset_registry import canonical_manifest, register_version, version_key
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.store import Store

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_suffix('.json')
SOURCE='backend/app/data/quality_mask_bundle.py'
TEST='tests/test_quality_mask_bundle.py'
EXPECTED_SOURCE='72750fe9f1299a878a589e66ac1e0d53b01eddfc3af6237915e6e16bce623945'
EXPECTED_TEST='1bfa06a5a21346af4c8d30390c6deaaf4690138eced2e6e99eccf46c5c70ffa6'
OLD=['backend/app/dataset_registry.py','backend/app/ml/per_scene_normalization_files.py',
 'backend/app/ml/registered_quality_mask_files.py','backend/app/ml/registered_quality_mask_grid.py',
 'backend/app/ml/registered_binary_mask_values.py','scripts/collect_samples.py','scripts/collect_training_grid.py',
 'backend/app/main.py','frontend/src/AnnualInputDiagnostics.tsx']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def manifest(identifier,path,digest,*,mask=False,quality='RAW',access='PUBLIC'):
    source={'institution':'EXPLICIT SYNTHETIC TEST CALLER','product':'test-only product not authority',
      'license':'test-only','scene_id':'explicit-scene','band_names':list(BAND_NAMES)}
    if mask:source['mask_semantics']={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
    return {'schema_version':'0.2.0','dataset_id':identifier,'version':' 고정 🌏 v1 ',
      'source':source,'data_type':'raster','spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':quality,'access_class':access,'sha256':digest,'artifact_uri':path,'lineage':[]}
def declarations():return (manifest('영상 🌏','입력/image.tif','a'*64),
 manifest('마스크 🌏','입력/mask.tif','b'*64,mask=True,quality='STAGED'),
 {'id':'품질 🌏','version':' 고정 🌏 v1 ','artifact_uri':'입력/quality.json'})
def noio(image,mask,identity):
    with ExitStack() as stack:
        guards=[]
        for owner,name in [('builtins','open'),('io','open'),('os','open'),
          ('pathlib.Path','open'),('pathlib.Path','stat'),('pathlib.Path','resolve')]:
            guards.append(stack.enter_context(patch(owner+'.'+name,side_effect=AssertionError('preparer performed IO'))))
        result=api.prepare_quality_mask_bundle(image,mask,identity)
        for guard in guards:guard.assert_not_called()
        return result
@contextmanager
def readonly_connect(store):
    connection=sqlite3.connect(store.db.as_uri()+'?mode=ro',uri=True)
    try:yield connection
    finally:connection.close()

class Independent(unittest.TestCase):
    def test_01_frozen_sources_and_pure_import_boundary(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),EXPECTED_SOURCE)
        self.assertEqual(sha((ROOT/TEST).read_bytes()),EXPECTED_TEST)
        tree=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(n.name for n in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertEqual(set(imports),{'hashlib','json','math','re','datetime','model_reference_contract'})
        for forbidden in ('Store','canonical_manifest','register_version','resolve_version','verify_artifact'):
            self.assertNotIn(forbidden,{node.id for node in ast.walk(tree) if isinstance(node,ast.Name)})

    def test_02_exact_detached_bytes_unicode_patch_and_noio(self):
        image,mask,identity=declarations();original=copy.deepcopy((image,mask,identity))
        result=noio(image,mask,identity)
        self.assertEqual(len(result),22);self.assertEqual(result['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        self.assertIsNone(result['issue']);self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
        self.assertEqual(tuple(result['report_metadata_required']),('source','spatial','temporal','quality_status','access_class'))
        self.assertEqual(len(result['report_manifest_patch']),7)
        raw=json.dumps(result['report_envelope'],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
        self.assertEqual(result['report_bytes'],raw);self.assertEqual(result['report_sha256'],sha(raw))
        self.assertEqual(result['fixed_refs']['quality_report_ref']['sha256'],sha(raw))
        self.assertIn('품질',result['fixed_refs']['quality_report_ref']['id'])
        self.assertEqual(result['fixed_refs']['image_ref']['version'],' 고정 🌏 v1 ')
        self.assertNotIn('source',result['report_manifest_patch']);self.assertNotIn('quality_status',result['report_manifest_patch'])
        self.assertEqual(result['report_envelope']['quality_status'],'RAW')
        self.assertEqual(result['mask_manifest_draft']['quality_status'],'STAGED')
        self.assertEqual((image,mask,identity),original)
        result['image_manifest_draft']['source']['product']='changed output'
        result['mask_manifest_draft']['source']['mask_semantics']['valid_value']=0
        result['fixed_refs']['image_ref']['id']='changed output'
        self.assertEqual((image,mask,identity),original)
        again=noio(*original)
        reversed_image=dict(reversed(list(image.items())))
        self.assertEqual(noio(reversed_image,mask,identity)['report_bytes'],again['report_bytes'])

    def test_03_invalid_identity_alias_paths_optional_fields_fail_closed_noio(self):
        edits=[lambda i,m,r:r.update(version=' Current '),lambda i,m,r:r.update(extra=1),
          lambda i,m,r:r.update(id=i['dataset_id'],version=i['version']),
          lambda i,m,r:m.update(dataset_id=i['dataset_id'],version=i['version']),
          lambda i,m,r:r.update(artifact_uri='입력\\image.tif'),
          lambda i,m,r:r.update(artifact_uri='../quality.json'),lambda i,m,r:r.update(artifact_uri='C:/quality.json'),
          lambda i,m,r:r.update(artifact_uri='https://example.invalid/q'),lambda i,m,r:r.update(artifact_uri='x//q'),
          lambda i,m,r:r.update(artifact_uri='x/./q'),lambda i,m,r:r.update(artifact_uri='x /q.'),
          lambda i,m,r:i.update(quality_report_ref='different/q.json'),
          lambda i,m,r:m.update(quality_report_ref=123),lambda i,m,r:m.update(quality_report_ref='../q.json'),
          lambda i,m,r:i.update(sha256='A'*64),lambda i,m,r:m.update(quality_status='VALIDATED'),
          lambda i,m,r:m['source'].pop('mask_semantics'),
          lambda i,m,r:m['source']['mask_semantics'].update(valid_value=True),
          lambda i,m,r:m['source']['mask_semantics'].update(extra=1),
          lambda i,m,r:i.update(version='latest'),lambda i,m,r:r.update(id='\ud800'),
          lambda i,m,r:i['spatial'].update(bbox=[0,0,True,1]),
          lambda i,m,r:i['spatial'].update(bbox=[0,0,float('nan'),1]),
          lambda i,m,r:i['temporal'].update(start='2020-02-30T00:00:00Z')]
        for edit in edits:
            with self.subTest(edit=edits.index(edit)):
                i,m,r=declarations();edit(i,m,r);before=copy.deepcopy((i,m,r));result=noio(i,m,r)
                self.assertEqual(result['status'],'BLOCKED');self.assertIsNone(result['report_bytes'])
                self.assertIsNone(result['fixed_refs']);self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
                # NaN is not equal to its copy, so compare bounded serialization for that case.
                self.assertEqual(repr((i,m,r)),repr(before))

    def test_04_bounded_custom_types_cycles_and_no_callbacks(self):
        class Poison:
            calls=0
            def __str__(self):Poison.calls+=1;raise AssertionError('coercion')
            def __eq__(self,other):Poison.calls+=1;raise AssertionError('equality')
        for kind in ('custom','cycle','deep','large','many','int','surrogate'):
            i,m,r=declarations()
            if kind=='custom':i['source']['extension']=Poison()
            elif kind=='cycle':i['source']['extension']=i
            elif kind=='deep':
                v=0
                for _ in range(18):v=[v]
                i['source']['extension']=v
            elif kind=='large':i['source']['extension']='x'*4097
            elif kind=='many':i['source']['extension']=list(range(1025))
            elif kind=='int':i['source']['extension']=2**54
            else:i['source']['extension']='\ud800'
            result=noio(i,m,r);self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(Poison.calls,0)

    def fixture(self,*,nodata=None,mask_value=None,access='PUBLIC'):
        temp=tempfile.TemporaryDirectory(prefix='geoai-independent138-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();folder=root/'입력';folder.mkdir()
        imagepath=folder/'image.tif';maskpath=folder/'mask.tif';profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
        with rasterio.open(imagepath,'w',**profile,count=6,dtype='uint16',nodata=0) as target:
            target.write(np.ones((6,16,16),dtype='uint16'))
            target.descriptions=tuple(BAND_NAMES)
        values=(np.indices((16,16)).sum(axis=0)%2).astype('uint8')
        if mask_value is not None:values[:]=mask_value
        with rasterio.open(maskpath,'w',**profile,count=1,dtype='uint8',nodata=nodata) as target:target.write(values,1)
        image=manifest('실제 임시 영상','입력/image.tif',sha(imagepath.read_bytes()),access=access)
        mask=manifest('실제 임시 mask','입력/mask.tif',sha(maskpath.read_bytes()),mask=True,quality='STAGED',access=access)
        result=noio(image,mask,{'id':'실제 임시 품질','version':' 고정 🌏 v1 ','artifact_uri':'입력/quality.json'})
        self.assertEqual(result['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        (folder/'quality.json').write_bytes(result['report_bytes'])
        # Explicit TEST CALLER metadata, not inferred or produced by the preparer.
        report={**result['report_manifest_patch'],
          'source':{'institution':'EXPLICIT INDEPENDENT SYNTHETIC TEST CALLER','product':'explicit declared test report','license':'test-only'},
          'spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
          'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
          'quality_status':'RAW','access_class':access}
        store=Store(root,recover_jobs=False)
        for draft in (result['image_manifest_draft'],result['mask_manifest_draft'],report):
            expected,digest=canonical_manifest(draft);record=register_version(store,draft)
            self.assertEqual(record['manifest'],expected);self.assertEqual(record['manifest_sha256'],digest)
        return root,store,result

    def test_05_actual_temp_gtiff_sqlite_consumer131_and133_128of256_no_writes(self):
        root,store,bundle=self.fixture();before=files(root);refs=bundle['fixed_refs'];args=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'))
        with patch.object(store,'connect',lambda:readonly_connect(store)),patch.object(store,'put',side_effect=AssertionError('write')),patch.object(store,'get',wraps=store.get) as get:
            consumed=read_registered_quality_mask_files(store,*args)
            self.assertEqual(consumed['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
            self.assertEqual(get.call_count,3)
            counted=inspect_registered_binary_mask_values(store,*args)
            self.assertEqual(get.call_count,6)
        self.assertEqual(counted['status'],'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
        self.assertEqual(counted['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256})
        for value in (bundle,consumed,counted):
            self.assertIs(value['quality_report_verified'],False);self.assertIs(value['quality_mask_verified'],False)
            self.assertIs(value['scientific_accuracy_validated'],False);self.assertIs(value['execution_authorized'],False)
        self.assertIs(counted['mask_semantics_verified'],False)
        self.assertIs(counted['minimum_validity_policy_verified'],False)
        self.assertEqual(files(root),before)
        OBSERVATIONS.append({'fixture':'actual fresh TempStore SQLite +6bandGTiff+checkerboardGTiff+reportbytes',
          'registry_fixture_setup_writes':3,'consumer_gets':6,'counts':counted['counts'],
          'source_manifest_quality':'RAW','mask_manifest_quality':'STAGED','database_and_all_files_unchanged_after_consumption':True,
          'preparer_registry_or_file_operations':0,'scientific_accuracy_validated':False,'execution_authorized':False})

    def test_06_preparation_is_not_existing_mask_conversion_or_access_approval(self):
        for case,options,expected in [('nodata0',{'nodata':0},'MASK_INTRINSIC_VALIDITY_UNSUPPORTED'),
          ('value255',{'mask_value':255},'MASK_VALUES_NOT_BINARY'),
          ('restricted',{'access':'RESTRICTED'},'ACCESS_DECLARATION_BLOCKED')]:
            root,store,bundle=self.fixture(**options);before=files(root);refs=bundle['fixed_refs']
            with patch.object(store,'connect',lambda:readonly_connect(store)),patch.object(store,'put',side_effect=AssertionError('write')):
                result=inspect_registered_binary_mask_values(store,*(refs[k] for k in ('image_ref','quality_report_ref','mask_ref')))
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['issue']['code'],expected)
            self.assertIsNone(result['counts']);self.assertIs(result['execution_authorized'],False)
            self.assertEqual(files(root),before)
            OBSERVATIONS.append({'counterexample':case,'prepared':True,'consumer_status':'BLOCKED','issue':expected,'all_files_unchanged':True})

    def test_07_original_inputs_and_registered_version_not_silently_changed(self):
        i,m,r=declarations();i['artifact_uri']='입력\\image.tif';r['artifact_uri']='입력\\quality.json';i['quality_report_ref']='입력/quality.json'
        result=noio(i,m,r)
        self.assertEqual(result['image_manifest_draft']['quality_report_ref'],r['artifact_uri'])
        self.assertEqual(result['report_manifest_patch']['artifact_uri'],r['artifact_uri'])
        self.assertEqual(i['quality_report_ref'],'입력/quality.json')
        # Same URI/SHA aliases remain declarations, not a physical mask guarantee.
        m['artifact_uri']=i['artifact_uri'];m['sha256']=i['sha256']
        alias=noio(i,m,r);self.assertEqual(alias['status'],'REPORT_METADATA_REQUIRED_UNREGISTERED')
        self.assertIs(alias['artifact_bytes_verified'],False);self.assertIs(alias['registry_registered'],False)

OBSERVATIONS=[]
if __name__=='__main__':
    baseline=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,check=True,text=True).stdout.strip()
    previous={p:sha((ROOT/p).read_bytes()) for p in OLD}
    git_matches={p:sha(subprocess.run(['git','show',baseline+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==digest for p,digest in previous.items()}
    start=time.perf_counter();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Independent)
    result=unittest.TextTestRunner(verbosity=2).run(suite);elapsed=time.perf_counter()-start
    stable={p:sha((ROOT/p).read_bytes())==digest for p,digest in previous.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_QUALITY_MASK_BUNDLE_TEMP_FIXTURES_ONLY',
      'status':'TESTED_SYNTHETIC' if result.wasSuccessful() else 'FAILED','tests_run':result.testsRun,
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
      'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'elapsed_seconds':elapsed,'seconds':elapsed,
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),
      'git_baseline':baseline,'separate_git_baseline_matches':git_matches,'existing_source_unchanged':stable,
      'observations':OBSERVATIONS,'fixture_scope':{'actual':'fresh temporary GTiff files/report bytes and SQLite DatasetVersion registry; readonly SQL consumption',
       'mocked':'I/O denial guards, write denial guards, call counters and custom type poison only; no mocked successful consumer responses'},
      'operating_data_access':False,'operating_writes':0,'training':0,'inference':0,
      'api_or_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Producer prepares bytes/drafts only; explicit test caller supplies missing report metadata.',
       'TempStore registration setup is synthetic fixture creation, not preparation or operating registration.',
       '128/256 is binary syntax/count evidence, not semantic quality, scientific accuracy, or a minimum policy approval.',
       'Legacy nodata=0, missing image descriptions and label/AOI-combined collector masks remain unresolved.',
       'No source files, old tests, operating data, main or UI were edited.']}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(stable.values()) and all(git_matches.values()) else 1)
