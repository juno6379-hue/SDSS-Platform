"""Bounded within-file feature-pair diagnostics; no boundary repair or approval."""
import hashlib
import json
import math
from pathlib import Path
from .recovery_boundary import LIMITS, MAX_MANIFEST_BYTES, _read_bounded, _decode, _inspect_structure
from .recovery_boundary_topology import _geometry_runtime, _feature_topology
from .recovery_terminal import _confined
from .recovery_raster_content import _sha_valid, _file_stamp


def _construct_checked_geometry(feature, shape_fn, explain_fn):
    try:
        geometry = shape_fn(feature['geometry'])
    except Exception as exc:
        return {'status': 'UNKNOWN_ENGINE_ERROR', 'is_empty': None, 'is_valid': None,
                'area_square_degrees_planar': None, 'finite_positive_area': None,
                'validity_reason': 'UNKNOWN', 'error_type': type(exc).__name__}, None
    check = _feature_topology(feature, lambda unused: geometry, explain_fn)
    return check, geometry if check['status'] == 'VALID_TOPOLOGY' else None


def _pair_relation(left, right):
    try:
        intersection = left.intersection(right)
        empty = bool(intersection.is_empty)
        area = float(intersection.area)
        if not math.isfinite(area) or area < 0:
            return {'status': 'UNKNOWN_INVALID_INTERSECTION_AREA', 'intersection_area_square_degrees': None}
        if empty:
            if area != 0:
                return {'status': 'UNKNOWN_INCONSISTENT_RELATION', 'intersection_area_square_degrees': area}
            return {'status': 'DISJOINT', 'intersection_empty': True, 'intersects': False,
                    'disjoint': True, 'touches': False, 'equal': False,
                    'left_contains_right': False, 'right_contains_left': False,
                    'intersection_area_square_degrees': 0.0}
        touches = bool(left.touches(right))
        if area == 0:
            if not touches:
                return {'status': 'UNKNOWN_INCONSISTENT_RELATION', 'intersection_area_square_degrees': 0.0}
            return {'status': 'BOUNDARY_CONTACT', 'intersection_empty': False, 'intersects': True,
                    'disjoint': False, 'touches': True, 'equal': False,
                    'left_contains_right': False, 'right_contains_left': False,
                    'intersection_area_square_degrees': 0.0}
        if touches:
            return {'status': 'UNKNOWN_INCONSISTENT_RELATION', 'intersection_area_square_degrees': area}
        return {'status': 'POSITIVE_AREA_OVERLAP', 'intersection_empty': False, 'intersects': True,
                'disjoint': False, 'touches': False, 'equal': bool(left.equals(right)),
                'left_contains_right': bool(left.contains(right)), 'right_contains_left': bool(right.contains(left)),
                'intersection_area_square_degrees': area}
    except Exception as exc:
        return {'status': 'UNKNOWN_ENGINE_ERROR', 'intersection_area_square_degrees': None,
                'error_type': type(exc).__name__}


def inspect_recovery_boundary_relations(data_root, expected_manifest_sha256, *, max_pairs=64, **requested_limits):
    if type(max_pairs) is not int or not 1 <= max_pairs <= 8128: raise ValueError('Pair budget must be an integer from 1 through 8128')
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
    files, structures, documents = [], {}, {}
    runtime, shape_fn, explain_fn = _geometry_runtime()
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
                    document = _decode(payload)
                    structure = _inspect_structure(document, {**limits, 'max_features': limits['max_features'] - feature_total, 'max_vertices': limits['max_vertices'] - vertex_total})
                except (json.JSONDecodeError, UnicodeError):
                    structure = {'status': 'INVALID', 'issues': [{'code': 'BOUNDARY_JSON_INVALID'}], 'feature_count': 0, 'vertex_count': 0, 'province_features': {}}
                structures[path] = structure
                if structure['status'] == 'STRUCTURE_MATCH': documents[path] = document
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
    topology_checks, pair_plan, geometry_cache = [], [], {}
    pair_results = []
    cross_file_pair_count = 0
    topology_input_valid = plan_valid and not issues
    if topology_input_valid:
        feature_total_for_pairs = sum(len(document['features']) for document in documents.values())
        planned_pair_count = sum(len(document['features']) * (len(document['features']) - 1) // 2 for document in documents.values())
        cross_file_pair_count = feature_total_for_pairs * (feature_total_for_pairs - 1) // 2 - planned_pair_count
        if planned_pair_count > max_pairs:
            raise ValueError('Full within-file pair plan exceeds budget; no pair work performed')
        for path, document in documents.items():
            pair_plan.extend((path, left, right) for left in range(len(document['features'])) for right in range(left + 1, len(document['features'])))
    if topology_input_valid and runtime['available']:
        for path, document in documents.items():
            for index, feature in enumerate(document['features']):
                check, geometry = _construct_checked_geometry(feature, shape_fn, explain_fn)
                if geometry is not None: geometry_cache[(path, index)] = geometry
                check.update(boundary_path=str(path), feature_index=index,
                             province_id=feature['properties']['province_id'])
                topology_checks.append(check)
                if check['status'] != 'VALID_TOPOLOGY':
                    issues.append({'code': check['status'], 'path': str(path), 'feature_index': index})
    elif topology_input_valid and planned and not runtime['available']:
        issues.append({'code': 'GEOMETRY_ENGINE_UNAVAILABLE'})
    topology_all_valid = topology_input_valid and runtime['available'] and all(check['status'] == 'VALID_TOPOLOGY' for check in topology_checks)
    if topology_all_valid:
        for path, left, right in pair_plan:
            relation = _pair_relation(geometry_cache[(path, left)], geometry_cache[(path, right)])
            relation.update(boundary_path=str(path), left_feature_index=left, right_feature_index=right,
                left_province_id=documents[path]['features'][left]['properties']['province_id'],
                right_province_id=documents[path]['features'][right]['properties']['province_id'])
            pair_results.append(relation)
            if relation['status'].startswith('UNKNOWN'):
                issues.append({'code': relation['status'], 'path': str(path), 'left_feature_index': left, 'right_feature_index': right})
    for logical, target in targets.items():
        if _confined(root, logical) != target: raise ValueError('Logical input target changed during inspection')
    if _file_stamp(manifest) != manifest_stat: raise ValueError('Manifest changed during inspection')
    final_manifest = _read_bounded(manifest, manifest_stat, MAX_MANIFEST_BYTES, LIMITS['max_json_depth'])
    if hashlib.sha256(final_manifest).hexdigest() != expected_manifest_sha256: raise ValueError('Manifest content changed during inspection')
    for path, entry in planned.items():
        if _file_stamp(path) != entry['file_stat']: raise ValueError('Boundary changed during inspection')
    return {'schema_version': 1, 'kind': 'RECOVERY_BOUNDARY_FEATURE_RELATIONS', 'mode': 'READ_ONLY', 'status': 'BLOCKED',
        'boundary_validation': 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'ISSUES_FOUND' if issues else 'NO_RECORDED_REFERENCES' if not planned else 'KNOWN_STRUCTURE_MATCH_PARTIAL' if unknown else 'STRUCTURE_MATCH',
        'coverage_status': 'PLAN_INVALID' if not plan_valid else 'INCOMPLETE_REFERENCES' if unknown else 'COMPLETE_REFERENCES',
        'manifest': {'path': str(manifest), 'sha256': expected_manifest_sha256}, 'aggregate_scene_count': len(aggregate['scenes']),
        'declared_reference_rows': len(declared), 'unknown_references': unknown, 'planned_unique_file_count': len(planned),
        'planned_boundary_bytes': planned_bytes, 'actual_boundary_bytes_read': consumed, 'limits': limits,
        'feature_count': feature_total, 'vertex_count': vertex_total, 'files': files, 'region_links': links, 'issues': issues,
        'geometry_runtime': runtime, 'topology_feature_checks': topology_checks,
        'topology_validation': 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'NOT_CHECKED_INPUT_ISSUES' if not topology_input_valid else 'NO_RECORDED_REFERENCES' if not planned else 'NOT_CHECKED_ENGINE_UNAVAILABLE' if not runtime['available'] else 'TOPOLOGY_ISSUES_FOUND' if any(c['status'] != 'VALID_TOPOLOGY' for c in topology_checks) else 'KNOWN_TOPOLOGY_VALID_PARTIAL' if unknown else 'TOPOLOGY_VALID',
        'topology_engine_attempt_count': len(topology_checks), 'area_units': 'square_degrees_planar_diagnostic',
        'automatic_geometry_repair_performed': False, 'geometry_reprojected': False,
        'pair_scope': 'WITHIN_EACH_BOUNDARY_FILE_ONLY', 'cross_file_pairs_status': 'OUT_OF_SCOPE',
        'cross_file_pair_count_out_of_scope': cross_file_pair_count,
        'pair_plan_evaluated': topology_input_valid, 'max_pairs': max_pairs,
        'planned_pair_count': len(pair_plan) if topology_input_valid else None,
        'pair_attempt_count': len(pair_results), 'pair_results': pair_results,
        'pair_validation': 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'NOT_CHECKED_INPUT_ISSUES' if not topology_input_valid else 'NO_RECORDED_REFERENCES' if not planned else 'NOT_CHECKED_ENGINE_UNAVAILABLE' if not runtime['available'] else 'NOT_CHECKED_TOPOLOGY_ISSUES' if not topology_all_valid else 'NO_PAIR_CANDIDATES' if not pair_plan else 'RELATION_ISSUES_FOUND' if any(p['status'].startswith('UNKNOWN') for p in pair_results) else 'KNOWN_RELATIONS_DIAGNOSED_PARTIAL' if unknown else 'RELATIONS_DIAGNOSED',
        'positive_area_overlap_pair_count': sum(p['status'] == 'POSITIVE_AREA_OVERLAP' for p in pair_results),
        'area_overlap_findings': [p for p in pair_results if p['status'] == 'POSITIVE_AREA_OVERLAP'],
        'cross_feature_pair_diagnostics_performed': bool(pair_results),
        'administrative_boundary_error_determined': False,
        'official_adm1_verified': False,
        'boundary_authorization_verified': False, 'pixel_inside_coverage_checked': False, 'geometric_independence_checked': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Within-file feature-pair planar intersection diagnostics only; area overlap is not an administrative boundary error determination. No repair, cross-file pairs, geodesic area, official status, authority, pixel coverage, independence or recovery approval.'}
