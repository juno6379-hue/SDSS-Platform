"""Pinned auxiliary GTiff header alignment; no raster content hashes or pixels."""
import hashlib
import json
import math
from pathlib import Path
import rasterio
from .recovery_terminal import _confined, _fingerprint, _finite, _pairs, _constant
from .recovery_raster_content import _sha_valid
from .recovery_raster_headers import (_stamp, _valid_transform, SAFE_GDAL_OPTIONS,
    TRANSFORM_ABSOLUTE_TOLERANCE, TRANSFORM_RELATIVE_TOLERANCE)

AUXILIARY_ROLES = ('patch_label', 'patch_quality', 'source_quality')
MAX_UNIQUE_HEADERS = 10000


def _read_auxiliary_header(path):
    with path.open('rb') as stream:
        magic = stream.read(8)
    if magic[:4] not in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
        return {'status': 'UNSUPPORTED', 'reason': 'NOT_TIFF_MAGIC'}
    if magic[:4] in (b'II+\x00', b'MM\x00+'):
        endian = 'little' if magic[:2] == b'II' else 'big'
        if len(magic) != 8 or int.from_bytes(magic[4:6], endian) != 8 or magic[6:8] != b'\x00\x00':
            return {'status': 'INVALID', 'reason': 'INVALID_BIGTIFF_HEADER'}
    try:
        with rasterio.Env(**SAFE_GDAL_OPTIONS):
            with rasterio.open(path, mode='r', driver='GTiff', GEOREF_SOURCES='INTERNAL') as dataset:
                if dataset.driver != 'GTiff':
                    return {'status': 'UNSUPPORTED', 'reason': 'DRIVER_NOT_GTIFF'}
                affine = tuple(dataset.transform)[:6]
                if any(type(value) is not int or value <= 0 for value in (dataset.width, dataset.height, dataset.count)) or dataset.crs is None or not _valid_transform(affine):
                    return {'status': 'INVALID', 'reason': 'INVALID_DIMENSIONS_CRS_OR_AFFINE'}
                nodata = [value if value is None or math.isfinite(value) else 'NON_FINITE' for value in dataset.nodatavals]
                return {'status': 'VALID_HEADER', 'driver': dataset.driver, 'width': dataset.width,
                    'height': dataset.height, 'count': dataset.count, 'dtypes': list(dataset.dtypes),
                    'nodata_values': nodata, 'crs_wkt': dataset.crs.to_wkt(), 'transform': list(affine)}
    except (rasterio.errors.RasterioError, ValueError, TypeError, OverflowError):
        return {'status': 'INVALID', 'reason': 'GTIFF_HEADER_UNREADABLE'}


def inspect_recovery_auxiliary_headers(data_root, expected_manifest_sha256, *, max_unique_headers=MAX_UNIQUE_HEADERS):
    if not _sha_valid(expected_manifest_sha256):
        raise ValueError('Explicit lowercase manifest SHA256 is required')
    if type(max_unique_headers) is not int or not 1 <= max_unique_headers <= MAX_UNIQUE_HEADERS:
        raise ValueError('Unique header budget must be an integer from 1 through 10000')
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')):
        raise ValueError('Data root must be local')
    root = requested.resolve()
    targets, planned = {}, {}

    def resolve(path):
        logical = Path(path)
        target = _confined(root, logical)
        if logical in targets and targets[logical] != target:
            raise ValueError('Logical input target changed')
        targets[logical] = target
        return target

    manifest = resolve(root / 'first-group-training-esri-v1/annual-window-report.json')
    manifest_ref = _fingerprint(manifest)
    if not manifest_ref['exists'] or manifest_ref['sha256'] != expected_manifest_sha256:
        raise ValueError('Pinned manifest missing or SHA mismatch')
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError('Manifest changed during read')
    aggregate = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    _finite(aggregate)
    if type(aggregate) is not dict or type(aggregate.get('scenes')) is not list or not aggregate['scenes']:
        raise ValueError('Manifest requires nonempty scenes list')
    issues, unknown, pairings = [], [], []
    coverage = {role: {'recorded_rows': 0, 'unknown_rows': 0, 'matched_rows': 0, 'exact_affine_rows': 0, 'unique_files': 0} for role in AUXILIARY_ROLES}

    def pair(role, index, paths, path_key, hashes, hash_key, optional=False):
        has_path, has_hash = path_key in paths, hash_key in hashes
        if not has_path and not has_hash and optional:
            unknown.append({'scene_index': index, 'role': role, 'status': 'UNKNOWN_REFERENCE_ABSENT'})
            coverage[role]['unknown_rows'] += 1
            return None
        if not has_path or not has_hash:
            issues.append({'code': 'REFERENCE_MISSING_OR_PARTIAL', 'scene_index': index, 'role': role})
            return None
        path, expected = paths[path_key], hashes[hash_key]
        if type(path) is not str or not path:
            issues.append({'code': 'EXPLICIT_PATH_INVALID', 'scene_index': index, 'role': role})
            return None
        target = resolve(path)
        if not _sha_valid(expected):
            issues.append({'code': 'EXPLICIT_SHA_INVALID', 'scene_index': index, 'role': role})
            return None
        if target not in planned:
            planned[target] = {'expected_sha256': expected, 'roles': set(), 'file_stat': _stamp(target)}
        entry = planned[target]
        if entry['expected_sha256'] != expected:
            issues.append({'code': 'EXPECTED_SHA_CANONICAL_PATH_CONFLICT', 'scene_index': index, 'path': str(target)})
        entry['roles'].add(role)
        if role in coverage:
            coverage[role]['recorded_rows'] += 1
        return target

    for index, row in enumerate(aggregate['scenes']):
        if type(row) is not dict:
            issues.append({'code': 'SCENE_INVALID', 'scene_index': index}); continue
        hashes, source = row.get('patch_sha256', {}), row.get('source_window', {})
        if type(hashes) is not dict or type(source) is not dict:
            issues.append({'code': 'REFERENCE_CONTAINER_INVALID', 'scene_index': index}); continue
        image = pair('patch_image', index, row, 'image_path', hashes, 'image')
        source_image = pair('source_image', index, source, 'path', source, 'sha256')
        label = pair('patch_label', index, row, 'label_path', hashes, 'label')
        quality = pair('patch_quality', index, row, 'quality_mask_path', hashes, 'quality')
        source_quality = pair('source_quality', index, source, 'quality_mask_path', source, 'quality_mask_sha256', optional=True)
        for role, auxiliary, reference in [('patch_label', label, image), ('patch_quality', quality, image), ('source_quality', source_quality, source_image)]:
            if auxiliary is not None and reference is not None:
                pairings.append({'scene_index': index, 'role': role, 'auxiliary': auxiliary, 'image': reference})
    for path, entry in planned.items():
        if not entry['file_stat']['exists']:
            issues.append({'code': 'FILE_MISSING', 'path': str(path)})
        for role in entry['roles']:
            if role in coverage: coverage[role]['unique_files'] += 1
    if len(planned) > max_unique_headers:
        raise ValueError('Unique header plan exceeds explicit budget; no headers opened')
    plan_valid = not issues
    headers = {}
    if plan_valid:
        for path, entry in planned.items():
            if _confined(root, path) != path or _stamp(path) != entry['file_stat']:
                raise ValueError('Header target changed before open')
            headers[path] = _read_auxiliary_header(path)
            if headers[path]['status'] != 'VALID_HEADER':
                issues.append({'code': 'DECLARED_HEADER_' + headers[path]['status'], 'path': str(path), 'roles': sorted(entry['roles'])})
            if _stamp(path) != entry['file_stat']:
                raise ValueError('Raster changed while reading header')
    checks = []
    if plan_valid:
        for pairing in pairings:
            auxiliary, image = headers[pairing['auxiliary']], headers[pairing['image']]
            codes = []
            exact_affine = None
            for label, header in [('AUXILIARY', auxiliary), ('PAIRED_IMAGE', image)]:
                if header['status'] != 'VALID_HEADER': codes.append(label + '_HEADER_' + header['status'])
            if auxiliary['status'] == image['status'] == 'VALID_HEADER':
                if (auxiliary['width'], auxiliary['height']) != (image['width'], image['height']): codes.append('DIMENSIONS_MISMATCH')
                if pairing['role'].startswith('patch_') and (auxiliary['width'], auxiliary['height']) != (256, 256): codes.append('PATCH_DIMENSIONS_NOT_256')
                if auxiliary['count'] != 1: codes.append('AUXILIARY_COUNT_NOT_ONE')
                if auxiliary['dtypes'] != ['uint8']: codes.append('AUXILIARY_DTYPE_NOT_UINT8')
                if auxiliary['nodata_values'] != [0]: codes.append('AUXILIARY_NODATA_NOT_ZERO')
                if rasterio.crs.CRS.from_wkt(auxiliary['crs_wkt']) != rasterio.crs.CRS.from_wkt(image['crs_wkt']): codes.append('CRS_MISMATCH')
                exact_affine = auxiliary['transform'] == image['transform']
                if exact_affine: coverage[pairing['role']]['exact_affine_rows'] += 1
                if not all(math.isclose(a, b, rel_tol=TRANSFORM_RELATIVE_TOLERANCE, abs_tol=TRANSFORM_ABSOLUTE_TOLERANCE) for a, b in zip(auxiliary['transform'], image['transform'])): codes.append('AFFINE_MISMATCH')
            check = {'scene_index': pairing['scene_index'], 'role': pairing['role'], 'auxiliary_path': str(pairing['auxiliary']), 'paired_image_path': str(pairing['image']), 'status': 'HEADER_ALIGNMENT_MATCH' if not codes else 'ISSUES_FOUND', 'affine_exact_match': exact_affine, 'issues': codes}
            checks.append(check)
            if not codes: coverage[pairing['role']]['matched_rows'] += 1
            issues.extend({'code': code, 'scene_index': pairing['scene_index'], 'role': pairing['role']} for code in codes)
    for logical, target in targets.items():
        if _confined(root, logical) != target:
            raise ValueError('Logical input target changed during inspection')
    if _fingerprint(manifest) != manifest_ref:
        raise ValueError('Pinned manifest changed during inspection')
    for path, entry in planned.items():
        if _stamp(path) != entry['file_stat']:
            raise ValueError('Local file changed during inspection')
    validation = 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'ISSUES_FOUND' if issues else 'KNOWN_HEADERS_MATCH_PARTIAL' if unknown else 'HEADERS_MATCH'
    return {'schema_version': 1, 'kind': 'RECOVERY_AUXILIARY_HEADER_ALIGNMENT', 'mode': 'READ_ONLY',
        'status': 'BLOCKED', 'header_validation': validation,
        'coverage_status': 'PLAN_INVALID' if not plan_valid else 'INCOMPLETE_REFERENCES' if unknown else 'COMPLETE_REFERENCES',
        'aggregate': manifest_ref, 'aggregate_scene_count': len(aggregate['scenes']), 'role_coverage': coverage,
        'unknown_references': unknown, 'boundary_status': 'OUT_OF_SCOPE', 'issues': issues, 'checks': checks,
        'planned_unique_file_count': len(planned), 'opened_unique_header_count': len(headers), 'max_unique_headers': max_unique_headers,
        'headers': [{'path': str(path), 'roles': sorted(planned[path]['roles']), 'file_stat': planned[path]['file_stat'], **header} for path, header in headers.items()],
        'safe_gdal_options': SAFE_GDAL_OPTIONS.copy(), 'transform_tolerance': {'absolute': TRANSFORM_ABSOLUTE_TOLERANCE, 'relative': TRANSFORM_RELATIVE_TOLERANCE},
        'readiness_full_gate_revalidated': False, 'pixel_arrays_read': False, 'raster_content_sha_revalidated': False, 'recorded_sha_status': 'FORMAT_AND_CONFLICT_ONLY',
        'label_semantics_validated': False, 'quality_suitability_validated': False, 'boundary_authorization_verified': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Pinned-manifest declared GTiff header alignment only; no pixel semantics, QA fitness, current raster SHA verification, boundary approval, independent geometry or recovery authorization.'}
