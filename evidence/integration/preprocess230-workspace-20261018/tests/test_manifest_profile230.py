"""230 isolated only. Temp synthetic files; no operating DATA/network/native QA."""
import asyncio,ast,copy,contextvars,hashlib,json,os,tempfile,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.app.ml import manifest_resource_profile as p
from backend.app.ml import candidate_staging as staging
from backend.app.ml import split_json_io as bounded
from backend.app.ml import readiness
from backend.app.ml.candidate_materialization import POLICY
from backend.app.ml.split_json_io import _stamp
from scripts import prepare_priority_candidate164 as cli
import test_collection_budget_status as bf
import test_ml_readiness as rf
import test_find_bare_targets173 as f173
import test_propose_deficit_centers182 as f182
from app import collection_budget_status as budget
from app.collection_status import collection_status
from app.collection_priority_status import candidate_quality
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class Profile230Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def test_copy_counts_both_directions_and_checks_before_destination_open(self):
        source=self.root/'candidate.JSON';source.write_bytes(b'12345678');target=self.root/'copy'
        with p.scope(p.NAME) as usage:
            staging._copy_bytes(source,target,_stamp(source.stat()),sha(source),128*1024**2)
            self.assertEqual((usage.reads,usage.writes,usage.bytes),(8,8,16))
        target2=self.root/'no-destination'
        with p.scope(p.NAME) as usage:
            usage._maximum=15
            with self.assertRaises(p.ProfileResourceError):staging._copy_bytes(source,target2,_stamp(source.stat()),sha(source),128*1024**2)
            self.assertFalse(target2.exists());self.assertEqual(usage.bytes,0)
    def test_copy_partial_write_failure_preserves_measured_bytes(self):
        source=self.root/'candidate';source.write_bytes(b'abcdefgh');target=self.root/'partial';original=Path.open
        class Partial:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def write(self,data):self.stream.write(data[:3]);raise OSError('synthetic partial')
        def opened(path,*a,**kw):
            stream=original(path,*a,**kw)
            return Partial(stream) if path==target else stream
        with p.scope(p.NAME) as usage,patch.object(Path,'open',opened):
            with self.assertRaises(OSError):staging._copy_bytes(source,target,_stamp(source.stat()),sha(source),128*1024**2)
            self.assertEqual((usage.reads,usage.writes),(8,3))
        self.assertEqual(target.read_bytes(),b'abc')
    def test_164_snapshot_uses_bounded_copy_with_actual_partial_accounting(self):
        source=self.root/'source';source.write_bytes(b'abcdefgh');target=self.root/'partial';pin=sha(source);original=Path.open
        class Partial:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*a):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def write(self,data):self.stream.write(data[:3]);raise OSError('synthetic partial')
        def opened(path,*a,**kw):
            stream=original(path,*a,**kw)
            return Partial(stream) if path==target else stream
        with p.scope(p.NAME) as usage,patch.object(Path,'open',opened):
            with self.assertRaises(OSError):cli.copy_pinned(source,target,pin)
            self.assertEqual((usage.reads,usage.writes),(16,3))
        self.assertEqual(target.read_bytes(),b'abc')
    def test_json_output_precheck_and_actual_partial_write(self):
        target=self.root/'output';original=Path.open;document={'value':'abcdef'}
        with p.scope(p.NAME) as usage:
            usage._maximum=1
            with self.assertRaises(p.ProfileResourceError):cli.write_new(target,document)
            self.assertFalse(target.exists());self.assertEqual(usage.bytes,0)
        class Partial:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*a):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def write(self,data):self.stream.write(data[:1]);raise OSError('synthetic partial')
        def opened(path,*a,**kw):
            stream=original(path,*a,**kw)
            return Partial(stream) if path==target else stream
        for route in ('164','bounded'):
            if target.exists():target.unlink()
            with p.scope(p.NAME) as usage,patch.object(Path,'open',opened):
                io=bounded.BoundedJSONIO(POLICY)
                with self.assertRaises(OSError):
                    if route=='164':cli.write_new(target,document)
                    else:io.write(target,document,'plan',io.measure(document,'plan'))
                self.assertEqual((usage.reads,usage.writes),(0,1))
            self.assertEqual(target.stat().st_size,1)

    def test_173_cli_snapshot_and_proposal_writes_are_measured(self):
        from scripts import find_bare_targets173 as module
        (self.root/'data').mkdir();(self.root/'evidence/integration').mkdir(parents=True)
        source=self.root/'data/source';source.write_bytes(b'{"scenes":[]}');boundary=self.root/'data/boundary';boundary.write_bytes(b'{}')
        args=SimpleNamespace(run_id='synthetic',source=source,source_sha256=sha(source),boundary=boundary,boundary_sha256=sha(boundary),window_stride=256,province=None)
        result={'local_label_crops_read':0,'windows_scanned':0,'qualified_dense_inside_windows':0,'split_qualified_counts':{}}
        with p.scope(p.NAME) as usage,patch.object(module,'ROOT',self.root),patch.object(module,'discover',return_value=result):
            self.assertEqual(module._run(args),0)
            written=sum(x.stat().st_size for base in (self.root/'data/bare173-synthetic',self.root/'evidence/integration/bare173-synthetic') for x in base.rglob('*') if x.is_file())
            self.assertEqual(usage.writes,written)
        target=self.root/'should-not-open'
        with p.scope(p.NAME) as usage:
            usage._maximum=2
            with self.assertRaises(p.ProfileResourceError):p.write_new_json_bytes(target,b'123','source')
            self.assertFalse(target.exists())

    def test_json_role_is_extension_independent_and_oversize_refused_before_open(self):
        for name in ('SOURCE.JSON','source'):
            source=self.root/name;source.write_bytes(b'{"scenes":[]}')
            with p.scope(p.NAME) as usage:
                self.assertEqual(cli.digest(source),sha(source));self.assertEqual(usage.bytes,13)
        source=self.root/'oversize'
        with source.open('wb') as stream:stream.truncate(128*1024**2+1)
        with p.scope(p.NAME),patch.object(Path,'open',side_effect=AssertionError('no read permitted')):
            with self.assertRaisesRegex(p.ProfileResourceError,'MANIFEST_JSON_FILE_LIMIT'):p.bounded_json_digest(source,'source')
    def test_growing_hash_reads_only_initial_bound_then_aborts(self):
        source=self.root/'source';source.write_bytes(b'12345678');original=Path.open;changed=[]
        class Growing:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def read(self,size):
                value=self.stream.read(size)
                if not changed:
                    changed.append(True)
                    with original(source,'ab') as writer:writer.write(b'grow')
                return value
        def opened(path,*a,**kw):
            stream=original(path,*a,**kw)
            return Growing(stream) if path==source and a[0]=='rb' else stream
        with p.scope(p.NAME) as usage,patch.object(Path,'open',opened):
            with self.assertRaisesRegex(p.ProfileResourceError,'MANIFEST_JSON_CHANGED'):p.bounded_json_digest(source,'source')
            self.assertEqual(usage.bytes,8)
    def test_profile_is_hard_ceiling_and_readonly_not_caller_controlled(self):
        for key in ('source','candidate'):
            policy=copy.deepcopy(POLICY);policy['input_caps'][key]=256*1024**2
            with p.scope(p.NAME),self.assertRaises(p.ProfileResourceError):bounded.BoundedJSONIO(policy)
        policy=copy.deepcopy(POLICY);policy['max_depth']=64
        with p.scope(p.NAME),self.assertRaises(p.ProfileResourceError):bounded.BoundedJSONIO(policy)
        policy=copy.deepcopy(POLICY);policy['input_caps']['source']=1024;policy['max_depth']=8
        with p.scope(p.NAME) as usage:
            io=bounded.BoundedJSONIO(policy);self.assertEqual(io.input_caps['source'],1024);self.assertEqual(io.max_depth,8)
            with self.assertRaises(AttributeError):usage.maximum=999999
            with self.assertRaises(TypeError):p.DESCRIPTOR['manifest_bytes']=256*1024**2
    def test_resource_error_aborts_entire_qa_legacy_metadata_error_stays_scene_blocker(self):
        f=rf.ReadinessTests();f.setUp();self.addCleanup(f.tearDown)
        old=readiness.bounded_json_digest
        def fail(path,role):
            if role=='evidence':raise p.ProfileResourceError('MANIFEST_JSON_FILE_LIMIT')
            return old(path,role)
        with p.scope(p.NAME),patch.object(readiness,'bounded_json_digest',side_effect=fail),patch.object(readiness,'read',wraps=readiness.read) as raster:
            with self.assertRaisesRegex(p.ProfileResourceError,'MANIFEST_JSON_FILE_LIMIT'):readiness.assess([f.manifest],f.root,f.policy,test_mode=True)
            self.assertEqual(raster.call_count,2)
        (f.root/'evidence0.json').write_bytes(b'{broken')
        report=readiness.assess([f.manifest],f.root,f.policy,test_mode=True)
        self.assertTrue(any(x['code']=='SCENE_QA_ERROR' for x in report['blockers']))
        self.assertEqual(sum(report['patch_counts_by_split'].values()),2)
    def test_dual_import_has_same_error_class_and_budget(self):
        from app.ml import manifest_resource_profile as alias
        self.assertIs(alias.ProfileResourceError,p.ProfileResourceError)
        with p.scope(p.NAME) as usage:self.assertIs(alias.active(),usage)
    def test_independent_threads_and_async_tasks_do_not_leak_scope(self):
        barrier=threading.Barrier(2)
        def worker(_):
            with p.scope(p.NAME) as usage:
                barrier.wait(timeout=5);p.charge(3);return usage
        with ThreadPoolExecutor(2) as pool:a,b=pool.map(worker,range(2))
        self.assertIsNot(a,b);self.assertEqual((a.bytes,b.bytes),(3,3));self.assertIsNone(p.active())
        async def run():
            async def task():
                with p.scope(p.NAME) as usage:
                    await asyncio.sleep(0);p.charge(5);return usage
            a,b=await asyncio.gather(task(),task());self.assertIsNot(a,b)
            with p.scope(p.NAME) as parent:
                async def child():self.assertIs(p.active(),parent);p.charge(2)
                await asyncio.create_task(child());self.assertEqual(parent.bytes,2)
            self.assertIsNone(p.active())
        asyncio.run(run())
    def test_shared_copied_context_serializes_precheck_read_charge(self):
        source=self.root/'source';source.write_bytes(b'12345678');started=threading.Event();release=threading.Event();second=threading.Event();opened=[];original=Path.open
        class Blocking:
            def __init__(self,s):self.s=s
            def __enter__(self):return self
            def __exit__(self,*args):self.s.close()
            def fileno(self):return self.s.fileno()
            def read(self,n):started.set();release.wait(2);return self.s.read(n)
        def open_file(path,*a,**kw):
            stream=original(path,*a,**kw)
            if path==source and a[0]=='rb':opened.append(path);return Blocking(stream)
            return stream
        with p.scope(p.NAME) as usage,patch.object(Path,'open',open_file):
            usage._maximum=12;one=contextvars.copy_context();two=one.copy()
            def first():return one.run(p.bounded_json_digest,source,'source')
            def other():
                second.set()
                try:two.run(p.bounded_json_digest,source,'source')
                except p.ProfileResourceError:return 'BLOCKED_BEFORE_READ'
            with ThreadPoolExecutor(2) as pool:
                a=pool.submit(first);self.assertTrue(started.wait(2));b=pool.submit(other);self.assertTrue(second.wait(2))
                self.assertEqual(len(opened),1);release.set();a.result(3);self.assertEqual(b.result(3),'BLOCKED_BEFORE_READ')
            self.assertEqual((len(opened),usage.bytes),(1,8))
    def config_fixture(self):
        f=bf.BudgetStatusTests();f.setUp();self.addCleanup(f.tearDown)
        cfg=f.root/'runtime/source-profile';cfg.parent.mkdir()
        value={'schema_version':1,'kind':'ROOT_SELECTED_SOURCE_MANIFEST_PROFILE','manifest_profile':dict(p.MARKER),'source_manifest_sha256':sha(f.root/budget.SOURCE)}
        cfg.write_text(json.dumps(value),encoding='utf-8');return f,cfg,value
    def test_budget_root_config_is_explicit_strict_pinned_readonly(self):
        f,cfg,value=self.config_fixture();before={x:x.read_bytes() for x in f.root.rglob('*') if x.is_file()}
        original=budget._read
        with patch.object(budget,'_read',wraps=original) as read:
            result=budget.collection_budget_status(f.root,source_profile_config_path=cfg)
        self.assertTrue(result['available']);self.assertTrue(any(c.args[1]==budget.SOURCE and c.args[2]==128*1024**2 for c in read.call_args_list))
        self.assertEqual(before,{x:x.read_bytes() for x in before})
        for change in (lambda d:d['manifest_profile'].update(name='bad'),lambda d:d['manifest_profile'].update(sha256='0'*64),lambda d:d.update(source_manifest_sha256='0'*64),lambda d:d.update(execute=True),lambda d:d.update(schema_version=True)):
            bad=copy.deepcopy(value);change(bad);cfg.write_text(json.dumps(bad),encoding='utf-8')
            self.assertFalse(budget.collection_budget_status(f.root,source_profile_config_path=cfg)['available'])
        cfg.unlink();self.assertTrue(budget.collection_budget_status(f.root,source_profile_config_path=cfg)['available'])
    def test_config_changes_mid_observation_and_source_drift_are_unconfirmed(self):
        f,cfg,value=self.config_fixture();original=budget._read;done=[]
        def change(*args,**kwargs):
            result=original(*args,**kwargs)
            if args[1]==budget.SOURCE and not done:
                done.append(True);value['source_manifest_sha256']='0'*64;cfg.write_text(json.dumps(value),encoding='utf-8')
            return result
        with patch.object(budget,'_read',side_effect=change):self.assertFalse(budget.collection_budget_status(f.root,source_profile_config_path=cfg)['available'])
        value['source_manifest_sha256']=sha(f.root/budget.SOURCE);cfg.write_text(json.dumps(value),encoding='utf-8')
        (f.root/budget.SOURCE).write_text('{"scenes":[],"changed":true}',encoding='utf-8')
        result=collection_status(f.root,source_profile_config_path=cfg)
        self.assertFalse(result['collection_targets']['available']);self.assertIsNone(result['training_readiness']['current_manifest_sha256'])
    def test_173_182_profile_only_expands_source_and_default_scope_stays_off(self):
        f=f173.BareTargets173Tests();f.setUp();self.addCleanup(f.tearDown)
        result=f.scan(manifest_profile=p.NAME);self.assertEqual(result['manifest_profile'],p.MARKER)
        self.assertNotIn('manifest_profile',f.scan())
        g=f182.DeficitCenters182Tests();g.setUp();self.addCleanup(g.doCleanups)
        document,_=g.run_proposal(manifest_profile=p.NAME);self.assertEqual(document['manifest_profile'],p.MARKER)
        self.assertIsNone(p.active())
    def test_cli_profile_forwarding_and_strict_unknown_choice(self):
        from scripts import find_bare_targets173 as a,propose_deficit_centers182 as b
        args=['--source','source','--source-sha256','0'*64,'--boundary','boundary','--boundary-sha256','1'*64,'--run-id','safe']
        with patch.object(a,'_run',return_value=0) as run:
            self.assertEqual(a.main(args+['--manifest-profile',p.NAME]),0)
            self.assertEqual(run.call_args.kwargs['manifest_profile'],p.NAME)
            a.main(args);self.assertIsNone(run.call_args.kwargs['manifest_profile'])
            with self.assertRaises(SystemExit):a.main(args+['--manifest-profile','automatic'])
            bad=args[:-1]+['../bad']
            with self.assertRaises(SystemExit):a.main(bad)
        args=['--source','source','--source-sha256','0'*64,'--boundary','boundary','--boundary-sha256','1'*64,'--config','config','--config-sha256','2'*64,'--prior-plan','prior','--prior-plan-sha256','3'*64,'--output','out']
        result=({'candidates':[],'target_status':[]},{'source_sha256':'4'*64})
        with patch.object(b,'propose',return_value=result) as run:
            self.assertEqual(b.main(args+['--manifest-profile',p.NAME]),0)
            self.assertEqual(run.call_args.kwargs['manifest_profile'],p.NAME)
            b.main(args);self.assertIsNone(run.call_args.kwargs['manifest_profile'])
            with self.assertRaises(SystemExit):b.main(args+['--manifest-profile','automatic'])

    def test_api_uses_root_internal_path_no_browser_profile_switch(self):
        f,cfg,value=self.config_fixture()
        tree=ast.parse((ROOT/'backend/app/main.py').read_text('utf-8'))
        functions=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('data_collection_status','data_collection_budget_status')]
        for fn in functions:fn.decorator_list=[]
        from starlette.responses import JSONResponse
        namespace={'__package__':'app','app':SimpleNamespace(state=SimpleNamespace(collection_source_profile_path=cfg)),'store':SimpleNamespace(root=f.root),'JSONResponse':JSONResponse}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'<isolated-main-endpoints>','exec'),namespace)
        response=namespace['data_collection_budget_status']();self.assertTrue(json.loads(response.body)['available'])
        status=namespace['data_collection_status']();self.assertTrue(status['collection_targets']['budget_status']['available'])

    def test_ui_default_does_not_inherit_unrelated_parent_profile(self):
        f,cfg,value=self.config_fixture();original=budget._read
        with p.scope(p.NAME) as parent,patch.object(budget,'_read',wraps=original) as read:
            self.assertTrue(budget.collection_budget_status(f.root)['available'])
            self.assertTrue(any(c.args[1]==budget.SOURCE and c.args[2]==64*1024**2 for c in read.call_args_list))
            self.assertEqual(parent.bytes,0)
    def test_v1_published_candidate_is_pinned_cohort_not_v2_comparison_or_current_source(self):
        f,cfg,value=self.config_fixture();folder=f.root/'qa-pinned';folder.mkdir()
        source=folder/'source.json';source.write_bytes(b'{"scenes":[],"old":true}')
        candidate=folder/'candidate.json';candidate.write_bytes(b'{"scenes":[]}')
        report=folder/'readiness.json';counts={'train':1,'val':2,'test':3}
        report.write_text(json.dumps({'schema_version':1,'patch_counts_by_split':counts,'blockers':[{'code':'CLASS_COVERAGE'}]}),encoding='utf-8')
        receipt={'files':[{'path':x.relative_to(f.root).as_posix(),'sha256':sha(x)} for x in (source,candidate,report)],
            'by_split':counts,'blocker_count':1,'source_manifest_sha256':sha(source),'scene_split_conflicts':[],
            'recorded_at':'2026-10-18T00:00:00Z'}
        pointer=f.root/'first-group-training-priority/latest-candidate.json';pointer.parent.mkdir()
        pointer.write_text(json.dumps(receipt),encoding='utf-8')
        with patch('app.ml.candidate_qa_comparison.compare_candidate_qa',side_effect=AssertionError('distinct consumer')):
            result=collection_status(f.root,source_profile_config_path=cfg)
        observed=result['candidate_quality'];self.assertTrue(observed['available'])
        self.assertFalse(observed['source_matches_current_manifest']);self.assertFalse(observed['ready_for_training'])
        self.assertEqual(observed['eligible_total'],6)
        self.assertEqual(observed['scope'],'PINNED_CANDIDATE_COHORT_NOT_AUTOMATIC_CURRENT_COLLECTION')
        candidate.write_bytes(b'changed')
        self.assertFalse(collection_status(f.root,source_profile_config_path=cfg)['candidate_quality']['available'])

if __name__=='__main__':unittest.main()
