"""127 Root actual temporary rasters/model/Registry, never scientific approval."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import torch
from backend.app.store import Store
from backend.app.dataset_registry import register_version,canonical_manifest,version_key
from backend.app.ml.dataset import file_digest
from backend.app.ml.network import TinyUNet
from backend.app.ml.registry_temporal_normalization import inspect_registry_temporal_normalization as inspect
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
    original_inputs=copy.deepcopy([model_ref,requested])
    def observe(rows=requested):
        with patch.object(store,'put',side_effect=AssertionError('no writes')),patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')),patch.object(TinyUNet,'load_state_dict',side_effect=AssertionError('no state load')):
            return inspect(store,model_ref,report_sha,rows)
    with patch('torch.load',wraps=torch.load) as loader,patch.object(store,'get',wraps=store.get) as getter:
        result=observe()
    assert result['status']=='REGISTRY_YEARS_MATCHED_UNVERIFIED' and result['artifact_bytes_verified'] is True
    assert result['registry_temporal_year_verified'] is True and len(result['temporal_observations'])==3
    assert result['batch_observation']['temporal_year_verified'] is False
    checks.append('three_actual_temp_geotiffs_nine_registered_roles_same_record_utc_year_windows_match')
    assert loader.call_count==1 and getter.call_count==10
    assert result['batch_observation']['model_observation']['checkpoint_manifest']==manifest
    checks.append('one_checkpoint_load_ten_gets_no_temporal_preread_or_report_signature_substitution')
    bad=copy.deepcopy(requested);bad[0]['year']=True
    with patch.object(store,'get',side_effect=AssertionError('invalid input no IO')):invalid=observe(bad)
    assert invalid['status']=='INVALID_INPUT'
    checks.append('boolean_request_year_rejected_before_any_registry_or_model_io')
    mismatch=copy.deepcopy(requested);mismatch[2]['year']=2024
    failed=observe(mismatch)
    assert failed['status']=='TEMPORAL_BLOCKED' and failed['artifact_bytes_verified'] is False
    assert failed['registry_temporal_year_verified'] is False
    checks.append('requested2024_vs_actual_registered2023_blocked_with_partial_earlier_rows')
    original_get=store.get
    def changed_record(index,temporal):
        target=version_key(requested[index]['image_ref']['id'],requested[index]['image_ref']['version'])
        def get(kind,key):
            body=original_get(kind,key)
            if kind=='dataset_versions' and key==target:
                body['manifest']['temporal']=temporal
                _,body['manifest_sha256']=canonical_manifest(body['manifest'])
            return body
        return get
    valid_offset={'start':'2021-12-31T23:30:00-01:00','end':'2022-01-01T00:30:00Z','calendar':'gregorian'}
    with patch.object(store,'get',changed_record(1,valid_offset)):offset=observe()
    assert offset['status']=='REGISTRY_YEARS_MATCHED_UNVERIFIED'
    checks.append('known_offset_local2021_instant_converts_to_requested_utc2022_and_matches')
    boundary={'start':'2021-01-01T00:00:00Z','end':'2022-01-01T00:00:00Z','calendar':'gregorian'}
    with patch.object(store,'get',changed_record(0,boundary)):edge=observe()
    assert edge['status']=='TEMPORAL_BLOCKED' and edge['batch_observation']['checked_rows']==1
    assert sum(row['status']=='NOT_CHECKED' for row in edge['batch_observation']['rows'])==2
    checks.append('end_at_next_january1_rejected_first_row_and_two_later_rows_unread')
    unknown={'start':'2022-01-01T00:00:00-00:00','end':'2022-01-01T00:00:00-00:00','calendar':'gregorian'}
    with patch.object(store,'get',changed_record(1,unknown)):unknown_result=observe()
    assert unknown_result['status']=='TEMPORAL_BLOCKED' and unknown_result['registry_temporal_year_verified'] is False
    checks.append('unknown_negative_zero_offset_rejected_without_assigning_utc_authority')
    assert before=={p.relative_to(f.root).as_posix():file_digest(p) for p in f.root.rglob('*') if p.is_file()}
    assert original_inputs==[model_ref,requested]
    for name in ('physical_acquisition_year_verified','source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
        assert result[name] is False
    proof={'scope':'TESTED_SYNTHETIC_TEMP_MODEL_THREE_GEOTIFFS_NINE_REGISTRY_RECORDS_TEMPORAL_YEAR_BINDING',
        'checks_passed':checks,'torch_version':torch.__version__,'fixture_files_restored_inputs_unchanged':True,
        'one_checkpoint_load_per_valid_batch':True,'no_extra_temporal_registry_reads':True,
        'changed_record_scenarios_use_mocked_returned_metadata_without_store_writes':True,
        'registered_temporal_declarations_are_not_physical_acquisition_authority':True,
        'operating_model_loaded':False,'operating_registry_contact':False,'training_inference_executed':False,
        'scientific_accuracy_validated':False}
    (ROOT/'evidence/integration/temporal-normalization-runtime-20261018.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(f'PASS {len(checks)} actual Temp temporal-batch scenarios; no inference/training/operating writes.')
finally:f.tearDown()
