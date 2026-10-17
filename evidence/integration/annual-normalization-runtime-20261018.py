"""127 Root actual temporary rasters/model/Registry, never scientific approval."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import torch
from backend.app.store import Store
from backend.app.dataset_registry import register_version
from backend.app.ml.dataset import file_digest
from backend.app.ml.network import TinyUNet
from backend.app.ml.pinned_annual_normalization import inspect_pinned_annual_normalization as inspect
from test_ml_readiness import ReadinessTests

ROOT=Path(__file__).resolve().parents[2]
f=ReadinessTests();f.setUp();checks=[]
try:
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
            'temporal':{'start':'2021-01-01T00:00:00Z','end':'2021-12-31T00:00:00Z','calendar':'gregorian'},
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
    original_inputs=copy.deepcopy([model_ref,requested])
    def observe(rows=requested):
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')),patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state load')):
            return inspect(store,model_ref,report_sha,rows)
    with patch('torch.load',wraps=torch.load) as loader,patch.object(store,'get',wraps=store.get) as getter:
        result=observe()
    assert result['status']=='PINNED_YEARS_MATCHED_UNVERIFIED' and result['artifact_bytes_verified'] is True
    assert result['checked_rows']==3 and all(row['status']=='MATCHED_UNVERIFIED' for row in result['rows'])
    checks.append('three_actual_temp_geotiffs_with_nine_registered_role_versions_match_pinned_model')
    assert loader.call_count==1 and getter.call_count==10
    assert result['model_observation']['checkpoint_manifest']==manifest
    checks.append('one_actual_checkpoint_load_and_one_model_plus_nine_dataset_record_reads_ignore_report_decoy')
    assert result['temporal_year_verified'] is False and requested[2]['year']==2023
    checks.append('request_year_labels_do_not_claim_registry_temporal_or_actual_observation_year_verification')
    bad=copy.deepcopy(requested);bad[0]['year']=True
    with patch.object(store,'get',side_effect=AssertionError('invalid input no IO')):
        invalid=observe(bad)
    assert invalid['status']=='INVALID_INPUT'
    checks.append('boolean_year_rejected_before_any_registry_or_model_io')
    for index,expected_checked,expected_unchecked in [(2,3,0),(0,1,2)]:
        path=f.root/f.rows[index]['image_path'];raw=path.read_bytes()
        try:
            path.write_bytes(raw+b'TAMPERED')
            failed=observe()
            assert failed['status']=='SCENE_BLOCKED' and failed['artifact_bytes_verified'] is False
            assert failed['checked_rows']==expected_checked
            assert sum(row['status']=='NOT_CHECKED' for row in failed['rows'])==expected_unchecked
            checks.append(f'actual_image_{index}_tamper_failfast_preserves_partial_rows_and_unchecked_count_{expected_unchecked}')
        finally:path.write_bytes(raw)
    assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
    assert original_inputs==[model_ref,requested]
    for name in ('execution_authorized','workflow_supported','state_dict_verified','raster_header_verified',
                 'quality_report_verified','quality_mask_verified','source_authority_verified','access_authorization_verified',
                 'other_lineage_parents_verified','scientific_accuracy_validated','temporal_year_verified'):
        assert result[name] is False
    proof={'scope':'TESTED_SYNTHETIC_TEMP_CPU_MODEL_THREE_GEOTIFFS_NINE_REGISTERED_ROLES',
        'checks_passed':checks,'torch_version':torch.__version__,'fixture_files_restored_inputs_unchanged':True,
        'one_checkpoint_load_per_valid_batch':True,'requested_years_are_not_verified_observation_years':True,
        'operating_model_loaded':False,'operating_registry_contact':False,'training_inference_executed':False,
        'scientific_accuracy_validated':False}
    (ROOT/'evidence/integration/annual-normalization-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(f'PASS {len(checks)} actual Temp annual-batch scenarios, no training/inference/operating writes.')
finally:f.tearDown()
