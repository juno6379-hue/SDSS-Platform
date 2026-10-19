"""Pinned declared boundary JSON structure/province linkage; never official approval."""
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
from .recovery_terminal import _confined, _finite, _pairs, _constant
from .recovery_raster_content import _sha_valid, _file_stamp, _stat_record

LIMITS = {'max_boundary_files': 16, 'max_local_bytes': 4 * 1024 ** 2,
          'max_features': 128, 'max_vertices': 100000, 'max_json_depth': 32}
MAX_MANIFEST_BYTES = 64 * 1024 ** 2


def _utf8_text(raw):
    text = raw.decode('utf-8')
    if text.startswith('\ufeff') or '\x00' in text:
        raise ValueError('Only UTF-8 JSON without BOM or NUL is supported')
    return text


def _check_depth(raw, maximum):
    """Scan decoded UTF-8 before parsing; reject alternate/NUL-based encodings."""
    text = _utf8_text(raw)
    depth, quoted, escaped = 0, False, False
    for value in text:
        if quoted:
            if escaped: escaped = False
            elif value == '\\': escaped = True
            elif value == '"': quoted = False
        elif value == '"': quoted = True
        elif value in '[{':
            depth += 1
            if depth > maximum: raise ValueError('JSON nesting exceeds explicit depth limit')
        elif value in ']}': depth -= 1


def _read_bounded(path, expected_stat, maximum, depth):
    if expected_stat['bytes'] > maximum: raise ValueError('JSON file exceeds byte limit')
    if _file_stamp(path) != expected_stat: raise ValueError('JSON input changed before read')
    pieces, count = [], 0
    with path.open('rb', buffering=0) as stream:
        if _stat_record(os.fstat(stream.fileno())) != expected_stat: raise ValueError('JSON descriptor changed')
        while count < expected_stat['bytes']:
            block = stream.read(min(65536, expected_stat['bytes'] - count))
            if not block: raise ValueError('JSON input ended early')
            count += len(block); pieces.append(block)
        if _stat_record(os.fstat(stream.fileno())) != expected_stat: raise ValueError('JSON input changed during read')
    if _file_stamp(path) != expected_stat: raise ValueError('JSON input changed after read')
    raw = b''.join(pieces)
    _check_depth(raw, depth)
    return raw


def _decode(raw):
    document = json.loads(_utf8_text(raw), object_pairs_hook=_pairs, parse_constant=_constant)
    _finite(document)
    return document


def _inspect_structure(document, limits):
    issues, identities = [], defaultdict(list)
    count = 0
    features = document.get('features') if type(document) is dict else None
    if type(document) is not dict or document.get('type') != 'FeatureCollection' or type(features) is not list or not features:
        return {'status': 'INVALID', 'issues': [{'code': 'FEATURE_COLLECTION_INVALID'}], 'feature_count': 0, 'vertex_count': 0, 'province_features': {}}
    if len(features) > limits['max_features']: raise ValueError('Boundary feature limit exceeded')
    if 'crs' in document: issues.append({'code': 'EXPLICIT_CRS_DECLARATION_NOT_SUPPORTED'})
    for index, feature in enumerate(features):
        local_issues = []
        if type(feature) is not dict or feature.get('type') != 'Feature':
            issues.append({'code': 'FEATURE_INVALID', 'feature_index': index}); continue
        properties = feature.get('properties')
        province = properties.get('province_id') if type(properties) is dict else None
        if type(province) is not str or not province.strip():
            local_issues.append('PROVINCE_ID_MISSING_OR_INVALID')
        geometry = feature.get('geometry')
        if type(geometry) is not dict or geometry.get('type') not in ('Polygon', 'MultiPolygon'):
            local_issues.append('GEOMETRY_TYPE_UNSUPPORTED')
        else:
            coordinates = geometry.get('coordinates')
            polygons = [coordinates] if geometry['type'] == 'Polygon' else coordinates
            if type(polygons) is not list or not polygons:
                local_issues.append('POLYGON_COORDINATES_INVALID')
            else:
                for polygon in polygons:
                    if type(polygon) is not list or not polygon:
                        local_issues.append('POLYGON_RINGS_INVALID'); continue
                    for ring in polygon:
                        if type(ring) is not list:
                            local_issues.append('RING_INVALID'); continue
                        if len(ring) < 4: local_issues.append('RING_INVALID')
                        if ring and ring[0] != ring[-1]: local_issues.append('RING_NOT_CLOSED')
                        for position in ring:
                            count += 1
                            if count > limits['max_vertices']: raise ValueError('Total boundary vertex limit exceeded')
                            if type(position) is not list or len(position) != 2 or any(type(v) not in (int, float) for v in position):
                                local_issues.append('POSITION_NOT_FINITE_2D_NUMBER'); continue
                            try:
                                valid = all(math.isfinite(v) for v in position) and -180 <= position[0] <= 180 and -90 <= position[1] <= 90
                            except OverflowError:
                                valid = False
                            if not valid: local_issues.append('POSITION_OUT_OF_RANGE_OR_NONFINITE')
        if type(province) is str and province.strip(): identities[province].append({'feature_index': index, 'structure_valid': not local_issues})
        issues.extend({'code': code, 'feature_index': index} for code in sorted(set(local_issues)))
    for province, entries in identities.items():
        if len(entries) > 1: issues.append({'code': 'DUPLICATE_PROVINCE_ID', 'province_id': province, 'feature_indexes': [entry['feature_index'] for entry in entries]})
    return {'status': 'STRUCTURE_MATCH' if not issues else 'INVALID', 'issues': issues,
            'feature_count': len(features), 'vertex_count': count, 'province_features': dict(identities)}


def inspect_recovery_boundary(data_root, expected_manifest_sha256, **requested_limits):
    if not _sha_valid(expected_manifest_sha256): raise ValueError('Explicit lowercase manifest SHA256 required')
    if set(requested_limits) - set(LIMITS): raise ValueError('Unknown boundary limit option')
    limits = {**LIMITS, **requested_limits}
    if any(type(value) is not int or not 1 <= value <= LIMITS[key] for key, value in limits.items()):
        raise ValueError('Boundary limits must be positive integers within fixed caps')
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')): raise ValueError('Data root must be local')
    root = requested.resolve()
    targets, planned = {}, {}

    def resolve(path):
        logical = Path(path); target = _confined(root, logical)
        if logical in targets and targets[logical] != target: raise ValueError('Logical input target changed')
        targets[logical] = target
        return target

    manifest = resolve(root / 'first-group-training-esri-v1/annual-window-report.json')
    manifest_stat = _file_stamp(manifest)
    if not manifest_stat['exists']: raise ValueError('Pinned manifest missing')
    raw = _read_bounded(manifest, manifest_stat, MAX_MANIFEST_BYTES, LIMITS['max_json_depth'])
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256: raise ValueError('Pinned manifest SHA mismatch')
    aggregate = _decode(raw)
    if type(aggregate) is not dict or type(aggregate.get('scenes')) is not list or not aggregate['scenes']: raise ValueError('Manifest requires nonempty scenes list')
    issues, unknown, declared = [], [], []
    for index, row in enumerate(aggregate['scenes']):
        if type(row) is not dict:
            issues.append({'code': 'SCENE_INVALID', 'scene_index': index}); continue
        source = row.get('source_window', {})
        if type(source) is not dict:
            issues.append({'code': 'SOURCE_CONTAINER_INVALID', 'scene_index': index}); continue
        has_path, has_sha = 'boundary_path' in source, 'boundary_sha256' in source
        if not has_path and not has_sha:
            unknown.append({'scene_index': index, 'status': 'UNKNOWN_REFERENCE_ABSENT'}); continue
        if not has_path or not has_sha:
            issues.append({'code': 'PARTIAL_BOUNDARY_REFERENCE', 'scene_index': index}); continue
        path, expected = source['boundary_path'], source['boundary_sha256']
        if type(path) is not str or not path:
            issues.append({'code': 'BOUNDARY_PATH_INVALID', 'scene_index': index}); continue
        target = resolve(path)
        if not _sha_valid(expected):
            issues.append({'code': 'BOUNDARY_SHA_INVALID', 'scene_index': index}); continue
        province = row.get('province')
        if type(province) is not str or not province.strip():
            issues.append({'code': 'ROW_PROVINCE_INVALID', 'scene_index': index}); continue
        if target not in planned:
            planned[target] = {'expected_sha256': expected, 'file_stat': _file_stamp(target)}
        if planned[target]['expected_sha256'] != expected:
            issues.append({'code': 'BOUNDARY_SHA_CANONICAL_CONFLICT', 'scene_index': index})
        declared.append({'scene_index': index, 'province': province, 'path': target})
    for path, entry in planned.items():
        if not entry['file_stat']['exists']: issues.append({'code': 'BOUNDARY_FILE_MISSING', 'path': str(path)})
    if len(planned) > limits['max_boundary_files']: raise ValueError('Boundary file-count limit exceeded before read')
    planned_bytes = sum(entry['file_stat'].get('bytes', 0) for entry in planned.values())
    if planned_bytes > limits['max_local_bytes']: raise ValueError('Boundary total-byte limit exceeded before read')
    plan_valid, consumed = not issues, 0
    files, structures = [], {}
    feature_total = vertex_total = 0
    if plan_valid:
        for path, entry in planned.items():
            if _confined(root, path) != path: raise ValueError('Canonical boundary target changed')
            payload = _read_bounded(path, entry['file_stat'], limits['max_local_bytes'] - consumed, limits['max_json_depth'])
            consumed += len(payload)
            observed = hashlib.sha256(payload).hexdigest()
            result = {'path': str(path), 'expected_sha256': entry['expected_sha256'], 'observed_sha256': observed, 'bytes_read': len(payload), 'file_stat': entry['file_stat']}
            if observed != entry['expected_sha256']:
                result['status'] = 'SHA_MISMATCH'; issues.append({'code': 'BOUNDARY_SHA_MISMATCH', 'path': str(path)})
            else:
                try:
                    structure = _inspect_structure(_decode(payload), {**limits, 'max_features': limits['max_features'] - feature_total, 'max_vertices': limits['max_vertices'] - vertex_total})
                except (json.JSONDecodeError, UnicodeError):
                    structure = {'status': 'INVALID', 'issues': [{'code': 'BOUNDARY_JSON_INVALID'}], 'feature_count': 0, 'vertex_count': 0, 'province_features': {}}
                structures[path] = structure
                feature_total += structure['feature_count']; vertex_total += structure['vertex_count']
                result.update(structure)
                issues.extend({'path': str(path), **issue} for issue in structure['issues'])
            files.append(result)
    links = []
    if plan_valid:
        for row in declared:
            structure = structures.get(row['path'])
            matches = structure['province_features'].get(row['province'], []) if structure else []
            status = 'UNKNOWN_BOUNDARY_INVALID' if structure is None else 'MISSING_PROVINCE' if not matches else 'AMBIGUOUS_PROVINCE' if len(matches) > 1 else 'UNIQUE_PROVINCE_MATCH' if matches[0]['structure_valid'] else 'INVALID_FEATURE_STRUCTURE'
            links.append({'scene_index': row['scene_index'], 'province': row['province'], 'boundary_path': str(row['path']), 'status': status})
            if status != 'UNIQUE_PROVINCE_MATCH': issues.append({'code': status, 'scene_index': row['scene_index']})
    for logical, target in targets.items():
        if _confined(root, logical) != target: raise ValueError('Logical input target changed during inspection')
    if _file_stamp(manifest) != manifest_stat: raise ValueError('Manifest changed during inspection')
    final_manifest = _read_bounded(manifest, manifest_stat, MAX_MANIFEST_BYTES, LIMITS['max_json_depth'])
    if hashlib.sha256(final_manifest).hexdigest() != expected_manifest_sha256: raise ValueError('Manifest content changed during inspection')
    for path, entry in planned.items():
        if _file_stamp(path) != entry['file_stat']: raise ValueError('Boundary changed during inspection')
    return {'schema_version': 1, 'kind': 'RECOVERY_BOUNDARY_JSON_VALIDATION', 'mode': 'READ_ONLY', 'status': 'BLOCKED',
        'boundary_validation': 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'ISSUES_FOUND' if issues else 'NO_RECORDED_REFERENCES' if not planned else 'KNOWN_STRUCTURE_MATCH_PARTIAL' if unknown else 'STRUCTURE_MATCH',
        'coverage_status': 'PLAN_INVALID' if not plan_valid else 'INCOMPLETE_REFERENCES' if unknown else 'COMPLETE_REFERENCES',
        'manifest': {'path': str(manifest), 'sha256': expected_manifest_sha256}, 'aggregate_scene_count': len(aggregate['scenes']),
        'declared_reference_rows': len(declared), 'unknown_references': unknown, 'planned_unique_file_count': len(planned),
        'planned_boundary_bytes': planned_bytes, 'actual_boundary_bytes_read': consumed, 'limits': limits,
        'feature_count': feature_total, 'vertex_count': vertex_total, 'files': files, 'region_links': links, 'issues': issues,
        'topology_validated': False, 'self_intersection_checked': False, 'official_adm1_verified': False,
        'boundary_authorization_verified': False, 'pixel_inside_coverage_checked': False, 'geometric_independence_checked': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Pinned declared GeoJSON structure and province_id linkage only; no topology, official status, authority, pixel coverage, independent geometry or recovery approval.'}
