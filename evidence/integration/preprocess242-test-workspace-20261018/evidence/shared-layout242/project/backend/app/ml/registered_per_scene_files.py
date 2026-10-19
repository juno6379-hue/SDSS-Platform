"""Bind three registered references to one scene's file declarations; no execution."""
import re

from ..dataset_registry import canonical_manifest, version_key
from ..model_reference_contract import model_reference_issue
from .model_checkpoint_manifest import _manifest, _Invalid
from .per_scene_normalization_contract import inspect_per_scene_normalization_contract
from .per_scene_normalization_files import (
    _root, _relative, _snapshot, _evidence_json, _Blocked,
    verify_per_scene_normalization_files, MAX_EVIDENCE,
)

ROLES = ('image', 'normalization_evidence', 'source_metadata')
LINEAGE_ROLES = ('normalization_input_image', 'normalization_source_metadata')


class _Issue(Exception):
    def __init__(self, code, field):self.code,self.field=code,field


def _need(condition,code,field):
    if not condition:raise _Issue(code,field)


def _ref(value):
    return (type(value) is dict and len(value)==3 and all(type(k) is str for k in value)
        and value.keys()=={'id','version','sha256'} and model_reference_issue(value) is None
        and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']) is not None)


def _text(value,maximum):
    return (type(value) is str and 1<=len(value)<=maximum and bool(value.strip())
        and all(ord(c)>=32 and not 127<=ord(c)<=159 and not 0xD800<=ord(c)<=0xDFFF for c in value))


def read_registered_per_scene_files(store, checkpoint_manifest, image_ref, evidence_ref, metadata_ref):
    """Read fixed records + bytes; caller checkpoint manifest remains unverified.

    PUBLIC/quality are registered declarations, not ACL or QA-body verification.
    Additional lineage parents are allowed and never recursively resolved.
    """
    result={'schema_version':1,'scope':'REGISTERED_PER_SCENE_FILES_READ_ONLY','status':'BLOCKED','issue':None,
        'registry_bindings':[],'file_observation':None,'registry_references_verified':False,'artifact_bytes_verified':False}
    result.update({field:False for field in ('checkpoint_artifact_verified','raster_header_verified','quality_report_verified',
        'quality_mask_verified','source_authority_verified','access_authorization_verified','other_lineage_parents_verified',
        'state_dict_verified','scientific_accuracy_validated','execution_authorized','workflow_supported')})
    try:
        probe=inspect_per_scene_normalization_contract(checkpoint_manifest,{}, {}, {})
        if probe['status']=='OUT_OF_SCOPE':
            result['status']='OUT_OF_SCOPE';return result
        _need(probe['status']=='INCOMPLETE' and probe['issue']=={'code':'MISSING_FIELD','field':'source_scene.scene_id'},
              'DECLARATION_NOT_CONSISTENT','checkpoint_manifest')
        refs=(image_ref,evidence_ref,metadata_ref)
        _need(all(_ref(ref) for ref in refs),'INVALID_INPUT','references')
        _need(len({(ref['id'],ref['version']) for ref in refs})==3,'INVALID_INPUT','references')
        manifests=[]
        for role,ref,kind in zip(ROLES,refs,('raster','document','document')):
            key=version_key(ref['id'],ref['version'])
            try:record=store.get('dataset_versions',key)
            except KeyError:raise _Issue('REGISTRY_RECORD_UNAVAILABLE',role) from None
            _need(type(record) is dict and len(record)<=128 and all(type(k) is str for k in record)
                  and record.get('id')==key,'REGISTRY_RECORD_INVALID',role)
            try:
                bounded=_manifest(record.get('manifest'))
                manifest,digest=canonical_manifest(bounded)
            except Exception:raise _Issue('REGISTRY_RECORD_INVALID',role) from None
            _need(manifest['dataset_id']==ref['id'] and manifest['version']==ref['version']
                  and manifest['sha256']==ref['sha256'] and record.get('manifest_sha256')==digest,
                  'REGISTRY_REFERENCE_CONFLICT',role)
            _need(manifest['data_type']==kind,'REGISTRY_TYPE_MISMATCH',role)
            _need(manifest['access_class']=='PUBLIC','ACCESS_DECLARATION_BLOCKED',role)
            manifests.append(manifest)
            result['registry_bindings'].append({'role':role,'ref':dict(ref),'manifest_sha256':digest,
                'quality_status':manifest['quality_status'],'access_class':manifest['access_class']})
        result['registry_references_verified']=True
        image_manifest,evidence_manifest,metadata_manifest=manifests
        source=image_manifest['source']
        _need('scene_id' in source and 'band_names' in source,'SCENE_DECLARATION_MISSING','image')
        _need(_text(source['scene_id'],128) and type(source['band_names']) is list and len(source['band_names'])==6
              and all(_text(name,64) for name in source['band_names']),'SCENE_DECLARATION_INVALID','image')
        parents=evidence_manifest['lineage']
        for ref,role in ((image_ref,LINEAGE_ROLES[0]),(metadata_ref,LINEAGE_ROLES[1])):
            matches=[parent for parent in parents if parent.get('role')==role]
            _need(len(matches)==1 and all(matches[0][key]==ref[key] for key in ('id','version','sha256')),
                  'LINEAGE_BINDING_INVALID','normalization_evidence')
        root=_root(store.root)
        paths=[_relative(root,manifest['artifact_uri'],role) for role,manifest in zip(ROLES,manifests)]
        digest,raw=_snapshot(root,paths[1],MAX_EVIDENCE,'normalization_evidence',True)
        _need(digest==evidence_ref['sha256'],'SHA256_MISMATCH','normalization_evidence')
        evidence=_evidence_json(raw)
        metadata_path=_relative(root,evidence.get('source_metadata_path'),'source_metadata')
        _need(metadata_path==paths[2] and evidence.get('source_metadata_sha256')==metadata_ref['sha256'],
              'EVIDENCE_BINDING_INVALID','source_metadata')
        # Derive only from pinned registry/JSON declarations, never source.product
        # or checkpoint band names masquerading as observed source metadata.
        scene={'scene_id':source['scene_id'],'image_sha256':image_ref['sha256'],'band_names':list(source['band_names'])}
        normalization={'scale':evidence.get('scale'),'offset':evidence.get('offset'),
            'evidence_path':evidence_manifest['artifact_uri'],'evidence_sha256':evidence_ref['sha256']}
        observation=verify_per_scene_normalization_files(root,checkpoint_manifest,scene,normalization,image_manifest['artifact_uri'])
        result['file_observation']=observation
        _need(observation['status']=='FILES_MATCHED_UNVERIFIED','DECLARATION_NOT_CONSISTENT','scene_files')
        result.update(status='REGISTERED_FILES_MATCHED_UNVERIFIED',artifact_bytes_verified=True)
    except (_Issue,_Blocked,_Invalid) as error:
        result['issue']={'code':error.code,'field':error.field}
    except Exception:
        result['issue']={'code':'REGISTRY_RECORD_UNAVAILABLE','field':'inputs'}
    return result
