"""Metadata-only image/mask grid diagnostic after fixed quality-file bindings."""
import math

from ..dataset_registry import canonical_manifest, version_key
from .model_checkpoint_manifest import _manifest
from .registered_per_scene_files import _ref, _Issue, _need
from .registered_quality_mask_files import read_registered_quality_mask_files
from .registry_raster_grid_normalization import _header, _RasterBlocked
from .per_scene_normalization_contract import BAND_NAMES
from .per_scene_normalization_files import _root, _relative, _snapshot, _Blocked

FALSE_FIELDS = ('quality_report_verified', 'quality_mask_verified', 'pixel_values_verified',
    'mask_semantics_verified', 'registry_aoi_verified', 'source_authority_verified',
    'scientific_accuracy_validated', 'execution_authorized', 'state_dict_verified', 'workflow_supported')


class _CaptureStore:
    def __init__(self, store, refs):
        self.store = store
        self.targets = {version_key(ref['id'], ref['version']): (role, ref)
            for role, ref in (('image', refs[0]), ('mask', refs[2]))}
        self.manifests = {}

    @property
    def root(self):
        return self.store.root

    def get(self, kind, identifier):
        record = self.store.get(kind, identifier)
        if kind != 'dataset_versions' or identifier not in self.targets:
            return record
        role, ref = self.targets[identifier]
        _need(type(record) is dict and len(record) <= 128 and all(type(k) is str for k in record)
            and type(record.get('id')) is str and record['id'] == identifier,
            'REGISTRY_RECORD_INVALID', role)
        try:
            manifest, digest = canonical_manifest(_manifest(record.get('manifest')))
        except Exception:
            raise _Issue('REGISTRY_RECORD_INVALID', role) from None
        _need(record.get('manifest_sha256') == digest and manifest['dataset_id'] == ref['id']
            and manifest['version'] == ref['version'] and manifest['sha256'] == ref['sha256'],
            'REGISTRY_REFERENCE_CONFLICT', role)
        _need(manifest['data_type'] == 'raster', 'REGISTRY_TYPE_MISMATCH', role)
        _need(manifest['access_class'] == 'PUBLIC', 'ACCESS_DECLARATION_BLOCKED', role)
        self.manifests[role] = manifest
        return {**record, 'manifest': manifest}


def _mask_header(raw):
    _need(raw[:4] in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'),
        'MASK_FORMAT_UNSUPPORTED', 'mask')
    try:
        import rasterio
        from rasterio.io import MemoryFile
        with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_GEOREF_SOURCES='INTERNAL'):
            with MemoryFile(raw) as memory:
                with memory.open(driver='GTiff') as dataset:
                    _need(dataset.driver == 'GTiff', 'MASK_FORMAT_UNSUPPORTED', 'mask')
                    _need(1 <= dataset.width <= 1024 and 1 <= dataset.height <= 1024
                        and dataset.count == 1 and dataset.dtypes == ('uint8',), 'MASK_HEADER_INVALID', 'shape_dtype')
                    crs = dataset.crs
                    _need(crs is not None and crs.is_projected, 'MASK_HEADER_INVALID', 'crs')
                    units, factor = crs.linear_units_factor
                    _need(units.lower() in ('metre', 'meter', 'metres', 'meters') and factor == 1.0,
                        'MASK_HEADER_INVALID', 'crs')
                    wkt = crs.to_wkt()
                    _need(type(wkt) is str and 1 <= len(wkt) <= 32768, 'MASK_HEADER_INVALID', 'crs')
                    transform = list(dataset.transform)[:6]
                    a, b, c, d, e, f = transform
                    _need(all(math.isfinite(v) for v in transform) and a > 0 and e < 0 and b == 0 and d == 0
                        and math.isfinite(a*e) and a*e != 0, 'MASK_HEADER_INVALID', 'transform')
                    corners = [(a*x+b*y+c, d*x+e*y+f) for x, y in
                        ((0, 0), (dataset.width, 0), (0, dataset.height), (dataset.width, dataset.height))]
                    _need(all(math.isfinite(v) for point in corners for v in point), 'MASK_HEADER_INVALID', 'bounds')
                    xs, ys = zip(*corners)
                    _need(min(xs) < max(xs) and min(ys) < max(ys), 'MASK_HEADER_INVALID', 'bounds')
                    return {'width': dataset.width, 'height': dataset.height, 'count': 1, 'dtype': 'uint8',
                        'crs_wkt': wkt, 'transform': transform, 'bounds': [min(xs), min(ys), max(xs), max(ys)]}
    except _Issue:
        raise
    except Exception:
        raise _Issue('MASK_HEADER_INVALID', 'mask') from None


def inspect_registered_quality_mask_grid(store, image_ref, quality_report_ref, mask_ref):
    """No pixels or approval; header reads intentionally follow all131 byte reads."""
    result = {'schema_version': 1, 'scope': 'REGISTERED_QUALITY_MASK_GRID_READ_ONLY', 'status': 'BLOCKED',
        'issue': None, 'quality_mask_observation': None, 'image_header': None, 'mask_header': None,
        'image_mask_headers_verified': False, 'image_mask_grid_verified': False, 'artifact_bytes_verified': False}
    result.update({field: False for field in FALSE_FIELDS})
    try:
        refs = (image_ref, quality_report_ref, mask_ref)
        if not all(_ref(ref) for ref in refs) or len({(ref['id'], ref['version']) for ref in refs}) != 3:
            result['quality_mask_observation'] = read_registered_quality_mask_files(store, None, None, None)
            result['issue'] = {'code': 'INVALID_INPUT', 'field': 'references'}
            return result
        refs = tuple(dict(ref) for ref in refs)
        proxy = _CaptureStore(store, refs)
        base = read_registered_quality_mask_files(proxy, *refs)
        result['quality_mask_observation'] = base
        if base['status'] != 'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED':
            result['issue'] = base['issue']
            return result
        image = proxy.manifests['image']; mask = proxy.manifests['mask']
        names = image['source'].get('band_names')
        _need(type(names) is list and len(names) == 6 and all(type(n) is str for n in names)
            and names == list(BAND_NAMES), 'RASTER_BAND_SIGNATURE_INVALID', 'band_names')
        root = _root(store.root)
        for role, manifest, ref, maximum in (('image', image, refs[0], 64*1024**2), ('mask', mask, refs[2], 16*1024**2)):
            try:
                path = _relative(root, manifest['artifact_uri'], role)
                digest, raw = _snapshot(root, path, maximum, role, True)
                _need(digest == ref['sha256'], 'SHA256_MISMATCH', role)
                result[role+'_header'] = _header(raw, names) if role == 'image' else _mask_header(raw)
            except (_Blocked, _RasterBlocked) as error:
                raise _Issue(error.code, role) from None
        image_header, mask_header = result['image_header'], result['mask_header']
        _need(all(image_header[key] == mask_header[key] for key in ('width', 'height', 'crs_wkt', 'transform', 'bounds')),
            'IMAGE_MASK_GRID_MISMATCH', 'grid')
        result.update(status='REGISTERED_QUALITY_MASK_GRID_MATCHED_UNVERIFIED',
            image_mask_headers_verified=True, image_mask_grid_verified=True, artifact_bytes_verified=True)
    except (_Issue, _Blocked, _RasterBlocked) as error:
        result['issue'] = {'code': error.code, 'field': error.field}
    except Exception:
        result['issue'] = {'code': 'MASK_GRID_UNAVAILABLE', 'field': 'inputs'}
    return result
