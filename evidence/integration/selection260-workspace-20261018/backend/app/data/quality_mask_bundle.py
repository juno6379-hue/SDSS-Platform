"""Pure unregistered declaration bundle; report metadata remains caller-required."""
import hashlib
import json
import math
import re
from datetime import datetime

from ..model_reference_contract import model_reference_issue

FALSE_FIELDS = ('artifact_bytes_verified', 'registry_references_verified', 'registry_registered',
    'quality_report_verified', 'quality_mask_verified', 'source_authority_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')
REQUIRED_REPORT_METADATA = ('source', 'spatial', 'temporal', 'quality_status', 'access_class')


class _Invalid(Exception):
    def __init__(self, code, field): self.code, self.field = code, field


def _need(value, code, field):
    if not value: raise _Invalid(code, field)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _copy_json(value, field):
    nodes = 0; budget = 0; active = set()
    def copy(item, depth):
        nonlocal nodes, budget
        nodes += 1
        _need(nodes <= 8192 and depth <= 16, 'INVALID_MANIFEST', field)
        kind = type(item)
        if kind in (dict, list):
            _need(id(item) not in active and len(item) <= (128 if kind is dict else 1024), 'INVALID_MANIFEST', field)
            active.add(id(item))
            try:
                if kind is dict:
                    _need(all(type(k) is str and 1 <= len(k) <= 128 and all(ord(c) >= 32
                        and not 127 <= ord(c) <= 159 and not 0xD800 <= ord(c) <= 0xDFFF for c in k) for k in item), 'INVALID_MANIFEST', field)
                    budget += 2 + 2*len(item) + sum(len(_canonical(k)) for k in item)
                    result = {key: copy(child, depth+1) for key, child in item.items()}
                else:
                    budget += 2 + len(item)
                    result = [copy(child, depth+1) for child in item]
            finally: active.remove(id(item))
        else:
            _need(kind in (str, int, float, bool, type(None)), 'INVALID_MANIFEST', field)
            if kind is str:
                _need(len(item) <= 4096 and all(not 0xD800 <= ord(c) <= 0xDFFF for c in item), 'INVALID_MANIFEST', field)
            elif kind is int: _need(abs(item) <= 2**53-1, 'INVALID_MANIFEST', field)
            elif kind is float: _need(math.isfinite(item), 'INVALID_MANIFEST', field)
            budget += len(_canonical(item)); result = item
        _need(budget <= 262144, 'INVALID_MANIFEST', field)
        return result
    _need(type(value) is dict, 'INVALID_MANIFEST', field)
    return copy(value, 0)


def _text(value):
    return (type(value) is str and 1 <= len(value) <= 512 and bool(value.strip())
        and all(ord(c) >= 32 and not 127 <= ord(c) <= 159 and not 0xD800 <= ord(c) <= 0xDFFF for c in value))


def _path(value, field):
    _need(_text(value), 'PATH_INVALID', field)
    normalized = value.replace('\\', '/')
    parts = normalized.split('/')
    _need(':' not in normalized and not normalized.startswith('/') and all(1 <= len(part) <= 128
        and part not in ('.', '..') and not part.endswith((' ', '.')) for part in parts), 'PATH_INVALID', field)
    return normalized


def _identity(value, field):
    _need(model_reference_issue({'id': value.get('dataset_id'), 'version': value.get('version')}) is None, 'INVALID_MANIFEST', field)
    _need(type(value.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None, 'INVALID_MANIFEST', field)
    return {'id': value['dataset_id'], 'version': value['version'], 'sha256': value['sha256']}


def _manifest(value, field):
    value = _copy_json(value, field)
    required = {'schema_version', 'dataset_id', 'version', 'source', 'data_type', 'spatial', 'temporal',
        'quality_status', 'access_class', 'sha256', 'artifact_uri', 'lineage'}
    optional = {'units', 'resolution', 'no_data', 'quality_report_ref', 'limitations'}
    _need(required <= value.keys() <= required | optional and value['schema_version'] == '0.2.0'
        and value['data_type'] == 'raster', 'INVALID_MANIFEST', field)
    ref = _identity(value, field)
    source = value['source']
    _need(type(source) is dict and all(_text(source.get(key)) for key in ('institution', 'product', 'license'))
        and ('source_uri' not in source or type(source['source_uri']) is str), 'INVALID_MANIFEST', field)
    spatial = value['spatial']
    _need(type(spatial) is dict and {'bbox','crs'} <= spatial.keys() <= {'bbox','crs','geometry_uri'}, 'INVALID_MANIFEST', field)
    bbox = spatial['bbox']; crs = spatial['crs']
    _need(type(bbox) is list and len(bbox) == 4 and all(type(v) in (int,float) and math.isfinite(v) for v in bbox)
        and bbox[0] < bbox[2] and bbox[1] < bbox[3] and type(crs) is str
        and re.fullmatch(r'(EPSG:[0-9]+|OGC:CRS84)', crs) is not None, 'INVALID_MANIFEST', field)
    if crs in ('EPSG:4326','OGC:CRS84'):
        _need(-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90, 'INVALID_MANIFEST', field)
    _need('geometry_uri' not in spatial or type(spatial['geometry_uri']) is str, 'INVALID_MANIFEST', field)
    temporal = value['temporal']
    _need(type(temporal) is dict and {'start','end','calendar'} <= temporal.keys()
        and _text(temporal['calendar']), 'INVALID_MANIFEST', field)
    dates = []
    for key in ('start','end'):
        stamp = temporal[key]
        _need(type(stamp) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})',stamp) is not None,
            'INVALID_MANIFEST', field)
        try: dates.append(datetime.fromisoformat(stamp.replace('Z','+00:00')))
        except ValueError: raise _Invalid('INVALID_MANIFEST',field) from None
    _need(dates[0] <= dates[1], 'INVALID_MANIFEST', field)
    _need(value['quality_status'] in ('RAW','STAGED'), 'QUALITY_STATUS_UNSUPPORTED', field)
    _need(value['access_class'] in ('PUBLIC','RESTRICTED','CONFIDENTIAL'), 'INVALID_MANIFEST', field)
    lineage = value['lineage']
    _need(type(lineage) is list and len(lineage) <= 128, 'INVALID_MANIFEST', field)
    for parent in lineage:
        _need(type(parent) is dict and {'id','version','sha256'} <= parent.keys() <= {'id','version','sha256','role','uri'}
            and model_reference_issue(parent) is None and type(parent['sha256']) is str
            and re.fullmatch('[0-9a-f]{64}',parent['sha256']) is not None
            and ('uri' not in parent or type(parent['uri']) is str), 'INVALID_MANIFEST', field)
    if 'units' in value: _need(type(value['units']) is str, 'INVALID_MANIFEST', field)
    if 'resolution' in value:
        resolution = value['resolution']; _need(type(resolution) is dict, 'INVALID_MANIFEST', field)
        for key in ('x','y'):
            if key in resolution: _need(type(resolution[key]) in (int,float), 'INVALID_MANIFEST', field)
        if 'unit' in resolution: _need(_text(resolution['unit']), 'INVALID_MANIFEST', field)
    if 'limitations' in value:
        _need(type(value['limitations']) is list and all(_text(item) for item in value['limitations']), 'INVALID_MANIFEST', field)
    if 'quality_report_ref' in value: _path(value['quality_report_ref'], field)
    _path(value['artifact_uri'], field)
    return value, ref


def prepare_quality_mask_bundle(image_manifest, mask_manifest, report_identity):
    """Return bytes + unregistered drafts, never fabricate report attribution."""
    result = {'schema_version':1, 'scope':'UNREGISTERED_QUALITY_MASK_BUNDLE_PREPARATION_ONLY', 'status':'BLOCKED',
        'issue':None, 'image_manifest_draft':None, 'mask_manifest_draft':None, 'report_manifest_patch':None,
        'report_metadata_required':list(REQUIRED_REPORT_METADATA), 'report_envelope':None, 'report_bytes':None,
        'report_sha256':None, 'fixed_refs':None}
    result.update({field:False for field in FALSE_FIELDS})
    try:
        image, image_ref = _manifest(image_manifest, 'image_manifest')
        mask, mask_ref = _manifest(mask_manifest, 'mask_manifest')
        identity = _copy_json(report_identity,'report_identity')
        _need(identity.keys() == {'id','version','artifact_uri'} and model_reference_issue(identity) is None,
            'REPORT_IDENTITY_INVALID','report_identity')
        report_path = _path(identity['artifact_uri'],'report_identity')
        _need(len({(ref['id'],ref['version']) for ref in (image_ref,mask_ref,identity)}) == 3,
            'REFERENCE_CONFLICT','references')
        _need(report_path not in (_path(image['artifact_uri'],'image_manifest'),_path(mask['artifact_uri'],'mask_manifest')),
            'REFERENCE_CONFLICT','report_identity')
        semantics = mask['source'].get('mask_semantics')
        _need(type(semantics) is dict and semantics.keys() == {'schema_version','kind','valid_value','invalid_value'}
            and type(semantics['schema_version']) is int and semantics['schema_version'] == 1
            and semantics['kind'] == 'binary_validity' and type(semantics['valid_value']) is int
            and semantics['valid_value'] == 1 and type(semantics['invalid_value']) is int and semantics['invalid_value'] == 0,
            'MASK_SEMANTICS_INVALID','mask_manifest')
        if 'quality_report_ref' in image:
            _need(_path(image['quality_report_ref'],'quality_report_ref') == report_path,
                'QUALITY_REPORT_REF_CONFLICT','image_manifest')
        envelope = {'schema_version':1,'scope':'LCLUC_QUALITY_MASK_EVIDENCE','image_ref':dict(image_ref),
            'mask_ref':dict(mask_ref),'quality_status':image['quality_status']}
        raw = _canonical(envelope); digest = hashlib.sha256(raw).hexdigest()
        report_ref = {'id':identity['id'],'version':identity['version'],'sha256':digest}
        patch = {'schema_version':'0.2.0','dataset_id':identity['id'],'version':identity['version'],
            'data_type':'document','sha256':digest,'artifact_uri':identity['artifact_uri'],
            'lineage':[{**image_ref,'role':'quality_input_image'},{**mask_ref,'role':'quality_input_mask'}]}
        image['quality_report_ref'] = identity['artifact_uri']
        result.update(status='REPORT_METADATA_REQUIRED_UNREGISTERED', image_manifest_draft=image,mask_manifest_draft=mask,
            report_manifest_patch=patch,report_envelope=envelope,report_bytes=raw,report_sha256=digest,
            fixed_refs={'image_ref':dict(image_ref),'quality_report_ref':report_ref,'mask_ref':dict(mask_ref)})
    except _Invalid as error: result['issue'] = {'code':error.code,'field':error.field}
    except Exception: result['issue'] = {'code':'INVALID_MANIFEST','field':'inputs'}
    return result
