"""Bounded binary mask counts after registered image/mask grid observations."""
from ..dataset_registry import canonical_manifest, version_key
from .model_checkpoint_manifest import _manifest
from .registered_per_scene_files import _ref, _Issue, _need
from .registered_quality_mask_grid import inspect_registered_quality_mask_grid
from .per_scene_normalization_files import _root, _relative, _snapshot, _Blocked

FALSE_FIELDS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified',
    'registry_aoi_verified', 'source_authority_verified', 'minimum_validity_policy_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')


class _MaskStore:
    def __init__(self, store, ref):
        self.store, self.ref = store, ref
        self.key = version_key(ref['id'], ref['version'])
        self.manifest = None

    @property
    def root(self):
        return self.store.root

    def get(self, kind, identifier):
        record = self.store.get(kind, identifier)
        if kind != 'dataset_versions' or identifier != self.key:
            return record
        _need(type(record) is dict and len(record) <= 128 and all(type(k) is str for k in record)
            and type(record.get('id')) is str and record['id'] == identifier, 'REGISTRY_RECORD_INVALID', 'mask')
        try:
            manifest, digest = canonical_manifest(_manifest(record.get('manifest')))
        except Exception:
            raise _Issue('REGISTRY_RECORD_INVALID', 'mask') from None
        _need(record.get('manifest_sha256') == digest and manifest['dataset_id'] == self.ref['id']
            and manifest['version'] == self.ref['version'] and manifest['sha256'] == self.ref['sha256'],
            'REGISTRY_REFERENCE_CONFLICT', 'mask')
        _need(manifest['data_type'] == 'raster', 'REGISTRY_TYPE_MISMATCH', 'mask')
        _need(manifest['access_class'] == 'PUBLIC', 'ACCESS_DECLARATION_BLOCKED', 'mask')
        self.manifest = manifest
        return {**record, 'manifest': manifest}


def _binary_counts(raw, expected):
    _need(raw[:4] in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'), 'MASK_FORMAT_UNSUPPORTED', 'mask')
    try:
        import numpy as np
        import rasterio
        from rasterio.enums import MaskFlags
        from rasterio.io import MemoryFile
        with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_GEOREF_SOURCES='INTERNAL'):
            with MemoryFile(raw) as memory:
                with memory.open(driver='GTiff') as dataset:
                    _need(dataset.driver == 'GTiff' and 1 <= dataset.width <= 1024
                        and 1 <= dataset.height <= 1024 and dataset.count == 1
                        and dataset.dtypes == ('uint8',), 'MASK_HEADER_INVALID', 'mask')
                    header = {'width': dataset.width, 'height': dataset.height, 'count': 1, 'dtype': 'uint8',
                        'crs_wkt': dataset.crs.to_wkt() if dataset.crs is not None else None,
                        'transform': list(dataset.transform)[:6], 'bounds': list(dataset.bounds)}
                    _need(header == expected, 'MASK_HEADER_CHANGED', 'mask')
                    _need(dataset.nodata is None and dataset.mask_flag_enums == ([MaskFlags.all_valid],),
                        'MASK_INTRINSIC_VALIDITY_UNSUPPORTED', 'mask')
                    values = dataset.read(1, masked=False)
                    _need(type(values) is np.ndarray and values.dtype == np.dtype('uint8')
                        and values.shape == (dataset.height, dataset.width), 'MASK_VALUES_INVALID', 'mask')
                    _need(bool(np.all((values == 0) | (values == 1))), 'MASK_VALUES_NOT_BINARY', 'mask')
                    valid = int(np.count_nonzero(values == 1))
                    total = dataset.width * dataset.height
                    return {'valid_pixels': valid, 'invalid_pixels': total-valid, 'total_pixels': total}
    except _Issue:
        raise
    except Exception:
        raise _Issue('MASK_VALUES_UNAVAILABLE', 'mask') from None


def inspect_registered_binary_mask_values(store, image_ref, quality_report_ref, mask_ref):
    """Count explicit 0/1 only; no minimum coverage or semantic/QA approval."""
    result = {'schema_version': 1, 'scope': 'REGISTERED_BINARY_MASK_VALUES_READ_ONLY', 'status': 'BLOCKED',
        'issue': None, 'grid_observation': None, 'counts': None, 'mask_declaration_verified': False,
        'mask_values_verified': False, 'artifact_bytes_verified': False}
    result.update({field: False for field in FALSE_FIELDS})
    try:
        refs = (image_ref, quality_report_ref, mask_ref)
        if not all(_ref(ref) for ref in refs) or len({(ref['id'], ref['version']) for ref in refs}) != 3:
            result['grid_observation'] = inspect_registered_quality_mask_grid(store, None, None, None)
            result['issue'] = {'code': 'INVALID_INPUT', 'field': 'references'}
            return result
        refs = tuple(dict(ref) for ref in refs)
        proxy = _MaskStore(store, refs[2])
        base = inspect_registered_quality_mask_grid(proxy, *refs)
        result['grid_observation'] = base
        if base['status'] != 'REGISTERED_QUALITY_MASK_GRID_MATCHED_UNVERIFIED':
            result['issue'] = base['issue']
            return result
        declaration = proxy.manifest['source'].get('mask_semantics')
        _need(type(declaration) is dict and len(declaration) == 4 and all(type(k) is str for k in declaration)
            and declaration.keys() == {'schema_version', 'kind', 'valid_value', 'invalid_value'},
            'MASK_DECLARATION_INVALID', 'mask_semantics')
        _need(type(declaration['schema_version']) is int and declaration['schema_version'] == 1
            and type(declaration['kind']) is str and declaration['kind'] == 'binary_validity'
            and type(declaration['valid_value']) is int and declaration['valid_value'] == 1
            and type(declaration['invalid_value']) is int and declaration['invalid_value'] == 0,
            'MASK_DECLARATION_INVALID', 'mask_semantics')
        result['mask_declaration_verified'] = True
        root = _root(store.root)
        path = _relative(root, proxy.manifest['artifact_uri'], 'mask')
        digest, raw = _snapshot(root, path, 16*1024**2, 'mask', True)
        _need(digest == refs[2]['sha256'], 'SHA256_MISMATCH', 'mask')
        result['counts'] = _binary_counts(raw, base['mask_header'])
        result.update(status='REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED',
            mask_values_verified=True, artifact_bytes_verified=True)
    except (_Issue, _Blocked) as error:
        result['issue'] = {'code': error.code, 'field': error.field}
    except Exception:
        result['issue'] = {'code': 'MASK_VALUES_UNAVAILABLE', 'field': 'inputs'}
    return result
