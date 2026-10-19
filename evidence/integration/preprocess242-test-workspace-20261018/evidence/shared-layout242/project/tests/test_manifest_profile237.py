"""237 Temp-only metadata I/O contract tests. No operating DATA/HTTP/QA."""
import hashlib,json,os,tempfile,unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from manifest_profile_baseline_fixtures import load_baseline
from backend.app.ml import manifest_resource_profile as p
from scripts import find_bare_targets173 as find,propose_deficit_centers182 as propose
from backend.app.data import candidates
from app import collection_status as status,collection_priority_status as priority
import test_propose_deficit_centers182 as f182
ROOT=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
@contextmanager
def observed_reads(paths):
    paths={Path(x) for x in paths};opened=[];counts={};original=Path.open
    class Stream:
        def __init__(self,path,stream):self.path=path;self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def __enter__(self):return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def read(self,*args):
            raw=self.stream.read(*args);counts[self.path]=counts.get(self.path,0)+len(raw if isinstance(raw,bytes) else raw.encode('utf-8'));return raw
    def opening(path,*args,**kwargs):
        if path in paths:
            opened.append(path);return Stream(path,original(path,*args,**kwargs))
        return original(path,*args,**kwargs)
    with patch.object(Path,'open',opening):yield opened,counts
class Metadata237Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        status._HASH_CACHE.clear()
    def put(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8');return path
    def candidate(self):
        source=self.put('pinned/source',{'scenes':[]});candidate=self.put('pinned/candidate',{'scenes':[]})
        counts={'train':1,'val':2,'test':3};report=self.put('pinned/report',{'patch_counts_by_split':counts,'blockers':['bare']})
        files=[{'path':x.relative_to(self.root).as_posix(),'sha256':sha(x)} for x in (source,candidate,report)]
        pointer=self.put('first-group-training-priority/latest-candidate.json',{'files':files,'by_split':counts,'blocker_count':1,'source_manifest_sha256':files[0]['sha256'],'recorded_at':'synthetic','scene_split_conflicts':[]})
        return source,candidate,report,pointer
    def bare(self):
        rows=[{'province':x,'candidates':0,'support_clear':0,'overlap':0,'local_invalid':0} for x in priority.PROVINCES]
        report=self.put('bare/report.json',{'ui_summary':{'schema_version':1,'status':'LOCAL_TARGET_REVIEW_FINISHED','execution_supported':False,'actual_quality_verified':False,'scientific_accuracy_validated':False,'current_manifest_sha256':'a'*64,'recorded_at':'2026-10-18T00:00:00Z','summary_by_province':rows,'candidate_total':0}})
        pointer=self.put('first-group-training-priority/latest-bare-review.json',{'schema_version':1,'report':{'path':report.relative_to(self.root).as_posix(),'sha256':sha(report)}})
        return report,pointer
    def test_role_caps_preserve_small_inputs_and_missing_role_fails(self):
        self.assertEqual(p.JSON_ROLE_CAPS['source'],128*1024**2);self.assertEqual(p.JSON_ROLE_CAPS['candidate'],128*1024**2)
        for role in ('boundary','local_config','local_plan','proposal','evidence'):self.assertEqual(p.JSON_ROLE_CAPS[role],2*1024**2)
        self.assertEqual(p.JSON_ROLE_CAPS['status_report'],16*1024**2);self.assertEqual(p.JSON_ROLE_CAPS['pointer'],65536)
        path=self.put('unknown',{})
        with p.scope(p.NAME),patch.object(Path,'open',side_effect=AssertionError('no open')):
            with self.assertRaisesRegex(p.ProfileResourceError,'ROLE_REQUIRED'):status.same_hash(path,'x')
    def test_small_roles_and_new_status_cap_refuse_before_open(self):
        path=self.root/'oversized'
        for role in ('pointer','boundary','local_config','local_plan','proposal','status_report'):
            with path.open('wb') as stream:stream.truncate(p.JSON_ROLE_CAPS[role]+1)
            with p.scope(p.NAME) as usage,patch.object(Path,'open',side_effect=AssertionError('must not open')):
                with self.assertRaisesRegex(p.ProfileResourceError,'FILE_LIMIT'):p.read_metadata(path,role)
                self.assertEqual(usage.bytes,0)
    def test_one_scope_exact_duplicate_reads_and_second_refusal_before_open(self):
        path=self.put('metadata',{'x':1});size=path.stat().st_size
        with p.scope(p.NAME) as usage,observed_reads([path]) as (opened,counts):
            usage._maximum=2*size
            p.read_metadata(path,'boundary');p.read_metadata(path,'boundary')
            self.assertEqual((usage.reads,counts[path],len(opened)),(2*size,2*size,2))
            with self.assertRaises(p.ProfileResourceError):p.read_metadata(path,'boundary')
            self.assertEqual(len(opened),2)
    def test_173_boundary_pin_all_rechecks_and_low_budget(self):
        path=self.put('boundary',{'type':'FeatureCollection','features':[]});pin=sha(path)
        with p.scope(p.NAME) as usage,observed_reads([path]) as (opened,counts):
            for _ in range(3):find.pin(self.root,path,pin,2*1024**2,json_role='boundary')
            self.assertEqual(usage.reads,3*path.stat().st_size);self.assertEqual(usage.reads,counts[path])
        with p.scope(p.NAME) as usage,patch.object(Path,'open',side_effect=AssertionError('no open')):
            usage._maximum=0
            with self.assertRaises(p.ProfileResourceError):find.pin(self.root,path,pin,2*1024**2,json_role='boundary')
    def test_173_cli_every_json_read_and_write_measured(self):
        source=self.put('data/source',{'scenes':[]});boundary=self.put('data/boundary',{'type':'FeatureCollection','features':[]})
        (self.root/'evidence/integration').mkdir(parents=True)
        args=SimpleNamespace(run_id='synthetic',source=source,source_sha256=sha(source),boundary=boundary,boundary_sha256=sha(boundary),window_stride=256,province=None)
        result={'local_label_crops_read':0,'windows_scanned':0,'qualified_dense_inside_windows':0,'split_qualified_counts':{}}
        proposal=self.root/'evidence/integration/bare173-synthetic/proposal.json'
        with p.scope(p.NAME) as usage,patch.object(find,'ROOT',self.root),patch.object(find,'discover',return_value=result),observed_reads([source,boundary,proposal]) as (_,counts):
            self.assertEqual(find._run(args),0);self.assertEqual(usage.reads,sum(counts.values()))
            self.assertEqual(counts[source],2*source.stat().st_size);self.assertEqual(counts[boundary],2*boundary.stat().st_size)
            self.assertEqual(counts[proposal],proposal.stat().st_size)
            outputs=list((self.root/'data/bare173-synthetic').glob('*'))+list(proposal.parent.glob('*'))
            self.assertEqual(usage.writes,sum(x.stat().st_size for x in outputs))
    def fixture182(self):
        f=f182.DeficitCenters182Tests();f.setUp();self.addCleanup(f.doCleanups)
        values={'root':f.root,'source':f.source,'source_sha':sha(f.source),'boundary':f.boundary,'boundary_sha':sha(f.boundary),'config':f.config,'config_sha':sha(f.config),'prior_plan':f.prior,'prior_sha':sha(f.prior),'output':f.output}
        return f,values
    def test_182_entire_json_consumption_matches_physical_reads(self):
        f,values=self.fixture182();paths=[f.source,f.boundary,f.config,f.prior,f.output]
        with p.scope(p.NAME) as usage,observed_reads(paths) as (_,counts):
            doc,_=propose.propose(**values)
            self.assertEqual(usage.reads,sum(counts.values()))
            self.assertEqual(usage.writes,f.output.stat().st_size)
            self.assertFalse(doc['collector_consumption_approved'])
            for path,multiplier in ((f.source,3),(f.boundary,7),(f.config,3),(f.prior,5),(f.output,3)):
                self.assertEqual(counts[path],multiplier*path.stat().st_size,path.name)
    def test_candidates_validator_exact_repeated_reads_and_budget_before_open(self):
        f,_=self.fixture182();paths=[f.boundary,f.prior];expected=sha(f.prior)
        with p.scope(p.NAME) as usage,observed_reads(paths) as (_,counts):
            result=candidates.validate_candidate_plan(f.prior,f.boundary)
            self.assertEqual(result['source_sha256'],expected)
            self.assertEqual(usage.reads,2*f.boundary.stat().st_size+2*f.prior.stat().st_size)
        with p.scope(p.NAME) as usage,patch.object(Path,'open',side_effect=AssertionError('no open')):
            usage._maximum=0
            with self.assertRaises(p.ProfileResourceError):candidates.validate_candidate_plan(f.prior,f.boundary)
    def test_validator_rejects_replacement_between_parse_and_final_hash(self):
        for target_name in ('prior','boundary'):
            f,_=self.fixture182();target=getattr(f,target_name);original=candidates.read_metadata;changed=[]
            def replace(path,role,*args):
                result=original(path,role,*args)
                if path==f.prior and not changed:
                    changed.append(True);value=json.loads(target.read_bytes());value['changed_after_parse']=True
                    alternate=target.with_name('replacement');alternate.write_text(json.dumps(value),encoding='utf-8');alternate.replace(target)
                return result
            with p.scope(p.NAME),patch.object(candidates,'read_metadata',side_effect=replace):
                with self.assertRaisesRegex(p.ProfileResourceError,'CHANGED'):candidates.validate_candidate_plan(f.prior,f.boundary)
    def test_182_default_artifact_bytes_equal_frozen230(self):
        f,values=self.fixture182()
        baseline=load_baseline('centers230','scripts._baseline_centers237','scripts')
        before=f.data/'baseline.json';baseline.propose(**(values|{'output':before}))
        propose.propose(**values)
        self.assertEqual(f.output.read_bytes(),before.read_bytes())

    def test_growth_reads_initial_bytes_then_aborts(self):
        path=self.put('growth',{'x':1});size=path.stat().st_size;original=Path.open;once=[]
        class Growing:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def read(self,n):
                raw=self.stream.read(n)
                if not once:
                    once.append(True)
                    with original(path,'ab') as out:out.write(b' ')
                return raw
        def opened(target,*a,**kw):return Growing(original(target,*a,**kw)) if target==path else original(target,*a,**kw)
        with p.scope(p.NAME) as usage,patch.object(Path,'open',opened):
            with self.assertRaisesRegex(p.ProfileResourceError,'CHANGED'):p.read_metadata(path,'boundary')
            self.assertEqual(usage.reads,size)
    def test_cache_hit_no_read_role_change_rechecks_and_replacement_invalidates(self):
        path=self.put('cache',{'x':1});expected=sha(path);size=path.stat().st_size
        with p.scope(p.NAME) as usage,observed_reads([path]) as (opened,_):
            self.assertTrue(status.same_hash(path,expected,json_role='source'));before=usage.reads
            usage._maximum=before
            self.assertTrue(status.same_hash(path,expected,json_role='source'));self.assertEqual((usage.reads,len(opened)),(size,1))
            with self.assertRaises(p.ProfileResourceError):status.same_hash(path,expected,json_role='candidate')
        replacement=self.put('new',{'x':1});replacement.replace(path)
        with p.scope(p.NAME) as usage,observed_reads([path]) as (opened,_):
            self.assertTrue(status.same_hash(path,expected,json_role='source'));self.assertEqual((usage.reads,len(opened)),(size,1))
    def test_cache_hit_still_checks_logical_path_change(self):
        path=self.put('cache',{});expected=sha(path)
        with p.scope(p.NAME):self.assertTrue(status.same_hash(path,expected,json_role='source'))
        identity=p.metadata_identity(path,'source');other=(self.root/'different',identity[1])
        with p.scope(p.NAME),patch.object(status,'metadata_identity',side_effect=[identity,other]):
            with self.assertRaisesRegex(p.ProfileResourceError,'CHANGED'):status.same_hash(path,expected,json_role='source')
    def test_candidate_v1_exact_bytes_and_cache_hit_readiness_reread(self):
        paths=self.candidate();source,candidate,report,pointer=paths
        legacy=priority.candidate_quality(self.root,'later',status.same_hash)
        with p.scope(p.NAME) as usage,observed_reads(paths) as (_,counts),patch('app.ml.candidate_qa_comparison.compare_candidate_qa',side_effect=AssertionError('separate v2')):
            selected=priority.candidate_quality(self.root,'later',status.same_hash)
            self.assertEqual(selected,legacy);self.assertFalse(selected['ready_for_training']);self.assertFalse(selected['source_matches_current_manifest'])
            self.assertEqual(usage.reads,sum(counts.values()));self.assertEqual(counts[report],2*report.stat().st_size)
            old=usage.reads;priority.candidate_quality(self.root,'later',status.same_hash)
            self.assertEqual(usage.reads-old,pointer.stat().st_size+report.stat().st_size)
    def test_candidate_bare_and_read_report_propagate_resource_errors(self):
        self.candidate();self.bare();report=self.put('report',{})
        for invoke in (lambda:priority.candidate_quality(self.root,None,status.same_hash),lambda:priority.bare_target_review(self.root,None),lambda:status.read_report(report,[])):
            with p.scope(p.NAME) as usage,patch.object(Path,'open',side_effect=AssertionError('no open')):
                usage._maximum=0
                with self.assertRaises(p.ProfileResourceError):invoke()
    def test_bare_exact_reads_and_legacy_result_same(self):
        report,pointer=self.bare();legacy=priority.bare_target_review(self.root,'a'*64)
        with p.scope(p.NAME) as usage,observed_reads([report,pointer]) as (_,counts):
            self.assertEqual(priority.bare_target_review(self.root,'a'*64),legacy)
            self.assertEqual(usage.reads,sum(counts.values()));self.assertEqual(usage.reads,report.stat().st_size+pointer.stat().st_size)
    def test_configured_status_resource_failure_is_whole_unconfirmed(self):
        source=self.put('first-group-training-esri-v1/annual-window-report.json',{'scenes':[]})
        config=self.put('runtime/profile',{'schema_version':1,'kind':'ROOT_SELECTED_SOURCE_MANIFEST_PROFILE','manifest_profile':dict(p.MARKER),'source_manifest_sha256':sha(source)})
        oversize=self.root/'first-group-old/run-result.json';oversize.parent.mkdir()
        with oversize.open('wb') as stream:stream.truncate(16*1024**2+1)
        with observed_reads([oversize]) as (opened,_):result=status.collection_status(self.root,source_profile_config_path=config)
        self.assertEqual(result['status'],'UNCONFIRMED');self.assertFalse(result['summary']['learning_ready']);self.assertEqual(opened,[])
    def test_unclassified_verified_entry_fails_explicit_instead_of_unmetered_hash(self):
        source=self.put('first-group-training-esri-v1/annual-window-report.json',{'scenes':[]});unknown=self.put('unknown',{})
        self.put('first-group/training-readiness.json',{'input_manifests':[{'path':source.relative_to(self.root).as_posix(),'sha256':sha(source)}],'verified_files':[{'path':unknown.name,'sha256':sha(unknown)}]})
        config=self.put('runtime/profile',{'schema_version':1,'kind':'ROOT_SELECTED_SOURCE_MANIFEST_PROFILE','manifest_profile':dict(p.MARKER),'source_manifest_sha256':sha(source)})
        with observed_reads([unknown]) as (opened,_):result=status.collection_status(self.root,source_profile_config_path=config)
        self.assertEqual(result['status'],'UNCONFIRMED');self.assertEqual(opened,[])
    def test_verified_kinds_require_context_for_collection_manifest(self):
        source=self.put('first-group-training-esri-v1/annual-window-report.json',{'scenes':[]})
        records=[{'path':source.relative_to(self.root).as_posix(),'sha256':sha(source),'kind':'collection_manifest'}]
        for kind in ('input_image','label','quality_mask','official_product_metadata','normalization_qa'):
            item=self.root/kind
            item.write_bytes(b'{}' if kind=='normalization_qa' else b'binary-or-XML')
            records.append({'path':item.name,'sha256':sha(item),'kind':kind})
        report=self.put('first-group/training-readiness.json',{'input_manifests':[{'path':source.relative_to(self.root).as_posix(),'sha256':sha(source)}],'verified_files':records})
        config=self.put('runtime/profile',{'schema_version':1,'kind':'ROOT_SELECTED_SOURCE_MANIFEST_PROFILE','manifest_profile':dict(p.MARKER),'source_manifest_sha256':sha(source)})
        observed=status.collection_status(self.root,source_profile_config_path=config)
        self.assertTrue(observed['training_readiness']['evidence_matched']);self.assertFalse(observed['summary']['learning_ready'])
        # QA's collection_manifest kind can also name a staged candidate. Its kind
        # alone cannot silently turn it into an original source in this reader.
        candidate=self.put('staged-candidate',{'scenes':[]});document=json.loads(report.read_bytes())
        document['verified_files'][0]={'path':candidate.name,'sha256':sha(candidate),'kind':'collection_manifest'}
        report.write_text(json.dumps(document),encoding='utf-8')
        with observed_reads([candidate]) as (opened,_):result=status.collection_status(self.root,source_profile_config_path=config)
        self.assertEqual(result['status'],'UNCONFIRMED');self.assertEqual(opened,[])

    def test_default_status_exact_result_matches_frozen230_and_dual_import_scope(self):
        self.put('first-group-training-esri-v1/annual-window-report.json',{'scenes':[]})
        self.put('first-group-old/annual-window-report.json',{'scenes':[]});report=self.put('some-report',{'x':1})
        baseline=load_baseline('status230','app._baseline_status237','app')
        clock=SimpleNamespace(now=lambda tz:datetime(2026,10,18,tzinfo=tz))
        with patch.object(status,'datetime',clock),patch.object(baseline,'datetime',clock):self.assertEqual(status.collection_status(self.root),baseline.collection_status(self.root))
        from backend.app import collection_status as other
        from app.ml import manifest_resource_profile as alias
        self.assertIs(p.ProfileResourceError,alias.ProfileResourceError)
        with p.scope(p.NAME) as usage:
            status.read_report(report,[]);other.read_report(report,[])
            self.assertEqual(usage.reads,2*report.stat().st_size)
            usage._maximum=usage.bytes
            with self.assertRaises(alias.ProfileResourceError):other.read_report(report,[])
if __name__=='__main__':unittest.main()
