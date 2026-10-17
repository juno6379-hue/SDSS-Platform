"""Header-corner source footprint diagnostics; no pixels, raster SHA or approval."""
from contextlib import contextmanager
import hashlib
import math
from pathlib import Path
from affine import Affine
from .recovery_boundary import LIMITS, MAX_MANIFEST_BYTES, _read_bounded, _decode, _inspect_structure
from .recovery_boundary_topology import _geometry_runtime
from .recovery_boundary_relations import _construct_checked_geometry, _pair_relation
from .recovery_raster_headers import _read_header, SAFE_GDAL_OPTIONS
from .recovery_raster_content import _sha_valid, _file_stamp
from .recovery_terminal import _confined


def _projection_runtime():
    result = {'available': False, 'pyproj_version': 'UNKNOWN', 'proj_version': 'UNKNOWN', 'network_enabled_at_entry': 'UNKNOWN'}
    try:
        import pyproj
        result['available'] = True
        for field, attr in [('pyproj_version', '__version__'), ('proj_version', 'proj_version_str')]:
            value = getattr(pyproj, attr, None)
            if type(value) is str and value.strip(): result[field] = value
        result['network_enabled_at_entry'] = pyproj.network.is_network_enabled()
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    return result


@contextmanager
def _offline_projection():
    import pyproj
    previous = pyproj.network.is_network_enabled()
    if type(previous) is not bool: raise ValueError('Projection network state cannot be verified')
    try:
        pyproj.network.set_network_enabled(False)
        if pyproj.network.is_network_enabled() is not False:
            raise ValueError('Projection network could not be disabled')
        yield pyproj
    finally:
        pyproj.network.set_network_enabled(previous)


def _source_footprint(header, shape_fn, explain_fn):
    try:
        width, height = header['width'], header['height']
        pixel_corners = [(0, 0), (width, 0), (width, height), (0, height)]
        affine = Affine(*header['transform'])
        native = [affine @ corner for corner in pixel_corners]
        if not all(math.isfinite(v) for position in native for v in position):
            return {'status': 'UNKNOWN_NONFINITE_NATIVE_CORNERS'}, None
        with _offline_projection() as pyproj:
            transformer = pyproj.Transformer.from_crs(header['crs_wkt'], 'EPSG:4326', always_xy=True, allow_ballpark=False, only_best=True)
            if transformer.is_network_enabled is not False:
                raise ValueError('Transformer network context is not offline')
            longitude, latitude = transformer.transform([p[0] for p in native], [p[1] for p in native], errcheck=True)
        corners = [[float(x), float(y)] for x, y in zip(longitude, latitude)]
        if len(corners) != 4 or not all(math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90 for x, y in corners):
            return {'status': 'UNKNOWN_INVALID_LON_LAT_CORNERS'}, None
        longitudes = [p[0] for p in corners]
        if max(longitudes) - min(longitudes) > 180 or any(abs(corners[(i+1)%4][0] - corners[i][0]) > 180 for i in range(4)):
            return {'status': 'UNKNOWN_UNSUPPORTED_LONGITUDE_WRAP', 'longitude_latitude_corners': corners}, None
        geometry_document = {'type': 'Polygon', 'coordinates': [corners + [corners[0]]]}
        topology, geometry = _construct_checked_geometry({'geometry': geometry_document}, shape_fn, explain_fn)
        if geometry is None:
            return {'status': 'UNKNOWN_INVALID_DERIVED_GEOMETRY', 'topology': topology}, None
        return {'status': 'CORNER_ONLY_FOOTPRINT_VALID', 'pixel_edge_corners': [list(p) for p in pixel_corners],
            'native_crs_corners': [list(p) for p in native], 'longitude_latitude_corners': corners,
            'geometry': geometry_document, 'topology': topology,
            'always_xy': True, 'transform_errcheck': True, 'projection_network_enabled_during_transform': False}, geometry
    except Exception as exc:
        return {'status': 'UNKNOWN_PROJECTION_OR_ENGINE_ERROR', 'error_type': type(exc).__name__}, None


def inspect_recovery_source_footprints(data_root, expected_manifest_sha256, *, max_source_headers=128, max_relations=256, **requested_limits):
    if type(max_source_headers) is not int or not 1 <= max_source_headers <= 10000:
        raise ValueError('Source-header budget must be an integer from 1 through 10000')
    if type(max_relations) is not int or not 1 <= max_relations <= 10000:
        raise ValueError('Relation budget must be an integer from 1 through 10000')
    if not _sha_valid(expected_manifest_sha256): raise ValueError('Explicit lowercase manifest SHA256 required')
    if set(requested_limits) - set(LIMITS): raise ValueError('Unknown boundary limit option')
    limits = {**LIMITS, **requested_limits}
    if any(type(v) is not int or not 1 <= v <= LIMITS[k] for k, v in limits.items()): raise ValueError('Boundary limits out of range')
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')): raise ValueError('Data root must be local')
    root = requested.resolve()
    targets, expected_hashes, sources, boundaries, relation_refs = {}, {}, {}, {}, {}

    def resolve(value):
        logical = Path(value); target = _confined(root, logical)
        if logical in targets and targets[logical] != target: raise ValueError('Logical input target changed')
        targets[logical] = target
        return target

    manifest = resolve(root / 'first-group-training-esri-v1/annual-window-report.json')
    manifest_stat = _file_stamp(manifest)
    if not manifest_stat['exists']: raise ValueError('Pinned manifest missing')
    raw = _read_bounded(manifest, manifest_stat, MAX_MANIFEST_BYTES, LIMITS['max_json_depth'])
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256: raise ValueError('Pinned manifest SHA mismatch')
    document = _decode(raw)
    if type(document) is not dict or type(document.get('scenes')) is not list or not document['scenes']: raise ValueError('Manifest requires nonempty scenes list')
    issues, unknown = [], []

    def asset(path, sha, kind, index):
        if type(path) is not str or not path or not _sha_valid(sha):
            issues.append({'code': 'DECLARED_ASSET_PATH_OR_SHA_INVALID', 'scene_index': index, 'kind': kind}); return None
        target = resolve(path)
        if target in expected_hashes and expected_hashes[target] != sha:
            issues.append({'code': 'CANONICAL_EXPECTED_SHA_CONFLICT', 'scene_index': index, 'path': str(target)})
        expected_hashes[target] = sha
        destination = sources if kind == 'source' else boundaries
        if target not in destination: destination[target] = {'expected_sha256': sha, 'file_stat': _file_stamp(target), 'scene_indexes': []}
        destination[target]['scene_indexes'].append(index)
        return target

    for index, row in enumerate(document['scenes']):
        source = row.get('source_window') if type(row) is dict else None
        if type(source) is not dict:
            issues.append({'code': 'SOURCE_WINDOW_INVALID', 'scene_index': index}); continue
        image = asset(source.get('path'), source.get('sha256'), 'source', index)
        has_path, has_sha = 'boundary_path' in source, 'boundary_sha256' in source
        if not has_path and not has_sha:
            unknown.append({'scene_index': index, 'source_path': str(image) if image else None, 'status': 'UNKNOWN_BOUNDARY_REFERENCE_ABSENT'}); continue
        if not has_path or not has_sha:
            issues.append({'code': 'PARTIAL_BOUNDARY_REFERENCE', 'scene_index': index}); continue
        boundary = asset(source['boundary_path'], source['boundary_sha256'], 'boundary', index)
        province = row.get('province')
        if type(province) is not str or not province.strip():
            issues.append({'code': 'DECLARED_PROVINCE_INVALID', 'scene_index': index}); continue
        if image is not None and boundary is not None: relation_refs.setdefault((image, boundary, province), []).append(index)
    for assets in (sources, boundaries):
        for path, entry in assets.items():
            if not entry['file_stat']['exists']: issues.append({'code': 'DECLARED_FILE_MISSING', 'path': str(path)})
    if len(sources) > max_source_headers: raise ValueError('Full source-header plan exceeds budget; no headers opened')
    if len(relation_refs) > max_relations: raise ValueError('Full source-boundary relation plan exceeds budget; no relation work performed')
    if len(boundaries) > limits['max_boundary_files']: raise ValueError('Boundary file limit exceeded')
    boundary_bytes = sum(v['file_stat'].get('bytes', 0) for v in boundaries.values())
    if boundary_bytes > limits['max_local_bytes']: raise ValueError('Boundary byte limit exceeded before content read')
    plan_valid = not issues
    geometry_runtime, shape_fn, explain_fn = _geometry_runtime()
    projection_runtime = _projection_runtime()
    boundary_files, boundary_geometries = [], {}
    consumed = feature_total = vertex_total = 0
    if plan_valid:
        for path, entry in boundaries.items():
            if _confined(root, path) != path: raise ValueError('Canonical boundary target changed')
            payload = _read_bounded(path, entry['file_stat'], limits['max_local_bytes'] - consumed, limits['max_json_depth'])
            consumed += len(payload)
            observed = hashlib.sha256(payload).hexdigest()
            result = {'path': str(path), 'expected_sha256': entry['expected_sha256'], 'observed_sha256': observed, 'bytes_read': len(payload)}
            boundary_files.append(result)
            if observed != entry['expected_sha256']:
                result['status'] = 'SHA_MISMATCH'; issues.append({'code': 'BOUNDARY_SHA_MISMATCH', 'path': str(path)}); continue
            boundary_doc = _decode(payload)
            structure = _inspect_structure(boundary_doc, {**limits, 'max_features': limits['max_features']-feature_total, 'max_vertices': limits['max_vertices']-vertex_total})
            feature_total += structure['feature_count']; vertex_total += structure['vertex_count']
            result.update(structure)
            if structure['status'] != 'STRUCTURE_MATCH':
                issues.append({'code': 'BOUNDARY_STRUCTURE_INVALID', 'path': str(path)}); continue
            if not geometry_runtime['available']:
                issues.append({'code': 'BOUNDARY_GEOMETRY_ENGINE_UNAVAILABLE', 'path': str(path)}); continue
            checks, geometries = [], {}
            for i, feature in enumerate(boundary_doc['features']):
                check, geometry = _construct_checked_geometry(feature, shape_fn, explain_fn)
                check.update(feature_index=i, province_id=feature['properties']['province_id']); checks.append(check)
                if geometry is not None: geometries[feature['properties']['province_id']] = geometry
            result['topology_feature_checks'] = checks
            if any(check['status'] != 'VALID_TOPOLOGY' for check in checks):
                issues.append({'code': 'BOUNDARY_TOPOLOGY_NOT_VALID', 'path': str(path)}); continue
            for province, geometry in geometries.items(): boundary_geometries[(path, province)] = geometry
    source_results, footprint_geometries = [], {}
    if plan_valid:
        for path, entry in sources.items():
            if _confined(root, path) != path or _file_stamp(path) != entry['file_stat']: raise ValueError('Source header target changed before open')
            header = _read_header(path)
            if _file_stamp(path) != entry['file_stat']: raise ValueError('Source changed during header read')
            result = {'path': str(path), 'recorded_sha256': entry['expected_sha256'], 'recorded_sha_revalidated': False, 'file_stat': entry['file_stat'], 'scene_indexes': entry['scene_indexes'], 'header': header}
            source_results.append(result)
            if header['status'] != 'VALID_HEADER':
                result['footprint_status'] = 'UNKNOWN_SOURCE_HEADER'; issues.append({'code': 'SOURCE_HEADER_NOT_VALID', 'path': str(path)}); continue
            if not geometry_runtime['available'] or not projection_runtime['available']:
                result['footprint_status'] = 'UNKNOWN_GEOMETRY_OR_PROJECTION_ENGINE_UNAVAILABLE'; issues.append({'code': result['footprint_status'], 'path': str(path)}); continue
            footprint, geometry = _source_footprint(header, shape_fn, explain_fn)
            result['footprint'] = footprint; result['footprint_status'] = footprint['status']
            if geometry is None: issues.append({'code': footprint['status'], 'path': str(path)})
            else: footprint_geometries[path] = geometry
    relations = []
    if plan_valid:
        for (source, boundary, province), indexes in relation_refs.items():
            source_geometry, province_geometry = footprint_geometries.get(source), boundary_geometries.get((boundary, province))
            if source_geometry is None: relation = {'status': 'UNKNOWN_SOURCE_FOOTPRINT'}
            elif province_geometry is None: relation = {'status': 'UNKNOWN_BOUNDARY_PROVINCE_GEOMETRY'}
            else: relation = _pair_relation(source_geometry, province_geometry)
            relation.update(source_path=str(source), boundary_path=str(boundary), province=province, scene_indexes=indexes)
            relations.append(relation)
            if relation['status'].startswith('UNKNOWN'): issues.append({'code': relation['status'], 'source_path': str(source), 'province': province})
    for logical, target in targets.items():
        if _confined(root, logical) != target: raise ValueError('Logical input target changed during inspection')
    if _file_stamp(manifest) != manifest_stat: raise ValueError('Manifest changed during inspection')
    if hashlib.sha256(_read_bounded(manifest, manifest_stat, MAX_MANIFEST_BYTES, LIMITS['max_json_depth'])).hexdigest() != expected_manifest_sha256: raise ValueError('Manifest content changed during inspection')
    for assets in (sources, boundaries):
        for path, entry in assets.items():
            if _file_stamp(path) != entry['file_stat']: raise ValueError('Declared asset changed during inspection')
    projection_after = _projection_runtime()
    projection_runtime['network_enabled_at_exit'] = projection_after['network_enabled_at_entry']
    projection_runtime['network_state_restored'] = projection_runtime['network_enabled_at_entry'] == projection_runtime['network_enabled_at_exit'] if type(projection_runtime['network_enabled_at_entry']) is bool else None
    if plan_valid and source_results and projection_runtime['network_state_restored'] is not True:
        issues.append({'code': 'PROJECTION_NETWORK_RESTORATION_UNVERIFIED'})
    return {'schema_version': 1, 'kind': 'RECOVERY_SOURCE_HEADER_CORNER_FOOTPRINTS', 'mode': 'READ_ONLY', 'status': 'BLOCKED',
        'footprint_validation': 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'ISSUES_FOUND' if issues else 'KNOWN_CORNER_DIAGNOSTICS_PARTIAL' if unknown else 'CORNER_DIAGNOSTICS_COMPLETED',
        'coverage_status': 'PLAN_INVALID' if not plan_valid else 'INCOMPLETE_BOUNDARY_REFERENCES' if unknown else 'COMPLETE_DECLARED_REFERENCES',
        'manifest': {'path': str(manifest), 'sha256': expected_manifest_sha256}, 'aggregate_scene_count': len(document['scenes']),
        'planned_source_header_count': len(sources), 'source_header_attempt_count': len(source_results), 'max_source_headers': max_source_headers,
        'planned_unique_relation_count': len(relation_refs), 'relation_attempt_count': len(relations), 'max_relations': max_relations,
        'boundary_files': boundary_files, 'boundary_bytes_read': consumed, 'limits': limits,
        'source_footprints': source_results, 'relations': relations, 'unknown_boundary_references': unknown, 'issues': issues,
        'geometry_runtime': geometry_runtime, 'projection_runtime': projection_runtime, 'safe_gdal_options': SAFE_GDAL_OPTIONS.copy(),
        'footprint_method': 'FOUR_PIXEL_EDGE_CORNERS_STRAIGHT_SEGMENTS', 'area_units': 'square_degrees_planar_diagnostic',
        'curved_edges_densified': False, 'exact_raster_footprint_verified': False, 'pixel_arrays_read': False,
        'source_content_sha_revalidated': False, 'pixel_inside_ratio_computed': False, 'geodesic_area_computed': False,
        'source_to_source_intersections_checked': False, 'training_split_leakage_resolved': False,
        'original_geometry_reprojected_or_written': False, 'automatic_geometry_repair_performed': False,
        'official_adm1_verified': False, 'boundary_authorization_verified': False, 'geometric_independence_checked': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Four transformed header corners joined by straight lines only; no densified true raster footprint, pixel coverage, exact/geodesic area, image content SHA, source independence, split approval, official boundary or recovery authorization.'}
