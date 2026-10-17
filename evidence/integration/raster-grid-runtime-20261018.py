"""129 Root actual temporary raster headers/grids/model/Registry, never scientific approval."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import torch
from backend.app.store import Store
from backend.app.dataset_registry import register_version,canonical_manifest,version_key
from backend.app.ml.dataset import file_digest
from backend.app.ml.network import TinyUNet
from backend.app.ml.registry_raster_grid_normalization import inspect_registry_raster_grid_normalization as inspect
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
        target=f.root/f.rows[1 if case in ('shift','band_order') else 2 if case=='width' else 0]['image_path']
        if case=='shift':
            with rasterio.open(target,'r+') as dst:dst.transform=from_origin(500010,9000000,10,10)
        elif case=='missing_description':
            with rasterio.open(target,'r+') as dst:dst.set_band_description(1,'')
        elif case=='band_order':
            with rasterio.open(target,'r+') as dst:
                dst.set_band_description(1,'B03');dst.set_band_description(2,'B02')
        elif case=='geographic':
            with rasterio.open(target,'r+') as dst:
                dst.crs='EPSG:4326';dst.transform=from_origin(106,-6,.0001,.0001)
        elif case=='width':
            with rasterio.open(target) as src:profile=src.profile
            profile['width']=128
            with rasterio.open(target,'w',**profile) as dst:
                dst.write(np.ones((6,256,128),dtype='uint16'))
                for band,name in enumerate(names,1):dst.set_band_description(band,name)
        elif case=='opaque':target.write_bytes(b'FIXTURE_NOT_A_TIFF_WITH_CORRECT_REGISTERED_SHA')
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
                'data_type':kind,'spatial':{'bbox':[106,-7,107,-6],'crs':'OGC:CRS84'},
                'temporal':{'start':f'{2021+int(identifier.rsplit("-",1)[1])}-01-01T00:00:00Z','end':f'{2021+int(identifier.rsplit("-",1)[1])}-12-31T23:59:59.999999999Z','calendar':'gregorian'},
                'quality_status':'RAW','access_class':'PUBLIC','sha256':file_digest(path),
                'artifact_uri':path.relative_to(f.root).as_posix(),'lineage':lineage or []}
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
            requested.append({'year':2021+i,'image_ref':image_ref,'evidence_ref':evidence_ref,'metadata_ref':metadata_ref})
        before={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')),patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state load')),patch('torch.load',wraps=torch.load) as loader,patch.object(store,'get',wraps=store.get) as getter:
            result=inspect(store,model_ref,report_sha,requested)
        if case=='valid':
            assert result['status']=='RASTER_GRID_MATCHED_UNVERIFIED'
            assert result['raster_header_verified'] and result['cross_scene_grid_verified'] and result['artifact_bytes_verified']
            assert result['registry_temporal_year_verified'] and len(result['header_observations'])==3
            assert loader.call_count==1 and getter.call_count==10
        else:
            assert result['status']=='RASTER_BLOCKED',(case,result)
            assert result['raster_header_verified'] is False and result['cross_scene_grid_verified'] is False
            assert result['artifact_bytes_verified'] is False
        for name in ('registry_aoi_verified','quality_mask_verified','quality_report_verified','state_dict_verified','pixel_values_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            assert result[name] is False
        assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        return {'case':case,'status':result['status'],'issue':result['issue'],
                'checked_headers':len(result['header_observations']),'store_gets':getter.call_count,'torch_loads':loader.call_count}
    finally:f.tearDown()

checks=[run_case(case) for case in ('valid','shift','missing_description','band_order','geographic','width','opaque')]
proof={'scope':'TESTED_SYNTHETIC_ACTUAL_TEMP_GEOTIFF_HEADERS_MODEL_AND_REGISTRY',
       'checks_passed':checks,'torch_version':torch.__version__,
       'all_fixtures_files_and_registry_bytes_unchanged_during_reader':True,
       'temporary_untrained_model_checkpoint_loaded':True,'operating_model_loaded':False,
       'training_inference_executed':False,'operating_registry_contact':False,
       'scientific_accuracy_validated':False,'pixel_values_verified':False,'registry_aoi_verified':False}
(ROOT/'evidence/integration/raster-grid-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(f'PASS {len(checks)} isolated actual Temp GeoTIFF/header/grid/model/Registry scenarios; no inference/training.')
