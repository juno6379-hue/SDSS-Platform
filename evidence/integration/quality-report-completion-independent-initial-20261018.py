"""Independent139: pure caller metadata completion and real Temp consumers."""
import ast
from contextlib import contextmanager, ExitStack
import copy
import hashlib
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
from app.data import quality_report_completion as api
from app.data.quality_mask_bundle import prepare_quality_mask_bundle
from app.dataset_registry import canonical_manifest, register_version
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store

ROOT=Path(__file__).resolve().parents[2]
SOURCE='backend/app/data/quality_report_completion.py'; TEST='tests/test_quality_report_completion.py'
SOURCE_SHA='0ef9c2930df1224eeb1f130b80b0dd15d799776d734cf713805abb08e05240e9'
TEST_SHA='21714a53670a15672fba44b0f4bfddaae8bbb503509c6bf86a9cbc2e62f4eb96'
BASE='200d22c3c7f146f795c26442eec1bd971733770d'
OLD=['backend/app/data/quality_mask_bundle.py','tests/test_quality_mask_bundle.py',
 'backend/app/dataset_registry.py','backend/app/ml/per_scene_normalization_files.py',
 'backend/app/ml/registered_quality_mask_files.py','backend/app/ml/registered_quality_mask_grid.py',
 'backend/app/ml/registered_binary_mask_values.py','scripts/collect_samples.py','scripts/collect_training_grid.py',
 'backend/app/main.py','frontend/src/AnnualInputDiagnostics.tsx']
PAYLOADS=('image_manifest_draft','mask_manifest_draft','report_manifest_draft','report_envelope','report_bytes','report_sha256','fixed_refs')
OBS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def snapshot(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def metadata(quality='STAGED',access='PUBLIC'):
    return {'source':{'institution':'명시 caller 🌏','product':'별도 보고서 제품 선언','license':'TEST ONLY',
      'source_uri':'https://example.invalid/metadata-is-not-fetched'},
      'spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':quality,'access_class':access}
def manifest(identifier,path,digest,mask=False,access='PUBLIC'):
    m={'schema_version':'0.2.0','dataset_id':identifier,'version':' 고정 🌏 v1 ',
      'source':{'institution':'명시 image/mask caller','product':'원본 제품 선언','license':'TEST ONLY','band_names':list(BAND_NAMES)},
      'data_type':'raster','spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':'RAW','access_class':access,'sha256':digest,'artifact_uri':path,'lineage':[]}
    if mask:m['source']['mask_semantics']={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
    return m
def inputs():return (manifest('영상 🌏','자료/image.tif','a'*64),manifest('mask 🌏','자료/mask.tif','b'*64,True),
 {'id':'보고서 🌏','version':' 고정 🌏 v1 ','artifact_uri':'자료/quality.json'},metadata())
def complete(*args):
    with ExitStack() as stack:
        guards=[]
        for name in ('builtins.open','io.open','os.open','pathlib.Path.open','pathlib.Path.stat','pathlib.Path.resolve'):
            guards.append(stack.enter_context(patch(name,side_effect=AssertionError('IO attempted'))))
        result=api.complete_quality_report(*args)
        for guard in guards:guard.assert_not_called()
        return result
@contextmanager
def ro(store):
    connection=sqlite3.connect(store.db.as_uri()+'?mode=ro',uri=True)
    try:yield connection
    finally:connection.close()

class Independent(unittest.TestCase):
    def test_01_frozen_sha_no_store_or_schema_io_imports(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA)
        self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)
        tree=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        imported=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imported.extend(n.name for n in node.names)
            if isinstance(node,ast.ImportFrom):imported.append(node.module)
        self.assertEqual(set(imported),{'hashlib','re','datetime','model_reference_contract','quality_mask_bundle'})
        names={node.id for node in ast.walk(tree) if isinstance(node,ast.Name)}
        self.assertFalse(names & {'Store','canonical_manifest','register_version','resolve_version','verify_artifact'})

    def test_02_exact_full_caller_metadata_and_detached_bytes(self):
        args=inputs();before=copy.deepcopy(args)
        with patch.object(api,'prepare_quality_mask_bundle',wraps=prepare_quality_mask_bundle) as parent:
            result=complete(*args)
        self.assertEqual(parent.call_count,1);self.assertEqual(len(result),21)
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        self.assertIsNone(result['issue']);self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
        report=result['report_manifest_draft'];self.assertEqual(len(report),12)
        self.assertEqual({k:report[k] for k in api.REQUIRED_REPORT_METADATA},args[3])
        self.assertEqual(report['quality_status'],'STAGED')
        self.assertEqual(result['report_envelope']['quality_status'],'RAW')
        self.assertEqual(report['source']['product'],'별도 보고서 제품 선언')
        self.assertNotEqual(report['source'],args[0]['source'])
        prepared=prepare_quality_mask_bundle(*before[:3])
        self.assertEqual(result['report_bytes'],prepared['report_bytes'])
        self.assertEqual(result['report_sha256'],sha(result['report_bytes']))
        self.assertEqual(result['fixed_refs'],prepared['fixed_refs'])
        self.assertEqual(args,before)
        result['report_manifest_draft']['source']['product']='mutated output'
        result['fixed_refs']['image_ref']['version']='mutated output'
        result['image_manifest_draft']['source']['product']='mutated output'
        self.assertEqual(args,before)

    def test_03_metadata_invalid_before_producer_noio(self):
        edits=[lambda m:m.pop('source'),lambda m:m.update(extra=1),lambda m:m.update(dataset_id='overwrite'),
          lambda m:m.update(quality_status='VALIDATED'),lambda m:m.update(access_class='APPROVED'),
          lambda m:m['source'].update(institution=''),lambda m:m['spatial'].update(bbox=[0,0,True,1]),
          lambda m:m['spatial'].update(bbox=[0,0,float('nan'),1]),lambda m:m['temporal'].update(start='2020-02-30T00:00:00Z'),
          lambda m:m['temporal'].update(end='2019-01-01T00:00:00Z'),lambda m:m['source'].update(product='\ud800'),
          lambda m:m['source'].update(product='x'*4097)]
        for edit in edits:
            args=list(inputs());edit(args[3]);before=repr(args)
            with patch.object(api,'prepare_quality_mask_bundle',side_effect=AssertionError('producer must not run')) as producer:
                result=complete(*args)
            producer.assert_not_called();self.assertEqual(result['status'],'BLOCKED')
            self.assertTrue(all(result[k] is None for k in PAYLOADS));self.assertEqual(repr(args),before)

    def test_04_untrusted_parent_typed_flags_refs_bytes_and_partial_failures(self):
        args=inputs();good=prepare_quality_mask_bundle(*args[:3])
        edits=[lambda p:p.update(extra='PRIVATE_PATH'),lambda p:p.update(schema_version=True),
          lambda p:p.update(execution_authorized=0),lambda p:p.update(quality_report_verified=True),
          lambda p:p.update(status='BLOCKED',issue={'code':'SECRET','field':'PRIVATE_PATH'}),
          lambda p:p.update(report_sha256='c'*64),lambda p:p.update(report_bytes=p['report_bytes']+b' '),
          lambda p:p.update(report_bytes=bytearray(p['report_bytes'])),lambda p:p.update(report_metadata_required=[]),
          lambda p:p['fixed_refs']['quality_report_ref'].update(id='other'),
          lambda p:p['report_manifest_patch']['lineage'].reverse(),
          lambda p:p['report_manifest_patch'].update(artifact_uri='wrong/q.json'),
          lambda p:p['image_manifest_draft'].update(access_class='CONFIDENTIAL'),
          lambda p:p['mask_manifest_draft']['source']['mask_semantics'].update(valid_value=True),
          lambda p:p['report_envelope'].update(schema_version=True),lambda p:p.update(fixed_refs=None)]
        for edit in edits:
            bad=copy.deepcopy(good);edit(bad)
            with patch.object(api,'prepare_quality_mask_bundle',return_value=bad):result=complete(*args)
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['issue'],{'code':'PREPARATION_OUTPUT_INVALID','field':'bundle'})
            self.assertTrue(all(result[k] is None for k in PAYLOADS));self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
            self.assertNotIn('PRIVATE_PATH',repr(result))
        class Key(str):
            calls=0
            def __hash__(self):return str.__hash__(self)
            def __eq__(self,other):Key.calls+=1;raise AssertionError('custom equality')
        bad={Key('schema_version') if k=='schema_version' else k:v for k,v in good.items()}
        with patch.object(api,'prepare_quality_mask_bundle',return_value=bad):result=complete(*args)
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(Key.calls,0)
        class Bad:
            calls=0
            def __eq__(self,other):Bad.calls+=1;raise AssertionError('custom equality')
        bad=copy.deepcopy(good);bad['report_envelope']['schema_version']=Bad()
        with patch.object(api,'prepare_quality_mask_bundle',return_value=bad):result=complete(*args)
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(Bad.calls,0)

    def test_05_producer_argument_mutation_cannot_change_verification_snapshot(self):
        args=inputs();before=copy.deepcopy(args)
        def corrupt(image,mask,identity):
            image['source']['product']='mutated producer argument';identity['id']='changed'
            return prepare_quality_mask_bundle(image,mask,identity)
        with patch.object(api,'prepare_quality_mask_bundle',side_effect=corrupt):result=complete(*args)
        self.assertEqual(result['status'],'BLOCKED');self.assertTrue(all(result[k] is None for k in PAYLOADS))
        self.assertEqual(args,before)
        for path in ('資料\\image.tif','../q.json','C:/q.json','資料//q.json'):
            i,m,r,meta=inputs();r['artifact_uri']=path
            if path=='資料\\image.tif':i['artifact_uri']='資料/image.tif'
            with patch.object(api,'prepare_quality_mask_bundle',side_effect=AssertionError('producer')) as parent:
                result=complete(i,m,r,meta)
            parent.assert_not_called();self.assertEqual(result['status'],'BLOCKED')

    def fixture(self,*,image_access='PUBLIC',report_access='PUBLIC',nodata=None,value=None):
        temp=tempfile.TemporaryDirectory(prefix='geoai-independent139-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();folder=root/'자료';folder.mkdir();ip=folder/'image.tif';mp=folder/'mask.tif'
        profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
        with rasterio.open(ip,'w',**profile,count=6,dtype='uint16',nodata=0) as dst:
            dst.write(np.ones((6,16,16),dtype='uint16'));dst.descriptions=tuple(BAND_NAMES)
        values=(np.indices((16,16)).sum(axis=0)%2).astype('uint8')
        if value is not None:values[:]=value
        with rasterio.open(mp,'w',**profile,count=1,dtype='uint8',nodata=nodata) as dst:dst.write(values,1)
        image=manifest('실제 영상','자료/image.tif',sha(ip.read_bytes()),access=image_access)
        mask=manifest('실제 mask','자료/mask.tif',sha(mp.read_bytes()),True)
        meta=metadata('STAGED',report_access);before=copy.deepcopy((image,mask,meta))
        result=complete(image,mask,{'id':'실제 품질','version':' 고정 🌏 v1 ','artifact_uri':'자료/quality.json'},meta)
        self.assertEqual(result['status'],'UNREGISTERED_REPORT_MANIFEST_PREPARED')
        self.assertEqual((image,mask,meta),before);self.assertEqual(result['image_manifest_draft']['access_class'],image_access)
        self.assertEqual(result['report_manifest_draft']['access_class'],report_access)
        (folder/'quality.json').write_bytes(result['report_bytes'])
        store=Store(root,recover_jobs=False)
        for key in ('image_manifest_draft','mask_manifest_draft','report_manifest_draft'):
            draft=result[key];canonical,digest=canonical_manifest(draft)
            record=register_version(store,draft);self.assertEqual(record['manifest'],canonical)
            self.assertEqual(record['manifest_sha256'],digest)
        return root,store,result

    def test_06_actual_temp_complete_manifest_schema_sqlite_consumption(self):
        root,store,bundle=self.fixture();before=snapshot(root);refs=bundle['fixed_refs'];args=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'))
        with patch.object(store,'connect',lambda:ro(store)),patch.object(store,'put',side_effect=AssertionError('write')),patch.object(store,'get',wraps=store.get) as get:
            report=read_registered_quality_mask_files(store,*args)
            values=inspect_registered_binary_mask_values(store,*args)
        self.assertEqual(report['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED');self.assertEqual(get.call_count,6)
        self.assertEqual(values['status'],'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
        self.assertEqual(values['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256})
        for result in (bundle,report,values):
            self.assertIs(result['scientific_accuracy_validated'],False);self.assertIs(result['execution_authorized'],False)
            self.assertIs(result['quality_report_verified'],False);self.assertIs(result['quality_mask_verified'],False)
        self.assertIs(values['mask_semantics_verified'],False);self.assertEqual(snapshot(root),before)
        OBS.append({'actual':'fresh Temp GTiff image6/mask1 +complete caller-metadata report +SQLite3versions',
          'fixture_registry_setup_writes':3,'readonly_consumer_gets':6,'counts':values['counts'],
          'source_quality':'RAW','report_quality':'STAGED','files_and_db_unchanged':True,'approval':False})

    def test_07_preparation_is_not_access_quality_or_mask_conversion(self):
        for case,options,code in [('restricted_image_public_report',{'image_access':'RESTRICTED','report_access':'PUBLIC'},'ACCESS_DECLARATION_BLOCKED'),
          ('nodata0',{'nodata':0},'MASK_INTRINSIC_VALIDITY_UNSUPPORTED'),('value255',{'value':255},'MASK_VALUES_NOT_BINARY')]:
            root,store,bundle=self.fixture(**options);before=snapshot(root);refs=bundle['fixed_refs']
            with patch.object(store,'connect',lambda:ro(store)),patch.object(store,'put',side_effect=AssertionError('write')):
                result=inspect_registered_binary_mask_values(store,*(refs[k] for k in ('image_ref','quality_report_ref','mask_ref')))
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['issue']['code'],code)
            self.assertIsNone(result['counts']);self.assertIs(result['execution_authorized'],False)
            self.assertEqual(snapshot(root),before)
            OBS.append({'counterexample':case,'completion_prepared':True,'consumer':'BLOCKED','code':code,
              'image_access_preserved':bundle['image_manifest_draft']['access_class'],
              'explicit_report_access_preserved':bundle['report_manifest_draft']['access_class'],
              'files_and_db_unchanged':True,'approval':False})

if __name__=='__main__':
    previous={p:sha((ROOT/p).read_bytes()) for p in OLD}
    matches={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==h for p,h in previous.items()}
    start=time.perf_counter();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent));seconds=time.perf_counter()-start
    stable={p:sha((ROOT/p).read_bytes())==h for p,h in previous.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_EXPLICIT_QUALITY_REPORT_COMPLETION_TEMP_ONLY',
      'status':'TESTED_SYNTHETIC' if result.wasSuccessful() else 'FAILED','tests':result.testsRun,
      'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'skipped':len(result.skipped),
      'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
      'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),
      'git_baseline':BASE,'separate_git_baseline_matches':matches,'old_sources_unchanged':stable,
      'observations':OBS,'actual_scope':'fresh Temp files, complete manifest96schema, actual SQLite version setup then readonlySQL131/133 consumption',
      'mock_scope':'I/O/write denial guards, producer call counter and explicitly malformed/argument-mutating138 parent only; no mocked successful131/133 responses',
      'operating_data_access':False,'operating_writes':0,'training':0,'inference':0,'api_ui_changed':False,
      'frontend_build_browser_required':False,'limitations':['Pure completion preserves caller statements; no report/image QA equality or cross-access authority policy is verified.',
       'Synthetic registration occurs only during explicit Temp fixture setup, not in product completion.',
       '128/256 is observed binary count, not scientific or institutional approval.',
       'Legacy nodata0 and label/AOI-derived masks, actual production/registration/approval remain separate.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(matches.values()) and all(stable.values()) else 1)
