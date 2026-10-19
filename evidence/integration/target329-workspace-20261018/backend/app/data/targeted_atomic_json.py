"""Opt-in atomic replacement of existing local JSON; no coordinator or ledger API."""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from ..ml import manifest_resource_profile as profile
from ..ml.split_json_io import _depth, _tree, _pairs, _constant, _local

ROLE_LIMITS = MappingProxyType({'config': 2097152, 'ledger': 8388608, 'source': 134217728})
JSON_ROLES = MappingProxyType({'config': 'local_config', 'ledger': 'status_report', 'source': 'source'})
EXPECTED_MARKER = MappingProxyType({'name': 'bounded128m-3000-v1',
    'sha256': 'db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4'})


class AtomicJSONWriteError(ValueError):
    """Fixed code; committed/temporary_preserved distinguish apply from verification."""


def _need(value, code):
    if not value:
        raise AtomicJSONWriteError(code)


def _identity(path, *, file=False):
    info = path.lstat()
    _need(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400,
          'ATOMIC_JSON_PATH_INVALID')
    if file:
        _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'ATOMIC_JSON_PATH_INVALID')
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    _need(stat.S_ISDIR(info.st_mode), 'ATOMIC_JSON_PARENT_INVALID')
    return (info.st_dev, info.st_ino)


def _parents(root, target):
    _need(root.is_absolute() and target.is_absolute() and root.resolve() == root and
          target.resolve() == target and target.is_relative_to(root) and target.parent != target,
          'ATOMIC_JSON_PATH_INVALID')
    chain = list(reversed(target.parent.parents)) + [target.parent]
    return [(p, _identity(p)) for p in chain]


def _check_parents(parents):
    _need(all(_identity(p) == identity for p, identity in parents), 'ATOMIC_JSON_PARENT_CHANGED')


@profile.resource_boundary
def _validate_payload(payload, role):
    _need(type(payload) is bytes, 'ATOMIC_JSON_BYTES_REQUIRED')
    _need(len(payload) <= ROLE_LIMITS[role], 'ATOMIC_JSON_PAYLOAD_LIMIT')
    text = payload.decode('utf-8')
    _need(not text.startswith('\ufeff') and '\x00' not in text, 'ATOMIC_JSON_ENCODING_INVALID')
    _depth(text, 32)
    document = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    _tree(document, 32, ROLE_LIMITS[role])
    _need(type(document) is dict, 'ATOMIC_JSON_OBJECT_REQUIRED')
    if role == 'source':
        _need(type(document.get('scenes')) is list, 'ATOMIC_JSON_SOURCE_INVALID')
        profile.structure(document, 'source')


def _write_once(stream, block):
    return stream.write(block)


def _sync(stream):
    stream.flush()
    os.fsync(stream.fileno())


def _measure(stream, before, amount):
    after = os.fstat(stream.fileno())
    if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
        raise OSError('unknown')
    delta = after.st_size - before.st_size
    if not stat.S_ISREG(after.st_mode) or not 0 <= delta <= amount:
        raise OSError('unknown')
    return delta


def _block(stream, data, state):
    profile.require_io_room(len(data))
    before = os.fstat(stream.fileno())
    _need(stat.S_ISREG(before.st_mode) and before.st_size == state['written'] and
          stream.tell() == before.st_size, 'ATOMIC_JSON_APPEND_STATE_INVALID')
    try:
        result = _write_once(stream, data)
    except BaseException:
        try:
            actual = _measure(stream, before, len(data))
        except Exception:
            state['measurement_known'] = False
            profile.charge(len(data), 'write')
            raise AtomicJSONWriteError('ATOMIC_JSON_WRITE_MEASUREMENT_UNKNOWN') from None
        profile.charge(actual, 'write')
        state['written'] += actual
        raise
    try:
        actual = _measure(stream, before, len(data))
    except Exception:
        state['measurement_known'] = False
        profile.charge(len(data), 'write')
        raise AtomicJSONWriteError('ATOMIC_JSON_WRITE_MEASUREMENT_UNKNOWN') from None
    if type(result) is not int or result != actual:
        state['measurement_known'] = False
        profile.charge(len(data), 'write')
        raise AtomicJSONWriteError('ATOMIC_JSON_WRITE_MEASUREMENT_UNKNOWN')
    profile.charge(actual, 'write')
    state['written'] += actual
    _need(actual == len(data), 'ATOMIC_JSON_INCOMPLETE_WRITE')


def _cleanup(temp, owner, parents, payload, state, role):
    """Delete only our unchanged, known prefix; lack of budget preserves temp."""
    try:
        _check_parents(parents)
        stamp = _identity(temp, file=True)
        if not state['measurement_known'] or stamp[:2] != owner or stamp[2] != state['written']:
            return False
        digest = profile.bounded_json_digest(temp, JSON_ROLES[role], maximum_bytes=ROLE_LIMITS[role])
        if digest != hashlib.sha256(payload[:state['written']]).hexdigest() or _identity(temp, file=True) != stamp:
            return False
        temp.unlink()
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class AtomicJSONReplacement:
    sha256: str
    bytes_written: int
    json_io_bytes: int
    maximum_json_io_bytes: int
    committed: bool = True
    coordinator_connected: bool = False


def replace_json(root, target, payload, *, role, expected_sha256, manifest_profile):
    """Replace an existing file only. Immutable bytes preserve validation/digest identity.

    Cooperative writers share one deterministic exclusive temp. This is not an OS
    compare-and-swap against arbitrary external writers in the final check gap.
    """
    _need(type(role) is str and role in ROLE_LIMITS, 'ATOMIC_JSON_ROLE_INVALID')
    _need(type(expected_sha256) is str and re.fullmatch('[a-f0-9]{64}', expected_sha256) is not None,
          'ATOMIC_JSON_EXPECTED_PIN_REQUIRED')
    _need(type(manifest_profile) is dict and set(manifest_profile) == {'name', 'sha256'} and
          all(type(manifest_profile[k]) is str and manifest_profile[k] == EXPECTED_MARKER[k] for k in EXPECTED_MARKER),
          'ATOMIC_JSON_PROFILE_INVALID')
    _need(dict(profile.MARKER) == dict(EXPECTED_MARKER), 'ATOMIC_JSON_PROFILE_INVALID')
    root, target = _local(root), _local(target)
    temp = target.with_name('.' + target.name + '.target329.tmp')
    committed = False
    commit_attempted = False
    owner = None
    state = {'written': 0, 'measurement_known': True}
    parents = []
    with profile.scope(EXPECTED_MARKER['name']) as budget, profile.io_transaction():
        _validate_payload(payload, role)  # Oversize/invalid JSON before any file open.
        parents = _parents(root, target)
        old = _identity(target, file=True)
        _need(profile.bounded_json_digest(target, JSON_ROLES[role], maximum_bytes=ROLE_LIMITS[role]) == expected_sha256,
              'ATOMIC_JSON_PIN_MISMATCH')
        _need(_identity(target, file=True) == old, 'ATOMIC_JSON_INPUT_CHANGED')
        try:
            with temp.open('xb', buffering=0) as stream:
                own = os.fstat(stream.fileno()); owner = (own.st_dev, own.st_ino)
                for start in range(0, len(payload), 65536):
                    _block(stream, payload[start:start+65536], state)
                _sync(stream)
            _check_parents(parents)
            temp_stamp = _identity(temp, file=True)
            new_sha = hashlib.sha256(payload).hexdigest()
            _need(temp_stamp[:2] == owner and temp_stamp[2] == len(payload), 'ATOMIC_JSON_TEMP_CHANGED')
            _need(profile.bounded_json_digest(temp, JSON_ROLES[role], maximum_bytes=ROLE_LIMITS[role]) == new_sha,
                  'ATOMIC_JSON_TEMP_CHANGED')
            _need(_identity(target, file=True) == old and
                  profile.bounded_json_digest(target, JSON_ROLES[role], maximum_bytes=ROLE_LIMITS[role]) == expected_sha256 and
                  _identity(target, file=True) == old, 'ATOMIC_JSON_INPUT_CHANGED')
            _check_parents(parents)
            _need(_identity(temp, file=True) == temp_stamp, 'ATOMIC_JSON_TEMP_CHANGED')
            profile.require_io_room(len(payload))  # Same locked budget reserves post-read room.
            commit_attempted = True
            os.replace(temp, target)
            committed = True
            _need(profile.bounded_json_digest(target, JSON_ROLES[role], maximum_bytes=ROLE_LIMITS[role]) == new_sha,
                  'ATOMIC_JSON_POSTCOMMIT_CHANGED')
            return AtomicJSONReplacement(new_sha, state['written'], budget.bytes, budget.maximum)
        except BaseException as exc:
            cleaned = bool(owner is not None and not committed and _cleanup(temp, owner, parents, payload, state, role))
            # Error remains the same class (including cancellation/resource errors).
            exc.atomic_json_committed = committed
            exc.atomic_json_commit_outcome = 'APPLIED' if committed else ('UNKNOWN' if commit_attempted else 'NOT_ATTEMPTED')
            exc.atomic_json_temporary_preserved = owner is not None and not committed and not cleaned
            exc.atomic_json_measurement_known = state['measurement_known']
            raise


def _detach(value, cap):
    """Only exact JSON builtins; never call caller-defined copy/iterator hooks."""
    nodes = [0]
    active = set()
    def visit(item, depth):
        nodes[0] += 1
        _need(nodes[0] <= 4000000, 'ATOMIC_JSON_NODE_LIMIT')
        kind = type(item)
        if kind in (dict, list):
            _need(depth <= 32 and id(item) not in active, 'ATOMIC_JSON_TREE_INVALID')
            _need(len(item) <= 4000000 - nodes[0], 'ATOMIC_JSON_NODE_LIMIT')
            active.add(id(item))
            try:
                if kind is dict:
                    snapshot = tuple(item.items())
                    _need(all(type(k) is str for k, _ in snapshot), 'ATOMIC_JSON_KEY_INVALID')
                    result = {visit(k, depth + 1): visit(v, depth + 1) for k, v in snapshot}
                    current = tuple(item.items())
                    _need(len(current) == len(snapshot) and all(k == oldk and v is oldv
                          for (k, v), (oldk, oldv) in zip(current, snapshot)), 'ATOMIC_JSON_VALUE_CHANGED')
                else:
                    snapshot = tuple(item)
                    result = [visit(v, depth + 1) for v in snapshot]
                    _need(len(item) == len(snapshot) and all(a is b for a, b in zip(item, snapshot)),
                          'ATOMIC_JSON_VALUE_CHANGED')
            finally:
                active.remove(id(item))
            return result
        if kind is str:
            _need(len(item) <= cap, 'ATOMIC_JSON_PAYLOAD_LIMIT')
            item.encode('utf-8')
        elif kind is float:
            _need(math.isfinite(item), 'ATOMIC_JSON_NUMBER_INVALID')
        else:
            _need(kind in (int, bool, type(None)), 'ATOMIC_JSON_VALUE_INVALID')
        return item
    return visit(value, 1)


def replace_json_value(root, target, value, *, role, expected_sha256, manifest_profile):
    """Detach then serialize in the same scope. Memory encoding is not disk I/O."""
    _need(type(role) is str and role in ROLE_LIMITS, 'ATOMIC_JSON_ROLE_INVALID')
    with profile.scope(EXPECTED_MARKER['name']), profile.io_transaction():
        detached = _detach(value, ROLE_LIMITS[role])
        parts = []
        total = 0
        for part in json.JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True,
                                     separators=(',', ':')).iterencode(detached):
            block = part.encode('utf-8')
            total += len(block)
            _need(total <= ROLE_LIMITS[role], 'ATOMIC_JSON_PAYLOAD_LIMIT')
            parts.append(block)
        return replace_json(root, target, b''.join(parts), role=role,
                            expected_sha256=expected_sha256, manifest_profile=manifest_profile)
