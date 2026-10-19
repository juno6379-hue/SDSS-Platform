"""Pure target256 profile declarations; no files, scopes, dispatch or authority."""
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from types import MappingProxyType

NAME = 'bounded128m-3000-v1'
DESCRIPTOR = MappingProxyType(dict(name=NAME, manifest_bytes=134217728, max_rows=3000,
                                 max_depth=32, max_nodes=4000000, max_json_io_bytes=17179869184))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


DIGEST = _digest(dict(DESCRIPTOR))
MARKER = MappingProxyType(dict(name=NAME, sha256=DIGEST))
SUPPORT_DESCRIPTOR = MappingProxyType(dict(name='TARGETED_LOCAL_SUPPORT_3G_V1', max_files=10000,
                                         max_support_bytes=3221225472, max_file_bytes=67108864))
SUPPORT_MARKER = MappingProxyType(dict(name=SUPPORT_DESCRIPTOR['name'], sha256=_digest(dict(SUPPORT_DESCRIPTOR))))
# Declarations only: this module never reads a file or activates these limits.
ROLE_LIMITS = MappingProxyType(dict(source=134217728, candidate=134217728, ledger=8388608,
                                   lineage=8388608, request=2097152, plan=2097152,
                                   proposal=2097152, boundary=2097152, base_config=2097152,
                                   label=67108864, image=67108864, support=67108864))
ROLE_LIMITS_SHA256 = _digest(dict(ROLE_LIMITS))
PLAN_KEYS = frozenset(('schema_version', 'kind', 'proposal_ref', 'current_manifest_ref',
                       'boundary_ref', 'policy', 'targets'))
OUTER_KEYS = frozenset(('schema_version', 'plan', 'ledger_ref', 'maximum_batches',
                        'local_support_profile', 'manifest_profile'))
TARGET_KEYS = frozenset(('target_id', 'proposal_window_index', 'province', 'fixed_split', 'year',
                        'source_label_ref', 'source_lineage_ref', 'source_label_window',
                        'source_label_grid', 'target_bbox_wgs84', 'target_footprint_native', 'declared_bare_pixels'))
SPLITS = MappingProxyType(dict(south_sulawesi='train', gorontalo='train', southeast_sulawesi='train',
                              east_java='train', banten='val', west_java='test'))
POLICY = MappingProxyType(dict(window_size=256, source_taxonomy_code=8, minimum_declared_bare_pixels=256,
                              minimum_valid_fraction=.8, minimum_inside_fraction=.95))


class TargetSourceContractError(ValueError):
    """Fixed codes only; caller paths and exception text are never exposed."""


def _need(ok, code):
    if not ok:
        raise TargetSourceContractError(code)


def _keys(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _copy(value):
    """Detach first, validate/serialize only that tree; not an atomic caller snapshot."""
    nodes = 0

    def clone(item, depth):
        nonlocal nodes
        nodes += 1
        _need(nodes <= 50000 and depth <= 32, 'TARGET_SOURCE_STRUCTURE_LIMIT')
        if type(item) is dict:
            _need(len(item) <= 256, 'TARGET_SOURCE_STRUCTURE_LIMIT')
            out = {}
            for key, val in item.items():
                _need(type(key) is str and len(key) <= 128 and len(out) < 256, 'TARGET_SOURCE_TYPE_INVALID')
                key.encode('utf-8')
                out[key] = clone(val, depth + 1)
            return out
        if type(item) is list:
            _need(len(item) <= 256, 'TARGET_SOURCE_STRUCTURE_LIMIT')
            out = []
            for val in item:
                _need(len(out) < 256, 'TARGET_SOURCE_STRUCTURE_LIMIT')
                out.append(clone(val, depth + 1))
            return out
        if type(item) is str:
            _need(len(item) <= 4096 and '\x00' not in item, 'TARGET_SOURCE_STRUCTURE_LIMIT')
            item.encode('utf-8')
        elif type(item) in (int, float):
            _need(math.isfinite(item) and abs(item) <= 2**63-1, 'TARGET_SOURCE_NUMBER_INVALID')
        else:
            _need(type(item) in (bool, type(None)), 'TARGET_SOURCE_TYPE_INVALID')
        return item

    try:
        detached = clone(value, 0)
        _need(len(_canonical(detached).encode('utf-8')) <= 2097152, 'TARGET_SOURCE_STRUCTURE_LIMIT')
        return detached
    except UnicodeError:
        raise TargetSourceContractError('TARGET_SOURCE_UTF8_INVALID') from None
    except RuntimeError:
        raise TargetSourceContractError('TARGET_SOURCE_INPUT_CHANGED') from None
    except (OverflowError, RecursionError):
        raise TargetSourceContractError('TARGET_SOURCE_STRUCTURE_LIMIT') from None


def _marker(value, expected):
    _keys(value, ('name', 'sha256'), 'TARGET_SOURCE_MARKER_INVALID')
    _need(all(type(value[k]) is str and value[k] == expected[k] for k in expected), 'TARGET_SOURCE_MARKER_INVALID')


def _ref(value, prefix):
    _keys(value, ('path', 'sha256'), 'TARGET_SOURCE_REFERENCE_INVALID')
    path, sha = value['path'], value['sha256']
    _need(type(path) is str and 1 <= len(path) <= 1024 and path.startswith(prefix + '/') and
          all(x not in path for x in ('\\', ':', '//')) and
          all(x not in ('', '.', '..') for x in path.split('/')) and
          type(sha) is str and re.fullmatch('[a-f0-9]{64}', sha) is not None, 'TARGET_SOURCE_REFERENCE_INVALID')


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _plan(plan, version):
    _keys(plan, PLAN_KEYS | ({'manifest_profile'} if version == 2 else set()), 'TARGET_SOURCE_PLAN_INVALID')
    _need(type(plan['schema_version']) is int and plan['schema_version'] == version and
          plan['kind'] == 'TARGETED_BARE_256_COLLECTION_PLAN', 'TARGET_SOURCE_PLAN_INVALID')
    if version == 2:
        _marker(plan['manifest_profile'], MARKER)
    _ref(plan['proposal_ref'], 'evidence/integration')
    _ref(plan['current_manifest_ref'], 'data')
    _ref(plan['boundary_ref'], 'data')
    policy = plan['policy']
    keys = set(POLICY) | {'maximum_new_batches'}
    _need(type(policy) is dict and set(policy) in (keys, keys | {'minimum_candidate_valid_fraction'}), 'TARGET_SOURCE_POLICY_INVALID')
    _need(all(type(policy[k]) is type(v) and policy[k] == v for k, v in POLICY.items()), 'TARGET_SOURCE_POLICY_INVALID')
    maximum = policy['maximum_new_batches']
    _need(type(maximum) is int and 1 <= maximum <= 2, 'TARGET_SOURCE_POLICY_INVALID')
    if 'minimum_candidate_valid_fraction' in policy:
        n = policy['minimum_candidate_valid_fraction']
        _need(_number(n) and .8 <= n <= 1, 'TARGET_SOURCE_POLICY_INVALID')
    targets = plan['targets']
    _need(type(targets) is list and 1 <= len(targets) <= maximum, 'TARGET_SOURCE_TARGET_INVALID')
    seen = set()
    for target in targets:
        _keys(target, TARGET_KEYS, 'TARGET_SOURCE_TARGET_INVALID')
        identifier = target['target_id']
        _need(type(identifier) is str and re.fullmatch('[A-Za-z0-9_-]{1,40}', identifier) is not None and
              identifier not in seen, 'TARGET_SOURCE_TARGET_INVALID')
        seen.add(identifier)
        _need(type(target['year']) is int and 2020 <= target['year'] <= 2025 and
              type(target['proposal_window_index']) is int and target['proposal_window_index'] >= 0 and
              type(target['province']) is str and target['province'] in SPLITS and
              target['fixed_split'] == SPLITS[target['province']], 'TARGET_SOURCE_TARGET_INVALID')
        _ref(target['source_label_ref'], 'data')
        _ref(target['source_lineage_ref'], 'data')
        window = target['source_label_window']
        _need(type(window) is list and len(window) == 4 and all(type(x) is int for x in window) and
              window[0] >= 0 and window[1] >= 0 and window[2:] == [256, 256], 'TARGET_SOURCE_TARGET_INVALID')
        grid = target['source_label_grid']
        _keys(grid, ('crs', 'transform', 'width', 'height'), 'TARGET_SOURCE_TARGET_INVALID')
        _need(type(grid['crs']) is str and bool(grid['crs']) and
              all(type(grid[k]) is int and 1 <= grid[k] <= 8192 for k in ('width', 'height')) and
              type(grid['transform']) is list and len(grid['transform']) == 6 and
              all(_number(x) for x in grid['transform']), 'TARGET_SOURCE_TARGET_INVALID')
        native = target['target_footprint_native']
        _keys(native, ('crs', 'corners'), 'TARGET_SOURCE_TARGET_INVALID')
        _need(type(native['crs']) is str and bool(native['crs']) and type(native['corners']) is list and
              len(native['corners']) == 4 and all(type(p) is list and len(p) == 2 and all(_number(x) for x in p)
              for p in native['corners']), 'TARGET_SOURCE_TARGET_INVALID')
        bbox = target['target_bbox_wgs84']
        _need(type(bbox) is list and len(bbox) == 4 and all(_number(x) for x in bbox) and
              -180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90 and
              type(target['declared_bare_pixels']) is int and 256 <= target['declared_bare_pixels'] <= 65536,
              'TARGET_SOURCE_TARGET_INVALID')


def upgrade_plan_v1(plan, marker):
    """Deep-copy adapter only: preserves refs/targets, explicitly adds the marker."""
    value, selected = _copy(plan), _copy(marker)
    _marker(selected, MARKER)
    _plan(value, 1)
    value['schema_version'] = 2
    value['manifest_profile'] = selected
    _plan(value, 2)
    return value


@dataclass(frozen=True)
class ValidatedTargetSourceContract:
    canonical_json: str
    request_sha256: str
    inventory_envelope_json: str
    status: str = field(default='DECLARED_CONTRACT_VALID_EXECUTION_BLOCKED', init=False)
    execution_supported: bool = field(default=False, init=False)
    source_bytes_verified: bool = field(default=False, init=False)
    source_profile_connected: bool = field(default=False, init=False)
    training_ready: bool = field(default=False, init=False)

    def to_dict(self):
        return json.loads(self.canonical_json)

    def inventory_envelope(self):
        return json.loads(self.inventory_envelope_json)


def validate_request_v3(request):
    """Validate detached declarations, never validate a preconstructed result token."""
    value = _copy(request)
    _keys(value, OUTER_KEYS, 'TARGET_SOURCE_REQUEST_INVALID')
    _need(type(value['schema_version']) is int and value['schema_version'] == 3, 'TARGET_SOURCE_REQUEST_INVALID')
    _marker(value['manifest_profile'], MARKER)
    _marker(value['local_support_profile'], SUPPORT_MARKER)
    _plan(value['plan'], 2)
    _need(value['manifest_profile'] == value['plan']['manifest_profile'], 'TARGET_SOURCE_MARKER_INVALID')
    _ref(value['ledger_ref'], 'data')
    _need(type(value['maximum_batches']) is int and 1 <= value['maximum_batches'] <= 2 and
          value['maximum_batches'] == value['plan']['policy']['maximum_new_batches'], 'TARGET_SOURCE_BATCH_INVALID')
    canonical = _canonical(value)
    # This envelope selects ONLY the unchanged232 3GiB options. It is not a
    # downgraded executable request: plan remains v2 and original digest stays v3.
    envelope = {k: value[k] for k in OUTER_KEYS if k != 'manifest_profile'}
    envelope['schema_version'] = 2
    return ValidatedTargetSourceContract(canonical, hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
                                         _canonical(envelope))


def inventory_envelope_v3(request):
    """Revalidate the raw declaration on every projection; no authority tokens."""
    return validate_request_v3(request).inventory_envelope()
