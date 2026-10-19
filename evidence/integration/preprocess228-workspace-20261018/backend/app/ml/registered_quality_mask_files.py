"""Read registered quality/mask declarations and bytes, never grant QA approval."""
from ..dataset_registry import canonical_manifest, version_key
from .model_checkpoint_manifest import _manifest, _Invalid
from .registered_per_scene_files import _ref, _Issue, _need
from .per_scene_normalization_files import _root, _relative, _snapshot, _evidence_json, _Blocked

ROLES = ('image', 'quality_report', 'mask')
MAXIMUMS = (64 * 1024**2, 2 * 1024**2, 16 * 1024**2)
FALSE_FIELDS = ('quality_report_verified', 'quality_mask_verified', 'raster_header_verified',
    'state_dict_verified', 'source_authority_verified', 'access_authorization_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported')


def read_registered_quality_mask_files(store, image_ref, quality_report_ref, mask_ref):
    """Three fixed references; the mask is opaque and the report is a declaration.

    Partial flags describe completed binding observations, not full success.
    Store predecode and sequential file snapshots are not an atomic/RSS boundary.
    """
    result = {'schema_version': 1, 'scope': 'REGISTERED_QUALITY_MASK_FILES_READ_ONLY',
        'status': 'BLOCKED', 'issue': None, 'registry_bindings': [],
        'file_bindings': [{'role': role, 'status': 'NOT_CHECKED'} for role in ROLES],
        'registry_references_verified': False, 'report_bindings_verified': False,
        'artifact_bytes_verified': False}
    result.update({field: False for field in FALSE_FIELDS})
    try:
        refs = (image_ref, quality_report_ref, mask_ref)
        _need(all(_ref(ref) for ref in refs), 'INVALID_INPUT', 'references')
        refs = tuple(dict(ref) for ref in refs)
        _need(len({(ref['id'], ref['version']) for ref in refs}) == 3, 'INVALID_INPUT', 'references')
        manifests = []
        for role, ref, kind in zip(ROLES, refs, ('raster', 'document', 'raster')):
            key = version_key(ref['id'], ref['version'])
            try:
                record = store.get('dataset_versions', key)
            except KeyError:
                raise _Issue('REGISTRY_RECORD_UNAVAILABLE', role) from None
            _need(type(record) is dict and len(record) <= 128
                and all(type(k) is str for k in record) and type(record.get('id')) is str
                and record['id'] == key, 'REGISTRY_RECORD_INVALID', role)
            try:
                manifest, digest = canonical_manifest(_manifest(record.get('manifest')))
            except Exception:
                raise _Issue('REGISTRY_RECORD_INVALID', role) from None
            _need(manifest['dataset_id'] == ref['id'] and manifest['version'] == ref['version']
                and manifest['sha256'] == ref['sha256'] and record.get('manifest_sha256') == digest,
                'REGISTRY_REFERENCE_CONFLICT', role)
            _need(manifest['data_type'] == kind, 'REGISTRY_TYPE_MISMATCH', role)
            _need(manifest['access_class'] == 'PUBLIC', 'ACCESS_DECLARATION_BLOCKED', role)
            manifests.append(manifest)
            result['registry_bindings'].append({'role': role, 'ref': dict(ref),
                'manifest_sha256': digest, 'quality_status': manifest['quality_status'],
                'access_class': manifest['access_class']})
        result['registry_references_verified'] = True
        image, report, mask = manifests
        for ref, role in ((refs[0], 'quality_input_image'), (refs[2], 'quality_input_mask')):
            parents = [parent for parent in report['lineage'] if parent.get('role') == role]
            _need(len(parents) == 1 and all(parents[0][key] == ref[key] for key in ('id', 'version', 'sha256')),
                'LINEAGE_BINDING_INVALID', 'quality_report')
        root = _root(store.root)
        paths = [_relative(root, manifest['artifact_uri'], role) for role, manifest in zip(ROLES, manifests)]
        _need(_relative(root, image.get('quality_report_ref'), 'quality_report') == paths[1],
            'QUALITY_REPORT_PATH_MISMATCH', 'quality_report')
        digest, raw = _snapshot(root, paths[1], MAXIMUMS[1], 'quality_report', True)
        _need(digest == refs[1]['sha256'], 'SHA256_MISMATCH', 'quality_report')
        result['file_bindings'][1]['status'] = 'MATCH'
        try:
            envelope = _manifest(_evidence_json(raw))
        except (_Blocked, _Invalid) as error:
            raise _Issue(error.code, 'quality_report') from None
        _need(len(envelope) == 5 and envelope.keys() ==
            {'schema_version', 'scope', 'image_ref', 'mask_ref', 'quality_status'},
            'QUALITY_REPORT_INVALID', 'quality_report')
        _need(type(envelope['schema_version']) is int and envelope['schema_version'] == 1
            and envelope['scope'] == 'LCLUC_QUALITY_MASK_EVIDENCE'
            and _ref(envelope['image_ref']) and _ref(envelope['mask_ref'])
            and type(envelope['quality_status']) is str,
            'QUALITY_REPORT_INVALID', 'quality_report')
        _need(envelope['image_ref'] == refs[0] and envelope['mask_ref'] == refs[2]
            and envelope['quality_status'] == image['quality_status'],
            'QUALITY_REPORT_BINDING_MISMATCH', 'quality_report')
        result['report_bindings_verified'] = True
        for index in (0, 2):
            digest, _ = _snapshot(root, paths[index], MAXIMUMS[index], ROLES[index])
            _need(digest == refs[index]['sha256'], 'SHA256_MISMATCH', ROLES[index])
            result['file_bindings'][index]['status'] = 'MATCH'
        result.update(status='REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED', artifact_bytes_verified=True)
    except (_Issue, _Blocked, _Invalid) as error:
        result['issue'] = {'code': error.code, 'field': error.field}
    except Exception:
        result['issue'] = {'code': 'REGISTRY_RECORD_UNAVAILABLE', 'field': 'inputs'}
    return result
