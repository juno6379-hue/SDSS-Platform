"""현재 Dataset 계보 검사 코어의 읽기 전용 내부 RFC HTTP 투영."""
from datetime import datetime, timezone
import re

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from .dataset_lineage import verify_dataset_lineage

_CODES = {
    'INVALID_ROOT_REF', 'INVALID_LIMITS', 'LINEAGE_REF_NOT_PINNED', 'DATASET_VERSION_NOT_FOUND',
    'DATASET_RECORD_CORRUPT', 'DATASET_REGISTRY_UNAVAILABLE', 'LINEAGE_INTEGRITY_FAILED',
    'LINEAGE_REFERENCE_CONFLICT', 'LINEAGE_CYCLE', 'LINEAGE_DEPTH_LIMIT', 'LINEAGE_NODE_LIMIT',
    'LINEAGE_ACL_NOT_IMPLEMENTED',
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _require(condition):
    if not condition:
        raise ValueError('계약 형식이 올바르지 않습니다.')


def _ref(value):
    _require(isinstance(value, dict))
    _require(all(isinstance(value.get(key), str) and value[key] for key in ('id', 'version', 'sha256')))
    _require(re.fullmatch('[a-f0-9]{64}', value['sha256']) is not None)
    return {key: value[key] for key in ('id', 'version', 'sha256')}


def _request(value):
    _require(isinstance(value, dict) and not (set(value) - {'root_ref', 'max_depth', 'max_nodes'}))
    root = _ref(value.get('root_ref'))
    _require(set(value['root_ref']) == {'id', 'version', 'sha256'})
    depth, count = value.get('max_depth', 32), value.get('max_nodes', 256)
    _require(type(depth) is int and 0 <= depth <= 64)
    _require(type(count) is int and 1 <= count <= 1024)
    return root, depth, count


def _bool(value):
    _require(type(value) is bool)
    return value


def _code(value):
    _require(isinstance(value, str) and value in _CODES)
    return value


def _project(core, root, depth, count):
    """코어가 반환해도 HTTP에는 고정 진단 allowlist만 노출한다."""
    _require(isinstance(core, dict) and type(core.get('schema_version')) is int and core['schema_version'] == 1)
    _require(core.get('scope') == 'DATASET_LINEAGE_INTEGRITY_ONLY' and core.get('edge_direction') == 'PARENT_TO_CHILD')
    _require(_ref(core.get('root_ref')) == root and core.get('status') in {'BLOCKED', 'INTEGRITY_VERIFIED'})
    _require(all(isinstance(core.get(key), list) for key in ('nodes', 'edges', 'blockers')))
    for field in ('network_requests', 'source_files_written'):
        _require(type(core.get(field)) is int and core[field] == 0)
    for field in ('authorization_verified', 'execution_authorized', 'scientific_approval'):
        _require(core.get(field) is False)
    nodes = []
    identities = set()
    for node in core['nodes']:
        projected = _ref(node)
        identity = tuple(projected.values())
        _require(identity not in identities)
        identities.add(identity)
        _require(node.get('status') in {'BLOCKED', 'VERIFIED'} and isinstance(node.get('blocker_codes'), list))
        projected.update(status=node['status'], integrity_verified=_bool(node.get('integrity_verified')),
                         expanded=_bool(node.get('expanded')), authorization_verified=False,
                         blocker_codes=[_code(code) for code in node['blocker_codes']])
        _require(node.get('authorization_verified') is False)
        _require((node['status'] == 'VERIFIED') == (node['integrity_verified'] and not node['blocker_codes']))
        if 'quality_status' in node:
            _require(node['quality_status'] in {'RAW', 'STAGED', 'STANDARDIZED', 'VALIDATED', 'REJECTED'})
            projected['quality_status'] = node['quality_status']
        if 'access_class' in node:
            _require(node['access_class'] in {'PUBLIC', 'RESTRICTED', 'CONFIDENTIAL'})
            projected['access_class'] = node['access_class']
        nodes.append(projected)
    edges = []
    for edge in core['edges']:
        source, target = _ref(edge['source']), _ref(edge['target'])
        _require(tuple(source.values()) in identities and tuple(target.values()) in identities)
        edges.append({'source': source, 'target': target})
    blockers = []
    for issue in core['blockers']:
        blockers.append({'code': _code(issue['code']), 'ref': None if issue['ref'] is None else _ref(issue['ref'])})
    integrity = _bool(core.get('lineage_integrity_verified'))
    _require(integrity == (bool(nodes) and not blockers and all(node['integrity_verified'] for node in nodes)))
    _require((core['status'] == 'INTEGRITY_VERIFIED') == integrity)
    limits = core['limits']
    _require(isinstance(limits, dict) and type(limits.get('max_depth')) is int and limits['max_depth'] == depth
             and type(limits.get('max_nodes')) is int and limits['max_nodes'] == count)
    _require(type(limits.get('root_depth')) is int and limits['root_depth'] == 0
             and type(limits.get('hard_max_depth')) is int and limits['hard_max_depth'] == 64
             and type(limits.get('hard_max_nodes')) is int and limits['hard_max_nodes'] == 1024)
    return {'schema_version': 1, 'scope': core['scope'], 'status': core['status'], 'root_ref': root,
        'nodes': nodes, 'edges': edges, 'edge_direction': core['edge_direction'], 'blockers': blockers,
        'limits': {'max_depth': depth, 'max_nodes': count, 'root_depth': 0, 'hard_max_depth': 64,
                   'hard_max_nodes': 1024, 'depth_limit_reached': _bool(limits.get('depth_limit_reached')),
                   'node_limit_reached': _bool(limits.get('node_limit_reached'))},
        'lineage_integrity_verified': integrity, 'current_assets_revalidated': _bool(core.get('current_assets_revalidated')),
        'authorization_verified': False, 'execution_authorized': False, 'scientific_approval': False,
        'network_requests': 0, 'source_files_written': 0}


def _error(code, message, status):
    return JSONResponse({'error': {'code': code, 'message': message, 'trace_id': 'unknown', 'retryable': False}},
                        status_code=status, headers={'Cache-Control': 'no-store'})


def create_dataset_lineage_router(get_store):
    router = APIRouter()

    @router.post('/v1/datasets/lineage/verify')
    async def verify_lineage(request: Request):
        try:
            root, depth, count = _request(await request.json())
        except (ValueError, TypeError, KeyError):
            return _error('INVALID_REQUEST', '고정 자료 참조와 허용 범위의 검사 한도가 필요합니다.', 400)
        started = _now()

        def inspect():
            # 해시 I/O는 event loop 밖에서 처리하며 새 Job·Trace·등록 기록을 만들지 않는다.
            result = verify_dataset_lineage(get_store(), root['id'], root['version'], root['sha256'],
                                             max_depth=depth, max_nodes=count)
            return _project(result, root, depth, count)

        try:
            diagnostic = await run_in_threadpool(inspect)
        except Exception:
            # 경로·URI·자격정보가 섞일 수 있는 내부 예외는 HTTP에 싣지 않는다.
            return _error('RESOURCE_UNAVAILABLE', '자료 계보 검사를 완료할 수 없습니다.', 503)
        return JSONResponse({'extension': 'greenblue.dataset-lineage-verification.rfc1',
            'approval_status': 'INTERNAL_REVIEW', 'present_in_upstream_openapi': False,
            'evaluation_scope': 'CURRENT_LOCAL_ASSET_CHECK_NOT_EXECUTION_AUTHORIZATION',
            'assessment_started_at': started, 'assessment_finished_at': _now(), 'diagnostic': diagnostic,
            'authorization_verified': False, 'execution_authorized': False, 'scientific_approval': False},
            headers={'Cache-Control': 'no-store'})

    return router
