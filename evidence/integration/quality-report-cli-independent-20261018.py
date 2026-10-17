"""Independent143: explicit CLI boundary, temporary fixtures only.

Fixture construction is reused from frozen142 independent evidence; no old
test cases are executed or counted. Product CLI tests are not imported.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASE = 'e3262a3acb09f89a48124cfc9f32c20bb923975a'
SOURCE = 'scripts/quality_report_cli.py'
TEST = 'tests/test_quality_report_cli.py'
OBS = []

def sha(raw): return hashlib.sha256(raw).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

fixture142 = load(ROOT/'evidence/integration/quality-report-registration-independent-20261018.py', 'independent143_fixture142')

class Independent(unittest.TestCase):
    def test_00_frozen_source_and_test_hashes(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),'a6fb6388674ef41ab30329ff55dcb1291e1221cb7d9d8068c7dd6689f5eed87d')
        self.assertEqual(sha((ROOT/TEST).read_bytes()),'37dd83beb849cc985ce4539d959be88b5de464731c21194816ec7e3cb8f0c3d1')

    def fixture(self, actual=False):
        return fixture142.Independent.fixture(self, actual=actual)

    def arguments(self, args, command='inspect'):
        store, root, image, mask, identity, metadata, uri = args
        inputs = root/'명시 CLI 입력'; inputs.mkdir(exist_ok=True)
        paths = []
        for name, value in zip(('image-manifest','mask-manifest','report-identity','report-metadata'), (image,mask,identity,metadata)):
            path = inputs/(name+'.json')
            path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8')
            paths.extend(('--'+name,str(path)))
        return [command,'--data-root',str(root),*paths,'--manifest-output-uri',uri]

    def process(self, args):
        environment = dict(os.environ)
        environment['PYTHONPATH'] = os.pathsep.join(str(ROOT/p) for p in ('.runtime','backend','tests'))
        environment['PYTHONIOENCODING'] = 'utf-8'
        return subprocess.run([sys.executable,str(ROOT/SOURCE),*args],cwd=ROOT,env=environment,capture_output=True,timeout=60)

    def response(self, completed, exit_code):
        self.assertEqual(completed.returncode,exit_code,completed.stderr.decode('utf-8',errors='replace'))
        self.assertEqual(completed.stderr,b'')
        text=completed.stdout.decode('utf-8')
        self.assertEqual(len(text.splitlines()),1)
        value=json.loads(text)
        self.assertEqual(set(value),{'schema_version','scope','command','status','issue','result'})
        self.assertIs(type(value['schema_version']),int)
        self.assertEqual(value['schema_version'],1)
        self.assertEqual(value['scope'],'EXPLICIT_QUALITY_REPORT_CLI_ONLY')
        return value

    def test_01_actual_subprocess_inspect_without_catalog_and_no_store_calls(self):
        args=self.fixture(actual=True); store,root=args[:2]
        argv=self.arguments(args);store.db.unlink();before=fixture142.files(root)
        value=self.response(self.process(argv),0)
        self.assertEqual(value['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        self.assertEqual(len(value['result']),23);self.assertEqual(fixture142.files(root),before)
        with patch.object(cli,'Store',side_effect=AssertionError('Store forbidden')),patch.object(cli.sqlite3,'connect',side_effect=AssertionError('SQL forbidden')):
            code,result=cli.run(argv)
        self.assertEqual(code,0);self.assertEqual(result,value);self.assertEqual(fixture142.files(root),before)
        OBS.append({'actual':'subprocess inspect with no catalog.sqlite3','same_files':True,'inprocess_guard_Store_and_SQL_calls':0})

    def test_02_actual_register_replay_and_readonly_consumers(self):
        args=self.fixture(actual=True);store,root=args[:2];argv=self.arguments(args,'register')
        before=fixture142.files(root);rows=fixture142.dbrows(store.db)
        value=self.response(self.process(argv),0);child=value['result']
        self.assertEqual(value['status'],'REPORT_REGISTERED_UNAPPROVED');self.assertEqual(len(child),22)
        self.assertEqual(len(fixture142.dbrows(store.db)),3)
        self.assertTrue(all(fixture142.dbrows(store.db)[k]==v for k,v in rows.items()))
        self.assertTrue(all(fixture142.files(root)[k]==v for k,v in before.items() if k!='catalog.sqlite3'))
        replay_before=fixture142.files(root);replay=self.response(self.process(argv),0)
        self.assertEqual(replay,value);self.assertEqual(fixture142.files(root),replay_before)
        refs=child['fixed_refs'];pins=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'))
        with patch.object(store,'connect',lambda:fixture142.ro(store)),patch.object(store,'put',side_effect=AssertionError('write')):
            q=fixture142.read_registered_quality_mask_files(store,*pins)
            binary=fixture142.inspect_registered_binary_mask_values(store,*pins)
        self.assertEqual(q['status'],'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertEqual(binary['counts'],{'valid_pixels':128,'invalid_pixels':128,'total_pixels':256})
        self.assertEqual(fixture142.files(root),replay_before)
        OBS.append({'actual':'subprocess report-only registration 2 to 3 rows, byte-identical replay and readonly131133', 'counts':binary['counts'],'operating_registration':0})

    def test_03_missing_invalid_catalog_and_schema_no_creation(self):
        for case in ('missing','opaque','wrong_schema','view'):
            args=self.fixture();store,root=args[:2];argv=self.arguments(args,'register');store.db.unlink()
            if case=='opaque':store.db.write_bytes(b'not sqlite')
            if case in ('wrong_schema','view'):
                connection=sqlite3.connect(store.db)
                try:
                    connection.execute('CREATE TABLE records(x TEXT)' if case=='wrong_schema' else 'CREATE VIEW records AS SELECT 1 AS kind,2 AS id,3 AS body');connection.commit()
                finally:connection.close()
            before=fixture142.files(root);value=self.response(self.process(argv),2)
            self.assertEqual(value['status'],'BLOCKED');self.assertIsNone(value['result']);self.assertEqual(fixture142.files(root),before)

    def test_04_actual_argument_errors_and_help_do_not_leak_secret(self):
        secret='PRIVATE_DO_NOT_ECHO_143'
        for argv in ([],[secret],['inspect','--unknown',secret],['register','--data-root',secret],['inspect','--data-ro',secret]):
            completed=self.process(argv);value=self.response(completed,2)
            self.assertNotIn(secret,completed.stdout.decode('utf-8'));self.assertEqual(value['issue'],{'code':'ARGUMENTS_INVALID'})
            self.assertNotIn('Traceback',completed.stdout.decode('utf-8'))
        completed=self.process(['--help']);self.assertEqual(completed.returncode,0);self.assertEqual(completed.stderr,b'')
        self.assertIn(b'inspect',completed.stdout);self.assertNotIn(secret,completed.stdout.decode('utf-8'))

    def test_05_actual_strict_json_and_size_before_constructor(self):
        args=self.fixture();store,root=args[:2];argv=self.arguments(args,'register');path=Path(argv[argv.index('--image-manifest')+1])
        samples=[b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e999}',b'{"x":9007199254740992}',b'\xff',b'{"x":"\\ud800"}',b'['*17+b']'*17,b' '*262145]
        for raw in samples:
            path.write_bytes(raw);before=fixture142.files(root)
            value=self.response(self.process(argv),2);self.assertIsNone(value['result']);self.assertEqual(fixture142.files(root),before)
        with patch.object(cli,'Store',side_effect=AssertionError('constructor')) as ctor:
            code,value=cli.run(argv)
        ctor.assert_not_called();self.assertEqual(code,2)

    def test_05b_repeated_options_and_missing_sources_no_registration(self):
        args=self.fixture();store,root=args[:2];argv=self.arguments(args,'register')
        for option in ('--data-root','--image-manifest','--mask-manifest','--report-identity','--report-metadata','--manifest-output-uri'):
            before=fixture142.files(root)
            value=self.response(self.process(argv+[option,argv[argv.index(option)+1]]),2)
            self.assertIsNone(value['result']);self.assertEqual(fixture142.files(root),before)
        connection=sqlite3.connect(store.db)
        try:connection.execute('DELETE FROM records WHERE kind=?',('dataset_versions',));connection.commit()
        finally:connection.close()
        before=fixture142.files(root);value=self.response(self.process(argv),2)
        self.assertEqual(value['status'],'BLOCKED');self.assertFalse(value['result']['registration_attempted'])
        self.assertEqual(fixture142.files(root),before);self.assertEqual(fixture142.dbrows(store.db),{})

    def test_06_inprocess_inspect_child_tamper_and_mutation(self):
        args=self.fixture();argv=self.arguments(args);good=fixture142.inspect_stored_quality_report(*args[1:])
        for edit in (lambda x:x.update(execution_authorized=0),lambda x:x.update(stored_report_files_verified=1),lambda x:x.update(extra='PRIVATE'),lambda x:x.update(scope='PRIVATE')):
            child=copy.deepcopy(good);edit(child)
            with patch.object(cli,'inspect_stored_quality_report',return_value=child):code,value=cli.run(argv)
            self.assertEqual(code,2);self.assertIsNone(value['result']);self.assertNotIn('PRIVATE',json.dumps(value))
        parent=copy.deepcopy(good);copier=cli._copy_json;changed=[]
        def mutate(actual,*parameters):
            answer=copier(actual,*parameters)
            if actual is parent:
                parent['report_manifest_draft']['source']['institution']='PRIVATE_POST_VALIDATION';changed.append(1)
            return answer
        with patch.object(cli,'inspect_stored_quality_report',return_value=parent),patch.object(cli,'_copy_json',side_effect=mutate):code,value=cli.run(argv)
        self.assertEqual(changed,[1]);self.assertEqual(code,0);self.assertNotIn('PRIVATE_POST_VALIDATION',json.dumps(value))

    def test_07_inprocess_post_constructor_error_and_real_commit_uncertainty(self):
        for case in ('constructor','before_commit','after_commit','corrupt_after_commit'):
            args=self.fixture();store,root=args[:2];argv=self.arguments(args,'register');real=cli.register_stored_quality_report
            if case=='constructor':guard=patch.object(cli,'Store',side_effect=RuntimeError('PRIVATE_CONSTRUCTOR'))
            else:
                def faulty(*params):
                    if case=='before_commit':raise RuntimeError('PRIVATE_BEFORE')
                    result=real(*params)
                    if case=='after_commit':raise RuntimeError('PRIVATE_AFTER')
                    result['execution_authorized']=True;return result
                guard=patch.object(cli,'register_stored_quality_report',side_effect=faulty)
            with guard:code,value=cli.run(argv)
            self.assertEqual(code,3);self.assertEqual(value['status'],'REGISTRATION_OUTCOME_UNCONFIRMED');self.assertIsNone(value['result'])
            self.assertNotIn('PRIVATE',json.dumps(value));self.assertEqual(len(fixture142.dbrows(store.db)),3 if case in ('after_commit','corrupt_after_commit') else 2)
        OBS.append({'explicit_fault_injection':'constructor / before commit / actual commit then error or contaminated return', 'actual_post_commit_rows':3,'rollback_retry_delete':0})

    def test_08_actual_input_symlink_permission_skip(self):
        args=self.fixture();argv=self.arguments(args);path=Path(argv[argv.index('--image-manifest')+1]);target=path.with_name('explicit-original.json');path.rename(target)
        try:
            try:os.symlink(target,path)
            except OSError as error:self.skipTest(f'actual symlink unavailable winerror={getattr(error,"winerror",None)} errno={error.errno}')
            before=fixture142.files(args[1]);self.response(self.process(argv),2);self.assertEqual(fixture142.files(args[1]),before)
        finally:
            if path.is_symlink():
                self.assertEqual(path.parent,target.parent);self.assertEqual(path.resolve(),target);path.unlink()
            if not path.exists():target.rename(path)

if __name__=='__main__':
    cli=load(ROOT/SOURCE,'independent143_product_cli')
    old=fixture142.OLD+[fixture142.SOURCE,fixture142.TEST]
    before={p:sha((ROOT/p).read_bytes()) for p in old}
    baseline={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==h for p,h in before.items()}
    started=time.perf_counter()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    seconds=time.perf_counter()-started
    unchanged={p:sha((ROOT/p).read_bytes())==h for p,h in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_EXPLICIT_REPORT_CLI_TEMP_ONLY','git_baseline':BASE,
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
      'skipped':len(result.skipped),'skip_reasons':[reason for _,reason in result.skipped],
      'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),
      'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),'separate_git_baseline_matches':baseline,
      'old_sources_unchanged':unchanged,'observations':OBS,
      'actual_scope':'Fresh Temp GTiff/SQLite fixture, subprocess inspect/register/replay, readonly131133; no existing product test cases executed.',
      'mock_scope':'Explicit inprocess constructor and child-output faults, actual-commit-then-error, post-copy mutable output mutation.',
      'operating_store_access':False,'operating_writes':0,'training':0,'inference':0,
      'api_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Store constructor is intentionally used for register after readonly catalog checks; its mkdir/CREATE IF NOT EXISTS are normal no-op intent, not a universal physical-write guarantee.',
        'Constructor-started or malformed post-registration output can hide a committed report; UNCONFIRMED does not mean rollback or absence.',
        'Sequential filesystem/SQLite observations are not atomic, an OS sandbox, resource/SLA guarantee or institution/scientific/execution approval.',
        'Actual symlink creation depends on Windows privilege; permission failures are SKIP, not mock successes.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(baseline.values()) and all(unchanged.values()) else 1)
