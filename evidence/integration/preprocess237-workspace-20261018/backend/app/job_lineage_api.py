"""Job 제출 기록과 분리된 현재 입력 계보의 비쓰기 RFC companion."""
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from .dataset_lineage_api import _error, _now
from .job_lineage import validate_job_lineage


def create_job_lineage_router(get_store):
    router = APIRouter()

    @router.get('/v1/jobs/{job_id}/lineage-validation')
    async def current_job_lineage(job_id: str):
        started = _now()
        try:
            result = await run_in_threadpool(lambda: validate_job_lineage(get_store(), job_id))
        except KeyError as error:
            if error.args == (job_id,):
                return _error('JOB_NOT_FOUND', 'Job이 없습니다.', 404)
            return _error('RESOURCE_UNAVAILABLE', '현재 입력 계보 검사를 완료할 수 없습니다.', 503)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', '현재 입력 계보 검사를 완료할 수 없습니다.', 503)
        return JSONResponse({'extension': 'greenblue.job-lineage-validation.rfc1',
            'approval_status': 'INTERNAL_REVIEW', 'present_in_upstream_openapi': False,
            'evaluation_scope': 'CURRENT_TRANSITIVE_LINEAGE_NOT_SUBMISSION_SNAPSHOT',
            'assessment_started_at': started, 'assessment_finished_at': _now(), **result},
            headers={'Cache-Control': 'no-store'})

    return router
