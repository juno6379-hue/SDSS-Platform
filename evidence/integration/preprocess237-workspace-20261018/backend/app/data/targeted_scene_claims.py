"""Process-local scene check+claim only; no filesystem, network or dispatch."""
import copy
import re
from threading import Lock

from .quality_mask_bundle import _copy_json

SPLITS = {'train', 'val', 'test'}
FALSE_FIELDS = ('execution_supported', 'inventory_complete', 'source_pins_verified',
                'pending_verified', 'footprints_verified', 'image_aliases_verified', 'quality_verified')


def _identifier(value, maximum):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,' + str(maximum-1) + r'}', value) is not None


def _keys(value, expected):
    return type(value) is dict and value.keys() == expected


class SceneClaimRegistry:
    """One coordinator object's in-memory exclusion table; not cross-process.

    A seed is explicitly abbreviated caller-declared history, not a raw manifest
    or verified complete inventory. No release, TTL, refund, persistence or retry.
    """
    def __init__(self, seed, max_claims=256):
        self._lock = Lock()
        self._history = {}
        self._claims = {}
        self._source_sha = None
        self._maximum = 0
        self._initial_issue = 'SEED_INVALID'
        try:
            value = _copy_json(seed, 'seed')
            if not (_keys(value, {'schema_version', 'kind', 'source_manifest_sha256', 'scenes'}) and
                    type(value['schema_version']) is int and value['schema_version'] == 1 and
                    value['kind'] == 'DECLARED_SCENE_SPLIT_HISTORY' and
                    type(value['source_manifest_sha256']) is str and
                    re.fullmatch('[a-f0-9]{64}', value['source_manifest_sha256']) and
                    type(value['scenes']) is list and len(value['scenes']) <= 1024):
                return
            if type(max_claims) is not int or not 1 <= max_claims <= 1024:
                self._initial_issue = 'CLAIM_CAP_INVALID'
                return
            history = {}
            for row in value['scenes']:
                if not (_keys(row, {'scene_id', 'split'}) and _identifier(row['scene_id'], 160) and
                        type(row['split']) is str and row['split'] in SPLITS):
                    return
                history.setdefault(row['scene_id'], set()).add(row['split'])
            self._history = history
            self._source_sha = value['source_manifest_sha256']
            self._maximum = max_claims
            self._initial_issue = None
        except Exception:
            pass

    def _result(self, issue, claim=None, replayed=False):
        # Caller receives fresh nested records; no references to protected state.
        return {'schema_version': 1, 'scope': 'PROCESS_LOCAL_SCENE_CLAIMS_ONLY',
                'status': 'BLOCKED' if claim is None else 'LOCAL_SCENE_CLAIMED_EXECUTION_BLOCKED',
                'issue': issue, 'claim': copy.deepcopy(claim), 'replayed': replayed,
                'claim_count': len(self._claims), 'maximum_claims': self._maximum,
                'source_manifest_sha256_declaration': self._source_sha,
                **{key: False for key in FALSE_FIELDS}}

    def claim(self, request):
        """Atomically check declared history and active ownership, then claim.

        Request exact4: schema_version1, scene_id, split, owner_id. Only an exact
        same-owner/same-scene/same-split repetition is idempotent.
        """
        try:
            value = _copy_json(request, 'request')
            valid = (_keys(value, {'schema_version', 'scene_id', 'split', 'owner_id'}) and
                     type(value['schema_version']) is int and value['schema_version'] == 1 and
                     _identifier(value['scene_id'], 160) and _identifier(value['owner_id'], 80) and
                     type(value['split']) is str and value['split'] in SPLITS)
        except Exception:
            valid = False
        with self._lock:
            if self._initial_issue:
                return self._result(self._initial_issue)
            if not valid:
                return self._result('CLAIM_REQUEST_INVALID')
            scene, split, owner = value['scene_id'], value['split'], value['owner_id']
            history = self._history.get(scene, set())
            if len(history) > 1:
                return self._result('SEEDED_SCENE_QUARANTINED')
            if history and split not in history:
                return self._result('DECLARED_SPLIT_CONFLICT')
            existing = self._claims.get(scene)
            if existing:
                if existing['owner_id'] == owner and existing['split'] == split:
                    return self._result('EXECUTION_GUARDS_NOT_CONNECTED', existing, replayed=True)
                return self._result('SCENE_ALREADY_CLAIMED')
            if len(self._claims) >= self._maximum:
                return self._result('CLAIM_CAP_REACHED')
            record = {'scene_id': scene, 'split': split, 'owner_id': owner}
            self._claims[scene] = record
            return self._result('EXECUTION_GUARDS_NOT_CONNECTED', record)

    def snapshot(self):
        """Fresh read-only diagnostic copy, not an execution clearance token."""
        with self._lock:
            return {'schema_version': 1, 'scope': 'PROCESS_LOCAL_SCENE_CLAIMS_ONLY',
                    'status': 'BLOCKED' if self._initial_issue else 'LOCAL_REGISTRY_INITIALIZED_EXECUTION_BLOCKED',
                    'issue': self._initial_issue or 'EXECUTION_GUARDS_NOT_CONNECTED',
                    'source_manifest_sha256_declaration': self._source_sha,
                    'declared_history_scene_count': len(self._history),
                    'quarantined_scene_count': sum(len(v) > 1 for v in self._history.values()),
                    'maximum_claims': self._maximum, 'claim_count': len(self._claims),
                    'claims': copy.deepcopy(list(self._claims.values())),
                    **{key: False for key in FALSE_FIELDS}}
