"""Read-only composition of actual checkpoint and one registered scene.

This is neither a Workflow executor nor a multi-file transaction/approval gate.
"""
from .model_checkpoint_manifest import read_pinned_model_checkpoint_manifest
from .registered_per_scene_files import read_registered_per_scene_files


def inspect_pinned_scene_normalization(store, model_ref, training_report_sha256, image_ref, evidence_ref, metadata_ref):
    """Use only the manifest decoded by124; no caller manifest/path input exists."""
    result={'schema_version':1,'scope':'PINNED_MODEL_REGISTERED_SCENE_READ_ONLY','status':'MODEL_BLOCKED','issue':None,
        'model_observation':None,'scene_observation':None,'checkpoint_artifact_verified':False,
        'training_report_artifact_verified':False,'registry_references_verified':False,'artifact_bytes_verified':False}
    result.update({field:False for field in ('state_dict_verified','raster_header_verified','quality_report_verified',
        'quality_mask_verified','source_authority_verified','access_authorization_verified','other_lineage_parents_verified',
        'scientific_accuracy_validated','execution_authorized','workflow_supported')})
    try:
        model=read_pinned_model_checkpoint_manifest(store,model_ref,training_report_sha256)
        result['model_observation']=model
        result['checkpoint_artifact_verified']=model['checkpoint_artifact_verified'] is True
        result['training_report_artifact_verified']=model['training_report_artifact_verified'] is True
        if model['status']!='MANIFEST_BOUND_UNVERIFIED':
            result['issue']={'code':'MODEL_OBSERVATION_BLOCKED','field':'model'}
            return result
    except Exception:
        result['issue']={'code':'MODEL_OBSERVATION_BLOCKED','field':'model'}
        return result
    try:
        scene=read_registered_per_scene_files(store,model['checkpoint_manifest'],image_ref,evidence_ref,metadata_ref)
        result['scene_observation']=scene
        result['registry_references_verified']=scene['registry_references_verified'] is True
        if scene['status']=='OUT_OF_SCOPE':
            result['status']='OUT_OF_SCOPE'
        elif scene['status']=='REGISTERED_FILES_MATCHED_UNVERIFIED':
            result['status']='PINNED_SCENE_MATCHED_UNVERIFIED'
            result['artifact_bytes_verified']=(result['checkpoint_artifact_verified']
                and result['training_report_artifact_verified'] and scene['artifact_bytes_verified'] is True)
        else:
            result['status']='SCENE_BLOCKED'
            result['issue']={'code':'SCENE_OBSERVATION_BLOCKED','field':'scene'}
    except Exception:
        result['status']='SCENE_BLOCKED'
        result['issue']={'code':'SCENE_OBSERVATION_BLOCKED','field':'scene'}
    return result
