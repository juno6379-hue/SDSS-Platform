"""현재 로컬 자산을 재검증하는 읽기 전용 계보 진단. 실행·과학·기관 권한 승인은 아니다."""
import copy
import re
import sqlite3

from .dataset_registry import resolve_version, version_key


def verify_dataset_lineage(store, dataset_id, version, sha256, *, max_depth=32, max_nodes=256):
    """부모→자식 DAG를 고정 참조로 검사하며 제한자료의 상위 계보는 확장하지 않는다."""
    response = {
        'schema_version': 1, 'scope': 'DATASET_LINEAGE_INTEGRITY_ONLY', 'status': 'BLOCKED',
        'root_ref': None, 'nodes': [], 'edges': [], 'edge_direction': 'PARENT_TO_CHILD',
        'blockers': [], 'lineage_integrity_verified': False, 'current_assets_revalidated': False,
        'authorization_verified': False, 'execution_authorized': False, 'scientific_approval': False,
        'network_requests': 0, 'source_files_written': 0,
        'limits': {'max_depth': max_depth if type(max_depth) is int else None,
                   'max_nodes': max_nodes if type(max_nodes) is int else None,
                   'root_depth': 0, 'hard_max_depth': 64, 'hard_max_nodes': 1024,
                   'depth_limit_reached': False, 'node_limit_reached': False},
    }
    nodes, adjacency, deepest, edges, issues, identities = {}, {}, {}, set(), set(), {}
    active = set()

    def ref(key):
        return dict(zip(('id', 'version', 'sha256'), key))

    def block(code, key=None):
        issues.add((code, key))
        if key in nodes:
            nodes[key]['blocker_codes'].add(code)

    def clean(value):
        if not isinstance(value, dict):
            return None
        if (not all(isinstance(value.get(field), str) and value[field] for field in ('id', 'version', 'sha256'))
                or re.fullmatch('[a-f0-9]{64}', value['sha256']) is None):
            return None
        return tuple(value[field] for field in ('id', 'version', 'sha256'))

    root_key = clean({'id': dataset_id, 'version': version, 'sha256': sha256})
    if root_key is not None:
        response['root_ref'] = ref(root_key)
    if type(max_depth) is not int or not 0 <= max_depth <= 64 or type(max_nodes) is not int or not 1 <= max_nodes <= 1024:
        block('INVALID_LIMITS')
    elif root_key is None:
        block('INVALID_ROOT_REF')
    else:
        def visit(key, depth):
            try:
                version_key(key[0], key[1])
            except ValueError:
                block('LINEAGE_REF_NOT_PINNED', key)
                return None
            if key in active:
                block('LINEAGE_CYCLE', key)
                return key
            if depth > max_depth:
                response['limits']['depth_limit_reached'] = True
                block('LINEAGE_DEPTH_LIMIT', key)
                return None
            if key not in nodes:
                if len(nodes) >= max_nodes:
                    response['limits']['node_limit_reached'] = True
                    block('LINEAGE_NODE_LIMIT', key)
                    return None
                nodes[key] = dict(ref(key), status='BLOCKED', integrity_verified=False,
                    authorization_verified=False, expanded=False, blocker_codes=set())
                variants = identities.setdefault(key[:2], set())
                variants.add(key)
                if len(variants) > 1:
                    for variant in variants:
                        block('LINEAGE_REFERENCE_CONFLICT', variant)
                response['current_assets_revalidated'] = True
                try:
                    record = resolve_version(store, *key)
                    manifest = record['manifest']
                    if ((manifest['dataset_id'], manifest['version'], manifest['sha256']) != key
                            or manifest['quality_status'] not in {'RAW', 'STAGED', 'STANDARDIZED', 'VALIDATED', 'REJECTED'}
                            or manifest['access_class'] not in {'PUBLIC', 'RESTRICTED', 'CONFIDENTIAL'}):
                        raise ValueError('등록 계보의 식별자 또는 상태가 올바르지 않습니다')
                    nodes[key].update(integrity_verified=True, quality_status=manifest['quality_status'],
                                      access_class=manifest['access_class'])
                    if manifest['access_class'] != 'PUBLIC':
                        # 비공개 manifest의 조상 ID·URI를 반환하거나 조회하지 않는다.
                        block('LINEAGE_ACL_NOT_IMPLEMENTED', key)
                        return key
                    if not isinstance(manifest['lineage'], list):
                        raise ValueError('계보가 목록이 아닙니다')
                    parents = set()
                    for parent in manifest['lineage']:
                        parent_key = clean(parent)
                        if parent_key is None:
                            block('LINEAGE_INTEGRITY_FAILED', key)
                        else:
                            parents.add(parent_key)
                    adjacency[key] = sorted(parents)
                except KeyError as error:
                    expected = version_key(key[0], key[1])
                    block('DATASET_VERSION_NOT_FOUND' if error.args == (expected,) else 'DATASET_RECORD_CORRUPT', key)
                    return key
                except sqlite3.Error:
                    block('DATASET_REGISTRY_UNAVAILABLE', key)
                    return key
                except (OSError, ValueError, TypeError):
                    block('LINEAGE_INTEGRITY_FAILED', key)
                    return key
            if key not in adjacency:
                return key
            if depth <= deepest.get(key, -1):
                return key
            # 자산 재해시는 중복하지 않고 더 깊은 경로의 계보 한도만 다시 검사한다.
            deepest[key] = depth
            active.add(key)
            try:
                for parent in adjacency[key]:
                    parent_key = visit(parent, depth + 1)
                    if parent_key is not None:
                        edges.add((parent_key, key))
                nodes[key]['expanded'] = True
            finally:
                active.remove(key)
            return key

        visit(root_key, 0)
    response['nodes'] = [dict(nodes[key], blocker_codes=sorted(nodes[key]['blocker_codes']),
        status='VERIFIED' if nodes[key]['integrity_verified'] and not nodes[key]['blocker_codes'] else 'BLOCKED')
        for key in sorted(nodes)]
    response['edges'] = [{'source': ref(parent), 'target': ref(child)} for parent, child in sorted(edges)]
    response['blockers'] = [{'code': code, 'ref': ref(key) if key is not None else None}
        for code, key in sorted(issues, key=lambda item: (item[0], item[1] or ('', '', '')))]
    response['lineage_integrity_verified'] = not response['blockers'] and bool(nodes) and all(node['integrity_verified'] for node in nodes.values())
    if response['lineage_integrity_verified']:
        response['status'] = 'INTEGRITY_VERIFIED'
    # 반환 객체를 바꾸어도 검사 중 사용한 참조나 카탈로그 원본에는 영향을 주지 않는다.
    return copy.deepcopy(response)
