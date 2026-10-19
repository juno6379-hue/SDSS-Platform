"""Temporary explicit CLI subprocesses and isolated malformed-child boundaries."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import quality_report_cli as cli
import test_quality_report_registration as fixtures

PROJECT = Path(__file__).resolve().parents[1]


class QualityReportCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.QualityReportRegistrationTests.setUpClass()
        cls.addClassCleanup(fixtures.QualityReportRegistrationTests.doClassCleanups)

    def setUp(self):
        self.fixture = fixtures.QualityReportRegistrationTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root; self.f = self.fixture.f
        self.paths = []
        for name,value in (('image',self.f.image),('mask',self.f.mask),('identity',self.f.identity),('metadata',self.f.metadata)):
            path = self.root/(name+'-입력.json'); path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8'); self.paths.append(path)

    def args(self,command='inspect'):
        result = [command,'--data-root',str(self.root)]
        for key,path in zip(('image-manifest','mask-manifest','report-identity','report-metadata'),self.paths): result += ['--'+key,str(path)]
        return result+['--manifest-output-uri',self.fixture.sidecar]

    def snapshot(self):
        return {p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}

    def process(self,args):
        environment = dict(os.environ); environment['PYTHONPATH'] = os.pathsep.join(('.runtime','.','backend','tests'))
        return subprocess.run([sys.executable,str(PROJECT/'scripts/quality_report_cli.py'),*args],cwd=PROJECT,
            env=environment,capture_output=True,timeout=60)

    def test_subprocess_inspect_without_database_utf8_single_json_readonly(self):
        self.fixture.store.db.unlink(); before = self.snapshot()
        completed = self.process(self.args())
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertEqual(completed.stderr,b''); self.assertEqual(completed.stdout.count(b'\n'),1)
        result = json.loads(completed.stdout.decode('utf-8')); self.assertEqual(len(result),6)
        self.assertEqual(result['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertEqual(len(result['result']),23); self.assertFalse(self.fixture.store.db.exists())
        self.assertEqual(self.snapshot(),before)
        with patch.object(cli.sqlite3,'connect',side_effect=AssertionError('inspect no SQL')),patch.object(cli,'Store',side_effect=AssertionError('no constructor')):
            self.assertEqual(cli.run(self.args())[0],0)

    def test_subprocess_explicit_registration_and_identical_replay(self):
        before = self.snapshot(); first = self.process(self.args('register'))
        self.assertEqual(first.returncode,0,first.stderr); result = json.loads(first.stdout)
        self.assertEqual(result['status'],'REPORT_REGISTERED_UNAPPROVED'); self.assertTrue(result['result']['registry_registered'])
        after = self.snapshot(); second = self.process(self.args('register'))
        self.assertEqual(second.returncode,0,second.stderr); self.assertEqual(json.loads(second.stdout),result)
        self.assertEqual(self.snapshot(),after)
        self.assertEqual({k:v for k,v in before.items() if k != 'catalog.sqlite3'},{k:v for k,v in after.items() if k != 'catalog.sqlite3'})
        self.assertEqual(len(self.fixture.store.list('dataset_versions')),3)

    def test_static_help_and_unknown_arguments_never_echo_raw_input(self):
        help_result = self.process(['--help']); self.assertEqual(help_result.returncode,0); self.assertIn(b'inspect',help_result.stdout)
        self.assertEqual(help_result.stderr,b'')
        for args in ([],['PRIVATE_SECRET_COMMAND'],['inspect','--PRIVATE_SECRET_PATH','x'],['--data-r','PRIVATE_SECRET_PATH']):
            completed = self.process(args); self.assertEqual(completed.returncode,2); self.assertEqual(completed.stderr,b'')
            value = json.loads(completed.stdout); self.assertEqual(value['issue'],{'code':'ARGUMENTS_INVALID'})
            self.assertNotIn('PRIVATE_SECRET',str(value)); self.assertIsNone(value['result'])

    def test_duplicate_flags_including_equals_and_abbreviations_fail_before_inputs(self):
        for extra in (['--data-root','PRIVATE_SECRET_TARGET'],['--data-root=PRIVATE_SECRET_TARGET']):
            with patch.object(cli,'_input_file') as reader: code,result = cli.run(self.args()+extra)
            self.assertEqual(code,2); self.assertEqual(result['issue'],{'code':'CLI_ARGUMENT_INVALID'})
            reader.assert_not_called(); self.assertNotIn('PRIVATE_SECRET',str(result))
        args = self.args(); args[1] = '--data-r'
        with patch.object(cli,'_input_file') as reader: self.assertEqual(cli.run(args)[0],2); reader.assert_not_called()

    def test_strict_input_json_invalid_utf8_duplicate_nonfinite_depth_and_boundaries(self):
        path = self.paths[0]; original = path.read_bytes()
        for raw in (b'\xff',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e9999}',
                    b'{"x":"\\ud800"}',b'{"x":9007199254740992}',b'{"x":'+b'['*17+b'0'+b']'*17+b'}'):
            path.write_bytes(raw)
            with patch.object(cli,'inspect_stored_quality_report') as child: code,result = cli.run(self.args())
            self.assertEqual(code,2); self.assertIsNone(result['result']); child.assert_not_called()
        path.write_bytes(original+b' '*(cli.MAX_INPUT_BYTES-len(original)))
        self.assertEqual(cli.run(self.args())[0],0)
        path.write_bytes(path.read_bytes()+b' ')
        self.assertEqual(cli.run(self.args())[1]['issue'],{'code':'INPUT_FILE_LIMIT'})

    def test_missing_catalog_wrong_table_and_path_changes_no_constructor(self):
        self.fixture.store.db.unlink()
        with patch.object(cli,'Store') as ctor: code,result = cli.run(self.args('register'))
        self.assertEqual(code,2); ctor.assert_not_called(); self.assertFalse(self.fixture.store.db.exists())
        connection = sqlite3.connect(self.fixture.store.db)
        try: connection.execute('CREATE TABLE records (kind TEXT,id TEXT,body TEXT)'); connection.commit()
        finally: connection.close()
        with patch.object(cli,'Store') as ctor: code,result = cli.run(self.args('register'))
        self.assertEqual(result['issue'],{'code':'CATALOG_SCHEMA_INVALID'}); ctor.assert_not_called()
        args = self.args('register'); args[2] = str(self.root/'never-created')
        self.assertEqual(cli.run(args)[0],2); self.assertFalse((self.root/'never-created').exists())

    def test_constructor_explicit_recover_false_and_ro_schema_query(self):
        actual_connect = cli.sqlite3.connect; connections = []
        def record_connect(*args,**kwargs):
            connections.append((args,kwargs)); return actual_connect(*args,**kwargs)
        actual_store = cli.Store
        with patch.object(cli.sqlite3,'connect',side_effect=record_connect),patch.object(cli,'Store',wraps=actual_store) as ctor:
            code,result = cli.run(self.args('register'))
        self.assertEqual(code,0); ctor.assert_called_once_with(self.root,recover_jobs=False)
        self.assertTrue(connections[0][1]['uri']); self.assertTrue(connections[0][0][0].endswith('?mode=ro'))

    def test_inspect_malformed_child_clears_payload_and_private_issue(self):
        valid = cli.inspect_stored_quality_report(self.root,self.f.image,self.f.mask,self.f.identity,self.f.metadata,self.fixture.sidecar)
        for value in ({**valid,'execution_authorized':0},{**valid,'stored_report_files_verified':1},
                      {**valid,'issue':{'code':'PRIVATE_SECRET_PATH','field':'report'}}):
            with patch.object(cli,'inspect_stored_quality_report',return_value=value): code,result = cli.run(self.args())
            self.assertEqual(code,2); self.assertIsNone(result['result']); self.assertNotIn('PRIVATE_SECRET_PATH',str(result))

    def test_register_malformed_or_constructor_exception_classified_uncertain(self):
        with patch.object(cli,'register_stored_quality_report',return_value={'private':'PRIVATE_SECRET'}): code,result = cli.run(self.args('register'))
        self.assertEqual(code,3); self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED'); self.assertIsNone(result['result'])
        with patch.object(cli,'Store',side_effect=RuntimeError('PRIVATE_CONSTRUCTOR_PATH')): code,result = cli.run(self.args('register'))
        self.assertEqual(code,3); self.assertNotIn('PRIVATE_CONSTRUCTOR_PATH',str(result))

    def test_postcommit_exception_preserves_row_and_cannot_claim_rollback(self):
        actual = cli.register_stored_quality_report
        def commit_then_fail(*args):
            actual(*args); raise RuntimeError('PRIVATE_POSTCOMMIT')
        with patch.object(cli,'register_stored_quality_report',side_effect=commit_then_fail): code,result = cli.run(self.args('register'))
        self.assertEqual(code,3); self.assertIsNone(result['result']); self.assertEqual(len(self.fixture.store.list('dataset_versions')),3)
        self.assertNotIn('PRIVATE_POSTCOMMIT',str(result))

    def test_valid_blocked_child_and_unconfirmed_child_exitcodes(self):
        (self.root/'quality.json').write_bytes(b'BROKEN_REPORT')
        code,result = cli.run(self.args()); self.assertEqual(code,2); self.assertEqual(len(result['result']),23)
        self.assertEqual(result['status'],'BLOCKED'); self.assertIsNone(result['issue'])
        code,result = cli.run(self.args('register')); self.assertEqual(code,2); self.assertEqual(len(result['result']),22)
        self.assertFalse(result['result']['registration_attempted'])
        # Restore stored files only as explicit temporary fixture setup.
        (self.root/'quality.json').unlink(); (self.root/self.fixture.sidecar).unlink(); self.fixture.fixture.write()
        actual = cli.register_stored_quality_report
        from app.data import quality_report_registration
        def fail(*args): raise RuntimeError('PRIVATE_REGISTRY')
        with patch.object(quality_report_registration,'register_version',side_effect=fail): code,result = cli.run(self.args('register'))
        self.assertEqual(code,3); self.assertTrue(result['result']['registration_attempted'])


if __name__ == '__main__': unittest.main()
