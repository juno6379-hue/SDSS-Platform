"""Isolated228 only: Temp metadata, mocked gate, no real source/raster/HTTP."""
import copy,hashlib,json,types,unittest
from pathlib import Path
from unittest.mock import patch
from backend.app.ml import manifest_resource_profile as profile
from backend.app.ml.split_json_io import BoundedJSONIO
from backend.app.ml import split_json_io as bounded
from backend.app.ml import candidate_materialization as material
from backend.app.ml import candidate_staging as staging
from backend.app.ml import candidate_readiness_qa as qa
from backend.app.ml import candidate_qa_comparison as comparison
from scripts import prepare_priority_candidate164 as cli
import test_candidate_materialization as mf
import test_candidate_readiness_qa as qf
import test_candidate_qa_comparison as cf

ROOT=Path(__file__).resolve().parents[1]
def original(name):
    module=types.ModuleType('backend.app.ml.original228_'+name);module.__package__='backend.app.ml'
    path=ROOT/'baseline-code/backend/app/ml'/str(name+'.py')
    exec(compile(path.read_text('utf-8'),str(path),'exec'),module.__dict__)
    return module
class Profile228Tests(unittest.TestCase):
    def test_default_artifacts_byte_equal_to_original_and_old_reader_stays_strict(self):
        f=mf.CandidateMaterializationTests();f.setUp();self.addCleanup(f.tearDown)
        old=original('candidate_materialization');oldout=f.f.workspace/'old-package'
        old.materialize_split_candidate(f.f.root,f.paths,f.pins,oldout,evidence_root=f.f.workspace)
        f.run_package()
        for name in ('plan.json','candidate.json','receipt.json'):
            self.assertEqual((f.out/name).read_bytes(),(oldout/name).read_bytes())
    def test_explicit_materialization_staging_v2_and_old_contract_fail_closed(self):
        f=mf.CandidateMaterializationTests();f.setUp();self.addCleanup(f.tearDown)
        evidence=f.f.workspace/'evidence';evidence.mkdir();f.out=evidence/'new-package'
        moved=evidence/'saved.json';f.saved.rename(moved);f.saved=moved;f.paths['saved_plan']=moved
        receipt=material.materialize_split_candidate(f.f.root,f.paths,f.pins,f.out,evidence_root=evidence,manifest_profile=profile.NAME)
        self.assertEqual(receipt['schema_version'],2);self.assertEqual(receipt['manifest_profile'],profile.MARKER)
        with self.assertRaises(ValueError):staging._receipt_contract(receipt,f.pins)
        stamp=f.f.sha(f.out/'receipt.json');out=f.f.root/'new-stage'
        staged=staging.stage_split_candidate(f.f.root,f.out,stamp,f.pins,out,evidence_root=evidence,manifest_profile=profile.NAME)
        self.assertEqual(staged['manifest_profile'],profile.MARKER);self.assertEqual(staged['schema_version'],2)
        self.assertFalse(staged['ready_for_training'])
    def test_qa_v2_same_profile_and_default_rejection(self):
        f=qf.CandidateReadinessQATests();f.setUp();self.addCleanup(f.tearDown)
        with profile.scope(profile.NAME):f.stage=profile.stamp(f.stage)
        f.write('staging_receipt',f.stage);f.refresh()
        with patch.object(qa,'run',side_effect=f.fake_run):
            receipt=qa.assess_staged_candidate(f.data,f.paths,f.pins,f.out,manifest_profile=profile.NAME)
        self.assertEqual(receipt['schema_version'],2);self.assertEqual(receipt['manifest_profile'],profile.MARKER)
        self.assertFalse(receipt['ready_for_training'])
    def test_comparison_and_api_explicit_selection_old_reader_and_profile_tamper(self):
        f=cf.CandidateQAComparisonTests();f.setUp();self.addCleanup(f.tearDown)
        with profile.scope(profile.NAME):
            f.stage=profile.stamp(f.stage);f.qa=profile.stamp(f.qa)
        f.documents['staging_receipt_sha256']=f.stage;f.documents['qa_receipt_sha256']=f.qa
        f.write('staging_receipt_sha256')
        f.qa['inputs']['staging_receipt']['sha256']=f.sha(f.paths['staging_receipt_sha256'])
        f.qa['inputs']['staging_receipt']['bytes']=f.paths['staging_receipt_sha256'].stat().st_size
        f.write('qa_receipt_sha256');f.pins={k:f.sha(p) for k,p in f.paths.items()}
        f.refs={k:{'path':str(p),'bytes':p.stat().st_size} for k,p in f.paths.items()}
        with self.assertRaises(ValueError):f.project()
        with self.assertRaises(ValueError):original('candidate_qa_comparison').project_candidate_qa(f.documents,f.pins,f.refs,data_root_literal=str(f.root))
        with profile.scope(profile.NAME):self.assertEqual(f.project()['status'],'BLOCKED')
        response=f.client.post('/v1/diagnostics/candidate-readiness-comparison?manifest_profile='+profile.NAME,json=f.pins)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(f.client.post('/v1/diagnostics/candidate-readiness-comparison?manifest_profile=bad',json=f.pins).status_code,400)
        self.assertEqual(f.client.post('/v1/diagnostics/candidate-readiness-comparison',json=f.pins).status_code,503)
        f.stage['manifest_profile']['sha256']='0'*64
        with profile.scope(profile.NAME),self.assertRaises(ValueError):f.project()
    def test_profile_exact_name_scope_reset_and_legacy_receipts(self):
        for bad in ('bad','128m','',True,{},128):
            with self.assertRaises(ValueError):
                with profile.scope(bad):pass
        with profile.scope(profile.NAME):
            self.assertEqual(BoundedJSONIO(material.POLICY).input_caps['source'],128*1024**2)
            self.assertEqual(BoundedJSONIO(material.POLICY).input_caps['readiness'],16*1024**2)
            with self.assertRaises(ValueError):profile.receipt({'schema_version':1})
        self.assertIsNone(profile.active());self.assertEqual(BoundedJSONIO(material.POLICY).input_caps['source'],64*1024**2)
        self.assertEqual(profile.receipt({'schema_version':1}),{'schema_version':1})
    def test_rows_nodes_depth_io_and_output_budget_fail_closed(self):
        with profile.scope(profile.NAME) as budget:
            io=BoundedJSONIO(material.POLICY)
            io.measure({'scenes':[{}]*3000},'candidate')
            with self.assertRaisesRegex(ValueError,'MANIFEST_ROW_LIMIT'):io.measure({'scenes':[{}]*2999,'historical_noneligible_patches':[{},{}]},'candidate')
            with patch.object(bounded,'DESCRIPTOR',{**profile.DESCRIPTOR,'max_nodes':10}),self.assertRaisesRegex(ValueError,'MANIFEST_NODE_LIMIT'):io.measure({'scenes':[{}]*20},'candidate')
            deep={};at=deep
            for _ in range(34):at['next']={};at=at['next']
            with self.assertRaises(ValueError):io.measure(deep,'candidate')
            budget._maximum=4
            with self.assertRaisesRegex(ValueError,'MANIFEST_JSON_IO_LIMIT'):profile.charge(5)
        with profile.scope(profile.NAME):
            small=copy.deepcopy(material.POLICY);small['output_caps']['candidate']=64
            with self.assertRaises(ValueError):BoundedJSONIO(small).measure({'large':'x'*65},'candidate')
    def test_164_cli_explicit_choice_and_no_flag_preserves_default(self):
        args=['--data-root',str(ROOT/'evidence'),'--source',str(ROOT/'evidence/source.json'),'--source-sha256','a'*64,'--policy',str(ROOT/'evidence/policy.json'),'--policy-sha256','b'*64,'--run-id','synthetic228']
        with patch.object(cli,'prepare',return_value={'status':'PINNED_CANDIDATE_QA_COMPLETED','candidate_eligible':{}}) as prepare:
            self.assertEqual(cli.main(args+['--manifest-profile',profile.NAME]),0)
            self.assertEqual(prepare.call_args.kwargs['manifest_profile'],profile.NAME)
            self.assertEqual(cli.main(args),0);self.assertIsNone(prepare.call_args.kwargs['manifest_profile'])
        with self.assertRaises(SystemExit):cli.main(args+['--manifest-profile','bad'])

    def test_real_164_cli_entire_metadata_pipeline_with_mock_native_gate(self):
        import tempfile
        from backend.app.ml.readiness import default_policy
        from backend.app.ml.readiness_connectivity_adapter import failure_capture
        from scripts import run_experiment
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as directory:
            base=Path(directory);data=base/'data';data.mkdir();evidence=base/'evidence/integration';evidence.mkdir(parents=True)
            source=data/'source.json';policy=data/'policy.json'
            document={'synthetic':True,'scenes':[{'province':'banten','year':'2021','quality_status':'quality_insufficient',
                'source_group':'banten/synthetic','scene_id':'synthetic','image_path':str(data/'missing-image.tif'),
                'label_path':str(data/'missing-label.tif'),'quality_mask_path':str(data/'missing-quality.tif')}]}
            source.write_text(json.dumps(document),encoding='utf-8');policy_doc=default_policy();policy.write_text(json.dumps(policy_doc),encoding='utf-8')
            def fake_assess(manifests,root,policy_arg,**kwargs):
                path=Path(manifests[0]);pin=hashlib.sha256(path.read_bytes()).hexdigest();refs=[{'path':path.relative_to(data).as_posix(),'sha256':pin}]
                capture=failure_capture();capture.update(capture_status='NOT_CAPTURED_BUDGET',scene_count=1,supplied_eligible_patch_sum=0)
                return {'schema_version':1,'status':'blocked','ready_for_training':False,'scientific_accuracy_validated':False,
                    'policy':copy.deepcopy(policy_doc),'blockers':[{'code':'CLASS_COVERAGE'}],
                    'patch_counts_by_split':dict.fromkeys(('train','val','test'),0),'input_manifests':refs,
                    'verified_files':[{'path':refs[0]['path'],'sha256':pin,'kind':'collection_manifest'}],
                    'input_signature':{'band_names':policy_doc['band_names'],'class_names':['x']*9,'label_source':'esri_io'},
                    'class_counts_by_split':{k:[0]*9 for k in ('train','val','test')},
                    'class_patch_counts_by_split':{k:[0]*9 for k in ('train','val','test')},'connectivity_diagnostics':capture,'prepared_payload':None}
            args=['--data-root',str(data),'--source',str(source),'--source-sha256',hashlib.sha256(source.read_bytes()).hexdigest(),
                  '--policy',str(policy),'--policy-sha256',hashlib.sha256(policy.read_bytes()).hexdigest(),'--run-id','profile228-chain','--manifest-profile',profile.NAME]
            with patch.object(cli,'ROOT',base),patch.object(cli,'assess',side_effect=fake_assess),patch.object(run_experiment,'assess',side_effect=fake_assess):
                self.assertEqual(cli.main(args),0)
            package=evidence/'priority164-profile228-chain/candidate-package/receipt.json'
            package_value=json.loads(package.read_text('utf-8'))
            self.assertEqual(package_value['manifest_profile'],profile.MARKER);self.assertEqual(package_value['schema_version'],2)
            for leaf in ('stage/staging-receipt.json','qa/qa-receipt.json'):
                value=json.loads((data/'priority164-profile228-chain'/leaf).read_text('utf-8'))
                self.assertEqual(value['manifest_profile'],profile.MARKER);self.assertEqual(value['schema_version'],2)


    def test_both_import_names_share_only_the_explicit_operation_budget(self):
        from app.ml import manifest_resource_profile as alias
        from app.ml.split_json_io import BoundedJSONIO as AliasIO
        self.assertTrue(Path(alias.__file__).resolve().is_relative_to(ROOT))
        self.assertIsNone(alias.active())
        with profile.scope(profile.NAME) as budget:
            self.assertIs(alias.active(),budget)
            self.assertEqual(AliasIO(material.POLICY).input_caps['source'],128*1024**2)
            alias.charge(17)
            self.assertEqual(budget.bytes,17)
        self.assertIsNone(alias.active());self.assertIsNone(profile.active())

if __name__=='__main__':unittest.main()
