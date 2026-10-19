"""저장 Job capture만 읽는 최소 API. 현재 Registry/자산 재검증은 없다."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .execution_input_binding import _FALSE, _text
from .job_execution_binding_capture import project_job_execution_binding_capture

_HASH={'anyOf':[{'type':'string','pattern':'^[a-f0-9]{64}$'},{'type':'null'}]}
_COUNT={'anyOf':[{'type':'integer','minimum':1,'maximum':64},{'type':'null'}]}
RESPONSE_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'schema_version':{'const':1},'extension':{'const':'greenblue.stored-execution-input-binding.rfc1'},
    'approval_status':{'const':'INTERNAL_REVIEW'},'scope':{'const':'STORED_SUBMISSION_BINDING_ONLY'},
    'status':{'enum':['RECORDED','UNAVAILABLE','LEGACY','INVALID']},
    'request_job_sha256':_HASH,'request_binding_count':_COUNT,'capture_binding_count':_COUNT,
    'manifest_pin_count':_COUNT,'expected_bindings_sha256':_HASH,'stored_binding_integrity_match':{'type':'boolean'},
    'issues':{'type':'array','maxItems':1,'items':{'type':'object','additionalProperties':False,
      'required':['code','input_index'],'properties':{'code':{'enum':['CAPTURE_UNAVAILABLE','CAPTURE_TIME_INVALID',
      'CAPTURE_ROWS_UNAVAILABLE','CAPTURE_ROW_UNAVAILABLE','CAPTURE_BINDING_INVALID','CAPTURE_BOUNDARY_FAILURE',
      'LEGACY_CAPTURE_NOT_RECORDED','STORED_JOB_INVALID','STORED_CAPTURE_INVALID']},
      'input_index':{'anyOf':[{'type':'integer','minimum':0,'maximum':63},{'type':'null'}]}}}},
    **{key:{'const':False} for key in (*_FALSE,'current_files_revalidated','executor_bindings_compared')}}}
RESPONSE_SCHEMA['required']=list(RESPONSE_SCHEMA['properties'])
ERROR_SCHEMA={'type':'object','additionalProperties':False,'required':['error'],'properties':{'error':{
    'type':'object','additionalProperties':False,'required':['code','message','retryable'],
    'properties':{'code':{'enum':['JOB_NOT_FOUND','RESOURCE_UNAVAILABLE']},'message':{'type':'string'},'retryable':{'const':False}}}}}


def _error(code,status):
    return JSONResponse({'error':{'code':code,'message':'Job was not found.' if status==404 else 'Stored binding capture is unavailable.',
                                  'retryable':False}},status_code=status,headers={'Cache-Control':'no-store'})


def create_job_execution_binding_capture_router(get_store):
    router=APIRouter()
    @router.get('/v1/jobs/{job_id}/execution-input-binding',responses={200:{'content':{'application/json':{'schema':RESPONSE_SCHEMA}}},
        **{code:{'description':'Safe stored capture error','content':{'application/json':{'schema':ERROR_SCHEMA}}} for code in [404,503]}})
    async def read(job_id:str):
        if not _text(job_id):
            return JSONResponse(project_job_execution_binding_capture(None,job_id),headers={'Cache-Control':'no-store'})
        def worker():
            job=get_store().get('gmais_jobs',job_id)
            return project_job_execution_binding_capture(job,job_id)
        try: result=await run_in_threadpool(worker)
        except KeyError:return _error('JOB_NOT_FOUND',404)
        except Exception:return _error('RESOURCE_UNAVAILABLE',503)
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
    return router
