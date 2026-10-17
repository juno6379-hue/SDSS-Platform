"""Independent141 read-only stored-file preflight, explicit Temp fixtures only."""
import ast
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from jsonschema import Draft202012Validator, FormatChecker
from app.data import quality_report_preflight as api
from app.data.quality_report_storage import write_quality_report_files
from app.data.quality_report_completion import complete_quality_report
from app.dataset_registry import canonical_manifest, register_version, manifest_validator
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store

ROOT=Path(__file__).resolve().parents[2]
SOURCE='backend/app/data/quality_report_preflight.py';TEST='tests/test_quality_report_preflight.py'
SOURCE_SHA='04758b1ac3e03fb392790e2c0c7d87aa261a9563b160d704cbf06023af09e62a'
TEST_SHA='3b4dbf91d37a183cfa282c86a122d0755eae1ae615383a7eb0a303eee91a9a41'
BASE='c2165340a1d5f1cfd253f13bcf9603c843d526d0'
OLD=['backend/app/data/quality_report_storage.py','tests/test_quality_report_storage.py',
 'backend/app/data/quality_report_completion.py','backend/app/data/quality_mask_bundle.py','backend/app/dataset_registry.py',
 'backend/app/ml/registered_quality_mask_files.py','backend/app/ml/registered_quality_mask_grid.py',
 'backend/app/ml/registered_binary_mask_values.py','backend/app/main.py','frontend/src/AnnualInputDiagnostics.tsx']
PAYLOAD=('report_output_uri','manifest_output_uri','report_sha256','manifest_sha256','fixed_refs','report_manifest_draft')
OBS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def metadata(access='PUBLIC'):
    return {'source':{'institution':'명시 테스트 caller','product':'별도 보고서 선언 🌏','license':'TEST ONLY'},
      'spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':'STAGED','access_class':access}
def manifest(identifier,path,digest,mask=False,access='PUBLIC'):
    source={'institution':'명시 테스트 source','product':'별도 영상/mask 선언','license':'TEST ONLY','band_names':list(BAND_NAMES)}
    if mask:source['mask_semantics']={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
    return {'schema_version':'0.2.0','dataset_id':identifier,'version':' 고정 🌏 v1 ','source':source,
      'data_type':'raster','spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':'RAW','access_class':access,'sha256':digest,'artifact_uri':path,'lineage':[]}
@contextmanager
def ro(store):
    c=sqlite3.connect(store.db.as_uri()+'?mode=ro',uri=True)
    try:yield c
    finally:c.close()

class Independent(unittest.TestCase):
    def fixture(self,*,actual=False,nodata=None,access='PUBLIC',meta=None):
        t=tempfile.TemporaryDirectory(prefix='geoai-independent141-');self.addCleanup(t.cleanup)
        root=Path(t.name).resolve();(root/'입력').mkdir();(root/'출력').mkdir()
        image=root/'입력/image.tif';mask=root/'입력/mask.tif'
        if actual:
            profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
            with rasterio.open(image,'w',**profile,count=6,dtype='uint16',nodata=0) as dst:
                dst.write(np.ones((6,16,16),dtype='uint16'));dst.descriptions=tuple(BAND_NAMES)
            with rasterio.open(mask,'w',**profile,count=1,dtype='uint8',nodata=nodata) as dst:
                dst.write((np.indices((16,16)).sum(axis=0)%2).astype('uint8'),1)
        else:image.write_bytes(b'OPAQUE IMAGE DECLARATION NOT READ BY PREFLIGHT');mask.write_bytes(b'OPAQUE MASK DECLARATION NOT READ BY PREFLIGHT')
        i=manifest('영상 🌏','입력/image.tif',sha(image.read_bytes()),access=access);i['quality_report_ref']='출력/quality.json'
        m=manifest('mask 🌏','입력/mask.tif',sha(mask.read_bytes()),True)
        identity={'id':'품질 🌏','version':' 고정 🌏 v1 ','artifact_uri':'출력/quality.json'}
        args=(root,i,m,identity,metadata() if meta is None else meta,'출력/manifest.json')
        result=write_quality_report_files(*args);self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED')
        return args

    def inspect(self,args):
        opens=[];attempts=[];original=os.open
        def guarded(path,flags,*rest,**kwargs):
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                attempts.append(str(path));raise AssertionError('preflight attempted write')
            opens.append(Path(path).relative_to(args[0]).as_posix());return original(path,flags,*rest,**kwargs)
        with (patch.object(api.os,'open',side_effect=guarded),patch.object(Path,'mkdir',side_effect=AssertionError('mkdir')) as mkdir,
             patch.object(Path,'unlink',side_effect=AssertionError('unlink')) as unlink,
             patch.object(api.os,'remove',side_effect=AssertionError('remove')) as remove):
            value=api.inspect_stored_quality_report(*args)
        self.assertEqual(attempts,[]);mkdir.assert_not_called();unlink.assert_not_called();remove.assert_not_called()
        return value,opens

    def empty(self,result,code=None):
        self.assertEqual(len(result),23);self.assertEqual(result['status'],'BLOCKED')
        self.assertTrue(all(result[k] is None for k in PAYLOAD))
        self.assertFalse(result['stored_report_files_verified']);self.assertFalse(result['manifest_schema_verified'])
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
        self.assertEqual(result['files'],[{'role':role,'verified':False,'bytes':None} for role in ('report','manifest')])
        if code:self.assertEqual(result['issue']['code'],code)

    def test_01_frozen_sources_and_readonly_import_scope(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA);self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)
        tree=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
        self.assertFalse(names & {'Store','register_version','write_quality_report_files','rasterio','torch'})

    def test_02_actual140_files141_schema_then_fixture_registry_readonly_consumption(self):
        args=self.fixture(actual=True);root=args[0];before=files(root);caller=copy.deepcopy(args[1:])
        with (patch.object(api,'complete_quality_report',wraps=complete_quality_report) as producer,
             patch.object(api,'canonical_manifest',wraps=canonical_manifest) as schema):
            result,opens=self.inspect(args)
        self.assertEqual(producer.call_count,1);self.assertEqual(schema.call_count,1)
        self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED');self.assertEqual(len(result),23)
        self.assertTrue(result['stored_report_files_verified']);self.assertTrue(result['manifest_schema_verified'])
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
        self.assertEqual(opens,['출력/quality.json','출력/manifest.json']);self.assertEqual(files(root),before);self.assertEqual(args[1:],caller)
        completion=complete_quality_report(*args[1:5]);self.assertEqual(result['report_manifest_draft'],completion['report_manifest_draft'])
        self.assertEqual(result['report_sha256'],sha((root/args[3]['artifact_uri']).read_bytes()))
        self.assertEqual(result['manifest_sha256'],sha((root/args[5]).read_bytes()))
        result['report_manifest_draft']['source']['product']='mutated returned draft'
        self.assertEqual(args[4],caller[3]);self.assertEqual(files(root),before)
        # Registration exists only as this explicit synthetic caller setup, never as preflight work.
        store=Store(root,recover_jobs=False)
        for declaration in (args[1],args[2],completion['report_manifest_draft']):register_version(store,declaration)
        snapshot=files(root);refs=result['fixed_refs'];pins=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'))
        with patch.object(store,'connect',lambda:ro(store)),patch.object(store,'put',side_effect=AssertionError('write')):
            q=read_registered_quality_mask_files(store,*pins);v=inspect_registered_binary_mask_values(store,*pins)
        self.assertEqual(q['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertEqual(v['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256});self.assertEqual(files(root),snapshot)
        self.assertFalse(v['scientific_accuracy_validated']);self.assertFalse(v['execution_authorized'])
        OBS.append({'actual':'fresh Temp140stored files +141read-only schema +separate SQLite3version setup/131133RO',
          'preflight_data_file_opens':2,'preflight_original_raster_opens':0,'preflight_registry_calls':0,'fixture_registry_setup_writes':3,
          'counts':v['counts'],'preflight_and_consumer_db_files_unchanged':True,'schema_repo_read_may_occur_on_cold_cache':True})

    def test_03_missing_partial_tampered_reformatted_oversize_are_readonly_blocked(self):
        for case in ('report_missing','manifest_missing','partial','tamper','reformat','oversize'):
            args=self.fixture();root=args[0];rp=root/args[3]['artifact_uri'];mp=root/args[5]
            if case=='report_missing':rp.unlink()
            elif case=='manifest_missing':mp.unlink()
            elif case=='partial':mp.write_bytes(mp.read_bytes()[:11])
            elif case=='tamper':rp.write_bytes(b'X'+rp.read_bytes()[1:])
            elif case=='reformat':mp.write_text(json.dumps(json.loads(mp.read_bytes()),ensure_ascii=False,indent=2),encoding='utf-8')
            else:mp.write_bytes(b'x'*(2*1024**2+1))
            before=files(root);result,_=self.inspect(args);self.empty(result);self.assertEqual(files(root),before)
            OBS.append({'actual_stored_file_fault':case,'status':'BLOCKED','issue':result['issue'],'checker_file_changes':0})

    def test_04_invalid_paths_alias_and_reparse_mock_before_data_open(self):
        for uri in ('../manifest.json','출력/QUALITY.JSON','입력/IMAGE.TIF','출력/NUL.json','출력/q:stream','출력/q?.json'):
            args=list(self.fixture());args[5]=uri;before=files(args[0]);result,opened=self.inspect(args)
            self.empty(result);self.assertEqual(opened,[]);self.assertEqual(files(args[0]),before)
        args=self.fixture();before=files(args[0])
        for attrs,tag in ((0x400,0),(0,123)):
            fake=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=attrs,st_reparse_tag=tag,st_dev=1,st_ino=1)
            with patch.object(Path,'lstat',return_value=fake):result,opened=self.inspect(args)
            self.empty(result);self.assertEqual(opened,[])
        self.assertEqual(files(args[0]),before)
        OBS.append({'mock':'reparse attributes/tags only; no actual reparse point created','blocked':True})

    def test_05_untrusted139_output_cleared_before_file_reads(self):
        args=self.fixture();good=complete_quality_report(*args[1:5]);before=files(args[0])
        for edit in (lambda p:p.update(extra='PRIVATE'),lambda p:p.update(execution_authorized=0),
          lambda p:p.update(report_bytes=b'POISON'),lambda p:p.update(report_sha256='a'*64),
          lambda p:p['report_manifest_draft'].update(data_type='raster'),
          lambda p:p.update(status='BLOCKED',issue={'code':'SECRET','field':'PRIVATE'})):
            bad=copy.deepcopy(good);edit(bad)
            with patch.object(api,'complete_quality_report',return_value=bad):result,opened=self.inspect(args)
            self.empty(result,'COMPLETION_OUTPUT_INVALID');self.assertEqual(opened,[]);self.assertNotIn('PRIVATE',repr(result))
        self.assertEqual(files(args[0]),before)

    def test_06_postvalidation_producer_mutation_cannot_change_expected_return(self):
        args=self.fixture();parent=complete_quality_report(*args[1:5]);original=copy.deepcopy(parent);same=api._same;calls=[]
        def mutate(actual,expected):
            valid=same(actual,expected)
            if actual is parent:
                self.assertTrue(valid);calls.append(1);parent['report_bytes']=b'POISON';parent['fixed_refs']['image_ref']['id']='changed'
            return valid
        with patch.object(api,'complete_quality_report',return_value=parent),patch.object(api,'_same',side_effect=mutate):result,_=self.inspect(args)
        self.assertEqual(calls,[1]);self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertEqual(result['fixed_refs'],original['fixed_refs'])

    def test_07_schema_failure_and_contaminated_return_clear_entire_result(self):
        args=self.fixture();before=files(args[0]);completed=complete_quality_report(*args[1:5]);draft=completed['report_manifest_draft']
        correct,digest=canonical_manifest(draft)
        bads=[None,[correct,digest],(correct,'a'*64),(None,digest),({**correct,'schema_version':True},digest)]
        for bad in bads:
            with patch.object(api,'canonical_manifest',return_value=bad):result,_=self.inspect(args)
            self.empty(result,'MANIFEST_SCHEMA_OUTPUT_INVALID')
        # Explicit stricter test policy, not a rejection by unchanged production schema.
        strict=copy.deepcopy(manifest_validator().schema)
        strict['properties']['source']={'type':'object','properties':{'product':{'const':'EXPLICIT STRICTER TEST POLICY'}}}
        def strict_fixture(value):Draft202012Validator(strict).validate(value);return canonical_manifest(value)
        with patch.object(api,'canonical_manifest',side_effect=strict_fixture):result,_=self.inspect(args)
        self.empty(result,'MANIFEST_SCHEMA_INVALID');self.assertEqual(files(args[0]),before)
        OBS.append({'schema_failure':'explicit stricter Draft202012Validator fixture through real canonical helper',
          'unchanged_production_schema_rejection_claim':False,'failed_payloads_fully_cleared':True})

    def test_08_schema_snapshot_mutation_after_validation_is_not_returned(self):
        args=self.fixture();draft=complete_quality_report(*args[1:5])['report_manifest_draft'];expected=copy.deepcopy(draft)
        canonical,digest=canonical_manifest(draft);same=api._same;calls=[]
        def mutate(actual,wanted):
            valid=same(actual,wanted)
            if actual is canonical:
                self.assertTrue(valid);calls.append(1);canonical['source']['product']='POISON_AFTER_SCHEMA_VALIDATION'
            return valid
        with patch.object(api,'canonical_manifest',return_value=(canonical,digest)),patch.object(api,'_same',side_effect=mutate):result,_=self.inspect(args)
        self.assertEqual(calls,[1]);self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertEqual(result['report_manifest_draft'],expected)

    def test_09_first_report_changed_during_second_file_read_is_blocked(self):
        args=self.fixture();root=args[0];rp=root/args[3]['artifact_uri'];read=api._snapshot;injected=[]
        source={k:v for k,v in files(root).items() if k.startswith('입력/')}
        def change(path,parents,field):
            if field=='manifest':
                old=rp.stat();raw=rp.read_bytes();rp.write_bytes(b'X'+raw[1:]);os.utime(rp,ns=(old.st_atime_ns,old.st_mtime_ns+10000000));injected.append(1)
            return read(path,parents,field)
        with patch.object(api,'_snapshot',side_effect=change):result,_=self.inspect(args)
        self.assertEqual(injected,[1]);self.empty(result,'FILE_CHANGED')
        self.assertTrue(all(files(root)[k]==v for k,v in source.items()))
        OBS.append({'explicit_fault_injection':'test changes first report while second snapshot begins',
          'checker_detected_final_stat_change':True,'checker_write_calls':0,'atomic_snapshot_claim':False})

    def test_10_actual_temp_parent_replacement_fault_injection(self):
        args=self.fixture();root=args[0];read=api._snapshot;changed=[]
        def replace(path,parents,field):
            if field=='manifest':
                old=root/'출력';backup=root/'explicit-test-backup';old.rename(backup);os.mkdir(old)
                shutil.copyfile(backup/'quality.json',old/'quality.json');shutil.copyfile(backup/'manifest.json',old/'manifest.json');changed.append(1)
            return read(path,parents,field)
        with patch.object(api,'_snapshot',side_effect=replace):result,_=self.inspect(args)
        self.assertEqual(changed,[1]);self.empty(result,'DIRECTORY_CHANGED')
        OBS.append({'explicit_fault_injection':'test renames and recreates parent inside Temp only',
          'checker':'BLOCKED','checker_created_files':0,'complete_hostile_parent_confinement_claim':False})

    def test_11_actual_directory_symlink_or_permission_skip(self):
        args=list(self.fixture());root=args[0];target=root/'출력';link=root/'alias'
        try:os.symlink(target,link,target_is_directory=True)
        except OSError as error:
            reason=f'actual Windows symlink unavailable: winerror={getattr(error,"winerror",None)}, errno={error.errno}'
            OBS.append({'actual_symlink':'SKIPPED','reason':reason});self.skipTest(reason)
        try:
            args[3]['artifact_uri']='alias/quality.json';args[1]['quality_report_ref']='alias/quality.json';args[5]='alias/manifest.json'
            before=files(root);result,_=self.inspect(args);self.empty(result);self.assertEqual(files(root),before)
        finally:
            self.assertEqual(link.parent,root);self.assertTrue(link.is_symlink());self.assertEqual(link.resolve(),target)
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()

    def test_12_installed_datetime_format_limit_is_observed_not_scientific_approval(self):
        meta=metadata();stamp='2020-01-01T00:00:00+09:60';meta['temporal']['start']=stamp
        args=self.fixture(meta=meta);before=files(args[0]);result,_=self.inspect(args)
        conforms=FormatChecker().conforms(stamp,'date-time')
        if conforms:self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        else:self.empty(result,'MANIFEST_SCHEMA_INVALID')
        self.assertFalse(result['source_authority_verified']);self.assertFalse(result['execution_authorized'])
        self.assertEqual(files(args[0]),before)
        OBS.append({'actual_installed_format_checker':{'timestamp':stamp,'conforms':conforms,'preflight_status':result['status']},
          'full_rfc3339_conformance_or_semantic_temporal_verification_claim':False})

    def test_13_report_files_success_does_not_validate_mask_or_access(self):
        for case,options,code in [('nodata0',{'nodata':0},'MASK_INTRINSIC_VALIDITY_UNSUPPORTED'),
          ('restricted',{'access':'RESTRICTED'},'ACCESS_DECLARATION_BLOCKED')]:
            args=self.fixture(actual=True,**options);result,_=self.inspect(args)
            self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
            store=Store(args[0],recover_jobs=False)
            for declaration in (args[1],args[2],result['report_manifest_draft']):register_version(store,declaration)
            before=files(args[0]);refs=result['fixed_refs']
            with patch.object(store,'connect',lambda:ro(store)):
                binary=inspect_registered_binary_mask_values(store,*(refs[k] for k in ('image_ref','quality_report_ref','mask_ref')))
            self.assertEqual(binary['status'],'BLOCKED');self.assertEqual(binary['issue']['code'],code)
            self.assertEqual(files(args[0]),before);self.assertFalse(result['artifact_bytes_verified'])
            OBS.append({'actual_counterexample':case,'report_files_preflight':'SUCCESS_UNREGISTERED','binary_consumer':'BLOCKED','code':code})

if __name__=='__main__':
    before={p:sha((ROOT/p).read_bytes()) for p in OLD}
    baseline={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==h for p,h in before.items()}
    start=time.perf_counter();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent));seconds=time.perf_counter()-start
    unchanged={p:sha((ROOT/p).read_bytes())==h for p,h in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_READONLY_STORED_REPORT_PREFLIGHT_TEMP_ONLY','status':'TESTED_SYNTHETIC' if result.wasSuccessful() else 'FAILED',
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
      'skipped':len(result.skipped),'skip_reasons':[reason for _,reason in result.skipped],'failures':len(result.failures),'errors':len(result.errors),
      'seconds':seconds,'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),'git_baseline':BASE,
      'separate_git_baseline_matches':baseline,'old_sources_unchanged':unchanged,'observations':OBS,
      'actual_scope':'fresh Temp140stored files; actual GTiff/SQLite only designated success/counterexamples; readonly131133 and actual installed96schema',
      'mock_scope':'139/schema output contamination and postvalidation mutation; stricter test schema; explicit first-file/parent filesystem fault injections; reparse attr guard',
      'operating_data_access':False,'operating_writes':0,'training':0,'inference':0,'api_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Two stored data artifacts only; cold trusted local schema read is allowed and separate from source image/mask reads.',
       'File/stat checks do not establish an atomic snapshot or complete hostile concurrent filesystem confinement.',
       'Manifest schema verification is not actual raster/mask QA, acquisition/AOI truth, access authority or model/execution approval.',
       'Installed format-checker permissiveness is recorded; stricter synthetic schema rejection is not a production-schema rejection.',
       'Registry setup writes occur only in explicit Temp caller fixtures, never in the preflight helper.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(baseline.values()) and all(unchanged.values()) else 1)
