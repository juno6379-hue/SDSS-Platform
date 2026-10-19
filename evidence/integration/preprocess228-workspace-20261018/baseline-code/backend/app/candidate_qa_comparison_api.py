"""고정 원본/후보 QA 보고서 비교의 명시 조회 API. 경로·상세 원문은 반환하지 않는다."""
import threading
from fastapi import APIRouter,Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from .ml.candidate_qa_comparison import compare_candidate_qa,PIN_NAMES,FALSE_FIELDS,_sha
from .data.recovery_boundary import _check_depth,_decode
from .readiness_source_identity_api import _error,ERROR_SCHEMA

BODY_BYTES=2048
REQUEST_SCHEMA={'type':'object','additionalProperties':False,'required':list(PIN_NAMES),'properties':{k:{'type':'string','pattern':'^[0-9a-f]{64}$'} for k in PIN_NAMES}}


def _object(properties):return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}

def _integer(maximum):return {'type':'integer','minimum':0,'maximum':maximum}

SPLIT_SCHEMA=_object({s:_integer(3000) for s in ['train','val','test']})
SUMMARY_SCHEMA=_object({'eligible_patches_by_split':SPLIT_SCHEMA,'eligible_patch_count':_integer(9000),'blocker_count':_integer(10000)})
RESPONSE_SCHEMA=_object({'schema_version':{'type':'integer','const':1},'status':{'const':'BLOCKED'},'scope':{'const':'PINNED_REPORT_COMPARISON_ONLY'},'pins':REQUEST_SCHEMA,'original':SUMMARY_SCHEMA,'candidate':SUMMARY_SCHEMA,
 'blocker_frequencies':{'type':'array','minItems':1,'maxItems':32,'items':_object({'code':{'type':'string','pattern':'^[A-Z][A-Z0-9_]{0,63}$'},'original_count':_integer(10000),'candidate_count':_integer(10000)})},
 'shared_source_blocker':_object({'code':{'const':'SHARED_SOURCE_CROSSES_FIXED_SPLIT'},'original_observed':{'type':'boolean'},'candidate_observed':{'type':'boolean'},'absence_proves_independence':{'type':'boolean','const':False}}),
 'row_counts':_object({'original_report_physical_scene_count':{'type':'null'},'original_report_scope':{'const':'NOT_PERSISTED'},'source_rows_declared':_integer(100000),'candidate_rows_declared':_integer(100000),'declared_scope':{'const':'PINNED_STAGING_RECEIPT_DECLARATION'},'candidate_appended_scene_count':{'type':['integer','null'],'minimum':0,'maximum':2000},'candidate_capture_scope':{'enum':['STORED_QA_CAPTURE','NOT_CAPTURED']}}),
 'bare_class':_object({'class_index':{'type':'integer','const':7},'class_name':{'const':'bare'},'original_pixels_by_split':_object({s:_integer(9007199254740991) for s in ['train','val','test']}),'candidate_pixels_by_split':_object({s:_integer(9007199254740991) for s in ['train','val','test']}),'original_patch_counts_by_split':SPLIT_SCHEMA,'candidate_patch_counts_by_split':SPLIT_SCHEMA,'required_min_pixels_per_split':{'type':'integer','minimum':256,'maximum':65536},'required_min_class_patches_per_split':{'type':'integer','minimum':5,'maximum':3000},'candidate_shortage_observed':{'type':'boolean'},'shortage_resolved':{'type':'boolean','const':False}}),
 **{k:{'type':'boolean','const':False} for k in sorted(FALSE_FIELDS)}})


def _request(raw):
    _check_depth(raw,8);value=_decode(raw)
    if type(value) is not dict or set(value)!=set(PIN_NAMES) or not all(_sha(p) for p in value.values()):raise ValueError('Invalid comparison request')
    return value


def create_candidate_qa_comparison_router(get_store):
    router=APIRouter();gate=threading.BoundedSemaphore(1)
    @router.post('/v1/diagnostics/candidate-readiness-comparison',responses={200:{'content':{'application/json':{'schema':RESPONSE_SCHEMA}}},**{code:{'description':'Safe diagnostic error','content':{'application/json':{'schema':ERROR_SCHEMA}}} for code in [400,409,413,429,503]}},openapi_extra={'requestBody':{'required':True,'content':{'application/json':{'schema':REQUEST_SCHEMA}}}})
    async def inspect(request:Request):
        body=bytearray()
        try:
            async for chunk in request.stream():
                if len(body)+len(chunk)>BODY_BYTES:return _error('REQUEST_TOO_LARGE',413)
                body.extend(chunk)
            pins=_request(bytes(body))
        except Exception:return _error('INVALID_REQUEST',400)
        def worker():
            if not gate.acquire(blocking=False):return None
            try:return compare_candidate_qa(get_store().root,pins)
            finally:gate.release()
        try:result=await run_in_threadpool(worker)
        except ValueError as exc:
            if any(marker in str(exc) for marker in ['SHA mismatch','changed','retarget']):return _error('PINNED_INPUT_CONFLICT',409)
            return _error('RESOURCE_UNAVAILABLE',503)
        except Exception:return _error('RESOURCE_UNAVAILABLE',503)
        if result is None:return _error('DIAGNOSTIC_BUSY',429)
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
    return router
