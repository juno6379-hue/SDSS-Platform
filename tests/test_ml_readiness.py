"""학습 gate의 출처·시기·충분성·train-only 가중치와 출력 붕괴 검사."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from backend.app.ml.readiness import assess, train_only_weights, prediction_check, verify_files, validate_prepared_training, balance_diagnostics, default_policy
from backend.app.ml.readiness import reference_labels, FIRST_GROUP
from backend.app.ml.raster import ESRI_IO_CLASS_NAMES
from backend.app.ml.dataset import file_digest


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.policy={'required_provinces':['a','b','c'],'required_years':[2021],
                     'min_patches':3,'min_patches_per_split':{'train':1,'val':1,'test':1},
                     'required_classes':[1,4],'min_class_pixels_per_split':1}
        self.rows=[]
        for i,province in enumerate(['a','b','c']):
            profile={'driver':'GTiff','crs':'EPSG:32748','width':256,'height':256,'transform':from_origin(500000+i*20000,9000000,10,10),'nodata':0}
            for name,count,dtype,values in [('image',6,'uint16',np.full((6,256,256),1000+i,dtype='uint16')),
                                            ('quality',1,'uint8',np.ones((1,256,256),dtype='uint8'))]:
                with rasterio.open(self.root/f'{name}{i}.tif','w',**profile,count=count,dtype=dtype) as dst:
                    dst.write(values)
            label=np.full((1,256,256),10,dtype='uint8');label[:,:,128:]=40
            with rasterio.open(self.root/f'label{i}.tif','w',**profile,count=1,dtype='uint8') as dst:
                dst.write(label)
            metadata=self.root/f'product{i}.xml';metadata.write_text('<explicit_synthetic_metadata_fixture/>',encoding='utf-8')
            evidence={'status':'verified_product_metadata','product_id':f'scene{i}',
                      'band_names':['B02','B03','B04','B08','B11','B12'],'scale':[.0001]*6,'offset':[-.1]*6,
                      'source_metadata_path':metadata.name,'source_metadata_sha256':file_digest(metadata),
                      'source_url':'https://example.invalid/explicit-synthetic-metadata'}
            ep=self.root/f'evidence{i}.json';ep.write_text(json.dumps(evidence),encoding='utf-8')
            self.rows.append({'aoi':province,'year':2021,'datetime':'2021-06-01T00:00:00Z','scene_id':f'scene{i}',
                              'bands':evidence['band_names'],'image_path':f'image{i}.tif','label_path':f'label{i}.tif',
                              'quality_mask_path':f'quality{i}.tif','label_source':'worldcover','label_year':2021,
                              'label_dataset_version':'WorldCover2021v200',
                              'label_source_url':'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/fixture.tif',
                              'normalization':{'scale':evidence['scale'],'offset':evidence['offset'],'evidence_path':ep.name,'evidence_sha256':file_digest(ep)}})
        self.manifest=self.root/'inputs.json';self.save()

    def save(self):
        self.manifest.write_text(json.dumps({'synthetic':True,'scenes':self.rows}),encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def test_explicit_test_gate_passes_and_all_files_are_hash_bound(self):
        report=assess([self.manifest],self.root,self.policy,test_mode=True)
        self.assertTrue(report['ready_for_training']);self.assertTrue(report['synthetic'])
        self.assertEqual(report['patch_counts_by_split'],{'train':1,'val':1,'test':1})
        self.assertFalse(report['scientific_accuracy_validated'])
        self.assertEqual(report['prepared_payload']['band_names'],self.rows[0]['bands'])
        (self.root/'product0.xml').write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'변경'):
            verify_files(report['verified_files'],self.root)

    def test_real_gate_cannot_reduce_1000_or_use_synthetic_as_actual(self):
        report=assess([self.manifest],self.root,{**self.policy,'required_provinces':FIRST_GROUP})
        self.assertFalse(report['ready_for_training'])
        self.assertEqual(report['policy']['min_patches'],1000)
        self.assertIn('SYNTHETIC_NOT_REAL',[row['code'] for row in report['blockers']])

    def test_westcover_2021_cannot_be_declared_as_2020_reference(self):
        for row in self.rows:
            row.update(year=2020,datetime='2020-06-01T00:00:00Z',label_year=2020)
        self.save()
        report=assess([self.manifest],self.root,{**self.policy,'required_years':[2020]},test_mode=True)
        self.assertFalse(report['ready_for_training'])
        self.assertIn('WORLDCOVER_YEAR_REUSE',[row['code'] for row in report['blockers']])

    def test_product_evidence_hash_mismatch_blocks_training(self):
        self.rows[0]['normalization']['evidence_sha256']='incorrect';self.save()
        report=assess([self.manifest],self.root,self.policy,test_mode=True)
        self.assertFalse(report['ready_for_training'])
        self.assertIn('SCENE_QA_ERROR',[row['code'] for row in report['blockers']])

    def test_inference_product_contract_checks_actual_image_and_metadata(self):
        from backend.app.ml.normalization import verify_inference_normalization
        row=self.rows[0];image=self.root/row['image_path']
        source={'scene_id':row['scene_id'],'image_sha256':file_digest(image),'band_names':row['bands']}
        result=verify_inference_normalization(row['normalization'],source,image,row['bands'],self.root)
        self.assertEqual(result['scene_id'],'scene0')
        for wrong in ({**source,'image_sha256':'wrong'},{**source,'scene_id':'another_product'},
                      {**source,'band_names':list(reversed(row['bands']))}):
            with self.assertRaises(ValueError):
                verify_inference_normalization(row['normalization'],wrong,image,row['bands'],self.root)
        with self.assertRaisesRegex(ValueError,'scale/offset'):
            verify_inference_normalization({**row['normalization'],'scale':[.123]*6},source,image,row['bands'],self.root)
        (self.root/'product0.xml').write_text('tampered',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'메타데이터'):
            verify_inference_normalization(row['normalization'],source,image,row['bands'],self.root)

    def test_runner_resume_rejects_changed_plan_before_mutating_experiment(self):
        from unittest.mock import patch
        from scripts.run_experiment import run
        destination=self.root/'results/resume_fixture';destination.mkdir(parents=True)
        old={'status':'paused_training','dataset':{'manifest_path':'prepared.json'}}
        record=destination/'experiment.json';record.write_text(json.dumps(old),encoding='utf-8')
        (self.root/'prepared.json').write_text(json.dumps({'readiness_contract':{'policy':{'required_years':[2020]},'verified_files':[]}}),encoding='utf-8')
        result={'ready_for_training':True,'verified_files':[],'prepared_payload':{'readiness_contract':{'policy':{'required_years':[2021]},'verified_files':[]}}}
        before=file_digest(record)
        with patch('scripts.run_experiment.assess',return_value=result),patch('scripts.run_experiment.train_model') as train:
            with self.assertRaisesRegex(ValueError,'계획'):
                run([],self.root,'readiness.json',execute=True,run_id='resume_fixture',resume=True)
            train.assert_not_called()
        self.assertEqual(before,file_digest(record))

    def test_reference_balance_rejects_dominance_and_rare_patch_concentration(self):
        policy={**default_policy(),'required_classes':[1,4]}
        counts=[0,9000,0,0,1000,0,0,0,0];patches=[0,10,0,0,5,0,0,0,0]
        self.assertTrue(balance_diagnostics(counts,patches,policy)['passed'])
        dominant=balance_diagnostics([0,9900,0,0,100,0,0,0,0],patches,policy)
        self.assertIn('dominant_reference_class',dominant['failures'])
        concentrated=balance_diagnostics(counts,[0,10,0,0,1,0,0,0,0],policy)
        self.assertIn('class4_patch_representation',concentrated['failures'])
        rare=balance_diagnostics([0,5000,4999,0,1,0,0,0,0],patches,policy)
        self.assertIn('class4_pixel_ratio',rare['failures'])

    def test_balance_diagnostics_cannot_count_single_pixel_patch_as_representative(self):
        for i in range(3):
            with rasterio.open(self.root/f'label{i}.tif','r+') as dst:
                labels=dst.read();labels[:]=10;labels[:,0,0]=40;dst.write(labels)
        report=assess([self.manifest],self.root,self.policy,test_mode=True)
        self.assertFalse(report['ready_for_training'])
        self.assertIn('REFERENCE_CLASS_IMBALANCE',[b['code'] for b in report['blockers']])
        self.assertTrue(all(d['class_patch_counts'][4]==0 for d in report['reference_balance_by_split'].values()))

    def test_shared_original_scene_cannot_cross_region_holdout(self):
        # 제품 근거까지 동일 제품으로 수정한 별도 지역은 같은 source group에 묶여야 한다.
        self.rows[1]['source_group']=self.rows[0]['scene_id'];self.save()
        report=assess([self.manifest],self.root,self.policy,test_mode=True)
        self.assertFalse(report['ready_for_training'])
        self.assertEqual(report['province_groups']['a'],report['province_groups']['b'])
        self.assertIn('SPLIT_INDEPENDENCE',[row['code'] for row in report['blockers']])

    def test_weights_are_train_only_and_absent_classes_are_zero(self):
        counts=[0]*9;counts[1]=100;counts[4]=25
        weights=train_only_weights(counts)
        self.assertAlmostEqual(weights[4]/weights[1],2)
        self.assertEqual(weights[0],0)
        self.assertAlmostEqual((weights[1]+weights[4])/2,1)

    def test_more_than_one_class_does_not_hide_near_total_collapse(self):
        matrix=np.zeros((9,9),dtype='int64');matrix[1,2]=999;matrix[4,4]=1
        self.assertFalse(prediction_check(matrix)['passed'])
        matrix[:]=0;matrix[1,1]=100;matrix[4,4]=100
        self.assertTrue(prediction_check(matrix)['passed'])

    def test_ungated_actual_manifest_is_rejected_before_loading_patches(self):
        with self.assertRaisesRegex(ValueError,'gate'):
            validate_prepared_training({'synthetic':False},self.root/'manifest.json',self.root)

    def test_esri_mapping_ignores_clouds_and_preserves_rangeland_meaning(self):
        raw=np.asarray([[[0,1,2,4,5,7,8,9,10,11]]],dtype='uint8')
        mapped=reference_labels(raw,np.ones(raw.shape[1:],dtype=bool),'esri_io')
        self.assertEqual(mapped.tolist(),[[255,0,1,3,4,6,7,8,255,2]])
        self.assertEqual(ESRI_IO_CLASS_NAMES[2],'grass_or_shrub_rangeland')
        self.assertTrue(ESRI_IO_CLASS_NAMES[5].startswith('unused_'))

    def test_mixed_esri_worldcover_and_wrong_esri_year_are_blocked(self):
        self.rows[0].update(label_source='esri_io',label_dataset_version='EsriIOv003',label_source_url='https://example.invalid/48M_20200101-20210101.tif')
        # 두 라벨 모두 실제 임시 파일을 사용하되 제품 의미와 연도 계약은 고의로 불일치시킨다.
        self.save()
        result=assess([self.manifest],self.root,self.policy,test_mode=True)
        self.assertFalse(result['ready_for_training'])
        codes=[entry['code'] for entry in result['blockers']]
        self.assertIn('MIXED_LABEL_TAXONOMY',codes)
        self.assertIn('ESRI_REFERENCE_YEAR',codes)

    def test_duplicate_spatial_observation_same_year_is_not_new_sample(self):
        self.rows[0]['spatial_location_id']='same-location'
        extra={**self.rows[0],'image_path':'second-image.tif','scene_id':'scene-extra'}
        # 위치는 같고 DN/파일은 다르므로 단순 파일 해시 중복 검사와 구분된다.
        with rasterio.open(self.root/'image0.tif') as source:
            profile=source.profile;image=source.read()+1
        with rasterio.open(self.root/'second-image.tif','w',**profile) as destination:
            destination.write(image)
        evidence_path=self.root/'extra-evidence.json'
        evidence=json.loads((self.root/'evidence0.json').read_text(encoding='utf-8'));evidence['product_id']='scene-extra'
        evidence_path.write_text(json.dumps(evidence),encoding='utf-8')
        extra['normalization']={**extra['normalization'],'evidence_path':evidence_path.name,'evidence_sha256':file_digest(evidence_path)}
        self.rows.append(extra);self.save()
        result=assess([self.manifest],self.root,self.policy,test_mode=True)
        self.assertIn('DUPLICATE_SPATIAL_SAMPLE',[entry['code'] for entry in result['blockers']])


if __name__=='__main__':
    unittest.main()
