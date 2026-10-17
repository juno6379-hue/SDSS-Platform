"""132 actual temporary image/mask header and grid diagnostics; no model or pixel reads."""
import builtins
import json
from pathlib import Path
from unittest.mock import patch
from backend.app.store import Store
from backend.app.dataset_registry import register_version
from backend.app.ml.dataset import file_digest
from backend.app.ml.registered_quality_mask_grid import inspect_registered_quality_mask_grid as read
import rasterio
from rasterio.transform import from_origin
import numpy as np
from test_ml_readiness import ReadinessTests

ROOT=Path(__file__).resolve().parents[2]

def run_case(case):
    f=ReadinessTests();f.setUp()
    try:
        store=Store(f.root);image=f.root/f.rows[0]['image_path'];mask=f.root/f.rows[0]['quality_mask_path']
        with rasterio.open(image,'r+') as dst:
            for band,name in enumerate(f.rows[0]['bands'],1):dst.set_band_description(band,name)
        if case=='shift':
            with rasterio.open(mask,'r+') as dst:dst.transform=from_origin(500010,9000000,10,10)
        elif case=='mask_crs':
            with rasterio.open(mask,'r+') as dst:dst.crs='EPSG:32749'
        elif case in ('mask_width','mask_two_bands','mask_uint16'):
            width=128 if case=='mask_width' else 256
            count=2 if case=='mask_two_bands' else 1
            dtype='uint16' if case=='mask_uint16' else 'uint8'
            with rasterio.open(mask,'w',driver='GTiff',width=width,height=256,count=count,dtype=dtype,
                               crs='EPSG:32748',transform=from_origin(500000,9000000,10,10),nodata=0) as dst:
                dst.write(np.ones((count,256,width),dtype=dtype))
        report=f.root/'quality-mask-evidence.json'
        if case=='opaque_mask':mask.write_bytes(b'OPAQUE_MASK_ROLE_BYTES_NOT_A_RASTER')
        refs=[{'id':name,'version':'v1','sha256':file_digest(path)} for name,path in (('quality-image',image),('quality-mask',mask))]
        envelope={'schema_version':1,'scope':'LCLUC_QUALITY_MASK_EVIDENCE','image_ref':refs[0],
                  'mask_ref':refs[1],'quality_status':'RAW'}
        report.write_text(json.dumps({'passed':[]} if case=='legacy_report' else envelope),encoding='utf-8')
        report_ref={'id':'quality-report','version':'v1','sha256':file_digest(report)}
        def manifest(ref,path,kind,lineage=None):
            return {'schema_version':'0.2.0','dataset_id':ref['id'],'version':'v1',
                'source':{'institution':'SYNTHETIC_TEMP_FIXTURE','product':'Explicit quality binding fixture','license':'test only'},
                'data_type':kind,'spatial':{'bbox':[100,-20,120,0],'crs':'OGC:CRS84'},
                'temporal':{'start':'2021-01-01T00:00:00Z','end':'2021-12-31T23:59:59Z','calendar':'gregorian'},
                'quality_status':'RAW','access_class':'PUBLIC','sha256':ref['sha256'],
                'artifact_uri':path.relative_to(f.root).as_posix(),'lineage':lineage or []}
        image_manifest=manifest(refs[0],image,'raster')
        image_manifest['source']['band_names']=f.rows[0]['bands']
        if case!='missing_report_path':image_manifest['quality_report_ref']=report.relative_to(f.root).as_posix()
        mask_manifest=manifest(refs[1],mask,'raster')
        report_manifest=manifest(report_ref,report,'document',[
            {**refs[0],'role':'quality_input_image'},{**refs[1],'role':'quality_input_mask'}])
        for value in (mask_manifest,image_manifest,report_manifest):register_version(store,value)
        changed={'report_tamper':report,'image_tamper':image,'mask_tamper':mask}.get(case)
        if changed is not None:changed.write_bytes(changed.read_bytes()+b' ')
        before={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        attempted=[];original_import=builtins.__import__
        def guarded_import(name,*args,**kwargs):
            if name.split('.')[0]=='torch':
                attempted.append(name);raise AssertionError('reader cannot import model')
            return original_import(name,*args,**kwargs)
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(store,'get',wraps=store.get) as getter,patch('builtins.__import__',side_effect=guarded_import),patch('rasterio.io.DatasetReader.read',side_effect=AssertionError('no pixel reads')),patch('rasterio.io.DatasetReader.read_masks',side_effect=AssertionError('no mask-pixel reads')):
            result=read(store,refs[0],report_ref,refs[1])
        expected='REGISTERED_QUALITY_MASK_GRID_MATCHED_UNVERIFIED' if case=='valid' else 'BLOCKED'
        assert result['status']==expected,(case,result)
        base=result['quality_mask_observation']
        assert base['status']=='REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED' and base['artifact_bytes_verified'] is True
        assert getter.call_count==3 and attempted==[]
        assert result['artifact_bytes_verified']==(case=='valid')
        assert result['image_mask_headers_verified']==(case=='valid') and result['image_mask_grid_verified']==(case=='valid')
        for field in ('quality_report_verified','quality_mask_verified','pixel_values_verified','mask_semantics_verified',
                      'registry_aoi_verified','state_dict_verified','source_authority_verified',
                      'scientific_accuracy_validated','execution_authorized','workflow_supported'):
            assert result[field] is False
        assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        return {'case':case,'status':result['status'],'issue':result['issue'],'store_gets':getter.call_count,
                'parent131_all_file_bytes_verified':base['artifact_bytes_verified'],
                'image_header_observed':result['image_header'] is not None,
                'mask_header_observed':result['mask_header'] is not None}
    finally:f.tearDown()

checks=[run_case(case) for case in ('valid','shift','mask_crs','mask_width','mask_two_bands','mask_uint16','opaque_mask')]
proof={'scope':'TESTED_SYNTHETIC_ACTUAL_TEMP_IMAGE_MASK_HEADER_GRID_THREE_REGISTERED_REFERENCES',
       'checks_passed':checks,'reader_requested_torch_import':False,
       'all_fixture_files_and_database_bytes_unchanged_during_reader':True,
       'matching_file_bytes_are_not_header_grid_mask_semantics_or_quality_approval':True,
       'operating_model_loaded':False,'temporary_model_loaded':False,'operating_registry_contact':False,
       'training_inference_executed':False,'quality_report_verified':False,'quality_mask_verified':False,
       'scientific_accuracy_validated':False}
(ROOT/'evidence/integration/mask-grid-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(f'PASS {len(checks)} actual Temp registered quality/mask cases; no model load, pixel/mask reads, training or inference.')
