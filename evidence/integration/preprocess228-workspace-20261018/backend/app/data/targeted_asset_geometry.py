"""Read-only local image/reference coverage observation; never dispatches work."""
import hashlib
import json
import math

from .targeted_bare_plan import _pinned, _keys, _need
from .quality_mask_bundle import _copy_json, _Invalid
from ..ml.per_scene_normalization_files import _root, _Blocked

TOP = {'schema_version', 'kind', 'target_year', 'image_year', 'label_year',
       'target_bbox_wgs84', 'image_ref', 'label_ref'}
ISSUES = {'REQUEST_INVALID', 'YEAR_DECLARATION_MISMATCH', 'BBOX_INVALID',
          'REFERENCE_INVALID', 'PATH_INVALID', 'FILE_PIN_MISMATCH',
          'RASTER_INVALID', 'RASTER_GRID_INVALID', 'TRANSFORM_INVALID',
          'IMAGE_COVERAGE_SHORTFALL', 'LABEL_COVERAGE_SHORTFALL'}
MAXIMUM_BYTES = 64 * 1024**2


def _observe(raw, bbox, role):
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.warp import transform_bounds
    _need(raw[:4] in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'), 'RASTER_INVALID')
    with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                      GDAL_GEOREF_SOURCES='INTERNAL', PROJ_NETWORK='OFF'):
        with MemoryFile(raw) as memory:
            with memory.open(driver='GTiff') as ds:
                _need(ds.driver == 'GTiff' and not ds.subdatasets and not ds.gcps[0]
                      and ds.rpcs is None, 'RASTER_INVALID')
                t = ds.transform
                _need(ds.crs is not None and ds.crs.to_epsg() is not None and
                      (ds.crs.is_projected or ds.crs.is_geographic) and
                      1 <= ds.width <= 65536 and 1 <= ds.height <= 65536 and
                      1 <= ds.count <= 64 and all(math.isfinite(v) for v in t) and
                      t.b == t.d == 0 and t.a > 0 and t.e < 0, 'RASTER_GRID_INVALID')
                bounds = list(ds.bounds)
                _need(all(math.isfinite(v) for v in bounds), 'RASTER_GRID_INVALID')
                if ds.crs.to_epsg() == 4326:
                    requested = list(bbox)
                    padding = [0.0] * 4
                else:
                    # GDAL's densified edge envelope, expanded outward by 16 ULPs.
                    # This is a bounded numerical observation, not a proof over every
                    # point of an arbitrary nonlinear projection (see implementation160).
                    requested = list(transform_bounds('EPSG:4326', ds.crs, *bbox, densify_pts=1024))
                    _need(all(math.isfinite(v) for v in requested) and
                          requested[0] < requested[2] and requested[1] < requested[3], 'TRANSFORM_INVALID')
                    padding = [16 * math.ulp(v) for v in requested]
                    requested = [requested[0]-padding[0], requested[1]-padding[1],
                                 requested[2]+padding[2], requested[3]+padding[3]]
                _need(bounds[0] <= requested[0] and bounds[1] <= requested[1] and
                      requested[2] <= bounds[2] and requested[3] <= bounds[3],
                      'IMAGE_COVERAGE_SHORTFALL' if role == 'image' else 'LABEL_COVERAGE_SHORTFALL')
                return {'role': role, 'crs': ds.crs.to_string(), 'transform': list(t)[:6],
                        'width': ds.width, 'height': ds.height, 'band_count': ds.count,
                        'actual_bounds': bounds, 'request_native_envelope': requested,
                        'numerical_outward_padding': padding,
                        'sampled_native_envelope_contained': True,
                        'coverage_method': 'EPSG4326_EXACT' if ds.crs.to_epsg() == 4326 else 'DENSIFIED_ENVELOPE_NUMERICAL_OBSERVATION',
                        'complete_projection_coverage_proven': False}


def inspect_targeted_asset_geometry(project_root, request):
    """Check two explicitly pinned local GTiffs. Returns no jobs or authorization.

    Year equality is caller-declaration equality, not temporal provenance validation.
    A densified WGS84 envelope is checked independently in each actual raster CRS.
    No pixel quality, SCL, pending footprint, scene split, or execution is checked.
    """
    result = {'schema_version': 1, 'scope': 'LOCAL_PINNED_ASSET_COVERAGE_ONLY',
              'status': 'BLOCKED', 'issue': None, 'request_sha256': None, 'assets': [],
              'local_bytes_verified': False, 'declared_years_match': False,
              'same_grid_asserted': False, 'execution_supported': False,
              'pending_footprints_verified': False, 'support_assets_verified': False,
              'source_scene_split_verified': False, 'quality_verified': False,
              'temporal_truth_verified': False, 'training_ready': False}
    try:
        value = _copy_json(request, 'request')
        _need(_keys(value, TOP) and type(value['schema_version']) is int and
              value['schema_version'] == 1 and value['kind'] == 'TARGETED_ASSET_GEOMETRY_REQUEST', 'REQUEST_INVALID')
        years = [value[k] for k in ('target_year', 'image_year', 'label_year')]
        _need(all(type(y) is int and 2020 <= y <= 2025 for y in years), 'REQUEST_INVALID')
        _need(len(set(years)) == 1, 'YEAR_DECLARATION_MISMATCH')
        bbox = value['target_bbox_wgs84']
        _need(type(bbox) is list and len(bbox) == 4 and
              all(type(v) in (int, float) and math.isfinite(v) for v in bbox) and
              -180 <= bbox[0] < bbox[2] <= 180 and -90 < bbox[1] < bbox[3] < 90,
              'BBOX_INVALID')
        # Validate both explicit refs before any raster parsing.
        root = _root(project_root)
        pinned = [(role, value[role+'_ref'], _pinned(root, value[role+'_ref'], MAXIMUM_BYTES))
                  for role in ('image', 'label')]
        observed = []
        for role, ref, (_, raw) in pinned:
            row = _observe(raw, bbox, role)
            row['sha256'] = ref['sha256']
            observed.append(row)
        # Re-open and re-hash both originals after all geometry reads. This is not
        # an atomic OS snapshot; transient changes between reads remain outside scope.
        for _, ref, _ in pinned:
            _pinned(root, ref, MAXIMUM_BYTES)
        digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                          allow_nan=False, separators=(',', ':')).encode()).hexdigest()
        result.update(status='LOCAL_COVERAGE_OBSERVED_EXECUTION_BLOCKED',
                      issue='EXECUTION_GUARDS_NOT_CONNECTED', request_sha256=digest,
                      assets=observed, local_bytes_verified=True, declared_years_match=True)
    except _Blocked:
        result['issue'] = 'LOCAL_INPUT_UNAVAILABLE'
    except _Invalid:
        result['issue'] = 'REQUEST_INVALID'
    except ValueError as exc:
        result['issue'] = str(exc) if str(exc) in ISSUES else 'RASTER_INVALID'
    except Exception:
        result['issue'] = 'LOCAL_INPUT_UNAVAILABLE'
    return result
