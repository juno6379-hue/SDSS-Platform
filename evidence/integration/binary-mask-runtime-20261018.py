"""133 actual temporary explicit binary-mask literal counts; no image pixels or model."""
import builtins
import json
from pathlib import Path
from unittest.mock import patch
from backend.app.store import Store
from backend.app.dataset_registry import register_version
from backend.app.ml.dataset import file_digest
from backend.app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values as read
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
        values=np.ones((1,256,256),dtype='uint8')
        if case=='mixed':values[:,128:,:]=0
        if case=='all_zero':values[:]=0
        if case=='unexpected255':values[0,0,0]=255
        with rasterio.open(mask,'w',driver='GTiff',width=256,height=256,count=1,dtype='uint8',
                           crs='EPSG:32748',transform=from_origin(500010 if case=='shift' else 500000,9000000,10,10),
                           nodata=0 if case=='nodata_mask' else None) as dst:dst.write(values)
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
        if case!='missing_declaration':mask_manifest['source']['mask_semantics']={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
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
        original_read=rasterio.io.DatasetReader.read
        pixel_reads=[]
        def guarded_read(dataset,*args,**kwargs):
            pixel_reads.append({'count':dataset.count,'dtype':list(dataset.dtypes)})
            assert dataset.count==1 and dataset.dtypes==('uint8',), 'image pixel read forbidden'
            return original_read(dataset,*args,**kwargs)
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(store,'get',wraps=store.get) as getter,patch('builtins.__import__',side_effect=guarded_import),patch('rasterio.io.DatasetReader.read',new=guarded_read),patch('rasterio.io.DatasetReader.read_masks',side_effect=AssertionError('no GDAL mask reads')):
            result=read(store,refs[0],report_ref,refs[1])
        success=case in ('mixed','all_zero','all_one')
        assert (result['status']!='BLOCKED')==success,(case,result)
        assert getter.call_count==3 and attempted==[]
        assert result['artifact_bytes_verified'] is success and result['mask_values_verified'] is success
        for field in ('quality_report_verified','quality_mask_verified','mask_semantics_verified','registry_aoi_verified',
                      'source_authority_verified','minimum_validity_policy_verified','scientific_accuracy_validated',
                      'execution_authorized','state_dict_verified','workflow_supported'):
            assert result[field] is False,(field,result)
        if success:
            expected_valid={'mixed':32768,'all_zero':0,'all_one':65536}[case]
            assert result['counts']=={'valid_pixels':expected_valid,'invalid_pixels':65536-expected_valid,'total_pixels':65536}
        else:assert result['counts'] is None
        assert len(pixel_reads)==(1 if success or case=='unexpected255' else 0),(case,pixel_reads)
        assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        return {'case':case,'status':result['status'],'issue':result['issue'],'store_gets':getter.call_count,
                'counts':result['counts'],'mask_pixel_read_calls':len(pixel_reads),'image_pixel_reads':0}
    finally:f.tearDown()

checks=[run_case(case) for case in ('mixed','all_zero','all_one','unexpected255','missing_declaration','nodata_mask','shift')]
proof={'scope':'TESTED_SYNTHETIC_ACTUAL_TEMP_EXPLICIT_BINARY_MASK_LITERAL_COUNTS',
       'checks_passed':checks,'reader_requested_torch_import':False,
       'all_fixture_files_and_database_bytes_unchanged_during_reader':True,
       'literal_binary_value_counts_are_not_physical_semantic_truth_or_quality_approval':True,
       'operating_model_loaded':False,'temporary_model_loaded':False,'operating_registry_contact':False,
       'training_inference_executed':False,'quality_report_verified':False,'quality_mask_verified':False,
       'scientific_accuracy_validated':False}
(ROOT/'evidence/integration/binary-mask-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(f'PASS {len(checks)} actual Temp explicit binary-mask cases; no model/image pixels/training/inference.')
