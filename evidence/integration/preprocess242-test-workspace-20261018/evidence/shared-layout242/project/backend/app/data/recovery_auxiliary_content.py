"""Pinned available auxiliary byte hashes with explicit missing-reference coverage."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from .recovery_terminal import _confined, _fingerprint, _finite, _pairs, _constant
from .recovery_raster_content import _sha_valid, _file_stamp, _stream_sha, CHUNK_BYTES

MAX_AUXILIARY_BYTES = 64 * 1024 ** 2
ROLES = ('patch_label', 'patch_quality', 'source_quality', 'boundary')


def inspect_recovery_auxiliary_content(data_root, expected_manifest_sha256, *, max_local_bytes=MAX_AUXILIARY_BYTES):
    if not _sha_valid(expected_manifest_sha256):
        raise ValueError('Explicit lowercase manifest SHA256 is required')
    if type(max_local_bytes) is not int or not 1 <= max_local_bytes <= MAX_AUXILIARY_BYTES:
        raise ValueError('Auxiliary byte budget must be an integer from 1 through 64 MiB')
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
        raise ValueError('Manifest SHA256 mismatch or missing pinned manifest')
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError('Manifest changed while reading')
    aggregate = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    _finite(aggregate)
    if type(aggregate) is not dict or type(aggregate.get('scenes')) is not list or not aggregate['scenes']:
        raise ValueError('Manifest requires nonempty scenes list')
    issues, unknown = [], []
    coverage = {role: {'recorded_reference_rows': 0, 'unknown_reference_rows': 0, 'unique_planned_files': 0} for role in ROLES}

    def pair(role, index, path_container, path_key, hash_container, hash_key):
        path_present, hash_present = path_key in path_container, hash_key in hash_container
        if not path_present and not hash_present:
            unknown.append({'scene_index': index, 'role': role, 'status': 'UNKNOWN_REFERENCE_ABSENT'})
            coverage[role]['unknown_reference_rows'] += 1
            return
        if not path_present or not hash_present:
            issues.append({'code': 'PARTIAL_REFERENCE', 'scene_index': index, 'role': role})
            return
        path, expected = path_container[path_key], hash_container[hash_key]
        if type(path) is not str or not path:
            issues.append({'code': 'EXPLICIT_PATH_INVALID', 'scene_index': index, 'role': role})
            return
        target = resolve(path)
        if not _sha_valid(expected):
            issues.append({'code': 'EXPLICIT_SHA_INVALID', 'scene_index': index, 'role': role, 'path': str(target)})
            return
        coverage[role]['recorded_reference_rows'] += 1
        if target not in planned:
            planned[target] = {'expected_sha256': expected, 'roles': set(), 'references': [], 'file_stat': _file_stamp(target)}
        entry = planned[target]
        if entry['expected_sha256'] != expected:
            issues.append({'code': 'EXPECTED_SHA_CANONICAL_PATH_CONFLICT', 'scene_index': index, 'role': role, 'path': str(target)})
        entry['roles'].add(role)
        entry['references'].append({'scene_index': index, 'role': role})

    for index, row in enumerate(aggregate['scenes']):
        if type(row) is not dict:
            issues.append({'code': 'SCENE_INVALID', 'scene_index': index})
            continue
        hashes = row.get('patch_sha256', {})
        source = row.get('source_window', {})
        if type(hashes) is not dict:
            issues.append({'code': 'PATCH_SHA_CONTAINER_INVALID', 'scene_index': index})
            hashes = {}
        if type(source) is not dict:
            issues.append({'code': 'SOURCE_WINDOW_CONTAINER_INVALID', 'scene_index': index})
            source = {}
        pair('patch_label', index, row, 'label_path', hashes, 'label')
        pair('patch_quality', index, row, 'quality_mask_path', hashes, 'quality')
        pair('source_quality', index, source, 'quality_mask_path', source, 'quality_mask_sha256')
        pair('boundary', index, source, 'boundary_path', source, 'boundary_sha256')
    for path, entry in planned.items():
        if not entry['file_stat']['exists']:
            issues.append({'code': 'FILE_MISSING', 'path': str(path)})
        for role in entry['roles']:
            coverage[role]['unique_planned_files'] += 1
    planned_bytes = sum(entry['file_stat'].get('bytes', 0) for entry in planned.values())
    if planned_bytes > max_local_bytes:
        raise ValueError('Planned auxiliary bytes exceed explicit budget; no content streamed')
    plan_valid = not issues
    budget = {'maximum': max_local_bytes, 'read_bytes': 0}
    files, matched = [], defaultdict(list)
    if plan_valid:
        for path, entry in planned.items():
            if _confined(root, path) != path:
                raise ValueError('Canonical input target changed')
            observed, count = _stream_sha(path, entry['file_stat'], budget)
            valid = observed == entry['expected_sha256']
            result = {'path': str(path), 'roles': sorted(entry['roles']), 'references': entry['references'],
                      'expected_sha256': entry['expected_sha256'], 'observed_sha256': observed,
                      'bytes_read': count, 'status': 'MATCH' if valid else 'MISMATCH', 'file_stat': entry['file_stat']}
            files.append(result)
            if valid:
                matched[observed].append({'path': str(path), 'roles': sorted(entry['roles'])})
            else:
                issues.append({'code': 'CONTENT_SHA_MISMATCH', 'path': str(path)})
    for logical, target in targets.items():
        if _confined(root, logical) != target:
            raise ValueError('Logical input target changed during inspection')
    if _fingerprint(manifest) != manifest_ref:
        raise ValueError('Pinned manifest changed during inspection')
    for path, entry in planned.items():
        if _file_stamp(path) != entry['file_stat']:
            raise ValueError('Auxiliary content changed during inspection')
    validation = 'NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'ISSUES_FOUND' if issues else 'NO_RECORDED_REFERENCES' if not planned else 'RECORDED_AVAILABLE_SHA_MATCH_PARTIAL' if unknown else 'RECORDED_SHA_MATCH'
    return {'schema_version': 1, 'kind': 'RECOVERY_AUXILIARY_CONTENT_VALIDATION', 'mode': 'READ_ONLY',
        'status': 'BLOCKED', 'content_validation': validation,
        'coverage_status': 'PLAN_INVALID' if not plan_valid else 'INCOMPLETE_REFERENCES' if unknown else 'COMPLETE_REFERENCES',
        'aggregate': manifest_ref, 'aggregate_scene_count': len(aggregate['scenes']), 'role_coverage': coverage,
        'unknown_references': unknown, 'issues': issues, 'planned_unique_file_count': len(planned),
        'planned_local_bytes': planned_bytes, 'actual_local_bytes_read': budget['read_bytes'],
        'max_local_bytes': max_local_bytes, 'chunk_bytes': CHUNK_BYTES, 'files': files,
        'same_digest_different_path_groups': [{'sha256': digest, 'files': entries} for digest, entries in matched.items() if len(entries) > 1],
        'pixel_decoder_used': False, 'label_semantics_validated': False, 'quality_suitability_validated': False,
        'boundary_authorization_verified': False, 'geometric_independence_checked': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Only explicitly recorded auxiliary byte hashes; absent pairs remain UNKNOWN without fallback. Matching bytes do not validate label meaning, quality fitness, boundary authority, geometry or recovery approval.'}
