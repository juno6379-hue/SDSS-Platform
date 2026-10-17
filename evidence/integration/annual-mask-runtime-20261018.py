"""134 Root actual temporary annual spatial and explicit binary-mask diagnostics."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import torch
from backend.app.store import Store
from backend.app.dataset_registry import register_version,canonical_manifest,version_key
from backend.app.ml.dataset import file_digest
from backend.app.ml.network import TinyUNet
from backend.app.ml.annual_quality_mask_diagnostics import inspect_annual_quality_mask_diagnostics as inspect
from backend.app.ml import registry_raster_grid_normalization as header_module
from rasterio.warp import transform_bounds
import rasterio
from rasterio.transform import from_origin
import numpy as np
from test_ml_readiness import ReadinessTests

ROOT=Path(__file__).resolve().parents[2]

def run_case(case):
    f=ReadinessTests();f.setUp()
    try:
        names=f.rows[0]['bands'];grid=from_origin(500000,9000000,10,10)
        for row in f.rows:
            with rasterio.open(f.root/row['image_path'],'r+') as dst:
                dst.transform=grid
                for band,name in enumerate(names,1):dst.set_band_description(band,name)
        store=Store(f.root); names=f.rows[0]['bands']
        manifest={'normalization_mode':'per_scene_product_metadata','bands':list(range(1,7)),
                  'band_names':names,'synthetic':True,'fixture_provenance':'UNTRAINED_RANDOM_TEMP_MODEL'}
        folder=f.root/'models'/'annual-root-fixture';folder.mkdir(parents=True)
        checkpoint=folder/'best.pt'
        torch.save({'architecture':'tiny_unet','manifest':manifest,'state_dict':TinyUNet(6).state_dict()},checkpoint)
        model_ref={'id':'annual-root-fixture','version':'model-v1','sha256':file_digest(checkpoint)}
        report_path=folder/'report.json'
        report_path.write_text(json.dumps({'model_id':model_ref['id'],'training_state':'completed',
            'checkpoint_sha256':model_ref['sha256'],'fixture_only_not_actual_training':True,
            'input_signature':{'normalization_mode':'global','bands':[1,2,3]}}),encoding='utf-8')
        report_sha=file_digest(report_path)
        store.put('models',{'id':model_ref['id'],'status':'Draft','checkpoint_path':'models/annual-root-fixture/best.pt',
            'checkpoint_sha256':model_ref['sha256'],'training_report_sha256':report_sha,
            'model_version_declaration':{'schema_version':1,'source':'CALLER_EXPLICIT_REGISTRATION','version':'model-v1',
            'checkpoint_sha256':model_ref['sha256'],'training_report_sha256':report_sha}})
        requested=[]
        def record(identifier,path,kind,source=None,lineage=None):
            m={'schema_version':'0.2.0','dataset_id':identifier,'version':'v1',
                'source':source or {'institution':'SYNTHETIC','product':'document','license':'fixture only'},
                'data_type':kind,'spatial':{'bbox':[100,-20,120,0],'crs':'EPSG:4326'},
                'temporal':{'start':f'{2021+int(identifier.rsplit("-",1)[1])}-01-01T00:00:00Z','end':f'{2021+int(identifier.rsplit("-",1)[1])}-12-31T23:59:59.999999999Z','calendar':'gregorian'},
                'quality_status':'RAW','access_class':'PUBLIC','sha256':file_digest(path),
                'artifact_uri':path.relative_to(f.root).as_posix(),'lineage':lineage or []}
            if kind=='raster':
                if case=='spatial_outside':m['spatial']['bbox']=[106,-7,107,-6]
                elif case=='narrow' and identifier=='image-1':m['spatial']['bbox']=[105,-10,105.000001,-8]
                elif case=='unsupported' and identifier=='image-0':m['spatial']['crs']='EPSG:3857'
                elif case=='crs84':m['spatial']['crs']='OGC:CRS84'
                elif case=='exact':m['spatial']['bbox']=list(transform_bounds('EPSG:32748','OGC:CRS84',500000,8997440,502560,9000000,densify_pts=21))
                elif case=='global' and identifier=='image-0':m['spatial']['bbox']=[-180,-90,180,90]
            if identifier.startswith('image-'):m['quality_report_ref']=f'quality-{identifier.rsplit("-",1)[1]}.json'
            register_version(store,m)
            return {'id':identifier,'version':'v1','sha256':m['sha256']}
        for i,row in enumerate(f.rows):
            image=f.root/row['image_path'];evidence=f.root/row['normalization']['evidence_path']
            body=json.loads(evidence.read_text('utf-8'));metadata=f.root/body['source_metadata_path']
            image_ref=record(f'image-{i}',image,'raster',{'institution':'SYNTHETIC','product':'generic not scene id',
                'license':'fixture only','scene_id':row['scene_id'],'band_names':names})
            metadata_ref=record(f'metadata-{i}',metadata,'document')
            evidence_ref=record(f'evidence-{i}',evidence,'document',lineage=[
                {**image_ref,'role':'normalization_input_image'},{**metadata_ref,'role':'normalization_source_metadata'}])
            mask=f.root/f'mask-{i}.tif'
            values=np.ones((1,256,256),dtype='uint8')
            if case=='all_zero':values[:]=0
            if case=='bad_second_values' and i==1:values[0,0,0]=255
            with rasterio.open(mask,'w',driver='GTiff',width=256,height=256,count=1,dtype='uint8',crs='EPSG:32748',
                               transform=from_origin(500010 if case=='second_shift' and i==1 else 500000,9000000,10,10)) as dst:dst.write(values)
            mask_source={'institution':'SYNTHETIC','product':'explicit binary mask','license':'fixture only'}
            if not(case=='second_missing_declaration' and i==1):mask_source['mask_semantics']={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
            mask_ref=record(f'mask-{i}',mask,'raster',mask_source)
            quality=f.root/f'quality-{i}.json'
            quality.write_text(json.dumps({'schema_version':1,'scope':'LCLUC_QUALITY_MASK_EVIDENCE','image_ref':image_ref,'mask_ref':mask_ref,'quality_status':'RAW'}),encoding='utf-8')
            quality_ref=record(f'quality-{i}',quality,'document',lineage=[{**image_ref,'role':'quality_input_image'},{**mask_ref,'role':'quality_input_mask'}])
            requested.append({'year':2021+i,'image_ref':image_ref,'evidence_ref':evidence_ref,'metadata_ref':metadata_ref,'quality_report_ref':quality_ref,'mask_ref':mask_ref})
        before={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        original_get=store.get;get_calls=[]
        def get(kind,identifier):
            get_calls.append((kind,identifier));value=original_get(kind,identifier)
            if case=='registry_changed' and len(get_calls)>10 and kind=='dataset_versions' and identifier==version_key('image-1','v1'):
                value=copy.deepcopy(value);value['manifest']['source']['institution']='CHANGED_BETWEEN_PHASES'
                value['manifest'],value['manifest_sha256']=canonical_manifest(value['manifest'])
            return value
        original_read=rasterio.io.DatasetReader.read;pixel_calls=[]
        def pixels(dataset,*args,**kwargs):
            assert dataset.count==1 and dataset.dtypes==('uint8',),'image pixels forbidden'
            pixel_calls.append(True);return original_read(dataset,*args,**kwargs)
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')),patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state load')),patch('torch.load',wraps=torch.load) as loader,patch.object(store,'get',side_effect=get) as getter,patch('rasterio.io.DatasetReader.read',new=pixels),patch('rasterio.io.DatasetReader.read_masks',side_effect=AssertionError('no GDAL mask reads')):
            result=inspect(store,model_ref,report_sha,requested)
        success=case in ('valid','all_zero')
        assert result['status']==('ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED' if success else 'ANNUAL_SPATIAL_BLOCKED' if case=='spatial_outside' else 'MASK_BLOCKED'),(case,result)
        assert loader.call_count==1
        expected_rows=3 if success else 0 if case=='spatial_outside' else 2
        assert result['checked_rows']==expected_rows and result['mask_observation_calls']==expected_rows
        assert getter.call_count==10+3*expected_rows,(case,getter.call_count)
        assert result['artifact_bytes_verified'] is success and result['registry_manifest_join_verified'] is success
        for field in ('quality_report_verified','quality_mask_verified','mask_semantics_verified','minimum_validity_policy_verified','registry_aoi_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','state_dict_verified','workflow_supported'):
            assert result[field] is False,(field,result)
        if case=='registry_changed':assert result['issue']['code']=='REGISTRY_IMAGE_MANIFEST_CHANGED'
        assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        return {'case':case,'status':result['status'],'issue':result['issue'],
                'mask_rows':[row['status'] for row in result['mask_observations']],
                'store_gets':getter.call_count,'torch_loads':loader.call_count,'actual_mask_pixel_reads':len(pixel_calls),
                'checked_rows':result['checked_rows'],'all_fixture_files_database_unchanged':True}
    finally:f.tearDown()

checks=[run_case(case) for case in ('valid','all_zero','bad_second_values','second_missing_declaration','second_shift','spatial_outside','registry_changed')]
proof={'scope':'TESTED_SYNTHETIC_ACTUAL_TEMP_ANNUAL_SPATIAL_AND_MASK_DIAGNOSTICS',
       'checks_passed':checks,'torch_version':torch.__version__,
       'all_fixtures_files_and_registry_bytes_unchanged_during_reader':True,
       'temporary_untrained_model_checkpoint_loaded':True,'operating_model_loaded':False,
       'training_inference_executed':False,'operating_registry_contact':False,
       'scientific_accuracy_validated':False,'registry_aoi_verified':False,
       'literal_counts_and_registry_join_are_not_quality_or_execution_approval':True}
(ROOT/'evidence/integration/annual-mask-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(f'PASS {len(checks)} isolated actual Temp annual spatial/mask diagnostics; no inference/training/image pixels.')
