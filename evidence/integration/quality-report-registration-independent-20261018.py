"""Independent142 report-only insertion/replay and uncertain commit outcomes, Temp only."""
import ast
from contextlib import contextmanager
import copy
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.data import quality_report_registration as api
from app.data.quality_report_storage import write_quality_report_files
from app.data.quality_report_preflight import inspect_stored_quality_report
from app.dataset_registry import register_version, resolve_version, version_key, canonical_manifest
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.ml.registered_quality_mask_files import read_registered_quality_mask_files
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store

ROOT=Path(__file__).resolve().parents[2]
SOURCE='backend/app/data/quality_report_registration.py';TEST='tests/test_quality_report_registration.py'
SOURCE_SHA='f401dbe295655e9b47b9b75d02cf9d1c7c28574e88386adb9fcabc7d714f475f'
TEST_SHA='4e6eda4fee0e94c7cd68fc4dfc45e4370c4985f03edf67e2a7130e112ce413d3'
BASE='4f55aeb492bd81911d389ef681172265bad2b418'
OLD=['backend/app/data/quality_report_preflight.py','tests/test_quality_report_preflight.py',
 'backend/app/data/quality_report_storage.py','backend/app/data/quality_report_completion.py','backend/app/dataset_registry.py',
 'backend/app/store.py','backend/app/ml/registered_quality_mask_files.py','backend/app/ml/registered_binary_mask_values.py',
 'backend/app/main.py','frontend/src/AnnualInputDiagnostics.tsx']
OBS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def dbrows(db):
    connection=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    try:return {(kind,key):body for kind,key,body in connection.execute('SELECT kind,id,body FROM records')}
    finally:connection.close()
def initial_cleanup_observation():
    log=Path(__file__).with_name('quality-report-registration-independent-initial-20261018.log')
    names=sorted(set(re.findall(r'geoai-independent142-[a-z0-9_-]+',log.read_text(encoding='utf-8',errors='replace')))) if log.exists() else []
    parent=Path(tempfile.gettempdir()).resolve();observed=[]
    for name in names:
        path=parent/name
        if path.parent!=parent:raise AssertionError('outside explicit temporary boundary')
        observed.append({'name':name,'exists':path.is_dir(),'explicit_temp_parent_verified':True})
    return {'reason':'Initial independent dbrows SQLite helper lacked explicit close; product Store.connect already closes correctly.',
      'cleanup':'No recursive deletion, lock cleanup, or operating path access performed; presence observed only, removal mechanism not inferred.',
      'known_initial_temp_names':observed,'final_run_cleanup_errors':0}
def metadata():
    return {'source':{'institution':'EXPLICIT TEST REPORT CALLER','product':'보고서 선언 🌏','license':'TEST ONLY'},
      'spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
      'temporal':{'start':'2020-01-01T00:00:00Z','end':'2020-12-31T23:59:59Z','calendar':'gregorian'},
      'quality_status':'STAGED','access_class':'PUBLIC'}
def manifest(identifier,path,digest,mask=False,access='PUBLIC'):
    source={'institution':'EXPLICIT TEST SOURCE CALLER','product':'영상/mask 선언','license':'TEST ONLY','band_names':list(BAND_NAMES)}
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
    def fixture(self,*,actual=False,missing=None,link=True,access='PUBLIC'):
        t=tempfile.TemporaryDirectory(prefix='geoai-independent142-');self.addCleanup(t.cleanup)
        root=Path(t.name).resolve();(root/'입력').mkdir();(root/'출력').mkdir()
        image=root/'입력/image.tif';mask=root/'입력/mask.tif'
        if actual:
            profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
            with rasterio.open(image,'w',**profile,count=6,dtype='uint16',nodata=0) as dst:
                dst.write(np.ones((6,16,16),dtype='uint16'));dst.descriptions=tuple(BAND_NAMES)
            with rasterio.open(mask,'w',**profile,count=1,dtype='uint8',nodata=None) as dst:
                dst.write((np.indices((16,16)).sum(axis=0)%2).astype('uint8'),1)
        else:image.write_bytes(b'EXPLICIT OPAQUE SOURCE HASH ONLY');mask.write_bytes(b'EXPLICIT OPAQUE MASK HASH ONLY')
        i=manifest('영상 🌏','입력/image.tif',sha(image.read_bytes()),access=access)
        if link:i['quality_report_ref']='출력/quality.json'
        m=manifest('mask 🌏','입력/mask.tif',sha(mask.read_bytes()),True)
        identity={'id':'품질 🌏','version':' 고정 🌏 v1 ','artifact_uri':'출력/quality.json'}
        raw=(root,i,m,identity,metadata(),'출력/manifest.json')
        written=write_quality_report_files(*raw);self.assertEqual(written['status'],'FILES_WRITTEN_UNREGISTERED')
        store=Store(root,recover_jobs=False)
        for role,declaration in (('image',i),('mask',m)):
            if missing!=role:register_version(store,declaration)
        return store,*raw

    def success(self,result):
        self.assertEqual(len(result),22);self.assertEqual(result['status'],'REPORT_REGISTERED_UNAPPROVED')
        for key in ('source_dataset_refs_verified','stored_report_files_verified','manifest_schema_verified','registration_attempted','registry_outcome_verified','registry_registered'):
            self.assertIs(result[key],True)
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS if k!='registry_registered'))
        self.assertIsNone(result['issue']);self.assertEqual(len(result['registration_record']),6)

    def unconfirmed(self,result):
        self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED')
        self.assertTrue(result['registration_attempted']);self.assertFalse(result['registry_outcome_verified'])
        self.assertFalse(result['registry_registered']);self.assertIsNone(result['registration_record'])
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS))

    def test_01_frozen_sha_and_no_store_constructor_or_native_raster_call(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA);self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)
        tree=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        self.assertNotIn('Store',calls);self.assertNotIn('write_quality_report_files',calls)
        names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
        self.assertFalse(names & {'rasterio','torch','requests','urlopen'})

    def test_02_actual_report_only_insert_and_byte_identical_replay_then_consumers(self):
        args=self.fixture(actual=True);store,root=args[:2];before=files(root);source_rows=dbrows(store.db);caller=copy.deepcopy(args[2:])
        with (patch.object(api,'inspect_stored_quality_report',wraps=inspect_stored_quality_report) as preflight,
              patch.object(api,'resolve_version',wraps=resolve_version) as resolve,
              patch.object(api,'register_version',wraps=register_version) as register,
              patch.object(store,'get',wraps=store.get) as get):
            result=api.register_stored_quality_report(*args)
        self.success(result);self.assertEqual((preflight.call_count,resolve.call_count,register.call_count,get.call_count),(1,2,1,3))
        after=files(root);self.assertEqual(set(after),set(before))
        self.assertTrue(all(after[k]==v for k,v in before.items() if k!='catalog.sqlite3'))
        inserted=dbrows(store.db);self.assertEqual(len(source_rows),2);self.assertEqual(len(inserted),3)
        self.assertTrue(all(inserted[k]==v for k,v in source_rows.items()));self.assertEqual(args[2:],caller)
        self.assertEqual(result['registration_record']['manifest']['quality_status'],'STAGED')
        self.assertEqual(args[2]['quality_status'],'RAW')
        replay_before=files(root);replayed=api.register_stored_quality_report(*args);self.success(replayed)
        self.assertEqual(replayed['registration_record'],result['registration_record']);self.assertEqual(files(root),replay_before)
        self.assertEqual(dbrows(store.db),inserted)
        refs=result['fixed_refs'];pins=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'));consumer_before=files(root)
        with patch.object(store,'connect',lambda:ro(store)),patch.object(store,'put',side_effect=AssertionError('write')):
            q=read_registered_quality_mask_files(store,*pins);binary=inspect_registered_binary_mask_values(store,*pins)
        self.assertEqual(q['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertEqual(binary['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256})
        self.assertEqual(files(root),consumer_before);self.assertFalse(binary['scientific_accuracy_validated'])
        result['registration_record']['manifest']['source']['product']='MUTATED RETURN ONLY'
        self.assertEqual(dbrows(store.db),inserted)
        OBS.append({'actual':'fresh Temp140files +2source fixture registrations +142report insertion +byte-identical replay +131133RO',
          'source_setup_registry_writes':2,'adapter_new_report_rows_observed':1,'normal_gets':3,'normal_resolves':2,'normal_register_calls':1,
          'replay_entire_db_and_files_unchanged':True,'source_rows_and_raster_bytes_unchanged':True,'counts':binary['counts'],
          'scientific_accuracy_validated':False,'execution_authorized':False})

    def test_03_missing_source_manifest_mismatch_and_actual_source_hash_change_no_report_attempt(self):
        for case in ('missing_image','missing_mask','metadata_mismatch','actual_sha_changed'):
            args=list(self.fixture(missing='image' if case=='missing_image' else 'mask' if case=='missing_mask' else None));store,root=args[:2]
            if case=='metadata_mismatch':args[2]=copy.deepcopy(args[2]);args[2]['source']['institution']='DIFFERENT CALLER RAW MANIFEST'
            if case=='actual_sha_changed':(root/'입력/image.tif').write_bytes(b'EXPLICIT TEST SOURCE TAMPER')
            before=files(root);rows=dbrows(store.db)
            with patch.object(api,'register_version',side_effect=AssertionError('register must not run')) as register:
                result=api.register_stored_quality_report(*args)
            register.assert_not_called();self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['registration_attempted'])
            self.assertFalse(result['source_dataset_refs_verified']);self.assertTrue(result['stored_report_files_verified'])
            self.assertEqual(files(root),before);self.assertEqual(dbrows(store.db),rows)
        OBS.append({'actual_pre_registration_source_failures':['missing_image','missing_mask','raw_manifest_mismatch','source_sha_changed'],
          'report_register_calls':0,'database_and_files_unchanged_during_adapter':True})

    def test_04_store_root_and_missing_or_retargeted_db_rejected_before_sql_calls(self):
        class Poison:
            accesses=0
            @property
            def root(self):Poison.accesses+=1;raise AssertionError('untrusted root')
        for case in ('wrong_type','root_mismatch','db_missing','db_retarget'):
            args=list(self.fixture());store,root=args[:2];original_db=store.db
            if case=='wrong_type':args[0]=Poison()
            elif case=='root_mismatch':args[1]=root/'출력'
            elif case=='db_missing':store.db.rename(root/'explicit-backup.sqlite3')
            else:store.db=root/'other.sqlite3';store.db.write_bytes(original_db.read_bytes())
            before=files(root)
            with patch.object(api,'resolve_version',side_effect=AssertionError('resolve')) as resolve,patch.object(api,'register_version',side_effect=AssertionError('register')) as register:
                result=api.register_stored_quality_report(*args)
            self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['registration_attempted'])
            resolve.assert_not_called();register.assert_not_called();self.assertEqual(files(root),before)
        self.assertEqual(Poison.accesses,0)

    def test_05_untrusted_preflight_and_postvalidation_parent_mutation(self):
        args=self.fixture();store,root=args[:2];good=inspect_stored_quality_report(*args[1:]);before=files(root)
        for edit in (lambda p:p.update(extra='PRIVATE'),lambda p:p.update(execution_authorized=0),
          lambda p:p.update(stored_report_files_verified=1),lambda p:p.update(report_sha256='a'*64),
          lambda p:p.update(status='BLOCKED'),lambda p:p['files'][0].update(verified=1)):
            bad=copy.deepcopy(good);edit(bad)
            with patch.object(api,'inspect_stored_quality_report',return_value=bad),patch.object(api,'register_version',side_effect=AssertionError('register')) as register:
                result=api.register_stored_quality_report(*args)
            register.assert_not_called();self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['registration_attempted'])
            self.assertEqual(files(root),before)
        parent=copy.deepcopy(good);same=api._same;changed=[]
        def mutate(actual,expected):
            valid=same(actual,expected)
            if actual is parent:
                self.assertTrue(valid);changed.append(1);parent['report_manifest_draft']['source']['product']='POSTVALIDATION POISON';parent['fixed_refs']['quality_report_ref']['id']='POISON'
            return valid
        with patch.object(api,'inspect_stored_quality_report',return_value=parent),patch.object(api,'_same',side_effect=mutate):result=api.register_stored_quality_report(*args)
        self.success(result);self.assertEqual(changed,[1]);self.assertEqual(result['fixed_refs'],good['fixed_refs'])
        self.assertEqual(result['registration_record']['manifest'],good['report_manifest_draft'])

    def test_06_contaminated_source_resolution_never_registers_report(self):
        args=self.fixture();store,root=args[:2];original=resolve_version;before=files(root)
        for change in ('manifest','flag','digest'):
            def corrupt(*params):
                record=original(*params)
                if change=='manifest':record['manifest']['source']['product']='POISON'
                elif change=='flag':record['scientific_accuracy_validated']=True
                else:record['manifest_sha256']='a'*64
                return record
            with patch.object(api,'resolve_version',side_effect=corrupt),patch.object(api,'register_version',side_effect=AssertionError('register')) as register:
                result=api.register_stored_quality_report(*args)
            self.assertEqual(result['status'],'BLOCKED');register.assert_not_called();self.assertEqual(files(root),before)

    def test_07_existing_conflicting_report_is_not_overwritten(self):
        args=self.fixture();store,root=args[:2];report=json.loads((root/args[6]).read_bytes())
        conflict=copy.deepcopy(report);conflict['source']['product']='EXPLICIT CONFLICTING EXISTING VERSION'
        register_version(store,conflict);before=files(root);rows=dbrows(store.db)
        result=api.register_stored_quality_report(*args);self.unconfirmed(result)
        self.assertEqual(files(root),before);self.assertEqual(dbrows(store.db),rows)
        OBS.append({'actual':'conflicting existing report same id/version','overwritten':False,'returned_status':result['status'],
          'registration_attempted':True,'database_unchanged':True})

    def test_08_register_exception_before_and_after_commit_are_distinguished_by_actual_rows(self):
        for when in ('before_commit','after_commit'):
            args=self.fixture();store,root=args[:2];before=files(root);source_rows=dbrows(store.db);calls=[]
            def fail(*params):
                calls.append(1)
                if when=='after_commit':register_version(*params)
                raise RuntimeError('PRIVATE_COMMIT_FAILURE')
            with patch.object(api,'register_version',side_effect=fail):result=api.register_stored_quality_report(*args)
            self.unconfirmed(result);self.assertEqual(calls,[1]);self.assertNotIn('PRIVATE_COMMIT_FAILURE',repr(result))
            rows=dbrows(store.db);self.assertEqual(len(rows),2 if when=='before_commit' else 3)
            self.assertTrue(all(rows[k]==v for k,v in source_rows.items()))
            self.assertTrue(all(files(root)[k]==v for k,v in before.items() if k!='catalog.sqlite3'))
            OBS.append({'explicit_fault_injection':when,'status':result['status'],'actual_rows_after':len(rows),
              'commit_observed':when=='after_commit','automatic_retry_calls':0,'rollback_or_absence_claim':False})

    def test_09_bad_register_return_no_commit_and_readback_failure_do_not_claim_success(self):
        for case in ('bad_return_after_commit','valid_return_without_commit','readback_raises','readback_changed'):
            args=self.fixture();store,root=args[:2];report=json.loads((root/args[6]).read_bytes());key=version_key(args[4]['id'],args[4]['version']);real_get=store.get
            def returned(*params):
                if case=='valid_return_without_commit':
                    _,digest=canonical_manifest(report)
                    return {'id':key,'manifest':copy.deepcopy(report),'manifest_sha256':digest,'registered_at':'2026-10-18T00:00:00+00:00',
                      'scientific_accuracy_validated':False,'deployment_approval':False}
                record=register_version(*params)
                if case=='bad_return_after_commit':record['scientific_accuracy_validated']=True
                return record
            def get(kind,identifier):
                if identifier==key:
                    if case=='readback_raises':raise RuntimeError('PRIVATE_READBACK_FAILURE')
                    if case=='readback_changed':
                        record=real_get(kind,identifier);record['registered_at']='2020-01-01T00:00:00+00:00';return record
                return real_get(kind,identifier)
            with patch.object(api,'register_version',side_effect=returned),patch.object(store,'get',side_effect=get):result=api.register_stored_quality_report(*args)
            self.unconfirmed(result);rows=dbrows(store.db);self.assertEqual(len(rows),2 if case=='valid_return_without_commit' else 3)
            self.assertNotIn('PRIVATE_READBACK_FAILURE',repr(result))
            OBS.append({'explicit_fault_injection':case,'status':result['status'],'actual_report_row_present':('dataset_versions',key) in rows})

    def test_10_mutable_register_return_is_copied_before_later_mutation(self):
        args=self.fixture();captured={};record=api._record
        def register(*params):captured['value']=register_version(*params);return captured['value']
        def copy_then_change(value,manifest,digest):
            fixed=record(value,manifest,digest)
            if value is captured.get('value'):
                value['manifest']['source']['product']='POISON_AFTER_RECORD_COPY';value['scientific_accuracy_validated']=True
            return fixed
        with patch.object(api,'register_version',side_effect=register),patch.object(api,'_record',side_effect=copy_then_change):result=api.register_stored_quality_report(*args)
        self.success(result);self.assertNotIn('POISON_AFTER_RECORD_COPY',repr(result))
        actual=args[0].get('dataset_versions',result['registration_record']['id'])
        self.assertEqual(result['registration_record'],actual);self.assertFalse(actual['scientific_accuracy_validated'])

    def test_11_store_retarget_or_db_inode_replaced_between_resolve_and_write_is_blocked(self):
        for case in ('store_retarget','db_replaced'):
            args=self.fixture();store,root=args[:2];original_root=store.root;original_db=store.db;calls=[]
            other_temp=tempfile.TemporaryDirectory(prefix='geoai-independent142-other-');self.addCleanup(other_temp.cleanup)
            other=Store(Path(other_temp.name).resolve(),recover_jobs=False);other_before=files(other.root)
            def resolve(*params):
                value=resolve_version(*params);calls.append(1)
                if len(calls)==2:
                    if case=='store_retarget':store.root=other.root;store.db=other.db
                    else:
                        old=root/'explicit-db-backup.sqlite3';original_db.rename(old);shutil.copyfile(old,original_db)
                return value
            try:
                with patch.object(api,'resolve_version',side_effect=resolve),patch.object(api,'register_version',side_effect=AssertionError('register')) as register:
                    result=api.register_stored_quality_report(*args)
                register.assert_not_called();self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['registration_attempted'])
                self.assertEqual(len(dbrows(original_db)),2);self.assertEqual(files(other.root),other_before)
            finally:store.root=original_root;store.db=original_db
        OBS.append({'explicit_fault_injection':'Store root/db retarget or SQLite inode replacement after source resolves',
          'registration_calls':0,'reports_inserted':0,'operating_roots_accessed':False})

    def test_12_actual_catalog_symlink_rejected_or_permission_skip(self):
        args=self.fixture();store,root=args[:2];original=store.db;target=root/'explicit-real-catalog.sqlite3';original.rename(target)
        try:
            try:os.symlink(target,original)
            except OSError as error:
                reason=f'actual Windows symlink unavailable: winerror={getattr(error,"winerror",None)}, errno={error.errno}'
                OBS.append({'actual_catalog_symlink':'SKIPPED','reason':reason});self.skipTest(reason)
            before=files(root);result=api.register_stored_quality_report(*args)
            self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['registration_attempted']);self.assertEqual(files(root),before)
        finally:
            if original.is_symlink():
                self.assertEqual(original.parent,root);self.assertEqual(original.resolve(),target);original.unlink()
            if not original.exists():target.rename(original)

    def test_13_report_registration_does_not_rewrite_source_link_or_grant_access(self):
        for case,options in (('missing_image_quality_report_ref',{'link':False}),('restricted_image_public_report',{'access':'RESTRICTED'})):
            args=self.fixture(actual=True,**options);store,root=args[:2];source_rows=dbrows(store.db)
            result=api.register_stored_quality_report(*args);self.success(result)
            refs=result['fixed_refs'];before=files(root)
            with patch.object(store,'connect',lambda:ro(store)):
                q=read_registered_quality_mask_files(store,*(refs[k] for k in ('image_ref','quality_report_ref','mask_ref')))
            self.assertEqual(q['status'],'BLOCKED');self.assertEqual(files(root),before)
            self.assertTrue(all(dbrows(store.db)[k]==v for k,v in source_rows.items()))
            self.assertFalse(result['scientific_accuracy_validated']);self.assertFalse(result['execution_authorized'])
            OBS.append({'actual_counterexample':case,'report_row_registered':True,'consumer131':'BLOCKED','consumer_issue':q['issue'],
              'source_versions_not_rewritten':True,'quality_or_access_approval':False})

if __name__=='__main__':
    before={p:sha((ROOT/p).read_bytes()) for p in OLD}
    baseline={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==h for p,h in before.items()}
    start=time.perf_counter();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent));seconds=time.perf_counter()-start
    unchanged={p:sha((ROOT/p).read_bytes())==h for p,h in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_EXPLICIT_REPORT_REGISTRATION_TEMP_ONLY','status':'TESTED_SYNTHETIC' if result.wasSuccessful() else 'FAILED',
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'skipped':len(result.skipped),
      'skip_reasons':[reason for _,reason in result.skipped],'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
      'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),
      'git_baseline':BASE,'separate_git_baseline_matches':baseline,'old_sources_unchanged':unchanged,'observations':OBS,
      'actual_scope':'fresh Temp files/GTiff/SQLite; two preexisting source fixture versions; adapter report insert and exact replay; readonly131133',
      'mock_scope':'preflight/resolve/register/get output contamination, explicit before/after-commit faults, mutable outputs and Store/db retarget fault injections',
      'operating_store_access':False,'operating_registration_calls':0,'operating_writes':0,'training':0,'inference':0,
      'api_ui_changed':False,'frontend_build_browser_required':False,'initial_fixture_cleanup_observation':initial_cleanup_observation(),
      'limitations':['Successful source hashes and report/schema checks are historical sequential observations, not an atomic source/DB/filesystem transaction.',
       'Source legacy hash reads and Store JSON predecode have no new hard source-size/CPU/RSS/time sandbox guarantee.',
       'UNCONFIRMED may follow a real commit; no absence, rollback, retry or deletion is claimed.',
       'Report-only registration does not rewrite source versions, assure consumer backlinks or grant QA/access/scientific/execution approval.',
       'All writes are explicit temporary fixture setup or adapter operations in those temporary roots; no operating Store is opened.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(baseline.values()) and all(unchanged.values()) else 1)
