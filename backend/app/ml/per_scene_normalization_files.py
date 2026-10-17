"""Bounded file-snapshot provenance observation, never an execution gate.

No Store, raster header, checkpoint, NumPy, Torch or network access is used.
Three sequential file snapshots are not a multi-file atomic snapshot.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from .per_scene_normalization_contract import inspect_per_scene_normalization_contract

MAX_IMAGE = 64 * 1024**2
MAX_EVIDENCE = 2 * 1024**2
MAX_METADATA = 2 * 1024**2
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 65536
_PATH_TYPE = type(Path())


class _Blocked(Exception):
    def __init__(self, code, field):
        self.code, self.field = code, field


def _need(condition, code, field):
    if not condition:
        raise _Blocked(code, field)


def _text(value, maximum):
    return (type(value) is str and 1 <= len(value) <= maximum and bool(value.strip())
            and all(ord(c) >= 32 and not 127 <= ord(c) <= 159
                    and not 0xD800 <= ord(c) <= 0xDFFF for c in value))


def _links(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def _root(value):
    _need(type(value) in (str, _PATH_TYPE), 'INVALID_INPUT', 'data_root')
    if type(value) is str:
        _need(_text(value, 4096), 'INVALID_INPUT', 'data_root')
    _need(not str(value).startswith(('\\\\', '//')), 'ROOT_UNAVAILABLE', 'data_root')
    path = Path(value)
    _need(path.is_absolute(), 'ROOT_UNAVAILABLE', 'data_root')
    try:
        _need(path.resolve(strict=True) == path and path.is_dir(), 'ROOT_UNAVAILABLE', 'data_root')
        # Explicit root and every lexical ancestor must be free of link aliases.
        for component in (path, *path.parents):
            _need(not _links(component), 'ROOT_UNAVAILABLE', 'data_root')
    except (OSError, ValueError, RuntimeError):
        raise _Blocked('ROOT_UNAVAILABLE', 'data_root') from None
    return path


def _relative(root, value, field):
    _need(_text(value, 512), 'PATH_INVALID', field)
    normalized = value.replace('\\', '/')
    parts = normalized.split('/')
    _need(':' not in normalized and not normalized.startswith('/') and all(
        1 <= len(part) <= 128 and part not in ('.', '..') and not part.endswith((' ', '.')) for part in parts),
        'PATH_INVALID', field)
    path = root.joinpath(*parts)
    _need(path.is_relative_to(root), 'PATH_INVALID', field)
    return path


def _check_path(root, path, field):
    _need(path.resolve() == path and root.resolve() == root, 'PATH_INVALID', field)
    for component in (path, *path.parents):
        _need(not _links(component), 'PATH_INVALID', field)
    attributes = path.lstat()
    _need(stat.S_ISREG(attributes.st_mode), 'FILE_UNAVAILABLE', field)
    return attributes


def _identity(attributes):
    return (attributes.st_dev, attributes.st_ino, attributes.st_size,
            attributes.st_mtime_ns, attributes.st_ctime_ns)


def _snapshot(root, path, maximum, field, copy_bytes=False):
    try:
        before = _check_path(root, path, field)
        _need(before.st_size <= maximum, 'FILE_LIMIT', field)
        checksum, chunks, size = hashlib.sha256(), [], 0
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            _need(_identity(opened) == _identity(before), 'FILE_CHANGED', field)
            while chunk := stream.read(min(1024**2, maximum + 1 - size)):
                size += len(chunk)
                _need(size <= maximum, 'FILE_LIMIT', field)
                checksum.update(chunk)
                if copy_bytes:
                    chunks.append(chunk)
            final_opened = os.fstat(stream.fileno())
        after = _check_path(root, path, field)
        _need(size == before.st_size and _identity(before) == _identity(final_opened) == _identity(after),
              'FILE_CHANGED', field)
        return checksum.hexdigest(), b''.join(chunks) if copy_bytes else None
    except _Blocked:
        raise
    except (OSError, ValueError, RuntimeError):
        raise _Blocked('FILE_UNAVAILABLE', field) from None


def _evidence_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate')
            value[key] = item
        return value
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
        # Iterative traversal bounds depth/nodes without serializing unknown data.
        stack, count = [(value, 0)], 0
        while stack:
            item, depth = stack.pop()
            count += 1
            if depth > MAX_JSON_DEPTH or count > MAX_JSON_NODES:
                raise ValueError('limit')
            if type(item) is dict:
                if count + len(stack) + len(item) > MAX_JSON_NODES:
                    raise ValueError('limit')
                for key, child in item.items():
                    if not all(not 0xD800 <= ord(c) <= 0xDFFF for c in key):
                        raise ValueError('surrogate')
                    stack.append((child, depth + 1))
            elif type(item) is list:
                if count + len(stack) + len(item) > MAX_JSON_NODES:
                    raise ValueError('limit')
                stack.extend((child, depth + 1) for child in item)
            elif type(item) is str:
                if any(0xD800 <= ord(c) <= 0xDFFF for c in item):
                    raise ValueError('surrogate')
            elif type(item) is float:
                if not (-float('inf') < item < float('inf')):
                    raise ValueError('finite')
        if type(value) is not dict:
            raise ValueError('object')
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise _Blocked('EVIDENCE_JSON_INVALID', 'normalization_evidence') from None


def verify_per_scene_normalization_files(data_root, checkpoint_manifest, source_scene, normalization, image_path):
    """Observe three role hashes and declarations, exposing no caller paths.

    A successful artifact flag covers only bytes read, not a checkpoint/header,
    mask, institution, scientific accuracy or Workflow execution permission.
    """
    result = {'schema_version': 1, 'scope': 'PER_SCENE_NORMALIZATION_FILE_SNAPSHOTS_ONLY',
        'status': 'BLOCKED', 'issue': None, 'declaration_observation': None,
        'file_bindings': {key: 'NOT_CHECKED' for key in ('image', 'normalization_evidence', 'source_metadata')},
        'artifact_bytes_verified': False, 'checkpoint_artifact_verified': False,
        'source_authority_verified': False, 'scientific_accuracy_validated': False,
        'execution_authorized': False, 'workflow_supported': False}
    try:
        # Probe validates source/norm before I/O. Empty evidence is deliberately
        # incomplete, never a fabricated default or file-verification result.
        observation = inspect_per_scene_normalization_contract(checkpoint_manifest, source_scene, normalization, {})
        result['declaration_observation'] = observation
        if observation['status'] == 'OUT_OF_SCOPE':
            result['status'] = 'OUT_OF_SCOPE'
            return result
        _need(observation['status'] == 'INCOMPLETE' and observation['issue'] == {
            'code': 'MISSING_FIELD', 'field': 'evidence.status'}, 'DECLARATION_NOT_CONSISTENT', 'declarations')
        root = _root(data_root)
        image = _relative(root, image_path, 'image')
        evidence_path = _relative(root, normalization['evidence_path'], 'normalization_evidence')
        evidence_sha, raw = _snapshot(root, evidence_path, MAX_EVIDENCE, 'normalization_evidence', True)
        matches = evidence_sha == normalization['evidence_sha256']
        result['file_bindings']['normalization_evidence'] = 'MATCH' if matches else 'MISMATCH'
        _need(matches, 'SHA256_MISMATCH', 'normalization_evidence')
        evidence = _evidence_json(raw)
        observation = inspect_per_scene_normalization_contract(checkpoint_manifest, source_scene, normalization, evidence)
        result['declaration_observation'] = observation
        _need(observation['status'] == 'DECLARATIONS_CONSISTENT_UNVERIFIED', 'DECLARATION_NOT_CONSISTENT', 'declarations')
        metadata_path = _relative(root, evidence['source_metadata_path'], 'source_metadata')
        for field, path, maximum, expected in (
            ('image', image, MAX_IMAGE, source_scene['image_sha256']),
            ('source_metadata', metadata_path, MAX_METADATA, evidence['source_metadata_sha256'])):
            digest, _ = _snapshot(root, path, maximum, field)
            matches = digest == expected
            result['file_bindings'][field] = 'MATCH' if matches else 'MISMATCH'
            _need(matches, 'SHA256_MISMATCH', field)
        result.update(status='FILES_MATCHED_UNVERIFIED', artifact_bytes_verified=True)
    except _Blocked as error:
        result['issue'] = {'code': error.code, 'field': error.field}
    except Exception:
        result['issue'] = {'code': 'INVALID_INPUT', 'field': 'inputs'}
    return result
