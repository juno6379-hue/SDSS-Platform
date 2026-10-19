"""실제 수신 본문 SHA와 현재 전이 계보를 반환하는 비실행 Workflow RFC companion."""
import hashlib
import json

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from .dataset_lineage_api import _error, _now
from .workflow_lineage import validate_workflow_lineage, WorkflowLineageRequestError


def create_workflow_lineage_router(get_store):
    router = APIRouter()

    @router.post('/v1/workflows/lineage-validation')
    async def workflow_lineage(request: Request):
        raw = await request.body()

        def reject_constant(_value):
            raise ValueError('표준 JSON 상수가 아닙니다.')

        try:
            payload = json.loads(raw, parse_constant=reject_constant)
        except (ValueError, UnicodeError):
            return _error('INVALID_REQUEST','Workflow JSON 요청을 읽을 수 없습니다.',400)
        started = _now()
        try:
            result = await run_in_threadpool(lambda:validate_workflow_lineage(get_store(),payload))
        except WorkflowLineageRequestError:
            return _error('INVALID_REQUEST','Workflow 형식·의존 관계·검사 한도를 확인하세요.',400)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE','Workflow 현재 계보 검사를 완료할 수 없습니다.',503)
        return JSONResponse({'extension':'greenblue.workflow-lineage-validation.rfc1',
            'approval_status':'INTERNAL_REVIEW','present_in_upstream_openapi':False,
            'evaluation_scope':'CURRENT_WORKFLOW_TRANSITIVE_LINEAGE_PLAN_ONLY',
            'request_sha256':hashlib.sha256(raw).hexdigest(),
            'assessment_started_at':started,'assessment_finished_at':_now(),**result},
            headers={'Cache-Control':'no-store'})

    return router
