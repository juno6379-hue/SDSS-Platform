"""분할 복구 계획의 원본 보존·누출 제외·stale 거부 계약시험."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from backend.app.ml.split_planning import digest,plan_split_repair,write_plan


class SplitPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.manifest=self.root/'source.json';self.readiness=self.root/'readiness.json'
        self.splits={'a':'train','b':'val','c':'test'}
        self.rows=[{'province':p,'year':2021,'scene_id':f'scene-{p}','source_group':f'group-{p}',
                    'quality_status':'quality_eligible','split':self.splits[p],
                    'patch_sha256':{'image':str(i+1)*64}} for i,p in enumerate(self.splits)]
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.manifest.write_text(json.dumps({'synthetic':True,'scenes':self.rows}),encoding='utf-8')
        self.sha=digest(self.manifest)

    def plan(self,**kwargs):
        return plan_split_repair(self.manifest,self.sha,province_splits=self.splits,**kwargs)

    def readiness_fixture(self):
        doc={'input_manifests':[{'path':self.manifest.name,'sha256':self.sha}],
             'patch_counts_by_split':{'train':1,'val':1,'test':1},
             'policy':{'province_splits':self.splits,'patch_size':256,'min_valid_fraction':.8,
                       'min_patches_per_split':{'train':1,'val':1,'test':1},'min_patches':3},
             'class_counts_by_split':{s:[100]*9 for s in self.splits.values()},
             'class_patch_counts_by_split':{s:[0]*9 for s in self.splits.values()}}
        self.readiness.write_text(json.dumps(doc),encoding='utf-8')
        return {'readiness_path':self.readiness,'readiness_sha256':digest(self.readiness),'data_root':self.root}

    def test_cross_split_source_component_keeps_test_and_never_reassigns_rows(self):
        # source_group과 scene_id가 연결하는 전이적 충돌을 하나로 처리한다.
        self.rows[0]['source_group']='scene-b';self.rows[1]['source_group']='scene-c';self.save()
        before=self.manifest.read_bytes();report=self.plan()
        self.assertEqual(report['retained_row_indexes'],[2])
        self.assertEqual(report['excluded_row_indexes'],[0,1])
        self.assertEqual(len(report['conflicts']),1)
        self.assertEqual(report['conflicts'][0]['keep_split'],'test')
        self.assertEqual(report['projected_after']['eligible_patches_by_split'],{'test':1,'val':0,'train':0})
        candidate=self.root/'new/candidate.json';output=self.root/'new/report.json'
        write_plan(report,output,derived_manifest=candidate)
        generated=json.loads(candidate.read_text(encoding='utf-8'))
        self.assertEqual(generated['scenes'],[self.rows[2]])
        self.assertEqual(generated['lineage']['source_manifest']['sha256'],self.sha)
        self.assertEqual(self.manifest.read_bytes(),before)
        self.assertFalse(generated['learning_ready']);self.assertFalse(report['training_executed'])

    def test_no_conflicts_is_reproducible_and_default_writer_creates_report_only(self):
        report=self.plan();again=self.plan()
        self.assertEqual(report['derived_manifest_version'],again['derived_manifest_version'])
        self.assertEqual(report['retained_row_indexes'],[0,1,2]);self.assertEqual(report['conflicts'],[])
        write_plan(report,self.root/'plan.json')
        self.assertEqual(set(p.name for p in self.root.iterdir()),{'source.json','plan.json'})

    def test_duplicate_recorded_image_identity_across_different_scene_names_is_excluded(self):
        self.rows[1]['patch_sha256']=copy.deepcopy(self.rows[2]['patch_sha256']);self.save()
        report=self.plan()
        self.assertEqual(report['excluded_row_indexes'],[1])
        self.assertFalse(report['spatial_overlap_rechecked'])

    def test_wrong_manifest_sha_and_unknown_provenance_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            plan_split_repair(self.manifest,'0'*64,province_splits=self.splits)
        self.rows[0].pop('scene_id');self.save()
        with self.assertRaisesRegex(ValueError,'scene_id'):
            self.plan()

    def test_stale_source_after_planning_never_writes_output(self):
        report=self.plan();self.manifest.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'stale'):
            write_plan(report,self.root/'plan.json')
        self.assertFalse((self.root/'plan.json').exists())

    def test_stale_readiness_source_reference_is_rejected(self):
        args=self.readiness_fixture()
        doc=json.loads(self.readiness.read_text());doc['input_manifests'][0]['sha256']='0'*64
        self.readiness.write_text(json.dumps(doc),encoding='utf-8');args['readiness_sha256']=digest(self.readiness)
        with self.assertRaisesRegex(ValueError,'stale'):
            self.plan(**args)

    def test_class_projection_uses_bounds_and_does_not_claim_bare_repair(self):
        self.rows[1]['scene_id']=self.rows[2]['scene_id'];self.save()
        report=self.plan(**self.readiness_fixture())
        impact=report['class_impact']
        self.assertFalse(impact['exact_after_counts_computed']);self.assertFalse(impact['bare_shortage_resolved'])
        self.assertTrue(impact['by_split']['val']['class_representation_can_worsen'])
        self.assertEqual(impact['by_split']['val']['class_pixel_lower_bounds'],[0]*9)
        self.assertEqual(report['degraded_province_year_cells'],[{'cell':'b/2021','before':1,'after':0}])
        self.assertFalse(report['ready_for_training'])

    def test_existing_outputs_source_and_stale_readiness_cannot_be_overwritten(self):
        args=self.readiness_fixture();report=self.plan(**args)
        for path in [self.manifest,self.readiness]:
            with self.assertRaisesRegex(ValueError,'덮어쓰지'):
                write_plan(report,path)
        self.readiness.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'stale'):
            write_plan(report,self.root/'plan.json')
        self.assertFalse((self.root/'plan.json').exists())


if __name__=='__main__':
    unittest.main()
