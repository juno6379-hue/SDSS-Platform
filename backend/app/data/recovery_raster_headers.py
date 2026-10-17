"""Local GTiff header-only crop checks. No pixels, raster digests or recovery writes."""
import hashlib
import json
import math
from pathlib import Path
import rasterio
from affine import Affine
from .recovery_terminal import _confined, _fingerprint, _finite, _pairs, _constant

SAFE_GDAL_OPTIONS = {
    'GDAL_PAM_ENABLED': 'NO', 'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR',
    'PROJ_NETWORK': 'OFF', 'GDAL_GEOREF_SOURCES': 'INTERNAL',
    'GDAL_VRT_ENABLE_PYTHON': 'NO',
}
TRANSFORM_ABSOLUTE_TOLERANCE = 1e-7
TRANSFORM_RELATIVE_TOLERANCE = 1e-12


def _stamp(path):
    if not path.exists():
        return {'exists': False}
    if not path.is_file():
        raise ValueError('Raster evidence must be a regular local file')
    stat = path.stat()
    return {'exists': True, 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
            'ctime_ns': stat.st_ctime_ns, 'inode': stat.st_ino, 'device': stat.st_dev}


def _valid_transform(values):
    if len(values) != 6 or not all(math.isfinite(v) for v in values):
        return False
    a, b, _, d, e, _ = values
    determinant = a * e - b * d
    return math.isfinite(determinant) and determinant != 0


def _read_header(path):
    """Only eight signature bytes and GDAL metadata; never calls dataset.read."""
    with path.open('rb') as stream:
        magic = stream.read(8)
    if magic[:4] not in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
        return {'status': 'UNSUPPORTED', 'reason': 'NOT_TIFF_MAGIC'}
    if magic[:4] in (b'II+\x00', b'MM\x00+'):
        order = 'little' if magic[:2] == b'II' else 'big'
        if len(magic) != 8 or int.from_bytes(magic[4:6], order) != 8 or magic[6:8] != b'\x00\x00':
            return {'status': 'INVALID', 'reason': 'INVALID_BIGTIFF_HEADER'}
    try:
        with rasterio.Env(**SAFE_GDAL_OPTIONS):
            with rasterio.open(path, mode='r', driver='GTiff', GEOREF_SOURCES='INTERNAL') as dataset:
                if dataset.driver != 'GTiff':
                    return {'status': 'UNSUPPORTED', 'reason': 'DRIVER_NOT_GTIFF'}
                transform = tuple(dataset.transform)[:6]
                if any(type(v) is not int or v <= 0 for v in (dataset.width, dataset.height, dataset.count)) or dataset.crs is None or not _valid_transform(transform):
                    return {'status': 'INVALID', 'reason': 'INVALID_DIMENSIONS_CRS_OR_AFFINE'}
                return {'status': 'VALID_HEADER', 'driver': dataset.driver,
                        'width': dataset.width, 'height': dataset.height, 'count': dataset.count,
                        'crs_wkt': dataset.crs.to_wkt(), 'transform': list(transform),
                        'dtypes': list(dataset.dtypes)}
    except (rasterio.errors.RasterioError, ValueError, TypeError, OverflowError):
        return {'status': 'INVALID', 'reason': 'GTIFF_HEADER_UNREADABLE'}


def inspect_recovery_raster_headers(data_root):
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')):
        raise ValueError('Data root must be local')
    root = requested.resolve()
    targets, raster_stamps, headers = {}, {}, {}

    def resolve(path):
        logical = Path(path)
        target = _confined(root, logical)
        if logical in targets and targets[logical] != target:
            raise ValueError('Logical input target changed')
        targets[logical] = target
        return target

    logical_manifest = root / 'first-group-training-esri-v1/annual-window-report.json'
    manifest = resolve(logical_manifest)
    manifest_reference = _fingerprint(manifest)
    if not manifest_reference['exists']:
        raise ValueError('Aggregate manifest missing')
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_reference['sha256']:
        raise ValueError('Aggregate changed while reading')
    aggregate = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    _finite(aggregate)
    if type(aggregate) is not dict or type(aggregate.get('scenes')) is not list:
        raise ValueError('Aggregate requires scenes list')

    def header(logical):
        path = resolve(logical)
        stamp = _stamp(path)
        if path in raster_stamps and raster_stamps[path] != stamp:
            raise ValueError('Raster changed between header observations')
        raster_stamps[path] = stamp
        if path not in headers:
            headers[path] = _read_header(path) if stamp['exists'] else {'status': 'MISSING', 'reason': 'FILE_MISSING'}
        if _stamp(path) != stamp:
            raise ValueError('Raster changed while reading header')
        return path, headers[path]

    issues, scene_checks = [], []
    for index, row in enumerate(aggregate['scenes']):
        codes = []
        if type(row) is not dict:
            issues.append({'scene_index': index, 'code': 'SCENE_INVALID'})
            scene_checks.append({'scene_index': index, 'status': 'INVALID', 'issues': ['SCENE_INVALID']})
            continue
        source_window = row.get('source_window')
        source_path = source_window.get('path') if type(source_window) is dict else None
        patch_path = row.get('image_path')
        if any(type(value) is not str or not value for value in (source_path, patch_path)):
            codes.append('SOURCE_OR_PATCH_PATH_INVALID')
        crop = row.get('window_in_source')
        crop_valid = type(crop) is list and len(crop) == 4 and all(type(value) is int for value in crop)
        crop_valid = crop_valid and crop[0] >= 0 and crop[1] >= 0 and crop[2:] == [256, 256] and crop[0] % 256 == 0 and crop[1] % 256 == 0
        if not crop_valid:
            codes.append('CROP_COORDINATES_INVALID')
        check = {'scene_index': index, 'status': 'NOT_CHECKED', 'issues': codes}
        scene_checks.append(check)
        if 'SOURCE_OR_PATCH_PATH_INVALID' not in codes:
            source_target, source = header(source_path)
            patch_target, patch = header(patch_path)
            check.update(source_path=str(source_target), patch_path=str(patch_target),
                         source_header_status=source['status'], patch_header_status=patch['status'])
            for label, value in [('SOURCE', source), ('PATCH', patch)]:
                if value['status'] != 'VALID_HEADER':
                    codes.append(label + '_HEADER_' + value['status'])
            if source['status'] == patch['status'] == 'VALID_HEADER' and crop_valid:
                x, y, width, height = crop
                if x + width > source['width'] or y + height > source['height']:
                    codes.append('CROP_OUTSIDE_SOURCE_BOUNDS')
                if (patch['width'], patch['height']) != (256, 256):
                    codes.append('PATCH_DIMENSIONS_MISMATCH')
                if patch['count'] != source['count']:
                    codes.append('PATCH_BAND_COUNT_MISMATCH')
                if patch['dtypes'] != source['dtypes']:
                    codes.append('PATCH_DTYPES_MISMATCH')
                if rasterio.crs.CRS.from_wkt(patch['crs_wkt']) != rasterio.crs.CRS.from_wkt(source['crs_wkt']):
                    codes.append('PATCH_CRS_MISMATCH')
                # Do not convert unbounded JSON offsets to float outside source bounds.
                if x + width <= source['width'] and y + height <= source['height']:
                    expected = Affine(*source['transform']) @ Affine.translation(x, y)
                    if not all(math.isclose(actual, target, rel_tol=TRANSFORM_RELATIVE_TOLERANCE, abs_tol=TRANSFORM_ABSOLUTE_TOLERANCE) for actual, target in zip(patch['transform'], tuple(expected)[:6])):
                        codes.append('PATCH_TRANSFORM_MISMATCH')
        check['status'] = 'HEADER_CONTRACT_MATCH' if not codes else 'ISSUES_FOUND'
        issues.extend({'scene_index': index, 'code': code} for code in codes)
    for logical, target in targets.items():
        if _confined(root, logical) != target:
            raise ValueError('Logical input target changed during inspection')
    if _fingerprint(manifest) != manifest_reference:
        raise ValueError('Aggregate changed during inspection')
    for path, stamp in raster_stamps.items():
        if _stamp(path) != stamp:
            raise ValueError('Raster changed during inspection')
    return {'schema_version': 1, 'kind': 'RECOVERY_LOCAL_GTIFF_HEADER_VALIDATION', 'mode': 'READ_ONLY',
        'status': 'BLOCKED', 'header_consistency': 'ISSUES_FOUND' if issues else 'CONSISTENT_HEADERS',
        'aggregate_scene_count': len(aggregate['scenes']), 'unique_raster_path_count': len(headers),
        'scene_checks': scene_checks, 'issues': issues, 'aggregate': manifest_reference,
        'raster_headers': [{'path': str(path), 'file_stat': raster_stamps[path], **value} for path, value in headers.items()],
        'safe_gdal_options': SAFE_GDAL_OPTIONS.copy(),
        'transform_tolerance': {'absolute': TRANSFORM_ABSOLUTE_TOLERANCE, 'relative': TRANSFORM_RELATIVE_TOLERANCE},
        'pixel_arrays_read': False, 'raster_content_sha_computed': False, 'label_quality_checked': False,
        'same_content_different_file_checked': False, 'geometric_independence_checked': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False,
        'execution_authorized': False, 'automatic_resume_allowed': False, 'proposed_refund_bytes': 0,
        'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Local GTiff headers/stat stability only; no pixels, raster content hashes, label/quality, independent geometry, scientific accuracy or recovery execution approval.'}
