"""Independent146: explicit source registration CLI, new temporary roots only."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.store import Store
from app.data.quality_report_storage import write_quality_report_files
from app.ml.per_scene_normalization_contract import BAND_NAMES

ROOT=Path(__file__).resolve().parents[2]
BASE='f4565f5ff9b743cfd51cea087bbcf7d2e840729f'
SOURCE='scripts/register_dataset_version.py';TEST='tests/test_source_raster_registration_cli.py'
SOURCE_SHA='befa11f07709501a10b440409e2dad495a8ee04570f30d9347818522a0511de8'
TEST_SHA='1f3b2e82a24accf68a0bc7a4464846ffb3890c61b2b3d1997d46d2e4c65517c4'
OBS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fixture142=load(ROOT/'evidence/integration/quality-report-registration-independent-20261018.py','ind146_fixture142')
cli=load(ROOT/SOURCE,'ind146_cli')

class Independent(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory(prefix='geoai-independent146-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();(root/'입력').mkdir();(root/'출력').mkdir();(root/'호출자').mkdir();(root/'cwd').mkdir()
        image_path=root/'입력/image.tif';mask_path=root/'입력/mask.tif'
        profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
        with rasterio.open(image_path,'w',**profile,count=6,dtype='uint16',nodata=0) as dst:
            dst.write(np.full((6,16,16),100,dtype='uint16'));dst.descriptions=tuple(BAND_NAMES)
        with rasterio.open(mask_path,'w',**profile,count=1,dtype='uint8',nodata=None) as dst:
            dst.write((np.indices((16,16)).sum(axis=0)%2).astype('uint8'),1);dst.set_band_description(1,'binary_validity')
        image=fixture142.manifest('영상 🌏', '입력/image.tif',sha(image_path.read_bytes()));image['quality_report_ref']='출력/quality.json'
        mask=fixture142.manifest('mask 🌏','입력/mask.tif',sha(mask_path.read_bytes()),True);mask['quality_status']='STAGED'
        store=Store(root,recover_jobs=False) # Empty catalog setup only: no Python source registration.
        self.assertEqual(fixture142.dbrows(store.db),{})
        return root,store,image,mask

    def manifest_path(self,root,value,name='manifest.json'):
        path=root/'호출자'/name;path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8');return path

    def argv(self,root,value,name='manifest.json'):
        return ['--data-root',str(root),'--manifest',str(self.manifest_path(root,value,name))]

    def process(self,argv,root,script=SOURCE):
        environment=dict(os.environ);environment.pop('PYTHONPATH',None);environment['PYTHONIOENCODING']='utf-8'
        return subprocess.run([sys.executable,str(ROOT/script),*argv],cwd=root/'cwd',env=environment,capture_output=True,timeout=60)

    def result(self,completed,exit_code):
        self.assertEqual(completed.returncode,exit_code,completed.stderr.decode('utf-8',errors='replace'))
        self.assertEqual(completed.stderr,b'');text=completed.stdout.decode('utf-8');self.assertEqual(len(text.splitlines()),1)
        value=json.loads(text);self.assertEqual(len(value),20)
        self.assertEqual(value['scope'],'EXPLICIT_SOURCE_RASTER_REGISTRATION_CLI_ONLY');self.assertIs(type(value['schema_version']),int)
        self.assertEqual(value['schema_version'],1);return value

    def success(self,value):
        self.assertEqual(value['status'],'SOURCE_RASTER_REGISTERED_UNAPPROVED')
        for field in ('store_initialization_started','registration_attempted','registry_outcome_verified','registry_registered'):self.assertIs(value[field],True)
        self.assertTrue(all(value[k] is False for k in cli.FALSE_FIELDS if k!='registry_registered'))
        self.assertIsNone(value['issue']);self.assertEqual(len(value['registration_record']),6)

    def test_00_frozen_source_and_tests(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA);self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)

    def test_01_actual_external_cwd_source2_cli_report_cli_and_readonly_consumers(self):
        root,store,image,mask=self.fixture();image_args=self.argv(root,image,'image.json');mask_args=self.argv(root,mask,'mask.json')
        before=fixture142.files(root)
        first=self.result(self.process(image_args,root),0);second=self.result(self.process(mask_args,root),0)
        self.success(first);self.success(second);self.assertEqual(len(fixture142.dbrows(store.db)),2)
        self.assertTrue(all(fixture142.files(root)[k]==v for k,v in before.items() if k!='catalog.sqlite3'))
        replay_before=fixture142.files(root);self.assertEqual(self.result(self.process(image_args,root),0),first)
        self.assertEqual(self.result(self.process(mask_args,root),0),second);self.assertEqual(fixture142.files(root),replay_before)
        identity={'id':'품질 🌏','version':' 고정 🌏 v1 ','artifact_uri':'출력/quality.json'};metadata=fixture142.metadata();uri='출력/manifest.json'
        self.assertEqual(write_quality_report_files(root,image,mask,identity,metadata,uri)['status'],'FILES_WRITTEN_UNREGISTERED')
        paths=[]
        for option,value,name in [('image-manifest',image,'image.json'),('mask-manifest',mask,'mask.json'),('report-identity',identity,'identity.json'),('report-metadata',metadata,'metadata.json')]:paths.extend(['--'+option,str(self.manifest_path(root,value,name))])
        common=['--data-root',str(root),*paths,'--manifest-output-uri',uri]
        # Existing143 does not bootstrap paths itself. Give its documented dependency path explicitly.
        environment=dict(os.environ);environment['PYTHONPATH']=os.pathsep.join(str(ROOT/p) for p in ('.runtime','backend'));environment['PYTHONIOENCODING']='utf-8'
        def report_command(command):return subprocess.run([sys.executable,str(ROOT/'scripts/quality_report_cli.py'),command,*common],cwd=root/'cwd',env=environment,capture_output=True,timeout=60)
        inspect=report_command('inspect');self.assertEqual(inspect.returncode,0,inspect.stderr);self.assertEqual(json.loads(inspect.stdout)['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        registered=report_command('register');self.assertEqual(registered.returncode,0,registered.stderr);reply=json.loads(registered.stdout)['result']
        self.assertEqual(reply['status'],'REPORT_REGISTERED_UNAPPROVED');self.assertEqual(len(fixture142.dbrows(store.db)),3)
        pins=tuple(reply['fixed_refs'][k] for k in ('image_ref','quality_report_ref','mask_ref'));stable=fixture142.files(root)
        with patch.object(store,'connect',lambda:fixture142.ro(store)),patch.object(store,'put',side_effect=AssertionError('consumer writes')):
            q=fixture142.read_registered_quality_mask_files(store,*pins);binary=fixture142.inspect_registered_binary_mask_values(store,*pins)
        self.assertEqual(q['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED');self.assertEqual(binary['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256})
        self.assertEqual(fixture142.files(root),stable)
        OBS.append({'actual':'external cwd/no PYTHONPATH new CLI image+mask two explicit registrations -> caller Python140 file preparation ->143 inspect/register ->131133 readonly',
          'python_source_registration_setup':0,'initial_empty_catalog_setup':True,'source_rows':2,'report_rows':1,'counts':binary['counts'],'replay_all_db_files_unchanged':True})

    def test_02_actual_raw_staged_accept_and_type_quality_upgrade_reject(self):
        root,store,image,mask=self.fixture()
        for field,value in [('quality_status','STANDARDIZED'),('quality_status','VALIDATED'),('data_type','document'),('data_type',True),('quality_status',True)]:
            bad=copy.deepcopy(image);bad[field]=value;argv=self.argv(root,bad);before=fixture142.files(root)
            result=self.result(self.process(argv,root),2);self.assertFalse(result['store_initialization_started']);self.assertFalse(result['registration_attempted'])
            self.assertEqual(fixture142.files(root),before);self.assertEqual(fixture142.dbrows(store.db),{})
        self.success(self.result(self.process(self.argv(root,image),root),0));self.success(self.result(self.process(self.argv(root,mask),root),0))

    def test_03_actual_conflict_preserves_original_and_uncertainty(self):
        root,store,image,mask=self.fixture();argv=self.argv(root,image);original=self.result(self.process(argv,root),0)
        conflict=copy.deepcopy(image);conflict['source']['institution']='CONFLICT CALLER';argv=self.argv(root,conflict);before=fixture142.files(root);rows=fixture142.dbrows(store.db)
        result=self.result(self.process(argv,root),3);self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED');self.assertFalse(result['registry_registered'])
        self.assertTrue(result['registration_attempted']);self.assertIsNone(result['registration_record']);self.assertEqual(fixture142.dbrows(store.db),rows);self.assertEqual(fixture142.files(root),before)

    def test_04_actual_opaque_raster_restricted_and_unresolved_lineage_are_unapproved(self):
        root,store,image,mask=self.fixture();path=root/'입력/opaque.bin';path.write_bytes(b'NOT_A_GTIFF')
        declaration=copy.deepcopy(image);declaration.update(dataset_id='opaque-declared-raster',artifact_uri='입력/opaque.bin',sha256=sha(path.read_bytes()),access_class='RESTRICTED')
        declaration['lineage']=[{'id':'absent-parent','version':'v1','sha256':'a'*64}]
        result=self.result(self.process(self.argv(root,declaration),root),0);self.success(result)
        self.assertEqual(result['registration_record']['manifest'],declaration);self.assertFalse(result['artifact_bytes_verified']);self.assertFalse(result['source_authority_verified'])
        OBS.append({'actual_counterexample':'opaque bytes + declared raster + RESTRICTED + nonexistent lineage parent accepted as unapproved metadata/hash registration',
          'native_GTIFF_or_parent_ACL_verification':False,'scientific_or_execution_approval':False})

    def test_05_actual_strict_json_bad_args_catalog_and_sha_no_registration(self):
        root,store,image,mask=self.fixture();argv=self.argv(root,image);path=Path(argv[3])
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'\xff',b' '*262145):
            path.write_bytes(raw);before=fixture142.files(root);result=self.result(self.process(argv,root),2)
            self.assertFalse(result['store_initialization_started']);self.assertEqual(fixture142.files(root),before)
        self.manifest_path(root,image)
        for suffix in (['--manifest',str(path)],['--data-root='+str(root)],['--unknown','SECRET_PRIVATE_146']):
            completed=self.process(argv+suffix,root);self.result(completed,2);self.assertNotIn(b'SECRET_PRIVATE_146',completed.stdout)
        for mode in ('source_tampered','missing_db'):
            root2,store2,image2,_=self.fixture();args=self.argv(root2,image2)
            if mode=='source_tampered':(root2/'입력/image.tif').write_bytes(b'EXPLICIT_TAMPER')
            else:store2.db.unlink()
            before=fixture142.files(root2);value=self.result(self.process(args,root2),2);self.assertFalse(value['store_initialization_started']);self.assertEqual(fixture142.files(root2),before)
        self.assertEqual(fixture142.dbrows(store.db),{})

    def test_06_inprocess_constructor_register_and_actual_post_commit_faults(self):
        for case in ('constructor','before_commit','after_commit','corrupt_after_commit'):
            root,store,image,_=self.fixture();args=self.argv(root,image);real=cli.register_version
            if case=='constructor':guard=patch.object(cli,'Store',side_effect=RuntimeError('SECRET_CTOR'))
            else:
                def faulty(*params):
                    if case=='before_commit':raise RuntimeError('SECRET_BEFORE')
                    answer=real(*params)
                    if case=='after_commit':raise RuntimeError('SECRET_AFTER')
                    answer['scientific_accuracy_validated']=True;return answer
                guard=patch.object(cli,'register_version',side_effect=faulty)
            with guard:code,value=cli.run(args)
            self.assertEqual(code,3);self.assertEqual(value['status'],'REGISTRATION_OUTCOME_UNCONFIRMED');self.assertFalse(value['registry_registered']);self.assertIsNone(value['registration_record'])
            self.assertTrue(value['store_initialization_started']);self.assertEqual(value['registration_attempted'],case!='constructor');self.assertNotIn('SECRET',json.dumps(value))
            self.assertEqual(len(fixture142.dbrows(store.db)),1 if case in ('after_commit','corrupt_after_commit') else 0)
        OBS.append({'explicit_fault_injection':'constructor/before-register/real-commit-then-error/contaminated-record','actual_after_commit_rows':1,'rollback_retry_delete':0})

    def test_07_inprocess_validator_and_return_record_mutation_private_copy(self):
        root,store,image,_=self.fixture();args=self.argv(root,image);canonical=cli.canonical_manifest;record=cli._record;events=[]
        def validator(*parameters):
            value=canonical(*parameters);original=value[0];same=cli._same
            def mutate(actual,expected):
                answer=same(actual,expected)
                if actual is original:actual['source']['institution']='SECRET_SCHEMA_MUTATION';events.append('schema')
                return answer
            self.addCleanup(patch.stopall)
            patch.object(cli,'_same',side_effect=mutate).start()
            return value
        def records(value,*parameters):
            fixed=record(value,*parameters);value['manifest']['source']['institution']='SECRET_RECORD_MUTATION';events.append('record');return fixed
        with patch.object(cli,'canonical_manifest',side_effect=validator),patch.object(cli,'_record',side_effect=records):code,value=cli.run(args)
        patch.stopall();self.assertEqual(code,0);self.success(value);self.assertIn('schema',events);self.assertIn('record',events)
        self.assertEqual(value['registration_record']['manifest'],image);self.assertNotIn('SECRET',json.dumps(value));self.assertEqual(json.loads(next(iter(fixture142.dbrows(store.db).values())))['manifest'],image)

    def test_08_actual_manifest_symlink_permission_skip(self):
        root,store,image,_=self.fixture();args=self.argv(root,image);path=Path(args[3]);target=path.with_name('explicit-original.json');path.rename(target)
        try:
            try:os.symlink(target,path)
            except OSError as error:self.skipTest(f'actual symlink unavailable winerror={getattr(error,"winerror",None)} errno={error.errno}')
            before=fixture142.files(root);self.result(self.process(args,root),2);self.assertEqual(fixture142.files(root),before)
        finally:
            if path.is_symlink():
                self.assertEqual(path.parent,target.parent);self.assertEqual(path.resolve(),target);path.unlink()
            if not path.exists():target.rename(path)

    def test_09_actual_catalog_and_sidecar_artifacts_block_before_constructor(self):
        for name in ('catalog.sqlite3','CATALOG.SQLITE3','catalog.sqlite3-journal','catalog.sqlite3-wal','catalog.sqlite3-shm'):
            root,store,image,_=self.fixture();artifact=root/name
            if not artifact.exists():artifact.write_bytes(b'EXPLICIT RESERVED CATALOG SIDECAR TEST')
            declaration=copy.deepcopy(image);declaration['artifact_uri']=name;declaration['sha256']=sha(artifact.read_bytes())
            args=self.argv(root,declaration);before=fixture142.files(root)
            result=self.result(self.process(args,root),2)
            self.assertEqual(result['issue'],{'code':'CATALOG_ARTIFACT_ALIAS'})
            self.assertFalse(result['store_initialization_started']);self.assertFalse(result['registration_attempted'])
            self.assertFalse(result['registry_registered']);self.assertEqual(fixture142.files(root),before)
        OBS.append({'actual_self_reference_prevention':'catalog and case alias plus journal/wal/shm artifact paths rejected before Store constructor','writes_during_cli':0})

    def test_10_actual_hardlink_to_catalog_block_before_constructor(self):
        root,store,image,_=self.fixture();alias=root/'입력/catalog-hardlink.bin'
        try:os.link(store.db,alias)
        except OSError as error:self.skipTest(f'actual hardlink unavailable winerror={getattr(error,"winerror",None)} errno={error.errno}')
        self.assertTrue(alias.samefile(store.db))
        declaration=copy.deepcopy(image);declaration['artifact_uri']='입력/catalog-hardlink.bin';declaration['sha256']=sha(alias.read_bytes())
        args=self.argv(root,declaration);before=fixture142.files(root);rows=fixture142.dbrows(store.db)
        result=self.result(self.process(args,root),2);self.assertFalse(result['store_initialization_started']);self.assertFalse(result['registration_attempted'])
        self.assertEqual(result['issue'],{'code':'CATALOG_ARTIFACT_ALIAS'})
        self.assertEqual(fixture142.files(root),before);self.assertEqual(fixture142.dbrows(store.db),rows)
        OBS.append({'actual_catalog_hardlink':'created in explicit Temp, samefile true; rejected before constructor','writes_during_cli':0})

if __name__=='__main__':
    old=fixture142.OLD+[fixture142.SOURCE,fixture142.TEST,'scripts/quality_report_cli.py','scripts/collect_samples.py','scripts/collect_training_grid.py']
    before={p:sha((ROOT/p).read_bytes()) for p in old};pins={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==h for p,h in before.items()}
    started=time.perf_counter()
    with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    seconds=time.perf_counter()-started;unchanged={p:sha((ROOT/p).read_bytes())==h for p,h in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_SOURCE_RASTER_REGISTRATION_CLI_TEMP_ONLY','git_baseline':BASE,
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'skipped':len(result.skipped),
      'skip_reasons':[reason for _,reason in result.skipped],'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),
      'old_sources_unchanged':unchanged,'separate_git_baseline_matches':pins,'observations':OBS,
      'initial_evidence_preserved':{ext:sha(Path(__file__).with_name('source-raster-registration-cli-independent-initial-20261018.'+ext).read_bytes()) for ext in ('py','json','log')},
      'initial_result':'8 PASS / 1 SKIP / 21.7476992s before catalog artifact alias hardening; not a final alias safety result',
      'actual_scope':'native Temp GTiffs, empty-catalog setup, new CLI two subprocess source registrations from external cwd with no PYTHONPATH, explicit Python140 preparation,143 subprocess report and131133readonly',
      'mock_scope':'inprocess constructor/validator/return faults and actual-commit-then-error; symlink permission unavailable is SKIP',
      'operating_writes':0,'operating_collection':0,'network_requests':0,'training':0,'inference':0,'api_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Declared raster plus matching SHA is not native GTiff/header/band/pixel/QA validation; opaque bytes can register unapproved.',
        'No parent lineage resolution, institution/source authority, ACL or scientific/execution approval is granted.',
        'Store constructor and registration can have effects before an exception; UNCONFIRMED does not claim rollback/absence and no automatic retry/delete occurs.',
        'Two source CLI calls and later report preparation/registration are explicit sequential caller actions, not one atomic transaction.',
        'Only Temp roots are used; operating data/ledgers/reservations/models are not opened or changed.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(pins.values()) and all(unchanged.values()) else 1)
