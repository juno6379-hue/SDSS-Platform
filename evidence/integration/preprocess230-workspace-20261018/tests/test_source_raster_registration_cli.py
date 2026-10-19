"""Explicit source registration only in temporary initialized catalogs."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts import register_dataset_version as cli
from app.store import Store

PROJECT = Path(__file__).resolve().parents[1]


class SourceRasterRegistrationCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.work = self.root/'outside-cwd'; self.work.mkdir()
        self.store = Store(self.root)
        artifact = self.root/'임시영상.tif'
        with rasterio.open(artifact,'w',driver='GTiff',count=1,width=8,height=8,dtype='uint16',crs='EPSG:32748',transform=from_origin(500000,9000000,10,10)) as dst:
            dst.write(np.ones((1,8,8),dtype='uint16')); dst.set_band_description(1,'CALLER_UNKNOWN_BAND')
        self.manifest = {'schema_version':'0.2.0','dataset_id':'명시자료','version':' v1 ',
            'source':{'institution':'CALLER_DECLARED','product':'TEST_ONLY','license':'TEST_ONLY','band_names':['CALLER_UNKNOWN_BAND']},
            'data_type':'raster','spatial':{'bbox':[100,-20,120,0],'crs':'EPSG:4326'},
            'temporal':{'start':'2021-01-01T00:00:00Z','end':'2021-12-31T00:00:00Z','calendar':'gregorian'},
            'quality_status':'RAW','access_class':'PUBLIC','artifact_uri':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'lineage':[]}
        self.input = self.root/'완성-manifest.json'; self.save()

    def save(self): self.input.write_text(json.dumps(self.manifest,ensure_ascii=False),encoding='utf-8')
    def args(self): return ['--data-root',str(self.root),'--manifest',str(self.input)]
    def snapshot(self): return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def process(self,args=None):
        environment = dict(os.environ); environment.pop('PYTHONPATH',None)
        return subprocess.run([sys.executable,str(PROJECT/'scripts/register_dataset_version.py'),*(self.args() if args is None else args)],
            cwd=self.work,env=environment,capture_output=True,timeout=60)

    def test_real_subprocess_outside_project_no_pythonpath_unicode_insert_and_replay(self):
        before = self.snapshot(); process = self.process()
        self.assertEqual(process.returncode,0,process.stderr); self.assertEqual(process.stderr,b''); self.assertEqual(process.stdout.count(b'\n'),1)
        result = json.loads(process.stdout.decode('utf-8')); self.assertEqual(len(result),20)
        self.assertEqual(result['status'],'SOURCE_RASTER_REGISTERED_UNAPPROVED'); self.assertEqual(result['dataset_ref']['id'],'명시자료')
        self.assertEqual(result['dataset_ref']['version'],' v1 '); self.assertTrue(result['registry_registered'])
        self.assertTrue(result['registration_attempted']); self.assertTrue(result['registry_outcome_verified'])
        self.assertTrue(all(result[k] is False for k in cli.FALSE_FIELDS if k != 'registry_registered'))
        after = self.snapshot(); self.assertEqual({k:v for k,v in before.items() if k != 'catalog.sqlite3'},{k:v for k,v in after.items() if k != 'catalog.sqlite3'})
        replay = self.process(); self.assertEqual(replay.returncode,0,replay.stderr); self.assertEqual(json.loads(replay.stdout),result)
        self.assertEqual(self.snapshot(),after); self.assertEqual(len(self.store.list('dataset_versions')),1)

    def test_same_version_conflict_preserves_existing_row_and_files(self):
        self.assertEqual(cli.run(self.args())[0],0); existing = self.store.list('dataset_versions')[0]
        self.manifest['source']['product'] = 'DIFFERENT_CALLER_DECLARATION'; self.save(); before = self.snapshot()
        code,result = cli.run(self.args())
        self.assertEqual(code,3); self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED')
        self.assertFalse(result['registry_registered']); self.assertIsNone(result['registration_record'])
        self.assertEqual(self.store.list('dataset_versions'),[existing]); self.assertEqual(self.snapshot(),before)

    def test_document_quality_upgrade_alias_and_wrong_file_hash_before_constructor(self):
        base = copy.deepcopy(self.manifest)
        for field,value in (('data_type','document'),('quality_status','VALIDATED'),('quality_status','STANDARDIZED'),('version',' latest '),('sha256','0'*64)):
            self.manifest = copy.deepcopy(base); self.manifest[field] = value; self.save()
            with patch.object(cli,'Store') as ctor,patch.object(cli,'register_version') as register:
                code,result = cli.run(self.args())
            self.assertEqual(code,2); self.assertFalse(result['store_initialization_started']); ctor.assert_not_called(); register.assert_not_called()
        self.assertEqual(self.store.list('dataset_versions'),[])

    def test_missing_or_wrong_catalog_schema_never_initializes_new_database(self):
        self.store.db.unlink()
        with patch.object(cli,'Store') as ctor: code,result = cli.run(self.args())
        self.assertEqual(code,2); self.assertFalse(self.store.db.exists()); ctor.assert_not_called()
        connection = sqlite3.connect(self.store.db)
        try: connection.execute('CREATE TABLE records(kind TEXT,id TEXT,body TEXT)'); connection.commit()
        finally: connection.close()
        with patch.object(cli,'Store') as ctor: code,result = cli.run(self.args())
        self.assertEqual(result['issue'],{'code':'CATALOG_SCHEMA_INVALID'}); ctor.assert_not_called()

    def test_strict_json_size_and_arguments_do_not_echo_private_input(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":"\\ud800"}',b'\xff',b'{"x":9007199254740992}'):
            self.input.write_bytes(raw)
            with patch.object(cli,'Store') as ctor: code,result = cli.run(self.args())
            self.assertEqual(code,2); ctor.assert_not_called(); self.assertIsNone(result['registration_record'])
        self.save(); original = self.input.read_bytes(); self.input.write_bytes(original+b' '*(256*1024-len(original)))
        self.assertEqual(cli.run(self.args())[0],0)
        self.input.write_bytes(self.input.read_bytes()+b' '); self.assertEqual(cli.run(self.args())[0],2)
        for args in ([],['PRIVATE_ARG_PATH'],self.args()+['--manifest=PRIVATE_ARG_PATH'],['--data-r',str(self.root),'--manifest',str(self.input)]):
            process = self.process(args); self.assertEqual(process.returncode,2); self.assertEqual(process.stderr,b'')
            result = json.loads(process.stdout); self.assertNotIn('PRIVATE_ARG_PATH',str(result))
        help_result = self.process(['--help']); self.assertEqual(help_result.returncode,0); self.assertIn(b'--manifest',help_result.stdout)

    def test_schema_output_contamination_before_io_and_mutation_after_validation(self):
        actual = cli.canonical_manifest
        with patch.object(cli,'canonical_manifest',return_value=({},'0'*64)),patch.object(cli,'Store') as ctor:
            code,result = cli.run(self.args())
        self.assertEqual(result['issue'],{'code':'MANIFEST_SCHEMA_OUTPUT_INVALID'}); ctor.assert_not_called()
        validated = actual(self.manifest); same = cli._same
        def mutate(value,expected):
            equal = same(value,expected)
            if value is validated[0]: validated[0]['source']['product'] = 'PRIVATE_POSTVALIDATION'
            return equal
        with patch.object(cli,'canonical_manifest',return_value=validated),patch.object(cli,'_same',side_effect=mutate): code,result = cli.run(self.args())
        self.assertEqual(code,0); self.assertNotIn('PRIVATE_POSTVALIDATION',json.dumps(result))

    def test_constructor_and_precommit_postcommit_errors_are_unconfirmed(self):
        with patch.object(cli,'Store',side_effect=RuntimeError('PRIVATE_CTOR_PATH')): code,result = cli.run(self.args())
        self.assertEqual(code,3); self.assertTrue(result['store_initialization_started']); self.assertFalse(result['registration_attempted'])
        self.assertNotIn('PRIVATE_CTOR_PATH',str(result))
        with patch.object(cli,'register_version',side_effect=RuntimeError('PRIVATE_PRECOMMIT')): code,result = cli.run(self.args())
        self.assertEqual(code,3); self.assertTrue(result['registration_attempted']); self.assertEqual(self.store.list('dataset_versions'),[])
        actual = cli.register_version
        def commit_then_fail(*args): actual(*args); raise RuntimeError('PRIVATE_POSTCOMMIT')
        with patch.object(cli,'register_version',side_effect=commit_then_fail): code,result = cli.run(self.args())
        self.assertEqual(code,3); self.assertEqual(len(self.store.list('dataset_versions')),1); self.assertNotIn('PRIVATE_POSTCOMMIT',str(result))

    def test_malformed_registration_return_readback_and_detached_record(self):
        actual = cli.register_version
        def bad(*args): record = actual(*args); record['deployment_approval'] = 0; return record
        with patch.object(cli,'register_version',side_effect=bad): code,result = cli.run(self.args())
        self.assertEqual(code,3); self.assertFalse(result['registry_registered']); self.assertEqual(len(self.store.list('dataset_versions')),1)
        captured = []; original_get = Store.get
        def keep(*args):
            value = actual(*args); captured.append(value); return value
        def mutate_after_snapshot(store,kind,key):
            value = original_get(store,kind,key); captured[0]['manifest']['source']['product'] = 'MUTATED_PARENT'; return value
        with patch.object(cli,'register_version',side_effect=keep),patch.object(Store,'get',mutate_after_snapshot): code,result = cli.run(self.args())
        self.assertEqual(code,0); self.assertNotIn('MUTATED_PARENT',json.dumps(result))
        with patch.object(Store,'get',side_effect=RuntimeError('PRIVATE_READBACK')): code,result = cli.run(self.args())
        self.assertEqual(code,3); self.assertIsNone(result['registration_record']); self.assertNotIn('PRIVATE_READBACK',str(result))

    def test_opaque_bytes_can_match_declared_raster_without_native_approval(self):
        artifact = self.root/self.manifest['artifact_uri']; artifact.write_bytes(b'OPAQUE_NOT_A_GEOTIFF')
        self.manifest['sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest(); self.save()
        with patch.object(rasterio,'open',side_effect=AssertionError('no native raster open')): code,result = cli.run(self.args())
        self.assertEqual(code,0); self.assertTrue(result['registry_registered']); self.assertFalse(result['artifact_bytes_verified'])
        self.assertFalse(result['quality_mask_verified']); self.assertFalse(result['scientific_accuracy_validated'])

    def test_catalog_and_direct_sidecars_rejected_before_sql_constructor_without_writes(self):
        base = copy.deepcopy(self.manifest)
        sidecars = [self.root/('catalog.sqlite3'+suffix) for suffix in ('-wal','-shm','-journal')]
        for path in sidecars: path.write_bytes(b'PRESERVED_SIDECAR_SENTINEL')
        before = self.snapshot()
        for name in ('catalog.sqlite3','CATALOG.SQLITE3','catalog.sqlite3-wal','catalog.sqlite3-shm','catalog.sqlite3-journal'):
            self.manifest = copy.deepcopy(base); self.manifest['artifact_uri'] = name
            self.manifest['sha256'] = hashlib.sha256(self.store.db.read_bytes()).hexdigest(); self.save()
            protected = {key:value for key,value in before.items() if key != self.input.name}
            with patch.object(cli,'_existing_catalog') as catalog,patch.object(cli,'Store') as ctor:
                code,result = cli.run(self.args())
            self.assertEqual(code,2); self.assertEqual(result['issue'],{'code':'CATALOG_ARTIFACT_ALIAS'})
            self.assertFalse(result['store_initialization_started']); self.assertFalse(result['registration_attempted'])
            catalog.assert_not_called(); ctor.assert_not_called()
            self.assertEqual(protected,{key:value for key,value in self.snapshot().items() if key != self.input.name})

    def test_actual_hardlink_to_catalog_rejected_before_sql(self):
        alias = self.root/'catalog-hardlink.tif'
        try: os.link(self.store.db,alias)
        except OSError as error: self.skipTest('hardlink unavailable: '+str(getattr(error,'winerror',error.errno)))
        self.manifest.update(artifact_uri=alias.name,sha256=hashlib.sha256(alias.read_bytes()).hexdigest()); self.save(); before = self.snapshot()
        with patch.object(cli,'_existing_catalog') as catalog,patch.object(cli,'Store') as ctor:
            code,result = cli.run(self.args())
        self.assertEqual(code,2); self.assertEqual(result['issue'],{'code':'CATALOG_ARTIFACT_ALIAS'})
        catalog.assert_not_called(); ctor.assert_not_called(); self.assertEqual(self.snapshot(),before)

    def test_actual_symlink_to_catalog_rejected_or_permission_skip(self):
        alias = self.root/'catalog-symlink.tif'
        try: alias.symlink_to(self.store.db)
        except OSError as error: self.skipTest('symlink unavailable: '+str(getattr(error,'winerror',error.errno)))
        self.manifest.update(artifact_uri=alias.name,sha256=hashlib.sha256(self.store.db.read_bytes()).hexdigest()); self.save()
        before = self.snapshot()
        with patch.object(cli,'_existing_catalog') as catalog,patch.object(cli,'Store') as ctor:
            code,result = cli.run(self.args())
        self.assertEqual(code,2); self.assertEqual(result['issue'],{'code':'CATALOG_ARTIFACT_ALIAS'})
        catalog.assert_not_called(); ctor.assert_not_called(); self.assertEqual(self.snapshot(),before)

    def test_nested_same_name_and_independent_copy_are_not_catalog_aliases(self):
        nested = self.root/'nested'; nested.mkdir()
        artifact = nested/'catalog.sqlite3'; artifact.write_bytes((self.root/self.manifest['artifact_uri']).read_bytes())
        self.manifest.update(artifact_uri='nested/catalog.sqlite3',sha256=hashlib.sha256(artifact.read_bytes()).hexdigest()); self.save()
        before = artifact.read_bytes(); code,result = cli.run(self.args())
        self.assertEqual(code,0); self.assertEqual(artifact.read_bytes(),before)
        separate = self.root/'independent-catalog-copy.tif'; separate.write_bytes(self.store.db.read_bytes())
        self.manifest.update(dataset_id='INDEPENDENT_COPY',artifact_uri=separate.name,sha256=hashlib.sha256(separate.read_bytes()).hexdigest()); self.save()
        before = separate.read_bytes(); code,result = cli.run(self.args())
        self.assertEqual(code,0); self.assertEqual(separate.read_bytes(),before)
        self.assertFalse(result['artifact_bytes_verified'])


if __name__ == '__main__': unittest.main()
