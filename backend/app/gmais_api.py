"""GMAIS v0.2 내부 검토 계약을 위한 로컬 Agent API 어댑터.

이 모듈은 제안 계약의 호환 구현이며 컨소시엄/BIG 승인이나 과학적 검증을 뜻하지 않는다.
실행 준비가 되지 않은 요청은 결과를 만들지 않고 BLOCKED 작업과 추적 근거만 남긴다.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from jsonschema import Draft202012Validator

from .schema_formats import create_format_checker
from .agent_capability_contract import agent_capability_issue
from .model_reference_contract import model_reference_issue
from .workflow_dependency_order import topological_order


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _agent_manifests() -> list[dict]:
    """실제 실행 코드와 외부 기관 인터페이스를 manifest에서 분리한다."""
    tools = [
        ('climate-downscaling-agent', '기후 다운스케일링', 'climate-downscaling', False),
        ('lcluc-agent', '토지피복·토지이용 변화', 'landcover.change_detection', True),
        ('net-carbon-footprint-agent', '순 탄소발자국', 'net-carbon-footprint', False),
        ('biodiversity-agent', '생물다양성', 'biodiversity', False),
        ('sea-level-subsidence-agent', '해수면·지반침하', 'sea-level-subsidence', False),
        ('flood-drought-agent', '홍수·가뭄', 'flood-drought', False),
    ]
    result = []
    for agent_id, title, capability, implemented in tools:
        result.append({
            'schema_version': '0.2.0',
            'agent_id': agent_id,
            'version': '0.1.0' if implemented else '0.0.0-interface',
            'provider': 'GreenBlue local platform',
            'model_type': 'trainable_ml' if implemented else 'external_service',
            'execution_mode': 'ASYNC_API' if implemented else 'EXTERNAL_API',
            'capabilities': [{
                'capability_id': capability,
                'input_schema': 'contracts/proposed/job-request.schema.json',
                'output_schema': 'contracts/proposed/result-manifest.schema.json',
                'required_dataset_types': ['sentinel-2-l2a', 'annual-landcover-reference'] if implemented else [],
            }],
            'readiness': 'BLOCKED' if implemented else 'NOT_IMPLEMENTED',
            **({'model_approval_status': 'DRAFT'} if implemented else {}),
            'deployment_profile': 'local-development-only' if implemented else 'external-adapter-required',
            'known_limitations': ([
                'GMAIS v0.2는 내부 검토용 제안이며 기관 승인본이 아니다.',
                '동년 공개 참조라벨 대비 실험도 독립 과학 검증과 구분한다.',
                '현재 학습자료 준비도 및 승인 모델 gate를 통과하지 못했다.',
            ] if implemented else [
                '기관별 모델·실행기·데이터·검증 증거가 아직 연결되지 않았다.',
                '계약 호환 인터페이스만 등록했으며 실행 결과를 만들지 않는다.',
            ]),
        })
    return result


@lru_cache(maxsize=1)
def _job_request_validator():
    """vendored v0.2 원문 JSON Schema를 직접 사용하며 스키마를 추측하지 않는다."""
    for parent in Path(__file__).resolve().parents:
        path = parent / 'contracts' / 'upstream' / 'GMAIS-v0.2' / 'schemas' / 'job-request.schema.json'
        if path.is_file():
            schema = json.loads(path.read_text(encoding='utf-8'))
            Draft202012Validator.check_schema(schema)
            return Draft202012Validator(schema, format_checker=create_format_checker())
    raise RuntimeError('GMAIS v0.2 job-request 원문 schema를 찾을 수 없습니다.')


@lru_cache(maxsize=1)
def _workflow_plan_validator():
    """패키지의 실제 Workflow Plan schema를 확장 endpoint 검증에 사용한다."""
    for parent in Path(__file__).resolve().parents:
        path = parent / 'contracts' / 'upstream' / 'GMAIS-v0.2' / 'schemas' / 'workflow-plan.schema.json'
        if path.is_file():
            schema = json.loads(path.read_text(encoding='utf-8'))
            Draft202012Validator.check_schema(schema)
            return Draft202012Validator(schema, format_checker=create_format_checker())
    raise RuntimeError('GMAIS v0.2 workflow-plan 원문 schema를 찾을 수 없습니다.')


def _validate_job(payload: object, path_agent_id: str, idempotency_key: str | None) -> tuple[dict | None, str | None]:
    """의존 라이브러리 설치 없이 실제 v0.2 필수 필드와 핵심 제약을 검사한다."""
    if not idempotency_key or not idempotency_key.strip() or len(idempotency_key) > 200:
        return None, 'Idempotency-Key 헤더가 필요합니다.'
    if not isinstance(payload, dict):
        return None, '요청 본문은 JSON 객체여야 합니다.'
    schema_errors = sorted(_job_request_validator().iter_errors(payload), key=lambda error: list(map(str, error.absolute_path)))
    if schema_errors:
        first = schema_errors[0]
        field = '.'.join(map(str, first.absolute_path)) or 'request'
        return None, f'GMAIS v0.2 JSON Schema 위반 ({field}): {first.message}'
    allowed = {'schema_version', 'agent_id', 'capability_id', 'input_refs', 'aoi', 'time_range', 'model_ref', 'parameters', 'requested_outputs', 'execution_context'}
    required = {'schema_version', 'agent_id', 'capability_id', 'input_refs', 'aoi', 'requested_outputs', 'execution_context'}
    if set(payload) - allowed or required - set(payload):
        return None, '요청 필수 필드 또는 허용 필드가 스키마와 다릅니다.'
    if payload.get('schema_version') != '0.2.0' or payload.get('agent_id') != path_agent_id:
        return None, 'schema_version 또는 경로와 본문의 agent_id가 일치하지 않습니다.'
    if not isinstance(payload.get('capability_id'), str) or not payload['capability_id']:
        return None, 'capability_id가 필요합니다.'
    refs = payload.get('input_refs')
    if not isinstance(refs, list) or not refs:
        return None, 'input_refs는 하나 이상의 고정 버전 참조가 필요합니다.'
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) - {'id', 'version', 'sha256', 'uri', 'role'} or not {'id', 'version', 'sha256'} <= set(ref):
            return None, 'input_refs는 id/version/sha256만으로 식별되어야 합니다.'
        if not all(isinstance(ref.get(key), str) and ref[key] for key in ('id', 'version')) or not re.fullmatch(r'[a-f0-9]{64}', str(ref.get('sha256', ''))):
            return None, 'input_refs의 버전 또는 SHA-256 형식이 올바르지 않습니다.'
    aoi = payload.get('aoi')
    if not isinstance(aoi, dict) or set(aoi) - {'bbox', 'crs', 'geometry_uri'} or not {'bbox', 'crs'} <= set(aoi):
        return None, 'aoi는 bbox와 CRS를 포함해야 합니다.'
    bbox = aoi.get('bbox')
    if (not isinstance(bbox, list) or len(bbox) != 4 or any(not isinstance(v, (int, float)) for v in bbox)
            or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
        return None, 'aoi bbox는 서쪽/남쪽/동쪽/북쪽 순서의 유효한 네 수여야 합니다.'
    if not isinstance(aoi.get('crs'), str) or not re.fullmatch(r'(EPSG:[0-9]+|OGC:CRS84)', aoi['crs']):
        return None, 'aoi CRS는 EPSG 코드 또는 OGC:CRS84여야 합니다.'
    outputs = payload.get('requested_outputs')
    if not isinstance(outputs, list) or not outputs or any(not isinstance(v, str) or not v for v in outputs):
        return None, 'requested_outputs는 하나 이상의 문자열이어야 합니다.'
    context = payload.get('execution_context')
    allowed_context = {'trace_id', 'purpose', 'environment', 'approval_ref', 'workflow_run_id', 'user_id'}
    if (not isinstance(context, dict) or set(context) - allowed_context
            or not {'trace_id', 'purpose', 'environment'} <= set(context)
            or any(not isinstance(context.get(key), str) or not context[key] for key in ('trace_id', 'purpose'))
            or context.get('environment') not in {'development', 'staging', 'production'}):
        return None, 'execution_context의 trace_id/purpose/environment가 유효하지 않습니다.'
    if 'model_ref' in payload:
        ref = payload['model_ref']
        if not isinstance(ref, dict) or set(ref) - {'id', 'version', 'sha256', 'uri', 'role'} or not {'id', 'version', 'sha256'} <= set(ref):
            return None, 'model_ref는 고정 id/version/sha256를 포함해야 합니다.'
        if not re.fullmatch(r'[a-f0-9]{64}', str(ref.get('sha256', ''))):
            return None, 'model_ref SHA-256 형식이 올바르지 않습니다.'
        issue = model_reference_issue(ref)
        if issue == 'MODEL_REFERENCE_INVALID':
            return None, 'model_ref의 id/version/role은 유효한 고정 문자열이어야 합니다.'
        if issue == 'MODEL_VERSION_NOT_PINNED':
            return None, 'model_ref version은 latest/current 별칭이 아닌 고정 버전이어야 합니다.'
    return payload, None


def _error(code: str, message: str, trace_id: str = 'unknown', status: int = 400, details: dict | None = None) -> JSONResponse:
    error = {'code': code, 'message': message, 'trace_id': trace_id, 'retryable': False}
    if details:
        error['details'] = details
    return JSONResponse({'error': error}, status_code=status)


def create_router(get_store: Callable[[], object]) -> APIRouter:
    router = APIRouter()

    @router.get('/healthz')
    def healthz():
        return {'status': 'UP', 'scope': 'local-platform-runtime'}

    @router.get('/readyz')
    def readyz():
        return {'status': 'UP', 'scope': 'runtime-only', 'scientific_readiness': 'not-implied'}

    @router.get('/v1/agents')
    def agents():
        return {'items': _agent_manifests()}

    @router.get('/v1/agents/{agent_id}')
    def agent(agent_id: str):
        selected = next((a for a in _agent_manifests() if a['agent_id'] == agent_id), None)
        if selected is None:
            return _error('AGENT_NOT_IMPLEMENTED', 'Agent가 Registry에 없습니다.', status=404)
        return selected

    @router.get('/v1/agents/{agent_id}/capabilities')
    def capabilities(agent_id: str):
        selected = next((a for a in _agent_manifests() if a['agent_id'] == agent_id), None)
        if selected is None:
            return _error('AGENT_NOT_IMPLEMENTED', 'Agent가 Registry에 없습니다.', status=404)
        return {'items': selected['capabilities']}

    @router.get('/v1/agents/{agent_id}/readiness')
    def readiness(agent_id: str):
        selected = next((a for a in _agent_manifests() if a['agent_id'] == agent_id), None)
        if selected is None:
            return _error('AGENT_NOT_IMPLEMENTED', 'Agent가 Registry에 없습니다.', status=404)
        if selected['readiness'] == 'NOT_IMPLEMENTED':
            axes = {k: {'state': 'NOT_IMPLEMENTED', 'evidence': '외부 기관 Agent 연동 미구현'} for k in ('runtime', 'dataset', 'science', 'deployment', 'contract')}
            blockers = ['기관별 모델·자료·검증·실행 Adapter 미연결']
        else:
            try:
                from .collection_status import collection_status
                dataset_ready = bool(collection_status(get_store().root).get('training_readiness', {}).get('ready_for_training'))
            except Exception:
                dataset_ready = False
            approved = any(m.get('status') == 'Deployed' and m.get('independent_evaluation') for m in get_store().list('models'))
            axes = {
                'runtime': {'state': 'READY', 'evidence': '로컬 FastAPI 프로세스 응답 확인'},
                'dataset': {'state': 'READY' if dataset_ready else 'BLOCKED', 'evidence': '기존 데이터 준비도 gate 결과'},
                'science': {'state': 'READY' if approved else 'BLOCKED', 'evidence': '체크포인트 해시 연결 독립평가 여부'},
                'deployment': {'state': 'APPROVED' if approved else 'BLOCKED', 'evidence': '독립평가·모델승인·배포 레지스트리'},
                'contract': {'state': 'PROPOSED', 'evidence': 'GMAIS v0.2 내부 검토본 구현이며 기관 미승인'},
            }
            blockers = [key for key, value in axes.items() if value['state'] in {'BLOCKED', 'NOT_IMPLEMENTED'}]
        return {'agent_id': agent_id, 'readiness': selected['readiness'], 'model_approval_status': selected.get('model_approval_status'), 'axes': axes, 'blockers': blockers}

    @router.post('/v1/agents/{agent_id}/jobs')
    async def submit_job(agent_id: str, request: Request, idempotency_key: str | None = Header(default=None, alias='Idempotency-Key')):
        try:
            payload = await request.json()
        except Exception:
            return _error('INVALID_REQUEST', 'JSON 요청 본문을 읽을 수 없습니다.')
        payload, invalid_reason = _validate_job(payload, agent_id, idempotency_key)
        trace_id = (payload or {}).get('execution_context', {}).get('trace_id', 'unknown') if isinstance(payload, dict) else 'unknown'
        if invalid_reason:
            return _error('INVALID_REQUEST', invalid_reason, trace_id, status=400)
        selected = next((a for a in _agent_manifests() if a['agent_id'] == agent_id), None)
        capability_issue = agent_capability_issue(selected, payload['capability_id'])
        if capability_issue == 'AGENT_NOT_IMPLEMENTED':
            return _error('AGENT_NOT_IMPLEMENTED', 'Agent가 Registry에 없습니다.', trace_id, status=409)
        if capability_issue == 'INVALID_REQUEST':
            return _error('INVALID_REQUEST', '등록되지 않은 capability_id입니다.', trace_id, status=400)
        store = get_store()
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
        previous = next((x for x in store.list('gmais_idempotency') if x.get('key') == idempotency_key), None)
        if previous:
            if previous.get('request_sha256') != digest:
                return _error('SCHEMA_MISMATCH', '같은 Idempotency-Key에 다른 요청 본문을 사용할 수 없습니다.', trace_id, status=409)
            job = store.get('gmais_jobs', previous['job_id'])
            code = job['status'].get('error_code', 'MODEL_NOT_READY')
            return JSONResponse({'error': {'code': code, 'message': job['message'], 'trace_id': trace_id,
                                           'retryable': False, 'details': {'job_id': job['job_id'], 'job_status': job['status'],
                                               **({'input_resolution': job['input_resolution']} if 'input_resolution' in job else {})}}},
                                status_code=409, headers={'Location': f"/v1/jobs/{job['job_id']}"})
        job_id = 'job-' + uuid.uuid4().hex
        stamp = _now()
        status = {
            'schema_version': '0.2.0', 'job_id': job_id, 'agent_id': agent_id,
            'status': 'BLOCKED', 'trace_id': trace_id, 'submitted_at': stamp,
            'progress': 0.0, 'message': '',
        }
        if selected['readiness'] == 'NOT_IMPLEMENTED':
            code, message = 'AGENT_NOT_IMPLEMENTED', '이 Agent는 인터페이스만 등록되어 있어 실행기가 없습니다.'
        else:
            code, message = 'MODEL_NOT_READY', 'LCLUC 데이터 준비도·독립 검증·승인된 배포 모델 gate를 통과하지 못했습니다.'
        status['message'] = message
        status['error_code'] = code
        # RFC 진단은 제출 시점 snapshot이며 과학/모델/배포 gate를 해제하지 않는다.
        # 원문 Job Status schema에는 확장 필드를 삽입하지 않는다.
        from .job_inputs import resolve_job_inputs_with_capture
        resolution, binding_capture = resolve_job_inputs_with_capture(
            store, payload['input_refs'], job_id=job_id, agent_id=agent_id,
            trace_id=trace_id, captured_at=stamp)
        input_resolution = {
            'extension': 'greenblue.job-input-resolution.rfc1',
            'approval_status': 'INTERNAL_REVIEW', 'evaluated_at': stamp,
            'evaluation_scope': 'SUBMISSION_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION',
            **resolution,
        }
        store.put('gmais_jobs', {'id': job_id, 'job_id': job_id, 'agent_id': agent_id, 'status': status, 'request': payload, 'message': message, 'result_id': None,
                                 'input_resolution': input_resolution,
                                 'execution_input_binding_capture': binding_capture})
        store.put('gmais_idempotency', {'id': hashlib.sha256(idempotency_key.encode()).hexdigest(), 'key': idempotency_key, 'request_sha256': digest, 'job_id': job_id})
        return JSONResponse({'error': {'code': code, 'message': message, 'trace_id': trace_id, 'retryable': False,
                                       'details': {'job_id': job_id, 'job_status': status, 'input_resolution': input_resolution}}}, status_code=409,
                            headers={'Location': f'/v1/jobs/{job_id}'})

    @router.post('/v1/workflows/plan')
    async def plan_workflow(request: Request):
        """RFC 확장: workflow를 검사하지만 Job 제출이나 Agent 실행은 하지 않는다."""
        try:
            payload = await request.json()
        except Exception:
            return _error('INVALID_REQUEST', 'JSON 요청 본문을 읽을 수 없습니다.')
        if not isinstance(payload, dict):
            return _error('INVALID_REQUEST', '요청 본문은 JSON 객체여야 합니다.')
        errors = sorted(_workflow_plan_validator().iter_errors(payload), key=lambda error: list(map(str, error.absolute_path)))
        if errors:
            first = errors[0]
            field = '.'.join(map(str, first.absolute_path)) or 'request'
            return _error('INVALID_REQUEST', f'Workflow Plan schema 위반 ({field}): {first.message}', payload.get('trace_id', 'unknown'))
        trace_id = payload['trace_id']
        nodes = payload['nodes']
        node_ids = [node['node_id'] for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            return _error('INVALID_REQUEST', 'Workflow node_id는 중복될 수 없습니다.', trace_id)
        known = set(node_ids)
        for node in nodes:
            if set(node['depends_on']) - known or node['node_id'] in node['depends_on']:
                return _error('INVALID_REQUEST', f"{node['node_id']}의 의존 노드가 없거나 자기 자신을 가리킵니다.", trace_id)
        # Kahn 순서로 DAG 여부를 검사한다. 사이클은 실행계획으로 승인하지 않는다.
        remaining = {node['node_id']: set(node['depends_on']) for node in nodes}
        ordered = topological_order(remaining)
        if ordered is None:
            return _error('INVALID_REQUEST', 'Workflow dependency graph에 cycle이 있습니다.', trace_id)
        manifests = {agent['agent_id']: agent for agent in _agent_manifests()}
        from .job_inputs import resolve_job_inputs
        store = get_store()
        assessed_at = _now()
        input_error_codes = {
            'INPUT_REFS_REQUIRED': 'DATA_MISSING', 'DATASET_VERSION_NOT_FOUND': 'DATA_MISSING',
            'INPUT_ACL_NOT_IMPLEMENTED': 'FORBIDDEN', 'DATASET_REGISTRY_UNAVAILABLE': 'RESOURCE_UNAVAILABLE',
            'INPUT_REF_SCHEMA_MISMATCH': 'SCHEMA_MISMATCH', 'INPUT_REF_NOT_PINNED': 'SCHEMA_MISMATCH',
            'INPUT_REF_CONFLICT': 'SCHEMA_MISMATCH', 'INPUT_URI_MISMATCH': 'SCHEMA_MISMATCH',
        }
        reviewed_nodes = []
        for node in nodes:
            agent = manifests.get(node['agent_id'])
            capability_issue = agent_capability_issue(agent, node['capability_id'])
            blockers = []
            if capability_issue == 'AGENT_NOT_IMPLEMENTED':
                blockers.append({'code': 'AGENT_NOT_IMPLEMENTED', 'message': 'Registry에 없는 Agent입니다.'})
            elif capability_issue == 'INVALID_REQUEST':
                blockers.append({'code': 'INVALID_REQUEST', 'message': 'Agent에 등록되지 않은 capability입니다.'})
            elif agent['readiness'] != 'READY':
                code = 'MODEL_NOT_READY' if agent['agent_id'] == 'lcluc-agent' else 'AGENT_NOT_IMPLEMENTED'
                blockers.append({'code': code, 'message': 'Agent readiness가 READY가 아니므로 실행할 수 없습니다.'})
            input_resolution = {
                'extension': 'greenblue.workflow-input-resolution.rfc1',
                'approval_status': 'INTERNAL_REVIEW', 'evaluated_at': assessed_at,
                'evaluation_scope': 'PLAN_REQUEST_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION',
                **resolve_job_inputs(store, node['input_bindings']),
            }
            for issue in input_resolution['blockers']:
                blockers.append({'code': input_error_codes.get(issue['code'], 'DATA_QUALITY'),
                                 'detail_code': issue['code'], 'input_index': issue['input_index'],
                                 'message': '고정 입력의 무결성·품질·접근 정책 진단을 통과하지 못했습니다.'})
            if not blockers:
                blockers.append({'code': 'MODEL_NOT_READY', 'message': '계획 검사만 지원하며 승인된 실제 실행기는 아직 연결되지 않았습니다.'})
            reviewed_nodes.append({
                'node_id': node['node_id'], 'agent_id': node['agent_id'], 'capability_id': node['capability_id'],
                'depends_on': node['depends_on'], 'status': 'BLOCKED', 'blockers': blockers,
                'execution_authorized': False, 'input_resolution': input_resolution,
            })
        from .workflow_policy import diagnose_workflow_blocking
        policy_resolution = {
            'extension': 'greenblue.workflow-blocking-policy.rfc1',
            'approval_status': 'INTERNAL_REVIEW', 'evaluated_at': assessed_at,
            **diagnose_workflow_blocking(reviewed_nodes, payload['policy']),
        }
        dependency_by_id = {item['node_id']: item for item in policy_resolution['nodes']}
        for node in reviewed_nodes:
            node['dependency_resolution'] = dependency_by_id[node['node_id']]
        return {
            'extension': {'id': 'greenblue.workflow-plan.rfc1', 'contract_basis': 'GMAIS v0.2 workflow-plan schema',
                          'present_in_upstream_openapi': False, 'approval_status': 'INTERNAL_REVIEW'},
            'workflow_run_id': payload['workflow_run_id'], 'trace_id': trace_id,
            'mode': 'PLAN_ONLY', 'execution_started': False, 'can_execute': False,
            'status': 'BLOCKED', 'topological_order': ordered, 'nodes': reviewed_nodes,
            'policy_resolution': policy_resolution,
            'blockers': ['Agent 실제 실행기·과학 검증·모델/배포 승인 gate가 아직 준비되지 않았습니다.'],
            'limitations': ['이 RFC 확장은 계획 검사만 수행하며 Job/Result/지도/보고서를 생성하지 않습니다.',
                            'GMAIS v0.2와 기관의 공식 승인 계약으로 해석하지 않습니다.'],
        }

    @router.get('/v1/jobs/{job_id}')
    def get_job(job_id: str):
        try:
            return get_store().get('gmais_jobs', job_id)['status']
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Job이 없습니다.', status=404)

    @router.get('/v1/jobs/{job_id}/input-resolution')
    def job_input_snapshot(job_id: str):
        """저장된 제출 시점 진단만 읽는다. 현재 입력을 재조회하거나 승인하지 않는다."""
        from .job_snapshot import project_job_input_snapshot
        try:
            job = get_store().get('gmais_jobs', job_id)
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Job이 없습니다.', status=404)
        return project_job_input_snapshot(job, job_id)

    @router.get('/v1/jobs/{job_id}/results')
    def job_results(job_id: str):
        try:
            job = get_store().get('gmais_jobs', job_id)
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Job이 없습니다.', status=404)
        if job.get('result_id'):
            try:
                return get_store().get('gmais_results', job['result_id'])
            except KeyError:
                return _error('INTERNAL_ERROR', 'Job에 연결된 Result manifest를 찾을 수 없습니다.', job['status']['trace_id'], status=500)
        return _error('MODEL_NOT_READY', '차단된 Job에는 결과가 생성되지 않았습니다.', job['status']['trace_id'], status=409)

    @router.post('/v1/jobs/{job_id}/cancel')
    def cancel_job(job_id: str):
        try:
            job = get_store().get('gmais_jobs', job_id)
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Job이 없습니다.', status=404)
        return _error('INVALID_REQUEST', '이미 BLOCKED 상태인 Job은 취소할 수 없습니다.', job['status']['trace_id'], status=409)

    @router.get('/v1/results/{result_id}')
    def get_result(result_id: str):
        try:
            return get_store().get('gmais_results', result_id)
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Result가 없습니다.', status=404)

    @router.get('/v1/results/{result_id}/sdss')
    def sdss_result(result_id: str):
        """RFC 확장: 검증에 성공한 Result만 SDSS 자산 목록으로 투영한다."""
        from .sdss_results import project_result
        try:
            return project_result(get_store(), result_id)
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Result가 없습니다.', status=404)

    @router.get('/v1/results/{result_id}/assets/{asset_index}')
    def result_asset(result_id: str, asset_index: int):
        """다운로드 직전에도 전체 gate와 파일 해시를 다시 확인한다."""
        from .sdss_results import download_snapshot
        store = get_store()
        try:
            projection, snapshot, filename = download_snapshot(store, result_id, asset_index)
        except KeyError:
            return _error('JOB_NOT_FOUND', 'Result가 없습니다.', status=404)
        except IndexError:
            return _error('INVALID_REQUEST', '자산 번호가 없습니다.', status=404)
        except (ValueError, OSError):
            return _error('INVALID_REQUEST', '자산 내용 또는 경로를 검증할 수 없습니다.', status=409)
        if not projection['publishable']:
            return _error('MODEL_NOT_READY', '검증되지 않은 Result 자산은 제공하지 않습니다.',
                          projection.get('trace_id') or 'unknown', status=409,
                          details={'blockers': projection['blockers']})
        def chunks():
            try:
                yield from iter(lambda: snapshot.read(1024 * 1024), b'')
            finally:
                snapshot.close()
        from urllib.parse import quote
        return StreamingResponse(chunks(), media_type='application/octet-stream',
                                 headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
                                          'Content-Disposition': "attachment; filename*=UTF-8''" + quote(filename, safe='')})

    return router
