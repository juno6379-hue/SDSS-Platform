"""Pure explicit report metadata completion; no file or Registry authorization."""
import hashlib
import re
from datetime import datetime

from ..model_reference_contract import model_reference_issue
from .quality_mask_bundle import (
    FALSE_FIELDS, REQUIRED_REPORT_METADATA, _Invalid, _need, _copy_json,
    _manifest, _path, _text, _canonical, prepare_quality_mask_bundle,
)


def _metadata(value):
    field = 'report_metadata'
    value = _copy_json(value, field)
    _need(value.keys() == set(REQUIRED_REPORT_METADATA), 'REPORT_METADATA_INVALID', field)
    source = value['source']
    _need(type(source) is dict and all(_text(source.get(key)) for key in ('institution','product','license'))
        and ('source_uri' not in source or type(source['source_uri']) is str), 'REPORT_METADATA_INVALID', field)
    spatial = value['spatial']
    _need(type(spatial) is dict and {'bbox','crs'} <= spatial.keys() <= {'bbox','crs','geometry_uri'}, 'REPORT_METADATA_INVALID', field)
    bbox = spatial['bbox']; crs = spatial['crs']
    _need(type(bbox) is list and len(bbox) == 4 and all(type(v) in (int,float) for v in bbox)
        and bbox[0] < bbox[2] and bbox[1] < bbox[3] and type(crs) is str
        and re.fullmatch(r'(EPSG:[0-9]+|OGC:CRS84)',crs) is not None, 'REPORT_METADATA_INVALID', field)
    if crs in ('EPSG:4326','OGC:CRS84'):
        _need(-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90, 'REPORT_METADATA_INVALID', field)
    _need('geometry_uri' not in spatial or type(spatial['geometry_uri']) is str, 'REPORT_METADATA_INVALID', field)
    temporal = value['temporal']
    _need(type(temporal) is dict and {'start','end','calendar'} <= temporal.keys() and _text(temporal['calendar']),
        'REPORT_METADATA_INVALID', field)
    dates = []
    for key in ('start','end'):
        stamp = temporal[key]
        _need(type(stamp) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})',stamp) is not None,
            'REPORT_METADATA_INVALID', field)
        try: dates.append(datetime.fromisoformat(stamp.replace('Z','+00:00')))
        except ValueError: raise _Invalid('REPORT_METADATA_INVALID',field) from None
    _need(dates[0] <= dates[1] and value['quality_status'] in ('RAW','STAGED')
        and value['access_class'] in ('PUBLIC','RESTRICTED','CONFIDENTIAL'), 'REPORT_METADATA_INVALID', field)
    return value


def _expected(image, mask, identity):
    image, image_ref = _manifest(image,'image_manifest')
    mask, mask_ref = _manifest(mask,'mask_manifest')
    identity = _copy_json(identity,'report_identity')
    _need(identity.keys() == {'id','version','artifact_uri'} and model_reference_issue(identity) is None,
        'REPORT_IDENTITY_INVALID','report_identity')
    path = _path(identity['artifact_uri'],'report_identity')
    _need(len({(ref['id'],ref['version']) for ref in (image_ref,mask_ref,identity)}) == 3
        and path not in (_path(image['artifact_uri'],'image_manifest'),_path(mask['artifact_uri'],'mask_manifest')),
        'REFERENCE_CONFLICT','references')
    semantics = mask['source'].get('mask_semantics')
    _need(type(semantics) is dict and semantics.keys() == {'schema_version','kind','valid_value','invalid_value'}
        and type(semantics['schema_version']) is int and semantics['schema_version'] == 1
        and type(semantics['kind']) is str and semantics['kind'] == 'binary_validity'
        and type(semantics['valid_value']) is int and semantics['valid_value'] == 1
        and type(semantics['invalid_value']) is int and semantics['invalid_value'] == 0, 'MASK_SEMANTICS_INVALID','mask_manifest')
    if 'quality_report_ref' in image:
        _need(_path(image['quality_report_ref'],'quality_report_ref') == path,'QUALITY_REPORT_REF_CONFLICT','image_manifest')
    envelope = {'schema_version':1,'scope':'LCLUC_QUALITY_MASK_EVIDENCE','image_ref':dict(image_ref),
        'mask_ref':dict(mask_ref),'quality_status':image['quality_status']}
    raw = _canonical(envelope); digest = hashlib.sha256(raw).hexdigest()
    patch = {'schema_version':'0.2.0','dataset_id':identity['id'],'version':identity['version'],'data_type':'document',
        'sha256':digest,'artifact_uri':identity['artifact_uri'],
        'lineage':[{**image_ref,'role':'quality_input_image'},{**mask_ref,'role':'quality_input_mask'}]}
    image['quality_report_ref'] = identity['artifact_uri']
    result = {'schema_version':1,'scope':'UNREGISTERED_QUALITY_MASK_BUNDLE_PREPARATION_ONLY',
        'status':'REPORT_METADATA_REQUIRED_UNREGISTERED','issue':None,'image_manifest_draft':image,'mask_manifest_draft':mask,
        'report_manifest_patch':patch,'report_metadata_required':list(REQUIRED_REPORT_METADATA),
        'report_envelope':envelope,'report_bytes':raw,'report_sha256':digest,
        'fixed_refs':{'image_ref':dict(image_ref),'quality_report_ref':{'id':identity['id'],'version':identity['version'],'sha256':digest},'mask_ref':dict(mask_ref)}}
    result.update({field:False for field in FALSE_FIELDS})
    return result


def _same(actual, expected):
    # Traverse only the bounded trusted expected shape; custom equality is never called.
    if type(actual) is not type(expected): return False
    if type(expected) is dict:
        return len(actual) == len(expected) and all(type(k) is str for k in actual) and actual.keys() == expected.keys() and all(_same(actual[k],v) for k,v in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(_same(a,b) for a,b in zip(actual,expected))
    if type(expected) is bytes: return len(actual) == len(expected) and actual == expected
    if type(expected) is float: return _canonical(actual) == _canonical(expected)
    return type(expected) in (str,int,bool,type(None)) and actual == expected


def complete_quality_report(image_manifest, mask_manifest, report_identity, report_metadata):
    """Complete a draft with caller-only metadata, preserving prepared report bytes."""
    result = {'schema_version':1,'scope':'UNREGISTERED_EXPLICIT_QUALITY_REPORT_COMPLETION_ONLY','status':'BLOCKED',
        'issue':None,'image_manifest_draft':None,'mask_manifest_draft':None,'report_manifest_draft':None,
        'report_envelope':None,'report_bytes':None,'report_sha256':None,'fixed_refs':None}
    result.update({field:False for field in FALSE_FIELDS})
    try:
        fixed_image = _copy_json(image_manifest,'image_manifest')
        fixed_mask = _copy_json(mask_manifest,'mask_manifest')
        fixed_identity = _copy_json(report_identity,'report_identity')
        expected = _expected(fixed_image,fixed_mask,fixed_identity)
        metadata = _metadata(report_metadata)
    except _Invalid as error:
        result['issue'] = {'code':error.code,'field':error.field}; return result
    except Exception:
        result['issue'] = {'code':'REPORT_INPUT_INVALID','field':'inputs'}; return result
    try:
        # Separate arguments protect verification snapshots from a mutable producer.
        producer = prepare_quality_mask_bundle(_copy_json(fixed_image,'image_manifest'),
            _copy_json(fixed_mask,'mask_manifest'),_copy_json(fixed_identity,'report_identity'))
        _need(_same(producer,expected),'PREPARATION_OUTPUT_INVALID','bundle')
        patch = expected['report_manifest_patch']
        _need(not (metadata.keys() & patch.keys()),'REPORT_METADATA_INVALID','report_metadata')
        report = {**metadata,**_copy_json(patch,'report_manifest_patch')}
        result.update(status='UNREGISTERED_REPORT_MANIFEST_PREPARED',image_manifest_draft=expected['image_manifest_draft'],
            mask_manifest_draft=expected['mask_manifest_draft'],report_manifest_draft=report,
            report_envelope=expected['report_envelope'],report_bytes=expected['report_bytes'],
            report_sha256=expected['report_sha256'],fixed_refs=expected['fixed_refs'])
    except Exception:
        result['issue'] = {'code':'PREPARATION_OUTPUT_INVALID','field':'bundle'}
    return result
