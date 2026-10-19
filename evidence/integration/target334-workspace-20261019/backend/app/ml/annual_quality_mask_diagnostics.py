"""Read-only annual spatial + binary mask diagnostics with registry digest join."""
from .pinned_annual_normalization import _request
from .model_checkpoint_manifest import _sha
from .registered_per_scene_files import _ref
from .registry_spatial_normalization import inspect_registry_spatial_normalization
from .registered_binary_mask_values import inspect_registered_binary_mask_values

FALSE_FIELDS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified',
    'minimum_validity_policy_verified', 'registry_aoi_verified', 'source_authority_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')
ROW_KEYS = {'year', 'image_ref', 'evidence_ref', 'metadata_ref', 'quality_report_ref', 'mask_ref'}


def _snapshot_request(model_ref, report_sha, rows):
    if not (type(rows) is list and 2 <= len(rows) <= 6):
        raise ValueError('invalid')
    snapshot = []
    for row in rows:
        if not (type(row) is dict and len(row) == 6 and all(type(k) is str for k in row)
                and row.keys() == ROW_KEYS and all(_ref(row[key]) for key in ROW_KEYS if key != 'year')):
            raise ValueError('invalid')
        snapshot.append({'year': row['year'], **{key: dict(row[key]) for key in ROW_KEYS if key != 'year'}})
    projection = [{key: row[key] for key in ('year', 'image_ref', 'evidence_ref', 'metadata_ref')} for row in snapshot]
    ref, projection = _request(model_ref, report_sha, projection)
    for row in snapshot:
        if len({(row[key]['id'], row[key]['version']) for key in ('image_ref', 'quality_report_ref', 'mask_ref')}) != 3:
            raise ValueError('invalid')
    return ref, snapshot, projection


def inspect_annual_quality_mask_diagnostics(store, model_ref, training_report_sha256, requested_years):
    """No execution; NOT_CHECKED mask rows can already have130 image file I/O."""
    result = {'schema_version': 1, 'scope': 'ANNUAL_REGISTERED_QUALITY_MASK_READ_ONLY', 'status': 'INVALID_INPUT',
        'issue': None, 'annual_spatial_observation': None, 'mask_observations': [],
        'spatial_observation_calls': 0, 'mask_observation_calls': 0, 'checked_rows': 0,
        'artifact_bytes_verified': False, 'mask_values_verified': False, 'registry_manifest_join_verified': False}
    result.update({field: False for field in FALSE_FIELDS})
    try:
        ref, rows, projection = _snapshot_request(model_ref, training_report_sha256, requested_years)
    except Exception:
        result['issue'] = {'code': 'INVALID_INPUT', 'field': 'request', 'year': None}
        return result
    result['mask_observations'] = [{'year': row['year'], 'status': 'NOT_CHECKED', 'mask_observation': None,
        'registry_manifest_join_verified': False, 'issue': None} for row in rows]
    result['status'] = 'ANNUAL_SPATIAL_BLOCKED'
    try:
        result['spatial_observation_calls'] = 1
        spatial = inspect_registry_spatial_normalization(store, ref, training_report_sha256, projection)
        result['annual_spatial_observation'] = spatial
        if spatial['status'] != 'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED':
            result['issue'] = spatial['issue'] or {'code': 'ANNUAL_SPATIAL_BLOCKED', 'field': 'annual', 'year': None}
            return result
        temporal = spatial['raster_batch_observation']['temporal_batch_observation']['temporal_observations']
        if type(temporal) is not list or len(temporal) != len(rows) or any(observation['year'] != row['year'] for observation, row in zip(temporal, rows)):
            raise ValueError('invalid observations')
    except Exception:
        result['issue'] = {'code': 'ANNUAL_SPATIAL_BLOCKED', 'field': 'annual', 'year': None}
        return result
    result['status'] = 'MASK_BLOCKED'
    for row, output, temporal_row in zip(rows, result['mask_observations'], temporal):
        try:
            result['mask_observation_calls'] += 1
            result['checked_rows'] += 1
            mask = inspect_registered_binary_mask_values(store, row['image_ref'], row['quality_report_ref'], row['mask_ref'])
            output['mask_observation'] = mask
            if mask['status'] != 'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED':
                output['issue'] = mask['issue'] or {'code': 'MASK_OBSERVATION_BLOCKED', 'field': 'mask'}
                raise ValueError('blocked')
            bindings = mask['grid_observation']['quality_mask_observation']['registry_bindings']
            images = [binding for binding in bindings if binding['role'] == 'image'] if type(bindings) is list and len(bindings) == 3 else []
            if (len(images) != 1 or not _sha(images[0].get('manifest_sha256'))
                    or not _sha(temporal_row.get('manifest_sha256'))
                    or images[0]['manifest_sha256'] != temporal_row['manifest_sha256']):
                output['issue'] = {'code': 'REGISTRY_IMAGE_MANIFEST_CHANGED', 'field': 'image_manifest'}
                raise ValueError('changed')
            output.update(status='MATCHED_UNVERIFIED', registry_manifest_join_verified=True)
        except Exception:
            output['status'] = 'BLOCKED'
            output['issue'] = output['issue'] or {'code': 'MASK_OBSERVATION_BLOCKED', 'field': 'mask'}
            result['issue'] = {**output['issue'], 'year': row['year']}
            return result
    result.update(status='ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED', artifact_bytes_verified=True,
        mask_values_verified=True, registry_manifest_join_verified=True)
    return result
