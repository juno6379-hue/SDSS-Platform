"""Read-only crop/year/province metadata companion. Does not inspect raster bytes."""
from collections import defaultdict
import hashlib
import json
import re
from pathlib import Path
from .recovery_terminal import _confined, _fingerprint, _finite, _pairs, _constant


def _year(value):
    valid_type = type(value) is int or type(value) is str and re.fullmatch(r'[0-9]{4}', value) is not None
    return valid_type and 2015 <= int(value) <= 2026


def inspect_recovery_crop(data_root):
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')):
        raise ValueError('Data root must be local')
    root = requested.resolve()
    references, targets, cache = {}, {}, {}

    def resolve(path):
        logical = Path(path)
        target = _confined(root, logical)
        if logical in targets and targets[logical] != target:
            raise ValueError('Logical input target changed')
        targets[logical] = target
        return target

    def read(path):
        target = resolve(path)
        reference = _fingerprint(target)
        if target in references and references[target] != reference:
            raise ValueError('Input changed between reads')
        references[target] = reference
        if target in cache:
            return cache[target]
        if not reference['exists']:
            result = (None, 'MISSING')
        else:
            raw = target.read_bytes()
            if hashlib.sha256(raw).hexdigest() != reference['sha256']:
                raise ValueError('Input changed during read')
            try:
                doc = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
                _finite(doc)
                result = (doc, 'PRESENT') if type(doc) is dict else (None, 'INVALID')
            except (ValueError, UnicodeError):
                result = (None, 'INVALID')
        cache[target] = result
        return result

    aggregate, status = read(root / 'first-group-training-esri-v1/annual-window-report.json')
    if status != 'PRESENT' or type(aggregate.get('source_manifests')) is not list or type(aggregate.get('scenes')) is not list:
        raise ValueError('Aggregate requires valid source_manifests and scenes lists')
    issues, reports = [], []
    source_index = defaultdict(dict)

    def issue(code, **context):
        issues.append({'code': code, **context})

    for reference_index, path in enumerate(aggregate['source_manifests']):
        if type(path) is not str or not path:
            issue('SOURCE_REFERENCE_INVALID', reference_index=reference_index)
            continue
        canonical = resolve(path)
        report, report_status = read(path)
        reports.append({'path': str(canonical), 'status': report_status})
        if report_status != 'PRESENT' or type(report.get('scenes')) is not list:
            issue('SOURCE_REPORT_MISSING_OR_INVALID', reference_index=reference_index)
            continue
        for row_index, row in enumerate(report['scenes']):
            if type(row) is not dict:
                issue('SOURCE_ROW_INVALID', reference_index=reference_index, source_row_index=row_index)
                continue
            if row.get('status') != 'rgb_window_downloaded':
                continue
            image, scene_id = row.get('image_path'), row.get('scene_id')
            if type(image) is not str or not image or type(scene_id) is not str or not scene_id:
                issue('SOURCE_ROW_IDENTITY_MISSING', reference_index=reference_index, source_row_index=row_index)
                continue
            source_index[(resolve(image), scene_id)][(str(canonical), row_index)] = row
    results, crops = [], defaultdict(list)
    for index, row in enumerate(aggregate['scenes']):
        if type(row) is not dict:
            issue('AGGREGATE_SCENE_INVALID', scene_index=index)
            results.append({'scene_index': index, 'source_link': 'INVALID', 'crop_status': 'INVALID'})
            continue
        crop = row.get('window_in_source')
        valid_crop = type(crop) is list and len(crop) == 4 and all(type(v) is int for v in crop)
        valid_crop = valid_crop and crop[0] >= 0 and crop[1] >= 0 and crop[2:] == [256, 256] and crop[0] % 256 == 0 and crop[1] % 256 == 0
        if not valid_crop:
            issue('CROP_COORDINATES_INVALID', scene_index=index)
        source = row.get('source_window')
        path = source.get('path') if type(source) is dict else None
        scene_id = row.get('scene_id')
        result = {'scene_index': index, 'crop_status': 'VALID_METADATA' if valid_crop else 'INVALID',
                  'year_binding': 'UNKNOWN', 'province_binding': 'UNKNOWN'}
        results.append(result)
        if type(path) is not str or not path or type(scene_id) is not str or not scene_id:
            issue('SCENE_SOURCE_IDENTITY_MISSING', scene_index=index)
            result['source_link'] = 'UNKNOWN_IDENTITY_MISSING'
            continue
        image = resolve(path)
        if valid_crop:
            crops[(image, scene_id, tuple(crop))].append(index)
        matches = source_index.get((image, scene_id), {})
        if len(matches) != 1:
            result['source_link'] = 'MISSING_MATCH' if not matches else 'AMBIGUOUS_MATCH'
            issue('SCENE_SOURCE_' + result['source_link'], scene_index=index)
            continue
        result['source_link'] = 'UNIQUE_METADATA_MATCH'
        (report_path, source_row_index), original = next(iter(matches.items()))
        result['source_reference'] = {'report_path': report_path, 'row_index': source_row_index}
        for field, validator in [('year', _year), ('province', lambda v: type(v) is str and bool(v.strip()))]:
            value, original_value = row.get(field), original.get(field)
            if value is None or original_value is None:
                issue(field.upper() + '_BINDING_UNKNOWN_MISSING', scene_index=index)
                continue
            if not validator(value) or not validator(original_value):
                result[field + '_binding'] = 'INVALID'
                issue(field.upper() + '_FIELD_INVALID', scene_index=index)
            elif type(value) is not type(original_value) or value != original_value:
                result[field + '_binding'] = 'MISMATCH'
                issue(field.upper() + '_BINDING_MISMATCH', scene_index=index)
            else:
                result[field + '_binding'] = 'EXACT_TYPED_MATCH'
    duplicates = [{'source_image_path': str(path), 'scene_id': scene_id, 'window_in_source': list(crop), 'scene_indexes': indexes}
                  for (path, scene_id, crop), indexes in crops.items() if len(indexes) > 1]
    for group in duplicates:
        issue('DUPLICATE_SOURCE_CROP', **group)
    for logical, target in targets.items():
        if _confined(root, logical) != target:
            raise ValueError('Logical input target changed during inspection')
    for path, reference in references.items():
        if _fingerprint(path) != reference:
            raise ValueError('Input changed during inspection')
    return {'schema_version': 1, 'kind': 'RECOVERY_CROP_METADATA_RECONCILIATION', 'mode': 'READ_ONLY',
        'status': 'BLOCKED', 'metadata_consistency': 'ISSUES_FOUND' if issues else 'CONSISTENT_METADATA',
        'source_reference_count': len(aggregate['source_manifests']), 'aggregate_scene_count': len(aggregate['scenes']),
        'source_reports': reports, 'scene_checks': results, 'duplicate_source_crops': duplicates,
        'issues': issues, 'artifacts': list(references.values()), 'crop_coordinate_contract_checked': True,
        'year_province_fields_checked': True, 'raster_bounds_checked': False,
        'different_file_same_sha_checked': False, 'geometric_overlap_checked': False,
        'source_file_hashes_verified': False, 'raster_files_read': 0,
        'exactly_once_applied': 'UNKNOWN', 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'proposed_refund_bytes': 0,
        'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Typed JSON field/crop identity only; province is compared to report, not authenticated batch configuration; no raster bounds, geometry, same-SHA content, exactly-once or scientific approval.'}
