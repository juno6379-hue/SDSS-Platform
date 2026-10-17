"""Independent140 exclusive Temp output files, no operating roots or registration."""
import ast
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
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
from app.data import quality_report_storage as api
from app.data.quality_report_completion import complete_quality_report
from app.dataset_registry import canonical_manifest, register_version
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store

ROOT=Path(__file__).resolve().parents[2]
SOURCE='backend/app/data/quality_report_storage.py';TEST='tests/test_quality_report_storage.py'
SOURCE_SHA='9fea7abb338e0c752f3fb7eb7b1e69d909627b3b48ada9319307fc15a5771f92'
TEST_SHA='ab063a3d53ac9dcbd8b51c7b9c683bc3ac001f60770d3574cd076e1acd6a38d9'
BASE='7b538b90c069789ca24dca0a1e237bf6dec47a8c'
OLD=['backend/app/data/quality_mask_bundle.py','backend/app/data/quality_report_completion.py',
 'tests/test_quality_mask_bundle.py','tests/test_quality_report_completion.py','backend/app/dataset_registry.py',
 'backend/app/ml/registered_quality_mask_files.py','backend/app/ml/registered_quality_mask_grid.py',
 'backend/app/ml/registered_binary_mask_values.py','backend/app/main.py','frontend/src/AnnualInputDiagnostics.tsx']
OBS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def metadata(access='PUBLIC'):
    return {'source':{'institution':'명시 TEST caller','product':'실제 임시 보고서','license':'TEST ONLY'},
      'spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':'STAGED','access_class':access}
def manifest(identifier,path,digest,mask=False,access='PUBLIC'):
    source={'institution':'명시 TEST source','product':'별도 image/mask 선언','license':'TEST ONLY','band_names':list(BAND_NAMES)}
    if mask:source['mask_semantics']={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
    return {'schema_version':'0.2.0','dataset_id':identifier,'version':' 고정 🌏 v1 ','source':source,
      'data_type':'raster','spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':'RAW','access_class':access,'sha256':digest,'artifact_uri':path,'lineage':[]}
@contextmanager
def readonly(store):
    c=sqlite3.connect(store.db.as_uri()+'?mode=ro',uri=True)
    try:yield c
    finally:c.close()

class Independent(unittest.TestCase):
    def fixture(self,*,actual=False,nodata=None,value=None,access='PUBLIC'):
        temp=tempfile.TemporaryDirectory(prefix='geoai-independent140-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();(root/'입력').mkdir();(root/'출력').mkdir()
        ip=root/'입력/image.tif';mp=root/'입력/mask.tif'
        if actual:
            profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
            with rasterio.open(ip,'w',**profile,count=6,dtype='uint16',nodata=0) as dst:
                dst.write(np.ones((6,16,16),dtype='uint16'));dst.descriptions=tuple(BAND_NAMES)
            values=(np.indices((16,16)).sum(axis=0)%2).astype('uint8')
            if value is not None:values[:]=value
            with rasterio.open(mp,'w',**profile,count=1,dtype='uint8',nodata=nodata) as dst:dst.write(values,1)
        else:ip.write_bytes(b'EXPLICIT SOURCE IMAGE NOT READ BY WRITER');mp.write_bytes(b'EXPLICIT SOURCE MASK NOT READ BY WRITER')
        image=manifest('영상 🌏','입력/image.tif',sha(ip.read_bytes()),access=access)
        image['quality_report_ref']='출력/quality.json'
        mask=manifest('mask 🌏','입력/mask.tif',sha(mp.read_bytes()),True)
        identity={'id':'품질 🌏','version':' 고정 🌏 v1 ','artifact_uri':'출력/quality.json'}
        return root,image,mask,identity,metadata(),'출력/manifest.json'

    def assert_blocked_no_files(self,args,code=None):
        before=files(args[0]);old=copy.deepcopy(args[1:])
        with patch.object(api.os,'open',side_effect=AssertionError('unexpected file open')) as opened,patch.object(Path,'mkdir',side_effect=AssertionError('mkdir')) as mkdir:
            result=api.write_quality_report_files(*args)
        opened.assert_not_called();mkdir.assert_not_called()
        self.assertEqual(result['status'],'BLOCKED');self.assertIs(result['stored_outputs_verified'],False)
        self.assertTrue(all(not r['created'] and not r['verified'] for r in result['outputs']))
        if code:self.assertEqual(result['issue']['code'],code)
        self.assertEqual(files(args[0]),before);self.assertEqual(args[1:],old)
        return result

    def test_01_frozen_sources_and_no_store_registry_or_raster_import(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA);self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)
        tree=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
        self.assertFalse(names & {'Store','canonical_manifest','register_version','resolve_version','rasterio','torch'})

    def test_02_actual_two_new_files_and_readonly_temp_registry_consumers(self):
        args=self.fixture(actual=True);root=args[0];before=files(root);caller=copy.deepcopy(args[1:]);opens=[];original_open=os.open
        def observe(path,flags,*rest,**kwargs):
            opens.append((Path(path).relative_to(root).as_posix(),bool(flags & os.O_CREAT)))
            return original_open(path,flags,*rest,**kwargs)
        with patch.object(api.os,'open',side_effect=observe),patch.object(Path,'mkdir',side_effect=AssertionError('mkdir')) as mkdir,patch.object(api,'complete_quality_report',wraps=complete_quality_report) as producer:
            result=api.write_quality_report_files(*args)
        mkdir.assert_not_called();self.assertEqual(producer.call_count,1);self.assertEqual(len(result),21)
        self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED');self.assertTrue(result['stored_outputs_verified'])
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))
        after=files(root);self.assertEqual(set(after)-set(before),{'출력/quality.json','출력/manifest.json'})
        self.assertTrue(all(after[k]==v for k,v in before.items()));self.assertEqual(args[1:],caller)
        self.assertEqual({p for p,_ in opens},{'출력/quality.json','출력/manifest.json'})
        self.assertEqual(sum(created for _,created in opens),2)
        completion=complete_quality_report(*args[1:5]);raw=(root/'출력/quality.json').read_bytes();report=json.loads((root/'출력/manifest.json').read_bytes())
        self.assertEqual(raw,completion['report_bytes']);self.assertEqual(sha(raw),result['report_sha256'])
        canonical,digest=canonical_manifest(report);self.assertEqual(report,canonical);self.assertEqual(digest,result['manifest_sha256'])
        self.assertEqual(result['outputs'],[{'role':'report','created':True,'verified':True,'bytes':len(raw)},
          {'role':'manifest','created':True,'verified':True,'bytes':(root/'출력/manifest.json').stat().st_size}])
        store=Store(root,recover_jobs=False)
        for declaration in (args[1],args[2],report):register_version(store,declaration)
        snapshot=files(root);refs=result['fixed_refs'];pinned=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'))
        with patch.object(store,'connect',lambda:readonly(store)),patch.object(store,'put',side_effect=AssertionError('registry write')):
            q=read_registered_quality_mask_files(store,*pinned);counts=inspect_registered_binary_mask_values(store,*pinned)
        self.assertEqual(q['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertEqual(counts['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256})
        self.assertIs(counts['scientific_accuracy_validated'],False);self.assertIs(counts['execution_authorized'],False)
        self.assertEqual(files(root),snapshot)
        OBS.append({'actual':'fresh Temp6bandGTiff/mask/report+manifest output and separate SQLite fixture registration',
          'writer_new_files':2,'writer_source_artifact_opens':0,'writer_registry_calls':0,'fixture_registry_setup_writes':3,
          'consumer_counts':counts['counts'],'all_source_bytes_unchanged':True,'consumer_db_and_files_unchanged':True})

    def test_03_each_preexisting_file_even_identical_refuses_every_write(self):
        for target in ('report','manifest','both'):
            args=self.fixture();root=args[0];done=complete_quality_report(*args[1:5])
            if target in ('report','both'):(root/args[3]['artifact_uri']).write_bytes(done['report_bytes'])
            if target in ('manifest','both'):(root/args[5]).write_bytes(api._canonical(done['report_manifest_draft']))
            self.assert_blocked_no_files(args,'OUTPUT_ALREADY_EXISTS')

    def test_04_invalid_path_alias_reserved_ads_unicode_and_no_auto_mkdir(self):
        bad=['../manifest.json','C:/manifest.json','//server/share/file.json','출력/x:stream','출력/NUL.json',
          '출력/com¹.json','출력/LPT9','출력/manifest.','출력/manifest ','출력/a//b.json','출력/./x.json',
          '출력/\u200bhidden.json','출력/QUALITY.JSON','입력/IMAGE.TIF','없는폴더/manifest.json']
        for uri in bad:
            args=list(self.fixture());args[5]=uri;self.assert_blocked_no_files(args)
        args=list(self.fixture());args[2]['quality_report_ref']='출력/manifest.json';self.assert_blocked_no_files(args,'OUTPUT_PATH_CONFLICT')
        args=list(self.fixture());args[3]['artifact_uri']='입력/IMAGE.TIF';args[1].pop('quality_report_ref');args[5]='입력/manifest.json'
        self.assert_blocked_no_files(args,'OUTPUT_PATH_CONFLICT')
        args=list(self.fixture());actual_root=args[0];before=files(actual_root);args[0]=str(actual_root)+'\u200b'
        with patch.object(api.os,'open',side_effect=AssertionError('unexpected open')) as opened:
            result=api.write_quality_report_files(*args)
        opened.assert_not_called();self.assertEqual(result['issue']['code'],'ROOT_INVALID');self.assertEqual(files(actual_root),before)

    def test_05_untrusted_completion_rejected_before_file_open(self):
        for edit in (lambda p:p.update(extra='SECRET'),lambda p:p.update(schema_version=True),
          lambda p:p.update(registry_registered=0),lambda p:p.update(report_bytes=b'POISON'),
          lambda p:p['report_manifest_draft'].update(dataset_id='changed'),
          lambda p:p.update(status='BLOCKED',issue={'code':'SECRET','field':'PRIVATE'})):
            args=self.fixture();bad=complete_quality_report(*args[1:5]);edit(bad)
            with patch.object(api,'complete_quality_report',return_value=bad):
                result=self.assert_blocked_no_files(args,'COMPLETION_OUTPUT_INVALID')
            self.assertNotIn('SECRET',repr(result))

    def test_06_postvalidation_producer_mutation_does_not_change_written_files(self):
        args=self.fixture();expected=complete_quality_report(*args[1:5]);producer=copy.deepcopy(expected);same=api._same;calls=[]
        def mutate(actual,wanted):
            valid=same(actual,wanted)
            if actual is producer:
                self.assertTrue(valid);calls.append(1);producer['report_bytes']=b'POST_VALIDATION_POISON'
                producer['report_manifest_draft']['source']['product']='POST_VALIDATION_POISON'
            return valid
        with patch.object(api,'complete_quality_report',return_value=producer),patch.object(api,'_same',side_effect=mutate):
            result=api.write_quality_report_files(*args)
        self.assertEqual(calls,[1]);self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED')
        self.assertEqual((args[0]/args[3]['artifact_uri']).read_bytes(),expected['report_bytes'])
        self.assertEqual(json.loads((args[0]/args[5]).read_bytes()),expected['report_manifest_draft'])

    def test_07_second_output_creation_race_preserves_other_winner(self):
        args=self.fixture();root=args[0];original_open=os.open;original_write=os.write;target=root/args[5];raced=[]
        def compete(path,flags,*rest,**kwargs):
            if Path(path)==target and flags & os.O_CREAT and not raced:
                raced.append(1);fd=original_open(path,flags,*rest,**kwargs)
                try:original_write(fd,b'OTHER_CREATOR_WINNER')
                finally:os.close(fd)
            return original_open(path,flags,*rest,**kwargs)
        with patch.object(api.os,'open',side_effect=compete):result=api.write_quality_report_files(*args)
        self.assertEqual(result['status'],'PARTIAL_FILES_PRESERVED');self.assertEqual(target.read_bytes(),b'OTHER_CREATOR_WINNER')
        self.assertEqual([r['created'] for r in result['outputs']],[True,False])
        self.assertEqual([r['verified'] for r in result['outputs']],[True,False]);self.assertFalse(result['stored_outputs_verified'])
        OBS.append({'explicit_mock_race':'other creator wins manifest EXCL after report succeeds','winner_bytes_preserved':True,
          'status':result['status'],'filesystem_atomicity_claim':False})

    def test_08_partial_second_write_preserved_and_no_automatic_retry(self):
        args=self.fixture();root=args[0];original=os.write;calls=[]
        def partial(fd,data):
            calls.append(1)
            if len(calls)==2:
                original(fd,data[:11]);raise OSError('PRIVATE_DEVICE_ERROR')
            return original(fd,data)
        with patch.object(api.os,'write',side_effect=partial):result=api.write_quality_report_files(*args)
        self.assertEqual(result['status'],'PARTIAL_FILES_PRESERVED');self.assertEqual([r['created'] for r in result['outputs']],[True,True])
        self.assertEqual([r['verified'] for r in result['outputs']],[True,False]);self.assertEqual((root/args[5]).stat().st_size,11)
        self.assertFalse(result['stored_outputs_verified']);self.assertNotIn('PRIVATE_DEVICE_ERROR',repr(result))
        preserved=files(root);retry=api.write_quality_report_files(*args)
        self.assertEqual(retry['status'],'BLOCKED');self.assertEqual(retry['issue']['code'],'OUTPUT_ALREADY_EXISTS');self.assertEqual(files(root),preserved)
        OBS.append({'explicit_mock':'second file wrote11bytes then OSError','partial_files_preserved':True,
          'retry_refused_without_modification':True,'atomic_or_rollback_claim':False})

    def test_09_parent_identity_change_and_reparse_guard_mock(self):
        args=self.fixture();before=files(args[0]);original=api._directory;calls=[]
        def different(path):
            value=original(path)
            if path==args[0]/'출력':
                calls.append(1)
                if len(calls)>1:return value[0],value[1]+1
            return value
        with patch.object(api,'_directory',side_effect=different):result=api.write_quality_report_files(*args)
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['issue']['code'],'DIRECTORY_CHANGED')
        self.assertEqual(files(args[0]),before)
        for attrs,tag in ((0x400,0),(0,123)):
            info=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=attrs,st_reparse_tag=tag,st_dev=1,st_ino=1)
            with patch.object(Path,'lstat',return_value=info):
                with self.assertRaises(api._Invalid):api._directory(args[0])
        OBS.append({'guard_mock':'parent inode changed and Windows reparse attr/tag','actual_reparse_object_created':False})

    def test_10_actual_directory_symlink_rejected_or_permission_skip(self):
        args=list(self.fixture());root=args[0];target=root/'출력';link=root/'alias'
        try:os.symlink(target,link,target_is_directory=True)
        except OSError as error:
            reason=f'actual Windows directory symlink unavailable: winerror={getattr(error,"winerror",None)}, errno={error.errno}'
            OBS.append({'actual_symlink':'SKIPPED','reason':reason});self.skipTest(reason)
        try:
            before=files(root);args[3]['artifact_uri']='alias/quality.json';args[1]['quality_report_ref']='alias/quality.json';args[5]='alias/manifest.json'
            result=api.write_quality_report_files(*args)
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(files(root),before)
            OBS.append({'actual_symlink':'created inside explicit Temp and blocked','target_unchanged':True})
        finally:
            self.assertEqual(link.parent,root);self.assertTrue(link.is_symlink());self.assertEqual(link.resolve(),target)
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()

    def test_11_files_written_is_not_binary_or_access_approval(self):
        for case,options,expected in [('nodata0',{'nodata':0},'MASK_INTRINSIC_VALIDITY_UNSUPPORTED'),
          ('255',{'value':255},'MASK_VALUES_NOT_BINARY'),('restricted',{'access':'RESTRICTED'},'ACCESS_DECLARATION_BLOCKED')]:
            args=self.fixture(actual=True,**options);root=args[0];result=api.write_quality_report_files(*args)
            self.assertEqual(result['status'],'FILES_WRITTEN_UNREGISTERED');self.assertFalse(result['registry_registered'])
            report=json.loads((root/args[5]).read_bytes());store=Store(root,recover_jobs=False)
            for declaration in (args[1],args[2],report):register_version(store,declaration)
            before=files(root);refs=result['fixed_refs']
            with patch.object(store,'connect',lambda:readonly(store)):
                counted=inspect_registered_binary_mask_values(store,*(refs[k] for k in ('image_ref','quality_report_ref','mask_ref')))
            self.assertEqual(counted['status'],'BLOCKED');self.assertEqual(counted['issue']['code'],expected)
            self.assertEqual(files(root),before);self.assertFalse(counted['execution_authorized'])
            OBS.append({'actual_counterexample':case,'new_files_written':2,'consumer':'BLOCKED','code':expected,
              'writer_source_inspection_or_registration':False})

    @unittest.skipUnless(os.name=='nt','native Windows invalid-name behavior only')
    def test_12_native_invalid_windows_characters_never_modify_sources(self):
        native=[]
        for char in '<>"|?*':
            args=list(self.fixture());root=args[0];before=files(root);args[5]='출력/invalid'+char+'manifest.json'
            # The pure URI guard does not claim to reject every native filename character.
            self.assertEqual(api._safe_uri(args[5],'test'),args[5])
            result=api.write_quality_report_files(*args)
            self.assertIn(result['status'],('BLOCKED','PARTIAL_FILES_PRESERVED'))
            self.assertFalse(result['stored_outputs_verified']);self.assertFalse(result['outputs'][1]['verified'])
            after=files(root);self.assertTrue(all(after[k]==v for k,v in before.items()))
            self.assertLessEqual(len(set(after)-set(before)),1)
            native.append({'character':char,'status':result['status'],'fixed_issue':result['issue'],
              'new_file_count':len(set(after)-set(before)),'original_files_unchanged':True})
        OBS.append({'actual_windows_native_invalid_name_cases':native,'full_native_name_prevalidation_claim':False})

if __name__=='__main__':
    before={p:sha((ROOT/p).read_bytes()) for p in OLD}
    baseline={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==s for p,s in before.items()}
    start=time.perf_counter();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent));seconds=time.perf_counter()-start
    unchanged={p:sha((ROOT/p).read_bytes())==s for p,s in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_EXCLUSIVE_REPORT_STORAGE_TEMP_ONLY','status':'TESTED_SYNTHETIC' if result.wasSuccessful() else 'FAILED',
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
      'skipped':len(result.skipped),'skip_reasons':[reason for _,reason in result.skipped],
      'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),'git_baseline':BASE,
      'separate_git_baseline_matches':baseline,'old_sources_unchanged':unchanged,'observations':OBS,
      'actual_scope':'fresh temporary GTiff/report/manifest files and separate SQLite registry fixture setup; readonly131/133 consumers',
      'mock_scope':'139 contamination/postvalidation mutation, EXCL winner race, partial os.write, changed parent inode, reparse attrs; no mocked consumer successes',
      'operating_data_access':False,'operating_writes':0,'training':0,'inference':0,'api_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Writes only report and manifest files; no actual image/mask validation, Registry registration, approval or execution.',
       'Sequential EXCL files are not a transaction; partial files remain and repeated call refuses existing outputs.',
       'Directory checks cannot establish complete hostile concurrent filesystem confinement or OS sandbox security.',
       'File fsync/readback is not directory fsync durability, CPU/RSS/time SLA or atomic multi-file snapshot.',
       'Actual symlink permission skip is distinct from synthetic reparse guard tests.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(baseline.values()) and all(unchanged.values()) else 1)
