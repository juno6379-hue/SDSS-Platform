"""131 real temporary raster bytes and registered quality/mask references; no model."""
import builtins
import json
from pathlib import Path
from unittest.mock import patch
from backend.app.store import Store
from backend.app.dataset_registry import register_version
from backend.app.ml.dataset import file_digest
from backend.app.ml.registered_quality_mask_files import read_registered_quality_mask_files as read
from test_ml_readiness import ReadinessTests

ROOT=Path(__file__).resolve().parents[2]

def run_case(case):
    f=ReadinessTests();f.setUp()
    try:
        store=Store(f.root);image=f.root/f.rows[0]['image_path'];mask=f.root/f.rows[0]['quality_mask_path']
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
            if name.split('.')[0] in ('torch','rasterio'):
                attempted.append(name);raise AssertionError('reader cannot import model or raster parser')
            return original_import(name,*args,**kwargs)
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(store,'get',wraps=store.get) as getter,patch('builtins.__import__',side_effect=guarded_import):
            result=read(store,refs[0],report_ref,refs[1])
        expected='REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED' if case in ('valid','opaque_mask') else 'BLOCKED'
        assert result['status']==expected,(case,result)
        assert getter.call_count==3 and attempted==[]
        assert result['artifact_bytes_verified']==(case in ('valid','opaque_mask'))
        if case in ('image_tamper','mask_tamper'):assert result['report_bindings_verified'] is True
        for field in ('quality_report_verified','quality_mask_verified','raster_header_verified','state_dict_verified',
                      'source_authority_verified','access_authorization_verified','scientific_accuracy_validated',
                      'execution_authorized','workflow_supported'):
            assert result[field] is False
        assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
        return {'case':case,'status':result['status'],'issue':result['issue'],'store_gets':getter.call_count,
                'registry_references_verified':result['registry_references_verified'],
                'report_bindings_verified':result['report_bindings_verified'],'file_bindings':result['file_bindings']}
    finally:f.tearDown()

checks=[run_case(case) for case in ('valid','opaque_mask','report_tamper','image_tamper','mask_tamper','legacy_report','missing_report_path')]
proof={'scope':'TESTED_SYNTHETIC_ACTUAL_TEMP_IMAGE_MASK_BYTES_THREE_REGISTERED_REFERENCES',
       'checks_passed':checks,'reader_requested_torch_or_rasterio_import':False,
       'all_fixture_files_and_database_bytes_unchanged_during_reader':True,
       'opaque_mask_with_matching_sha_is_not_mask_semantics_or_quality_approval':True,
       'operating_model_loaded':False,'temporary_model_loaded':False,'operating_registry_contact':False,
       'training_inference_executed':False,'quality_report_verified':False,'quality_mask_verified':False,
       'scientific_accuracy_validated':False}
(ROOT/'evidence/integration/quality-mask-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(f'PASS {len(checks)} actual Temp registered quality/mask cases; no model/raster parsing, training or inference.')
