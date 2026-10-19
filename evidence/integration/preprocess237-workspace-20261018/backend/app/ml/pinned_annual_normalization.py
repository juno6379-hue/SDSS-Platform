"""Read-only requested-year batch: one actual model read, sequential scene reads."""
import re

from .model_checkpoint_manifest import read_pinned_model_checkpoint_manifest, _keys, _sha
from .registered_per_scene_files import read_registered_per_scene_files, _ref
from .per_scene_normalization_contract import inspect_per_scene_normalization_contract


def _request(model_ref, report_sha, rows):
    if not (_ref(model_ref) and re.fullmatch('[A-Za-z0-9_-]{1,100}',model_ref['id']) and _sha(report_sha)
            and type(rows) is list and 2<=len(rows)<=6):
        raise ValueError('invalid')
    snapshot=[];previous=0;images=set()
    for row in rows:
        if not (_keys(row,('year','image_ref','evidence_ref','metadata_ref'))
                and type(row['year']) is int and 1900<=row['year']<=2200 and row['year']>previous
                and all(_ref(row[key]) for key in ('image_ref','evidence_ref','metadata_ref'))):
            raise ValueError('invalid')
        refs=[row[key] for key in ('image_ref','evidence_ref','metadata_ref')]
        image=(row['image_ref']['id'],row['image_ref']['version'])
        if image in images or len({(ref['id'],ref['version']) for ref in refs})!=3:
            raise ValueError('invalid')
        previous=row['year'];images.add(image)
        snapshot.append({'year':row['year'],**{key:dict(row[key]) for key in ('image_ref','evidence_ref','metadata_ref')}})
    return dict(model_ref),snapshot


def inspect_pinned_annual_normalization(store, model_ref, training_report_sha256, requested_years):
    """Years are request labels, NOT verified manifest/header acquisition years.

    All request rows are checked before Store I/O. The first scene failure stops
    later rows; one shared actual checkpoint manifest is used without reloading.
    """
    result={'schema_version':1,'scope':'PINNED_MODEL_REQUESTED_YEARS_READ_ONLY','status':'INVALID_INPUT','issue':None,
        'model_observation':None,'rows':[],'model_observation_calls':0,'scene_observation_calls':0,'checked_rows':0,
        'checkpoint_artifact_verified':False,'training_report_artifact_verified':False,
        'registry_references_verified':False,'artifact_bytes_verified':False}
    result.update({field:False for field in ('state_dict_verified','raster_header_verified','quality_report_verified',
        'quality_mask_verified','source_authority_verified','access_authorization_verified','other_lineage_parents_verified',
        'scientific_accuracy_validated','execution_authorized','workflow_supported','temporal_year_verified')})
    try:
        ref,rows=_request(model_ref,training_report_sha256,requested_years)
    except Exception:
        result['issue']={'code':'INVALID_INPUT','field':'request','year':None};return result
    result['rows']=[{'year':row['year'],'status':'NOT_CHECKED','scene_observation':None,'issue':None} for row in rows]
    result['status']='MODEL_BLOCKED'
    try:
        result['model_observation_calls']=1
        model=read_pinned_model_checkpoint_manifest(store,ref,training_report_sha256)
        result['model_observation']=model
        result['checkpoint_artifact_verified']=model['checkpoint_artifact_verified'] is True
        result['training_report_artifact_verified']=model['training_report_artifact_verified'] is True
        if model['status']!='MANIFEST_BOUND_UNVERIFIED':raise ValueError('blocked')
    except Exception:
        result['issue']={'code':'MODEL_OBSERVATION_BLOCKED','field':'model','year':None};return result
    try:
        probe=inspect_per_scene_normalization_contract(model['checkpoint_manifest'],{}, {}, {})
        if probe['status']=='OUT_OF_SCOPE':
            result['status']='OUT_OF_SCOPE';return result
    except Exception:
        result['issue']={'code':'MODEL_OBSERVATION_BLOCKED','field':'model','year':None};return result
    result['status']='SCENE_BLOCKED'
    for row,output in zip(rows,result['rows']):
        try:
            result['scene_observation_calls']+=1;result['checked_rows']+=1
            scene=read_registered_per_scene_files(store,model['checkpoint_manifest'],row['image_ref'],row['evidence_ref'],row['metadata_ref'])
            output['scene_observation']=scene
            if scene['status']!='REGISTERED_FILES_MATCHED_UNVERIFIED':raise ValueError('blocked')
            output['status']='MATCHED_UNVERIFIED'
        except Exception:
            output['status']='BLOCKED';output['issue']={'code':'SCENE_OBSERVATION_BLOCKED','field':'scene'}
            result['issue']={'code':'SCENE_OBSERVATION_BLOCKED','field':'scene','year':row['year']}
            return result
    result['status']='PINNED_YEARS_MATCHED_UNVERIFIED'
    result['registry_references_verified']=all(row['scene_observation']['registry_references_verified'] is True for row in result['rows'])
    result['artifact_bytes_verified']=(result['checkpoint_artifact_verified'] and result['training_report_artifact_verified']
        and all(row['scene_observation']['artifact_bytes_verified'] is True for row in result['rows']))
    return result
