"""Pinned-manifest bounded local streaming SHA256 checks; no decoding or writes."""
from collections import defaultdict
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from .recovery_terminal import _confined, _fingerprint, _finite, _pairs, _constant

CHUNK_BYTES = 1024 * 1024
MAX_LOCAL_BYTES = 3 * 1024 ** 3


def _sha_valid(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _stat_record(value):
    return {'exists': True, 'bytes': value.st_size, 'mtime_ns': value.st_mtime_ns,
            'ctime_ns': value.st_ctime_ns, 'inode': value.st_ino, 'device': value.st_dev}


def _file_stamp(path):
    try:
        value = path.stat()
    except FileNotFoundError:
        return {'exists': False}
    if not stat.S_ISREG(value.st_mode):
        raise ValueError('Content input must be a regular local file')
    return _stat_record(value)


def _stream_sha(path, expected_stamp, budget):
    """Unbuffered bounded reads; budget counts all returned bytes, including probes."""
    if _file_stamp(path) != expected_stamp:
        raise ValueError('File changed before streaming')
    digest, count = hashlib.sha256(), 0
    with path.open('rb', buffering=0) as stream:
        if _stat_record(os.fstat(stream.fileno())) != expected_stamp:
            raise ValueError('Opened descriptor differs from planned file')
        while True:
            remaining = budget['maximum'] - budget['read_bytes']
            expected_remaining = expected_stamp['bytes'] - count
            if expected_remaining < 0:
                raise ValueError('File grew beyond planned size')
            if expected_remaining == 0:
                # At an exact total budget there is no permitted extra-byte probe.
                # fstat verifies EOF size without reading beyond the allowed total.
                if remaining:
                    extra = stream.read(1)
                    budget['read_bytes'] += len(extra)
                    if extra:
                        raise ValueError('File grew beyond planned size')
                break
            if remaining <= 0:
                raise ValueError('Local read budget exhausted')
            block = stream.read(min(CHUNK_BYTES, expected_remaining, remaining))
            budget['read_bytes'] += len(block)
            count += len(block)
            if not block:
                raise ValueError('File ended before planned size')
            digest.update(block)
        if count != expected_stamp['bytes'] or _stat_record(os.fstat(stream.fileno())) != expected_stamp:
            raise ValueError('File changed during streaming')
    if _file_stamp(path) != expected_stamp:
        raise ValueError('File changed after streaming')
    return digest.hexdigest(), count


def inspect_recovery_raster_content(data_root, expected_manifest_sha256, *, max_local_bytes=MAX_LOCAL_BYTES):
    if not _sha_valid(expected_manifest_sha256):
        raise ValueError('Explicit lowercase manifest SHA256 is required')
    if type(max_local_bytes) is not int or not 1 <= max_local_bytes <= MAX_LOCAL_BYTES:
        raise ValueError('Local byte budget must be an integer from 1 through 3 GiB')
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
        raise ValueError('Manifest requires scenes list')
    issues = []
    for index, row in enumerate(aggregate['scenes']):
        if type(row) is not dict:
            issues.append({'code': 'SCENE_INVALID', 'scene_index': index})
            continue
        source = row.get('source_window')
        patch_hashes = row.get('patch_sha256')
        entries = [
            ('source', source.get('path') if type(source) is dict else None, source.get('sha256') if type(source) is dict else None),
            ('patch', row.get('image_path'), patch_hashes.get('image') if type(patch_hashes) is dict else None)]
        for role, path, expected in entries:
            if type(path) is not str or not path:
                issues.append({'code': 'PATH_MISSING_OR_INVALID', 'scene_index': index, 'role': role})
                continue
            target = resolve(path)
            if not _sha_valid(expected):
                issues.append({'code': 'EXPECTED_SHA_MISSING_OR_INVALID', 'scene_index': index, 'role': role, 'path': str(target)})
                continue
            if target not in planned:
                planned[target] = {'expected_sha256': expected, 'roles': set(), 'scene_indexes': set(), 'file_stat': _file_stamp(target)}
            entry = planned[target]
            if entry['expected_sha256'] != expected:
                issues.append({'code': 'EXPECTED_SHA_CANONICAL_PATH_CONFLICT', 'scene_index': index, 'path': str(target)})
            entry['roles'].add(role)
            entry['scene_indexes'].add(index)
    for path, entry in planned.items():
        if not entry['file_stat']['exists']:
            issues.append({'code': 'FILE_MISSING', 'path': str(path)})
    planned_bytes = sum(entry['file_stat'].get('bytes', 0) for entry in planned.values())
    if planned_bytes > max_local_bytes:
        raise ValueError('Planned local byte total exceeds explicit budget; no content streamed')
    budget = {'maximum': max_local_bytes, 'read_bytes': 0}
    files, matched = [], defaultdict(list)
    if not issues:
        for path, entry in planned.items():
            if _confined(root, path) != path:
                raise ValueError('Canonical content path changed')
            observed, count = _stream_sha(path, entry['file_stat'], budget)
            valid = observed == entry['expected_sha256']
            result = {'path': str(path), 'roles': sorted(entry['roles']), 'scene_indexes': sorted(entry['scene_indexes']),
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
            raise ValueError('Local content changed during inspection')
    groups = [{'sha256': digest, 'files': entries} for digest, entries in matched.items() if len(entries) > 1]
    return {'schema_version': 1, 'kind': 'RECOVERY_LOCAL_STREAMING_SHA256_VALIDATION', 'mode': 'READ_ONLY',
        'status': 'BLOCKED', 'content_validation': 'NOT_STARTED_PLAN_REJECTED' if not files and issues else 'ISSUES_FOUND' if issues else 'RECORDED_SHA_MATCH',
        'aggregate': manifest_ref, 'aggregate_scene_count': len(aggregate['scenes']),
        'planned_unique_file_count': len(planned), 'planned_local_bytes': planned_bytes,
        'max_local_bytes': max_local_bytes, 'actual_local_bytes_read': budget['read_bytes'], 'chunk_bytes': CHUNK_BYTES,
        'files': files, 'issues': issues, 'same_digest_different_path_groups': groups,
        'pixel_decoder_used': False, 'label_quality_checked': False, 'geometric_independence_checked': False,
        'exactly_once_applied': 'UNKNOWN', 'ready_for_training': False, 'training_executed': False,
        'scientific_accuracy_validated': False, 'settlement_authorized': False, 'execution_authorized': False,
        'automatic_resume_allowed': False, 'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Pinned recorded image byte hashes only; identical bytes across paths do not establish pixel semantics, independent geometry, split eligibility, scientific accuracy or recovery authorization.'}
