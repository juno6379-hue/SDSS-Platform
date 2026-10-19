"""합성 래스터로 수행하는 기능시험. 실자료 정확도 검증이 아니다."""
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from backend.app.ml.dataset import split_groups
from backend.app.ml.raster import safe_path, assert_aligned, pixel_areas
from backend.app.ml.service import prepare_dataset, train_model, infer_raster, analyze_change, analyze_timeseries, evaluate_model, metrics, runtime_status


class MLPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.profile={'driver':'GTiff','width':16,'height':16,'crs':'EPSG:32748','transform':from_origin(500000,9000000,10,10),'nodata':255}

    def tearDown(self):
        self.temp.cleanup()

    def write(self,name,data,profile=None):
        if data.ndim==2:
            data=data[None]
        p={**(profile or self.profile),'count':data.shape[0],'dtype':str(data.dtype)}
        with rasterio.open(self.root/name,'w',**p) as dst:
            dst.write(data)
        return name

    def scenes(self):
        scenes=[]
        for i in range(3):
            image=np.full((3,16,16),1000+i*500,dtype='uint16')
            label=np.zeros((16,16),dtype='uint8'); label[:,8:]=1
            profile={**self.profile,'transform':from_origin(500000+i*10000,9000000,10,10)}
            scenes.append({'image_path':self.write(f'image{i}.tif',image,profile),'label_path':self.write(f'label{i}.tif',label,profile),'group':f'region{i}'})
        return scenes

    def test_group_split_is_disjoint_and_reproducible(self):
        groups=split_groups([f'g{i}' for i in range(20)],42)
        self.assertEqual(groups,split_groups(list(groups),42))
        self.assertEqual([list(groups.values()).count(s) for s in ('train','val','test')],[14,3,3])
        with self.assertRaises(ValueError): split_groups(['one','two'])

    def test_path_escape_and_alignment(self):
        with self.assertRaises(ValueError): safe_path(self.root,'../secret')
        with self.assertRaises(ValueError): assert_aligned(self.profile,{**self.profile,'width':17})

    def test_duplicate_or_overlapping_region_rejected(self):
        scenes=self.scenes()
        scenes[1]['image_path']=scenes[0]['image_path']
        with self.assertRaisesRegex(ValueError,'중복 영상'):
            prepare_dataset({'scenes':scenes,'dataset_id':'leak'},self.root)
        scenes=self.scenes()
        # 영상 값이 달라도 지리 범위가 같으면 그룹을 달리 배정할 수 없다.
        scenes[1]['image_path']=self.write('overlap.tif',np.full((3,16,16),2000,dtype='uint16'))
        with self.assertRaisesRegex(ValueError,'중첩 공간'):
            prepare_dataset({'scenes':scenes,'dataset_id':'overlap'},self.root)

    def test_dynamic_world_confidence_and_padding(self):
        scenes=self.scenes()
        probability=np.zeros((9,16,16),dtype='float32'); probability[1]=.9; probability[0]=.1
        probability[:,0,0]=1/9
        for i,scene in enumerate(scenes):
            scene['label_path']=self.write(f'prob{i}.tif',probability,{**self.profile,'transform':from_origin(500000+i*10000,9000000,10,10)})
            scene['label_source']='dynamic_world'
        result=prepare_dataset({'scenes':scenes,'dataset_id':'dw','synthetic':True},self.root)
        self.assertEqual(result['counts'],{'train':1,'val':1,'test':1})
        with np.load(self.root/'datasets/dw'/result['patches'][0]['path']) as patch:
            self.assertEqual(patch['image'].shape,(3,256,256))
            self.assertEqual(patch['label'][0,0],255)
            self.assertEqual(patch['label'][1,1],1)
            self.assertEqual(patch['label'][30,30],255)

    def test_change_area_nodata_and_csv(self):
        a=np.zeros((16,16),dtype='uint8'); b=a.copy(); b[0,0]=1; a[0,1]=255
        report=analyze_change({'t1_path':self.write('t1.tif',a),'t2_path':self.write('t2.tif',b),'output_id':'change'},self.root)
        self.assertEqual(report['changed_area_m2'],100.)
        self.assertEqual(report['valid_pixels'],255)
        self.assertEqual(report['total_area_m2'],25500.)
        self.assertTrue((self.root/report['csv_path']).is_file())
        self.assertTrue((self.root/report['geojson_path']).is_file())
        self.assertEqual(len(report['geometry']['features']),1)
        self.assertEqual(report['geometry']['features'][0]['properties']['from_class'],0)
        self.assertEqual(report['geometry']['features'][0]['properties']['to_class'],1)
        self.assertFalse(report['vector_truncated'])
        with rasterio.open(self.root/report['geotiff_path']) as src:
            self.assertEqual(src.read(1)[0,1],65535)

    def test_vector_cap_preserves_full_raster_statistics(self):
        a=np.zeros((16,16),dtype='uint8'); b=a.copy(); b[0,0]=1; b[3,3]=1
        report=analyze_change({'t1_path':self.write('cap_t1.tif',a),'t2_path':self.write('cap_t2.tif',b),'output_id':'cap','max_features':1},self.root)
        self.assertEqual(report['vector_feature_count'],1)
        self.assertTrue(report['vector_truncated'])
        self.assertEqual(report['changed_area_m2'],200.)

    def test_geodesic_area(self):
        p={**self.profile,'crs':'EPSG:4326','transform':from_origin(106,-6,.001,.001)}
        areas,method=pixel_areas(p)
        self.assertEqual(method,'ellipsoidal_geodesic_m2')
        self.assertTrue(np.all(areas>10000))
        self.assertTrue(np.all(areas<15000))

    def test_known_metrics(self):
        result=metrics(np.asarray([[3,1],[1,3]]))
        self.assertAlmostEqual(result['overall_accuracy'],.75)
        self.assertAlmostEqual(result['mean_iou'],.6)

    def test_worldcover_mapping(self):
        scenes=self.scenes()
        labels=np.full((16,16),10,dtype='uint8'); labels[:,8:]=50
        for i,scene in enumerate(scenes):
            scene.update(label_path=self.write(f'wc{i}.tif',labels,{**self.profile,'transform':from_origin(500000+i*10000,9000000,10,10)}),label_source='worldcover')
        prepared=prepare_dataset({'scenes':scenes,'patch_size':16,'dataset_id':'wc'},self.root)
        with np.load(self.root/'datasets/wc'/prepared['patches'][0]['path']) as patch:
            self.assertEqual(set(np.unique(patch['label'])),{1,6})

    def test_esri_dataset_has_distinct_taxonomy_and_rejects_worldcover_mix(self):
        from backend.app.ml.raster import CLASS_NAMES,ESRI_IO_CLASS_NAMES
        scenes=self.scenes()
        labels=np.resize(np.asarray([0,1,2,4,5,7,8,9,10,11],dtype='uint8'),(16,16))
        for i,scene in enumerate(scenes):
            self.write(f'label{i}.tif',labels,{**self.profile,'transform':from_origin(500000+i*10000,9000000,10,10)})
            scene['label_source']='esri_io'
        mixed=[dict(scene) for scene in scenes];mixed[0]['label_source']='worldcover'
        with self.assertRaisesRegex(ValueError,'혼합'):
            prepare_dataset({'scenes':mixed,'dataset_id':'mixed'},self.root)
        result=prepare_dataset({'scenes':scenes,'dataset_id':'esri','patch_size':16,'synthetic':True},self.root)
        self.assertEqual(result['class_names'],ESRI_IO_CLASS_NAMES)
        self.assertEqual(CLASS_NAMES[2],'grass')
        self.assertEqual(result['class_names'][2],'grass_or_shrub_rangeland')
        self.assertEqual(len(result['label_taxonomy_signature']),64)
        with np.load(self.root/'datasets/esri/0_0_0.npz') as archive:
            self.assertEqual(set(np.unique(archive['label'])),{0,1,2,3,4,6,7,8,255})

    @unittest.skipUnless(importlib.util.find_spec('torch') is not None,'optional torch unavailable')
    def test_esri_inference_masks_reserved_class_and_reports_actual_class_names(self):
        import torch
        from backend.app.ml.network import TinyUNet
        from backend.app.ml.raster import ESRI_IO_CLASS_NAMES
        self.scenes();model=TinyUNet(3)
        with torch.no_grad():
            for value in model.parameters():
                value.zero_()
            model.head.bias[5]=100;model.head.bias[2]=1
        manifest={'bands':[1,2,3],'scale':.0001,'offset':0,'patch_size':16,'class_names':ESRI_IO_CLASS_NAMES,'label_taxonomy_signature':'explicit-fixture','version':'explicit-fixture'}
        torch.save({'state_dict':model.state_dict(),'manifest':manifest,'architecture':'tiny_unet'},self.root/'fixture.pt')
        result=infer_raster({'image_path':'image0.tif','checkpoint_path':'fixture.pt','output_id':'esri-mask'},self.root)
        with rasterio.open(self.root/result['classification_path']) as source:
            self.assertEqual(np.unique(source.read(1)).tolist(),[2])
        self.assertEqual(result['class_names'][2],'grass_or_shrub_rangeland')
        self.assertEqual(result['label_taxonomy_signature'],'explicit-fixture')
        with self.assertRaisesRegex(ValueError,'분류체계'):
            evaluate_model({'checkpoint_path':'fixture.pt','reference_kind':'expert_independent',
                            'label_provenance':'explicit-test-fixture','reviewer':'fixture','group':'new',
                            'label_taxonomy_signature':'worldcover-wrong-taxonomy'},self.root)
        series=analyze_timeseries({'checkpoint_path':'fixture.pt','output_id':'esri-series',
                                 'images':[{'year':year,'image_path':'image0.tif'} for year in (2020,2021)]},self.root)
        self.assertEqual(series['class_names'][2],'grass_or_shrub_rangeland')
        self.assertEqual(series['changes']['2020-2021']['class_names'],ESRI_IO_CLASS_NAMES)

    def test_evaluation_requires_independent_evidence(self):
        with self.assertRaisesRegex(ValueError,'expert_independent'):
            evaluate_model({},self.root)
        with self.assertRaisesRegex(ValueError,'label_provenance'):
            evaluate_model({'reference_kind':'expert_independent'},self.root)

    def test_timeseries_rejects_duplicate_unsorted_or_misaligned_years(self):
        for years in ([2020,2020],[2021,2020]):
            with self.assertRaisesRegex(ValueError,'오름차순'):
                analyze_timeseries({'images':[{'year':year,'image_path':'unused'} for year in years]},self.root)
        scenes=self.scenes()
        with self.assertRaisesRegex(ValueError,'공간 정합'):
            analyze_timeseries({'checkpoint_path':'unused','images':[{'year':2020,'image_path':scenes[0]['image_path']},{'year':2021,'image_path':scenes[1]['image_path']}]},self.root)

    @unittest.skipUnless(importlib.util.find_spec('torch') is not None,'optional torch unavailable')
    def test_six_bands_keep_per_product_normalization_and_require_it_at_inference(self):
        scenes=self.scenes()
        for i,scene in enumerate(scenes):
            profile={**self.profile,'transform':from_origin(500000+i*10000,9000000,10,10)}
            raw=np.stack([np.full((16,16),1000+band*100,dtype='uint16') for band in range(6)])
            self.write(f'image{i}.tif',raw,profile)
            scene['normalization']={'scale':[.0001]*6,'offset':[-i*.01]*6}
        names=['B02','B03','B04','B08','B11','B12']
        prepared=prepare_dataset({'scenes':scenes,'patch_size':16,'synthetic':True,'band_names':names},self.root)
        self.assertEqual(prepared['normalization_mode'],'per_scene_product_metadata')
        self.assertEqual(prepared['band_names'],names)
        with np.load(self.root/'datasets/dataset/1_0_0.npz') as archive:
            self.assertEqual(archive['image'].shape,(6,16,16))
            self.assertAlmostEqual(float(archive['image'][0,0,0]),.09,places=6)
            self.assertAlmostEqual(float(archive['image'][5,0,0]),.14,places=6)
        trained=train_model({'dataset_path':prepared['manifest_path'],'epochs':1,'device':'cpu'},self.root)
        self.assertEqual(trained['input_signature']['channels'],6)
        self.assertEqual(trained['input_signature']['band_names'],names)
        with self.assertRaisesRegex(ValueError,'normalization'):
            infer_raster({'image_path':'image1.tif','checkpoint_path':trained['checkpoint_path']},self.root)
        result=infer_raster({'image_path':'image1.tif','checkpoint_path':trained['checkpoint_path'],'normalization':scenes[1]['normalization'],'output_id':'six'},self.root)
        self.assertEqual(result['valid_pixels'],256)

    @unittest.skipUnless(importlib.util.find_spec('torch') is not None,'optional torch unavailable')
    def test_epoch_resume_matches_uninterrupted_optimizer_and_rng_state(self):
        import torch
        from backend.app.ml.dataset import file_digest
        prepared=prepare_dataset({'scenes':self.scenes(),'patch_size':16,'synthetic':True},self.root)
        payload={'dataset_path':prepared['manifest_path'],'model_id':'resumable','epochs':2,'device':'cpu','epochs_per_call':1}
        paused=train_model(payload,self.root)
        self.assertEqual(paused['training_state'],'paused')
        self.assertEqual(paused['epochs_executed'],1)
        self.assertIsNone(paused['test_metrics'])
        before=file_digest(self.root/paused['resume_path'])
        with self.assertRaisesRegex(ValueError,'설정'):
            train_model({**payload,'resume':True,'lr':.123},self.root)
        self.assertEqual(before,file_digest(self.root/paused['resume_path']))
        resumed=train_model({**payload,'resume':True},self.root)
        continuous=train_model({**payload,'model_id':'continuous','epochs_per_call':2},self.root)
        self.assertEqual(resumed['history'],continuous['history'])
        self.assertEqual(resumed['test_metrics'],continuous['test_metrics'])
        a=torch.load(self.root/resumed['checkpoint_path'],weights_only=True)
        b=torch.load(self.root/continuous['checkpoint_path'],weights_only=True)
        self.assertTrue(all(torch.equal(a['state_dict'][key],b['state_dict'][key]) for key in a['state_dict']))
        with self.assertRaisesRegex(ValueError,'완료된'):
            train_model({**payload,'resume':True},self.root)

    @unittest.skipUnless(importlib.util.find_spec('torch') is not None,'optional torch unavailable')
    def test_time_budget_pause_does_not_publish_unfinished_test_metrics(self):
        prepared=prepare_dataset({'scenes':self.scenes(),'patch_size':16,'synthetic':True},self.root)
        result=train_model({'dataset_path':prepared['manifest_path'],'model_id':'budget','epochs':2,'device':'cpu','max_seconds':1e-9},self.root)
        self.assertEqual(result['training_state'],'paused')
        self.assertEqual(result['epochs_executed'],0)
        self.assertIsNone(result['test_metrics'])
        self.assertTrue(result['discarded_incomplete_epoch'])
        self.assertTrue((self.root/result['resume_path']).is_file())

    @unittest.skipUnless(importlib.util.find_spec('torch') is not None,'optional torch unavailable')
    def test_actual_cpu_train_checkpoint_infer(self):
        prepared=prepare_dataset({'scenes':self.scenes(),'patch_size':16,'synthetic':True,'band_names':['B02','B03','B04']},self.root)
        trained=train_model({'dataset_path':prepared['manifest_path'],'model_id':'test','epochs':2,'device':'cpu',
                             'optimizer':'sgd','lr':.0123,'class_weights':[1.0]*9,'patience':4,'min_delta':.0002,'batch_size':1},self.root)
        self.assertEqual(trained['device'],'cpu')
        self.assertTrue(trained['synthetic'])
        self.assertEqual(len(trained['history']),2)
        self.assertEqual(sum(map(sum,trained['test_metrics']['confusion_matrix'])),256)
        self.assertTrue((self.root/trained['checkpoint_path']).exists())
        import torch
        saved=torch.load(self.root/trained['checkpoint_path'],map_location='cpu',weights_only=True)
        config=saved['training_config']
        self.assertEqual(config,trained['training_config'])
        self.assertEqual(config['optimizer'],'sgd')
        self.assertEqual(config['lr'],.0123)
        self.assertEqual(config['loss'],'cross_entropy')
        self.assertEqual(config['class_weights'],[1.0]*9)
        self.assertEqual(config['batch_size'],1)
        self.assertEqual(config['patience'],4)
        self.assertEqual(config['min_delta'],.0002)
        self.assertEqual(config['precision'],'float32')
        self.assertEqual(config['input_signature']['band_names'],['B02','B03','B04'])
        self.assertEqual(config['input_signature']['band_indices'],[1,2,3])
        self.assertEqual(config['input_signature']['patch_size'],16)
        # 반환 객체를 바꿔도 저장된 실행 설정이 바뀌지 않아야 한다.
        trained['training_config']['lr']=99
        unchanged=torch.load(self.root/trained['checkpoint_path'],map_location='cpu',weights_only=True)
        self.assertEqual(unchanged['training_config']['lr'],.0123)
        disk_report=json.loads((self.root/trained['checkpoint_path']).with_name('report.json').read_text(encoding='utf-8'))
        self.assertEqual(disk_report['training_config']['lr'],.0123)
        with self.assertRaisesRegex(ValueError,'합성'):
            evaluate_model({'checkpoint_path':trained['checkpoint_path'],'reference_kind':'expert_independent','label_provenance':'expert','reviewer':'test','group':'new'},self.root)
        inferred=infer_raster({'image_path':'image0.tif','checkpoint_path':trained['checkpoint_path'],'output_id':'pred'},self.root)
        with rasterio.open(self.root/inferred['classification_path']) as src:
            self.assertEqual(src.crs.to_epsg(),32748)
            self.assertEqual(src.read(1).shape,(16,16))
            self.assertTrue((src.read(1)<9).all())
        quality=np.ones((16,16),dtype='uint8');quality[0,0]=0
        self.write('quality.tif',quality)
        masked=infer_raster({'image_path':'image0.tif','checkpoint_path':trained['checkpoint_path'],'output_id':'masked',
                              'quality_mask_path':'quality.tif','quality_mask_basis':'explicit_synthetic_quality_mask'},self.root)
        self.assertEqual(masked['valid_pixels'],255)
        with rasterio.open(self.root/masked['classification_path']) as src:
            self.assertEqual(src.read(1)[0,0],255)
        # 연차별 영상은 같은 위치를 관측해야 하므로 동일 grid의 합성 시계열을 구성한다.
        for year in (2020,2021,2022):
            self.write(f'year{year}.tif',np.full((3,16,16),1000+(year-2020)*200,dtype='uint16'))
        series=analyze_timeseries({'checkpoint_path':trained['checkpoint_path'],'output_id':'annual',
                                  'images':[{'year':year,'image_path':f'year{year}.tif','source':'synthetic-test'} for year in (2020,2021,2022)]},self.root)
        self.assertEqual(series['years'],[2020,2021,2022])
        self.assertEqual(series['adjacent_pairs'],['2020-2021','2021-2022'])
        self.assertEqual(series['baseline_pairs'],['2020-2021','2020-2022'])
        self.assertEqual(len(series['changes']),3)
        self.assertEqual(len(series['classifications']),3)
        self.assertTrue((self.root/series['report_path']).is_file())
        self.assertTrue(series['synthetic'])
        self.assertEqual(series['changes']['2020-2021']['valid_pixels'],256)
        gaps=analyze_timeseries({'checkpoint_path':trained['checkpoint_path'],'output_id':'gaps',
                                'images':[{'year':year,'image_path':f'year{year}.tif'} for year in (2020,2022)]},self.root)
        self.assertEqual(gaps['adjacent_pairs'],[])
        self.assertEqual(gaps['adjacent_observation_pairs'],['2020-2022'])
        self.assertEqual(gaps['quality']['missing_years'],[2021])
        self.assertFalse(gaps['quality']['annual_coverage_complete'])


if __name__=='__main__':
    unittest.main()
