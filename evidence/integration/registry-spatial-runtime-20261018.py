"""130 Root actual temporary raster/Registry bbox containment diagnostics, never scientific approval."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import torch
from backend.app.store import Store
from backend.app.dataset_registry import register_version,canonical_manifest,version_key
from backend.app.ml.dataset import file_digest
from backend.app.ml.network import TinyUNet
from backend.app.ml.registry_spatial_normalization import inspect_registry_spatial_normalization as inspect
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
                if case=='outside':m['spatial']['bbox']=[106,-7,107,-6]
                elif case=='narrow' and identifier=='image-1':m['spatial']['bbox']=[105,-10,105.000001,-8]
                elif case=='unsupported' and identifier=='image-0':m['spatial']['crs']='EPSG:3857'
                elif case=='crs84':m['spatial']['crs']='OGC:CRS84'
                elif case=='exact':m['spatial']['bbox']=list(transform_bounds('EPSG:32748','OGC:CRS84',500000,8997440,502560,9000000,densify_pts=21))
                elif case=='global' and identifier=='image-0':m['spatial']['bbox']=[-180,-90,180,90]
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
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')),patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state load')),patch('torch.load',wraps=torch.load) as loader,patch.object(store,'get',wraps=store.get) as getter,patch.object(header_module,'_header',wraps=header_module._header) as header_reader:
            result=inspect(store,model_ref,report_sha,requested)
        expected='REGISTRY_ENVELOPE_MATCHED_UNVERIFIED' if case in ('valid','crs84','exact') else 'SPATIAL_BLOCKED'
        assert result['status']==expected,(case,result)
        assert result['raster_batch_observation']['status']=='RASTER_GRID_MATCHED_UNVERIFIED'
        assert loader.call_count==1 and getter.call_count==10 and header_reader.call_count==3
        if case in ('valid','crs84','exact'):
            assert result['registry_bbox_contains_raster_envelope_verified'] and result['artifact_bytes_verified']
        else:
            assert result['registry_bbox_contains_raster_envelope_verified'] is False and result['artifact_bytes_verified'] is False
        for name in ('registry_aoi_verified','physical_coverage_verified','quality_mask_verified','quality_report_verified','pixel_values_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            assert result[name] is False
        assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        return {'case':case,'status':result['status'],'issue':result['issue'],
                'spatial_rows':[row['status'] for row in result['spatial_observations']],
                'store_gets':getter.call_count,'torch_loads':loader.call_count,'actual_header_calls':header_reader.call_count,
                'parent129_completed_all_file_and_header_reads':True}
    finally:f.tearDown()

checks=[run_case(case) for case in ('valid','outside','narrow','unsupported','crs84','exact','global')]
proof={'scope':'TESTED_SYNTHETIC_ACTUAL_TEMP_GEOTIFF_REGISTRY_SPATIAL_POST_DIAGNOSTIC',
       'checks_passed':checks,'torch_version':torch.__version__,
       'all_fixtures_files_and_registry_bytes_unchanged_during_reader':True,
       'temporary_untrained_model_checkpoint_loaded':True,'operating_model_loaded':False,
       'training_inference_executed':False,'operating_registry_contact':False,
       'scientific_accuracy_validated':False,'pixel_values_verified':False,'registry_aoi_verified':False,
       'all_spatial_cases_already_completed129_file_reads_before_postdiagnostic':True,
       'reference_exact_bbox_uses_installed_rasterio_transform_bounds_not_independent_geodetic_truth':True}
(ROOT/'evidence/integration/registry-spatial-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(f'PASS {len(checks)} isolated actual Temp GeoTIFF/Registry bbox post-diagnostic scenarios; no inference/training.')
