"""명시적 현재 입력 preflight GET. worker 종료까지 단일 검사 lock을 유지한다."""
import hashlib
import threading
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .execution_input_binding import _FALSE, _text, _sha
from .job_snapshot import _CODES
from .stored_current_binding_preflight import inspect_stored_current_binding_preflight

TOP_FALSE=set(_FALSE)|{'executor_bindings_compared','stored_job_origin_verified','transitive_lineage_verified'}
INNER_FALSE=set(_FALSE)|{'current_files_revalidated','executor_bindings_compared','stored_job_origin_verified'}
INNER_IO={'network_requests','source_files_read','source_files_written','database_calls','registry_calls','resolver_calls','executor_calls'}
TOP_CODES={'INVALID_JOB_ID','JOB_NOT_FOUND','RESOURCE_UNAVAILABLE','STORED_JOB_INVALID','STORED_CAPTURE_INVALID',
 'LEGACY_EXPECTED_BINDING_NOT_RECORDED','EXPECTED_BINDING_CAPTURE_UNAVAILABLE','STORED_URI_UNSUPPORTED',
 'CURRENT_RESOLVER_RESOURCE_UNAVAILABLE','CURRENT_RESOLUTION_INVALID','CURRENT_CAPTURE_INVALID','CURRENT_CAPTURE_UNAVAILABLE',
 'CURRENT_INPUT_DIAGNOSTICS_BLOCKED','CURRENT_BINDINGS_MISMATCH'}
INNER_CODES={'ENVELOPE_SCHEMA_INVALID','IDENTITY_SCHEMA_INVALID','BINDING_COUNT_INVALID','BINDING_SCHEMA_INVALID',
 'BINDING_INDEX_INVALID','BINDING_IDENTITY_INVALID','BINDING_VERSION_NOT_PINNED','BINDING_SHA_INVALID','BINDING_ROLE_INVALID',
 'BINDING_MANIFEST_SHA_INVALID','BINDING_IDENTITY_CONFLICT','JOB_ID_MISMATCH','AGENT_ID_MISMATCH','TRACE_ID_MISMATCH',
 'BINDING_COUNT_MISMATCH','BINDING_ID_MISMATCH','BINDING_VERSION_MISMATCH','BINDING_SHA_MISMATCH','BINDING_ROLE_MISMATCH',
 'BINDING_MANIFEST_PIN_MISMATCH','STORED_JOB_INVALID','STORED_CAPTURE_INVALID','LEGACY_EXPECTED_BINDING_NOT_RECORDED',
 'EXPECTED_BINDING_CAPTURE_UNAVAILABLE'}
COUNTS={'current_input_count','current_integrity_verified_count','current_quality_public_observed_count','current_blocker_count'}
TOP_KEYS={'schema_version','scope','status','store_status','store_read_attempted','store_read_observed','store_get_calls',
 'request_job_sha256','stored_capture_status','resolver_pass_calls','current_resolution_status','current_capture_status',
 'current_quality_public_diagnostics_passed','current_blockers','binding_comparison','issues'}|COUNTS|TOP_FALSE
INNER_KEYS={'schema_version','scope','status','stored_capture_status','request_job_sha256','expected_bindings_sha256',
 'supplied_bindings_sha256','request_binding_count','stored_expected_binding_count','supplied_binding_count',
 'declarations_match','issues'}|INNER_FALSE|INNER_IO


def _require(value):
    if not value:raise ValueError('Invalid safe preflight response.')


def _exact(value,keys):
    _require(type(value) is dict and len(value)==len(keys) and set(value)==keys)


def _enum(value,choices):
    return type(value) is str and len(value)<=64 and value in choices


def _uint(value,maximum=64):
    return type(value) is int and 0<=value<=maximum


def _inner(value,job_sha,count):
    _exact(value,INNER_KEYS)
    _require(type(value['schema_version']) is int and value['schema_version']==1)
    _require(_enum(value['scope'],{'STORED_EXPECTED_TO_SUPPLIED_DECLARATIONS_ONLY'}) and _enum(value['status'],{'MATCH','BLOCKED'}))
    _require(_enum(value['stored_capture_status'],{'RECORDED'}) and _sha(value['request_job_sha256']) and value['request_job_sha256']==job_sha)
    for key in INNER_FALSE:_require(value[key] is False)
    for key in INNER_IO:_require(type(value[key]) is int and value[key]==0)
    for key in ('request_binding_count','stored_expected_binding_count','supplied_binding_count'):_require(type(value[key]) is int and value[key]==count)
    for key in ('expected_bindings_sha256','supplied_bindings_sha256'):_require(_sha(value[key]))
    _require(type(value['declarations_match']) is bool and value['declarations_match']==(value['status']=='MATCH'))
    issues=value['issues'];_require(type(issues) is list and len(issues)<=512)
    for issue in issues:
        _exact(issue,{'side','input_index','code'})
        _require(_enum(issue['side'],{'expected','supplied','stored','comparison'}) and _enum(issue['code'],INNER_CODES))
        _require(issue['input_index'] is None or _uint(issue['input_index'],count-1))
    _require((value['status']=='MATCH')==(len(issues)==0))
    if value['status']=='MATCH':_require(value['expected_bindings_sha256']==value['supplied_bindings_sha256'])


def validate_preflight_response(value,job_id):
    """Bounded typed checks before JSON serialization; rejects raw extra/nested data."""
    _exact(value,TOP_KEYS)
    _require(type(value['schema_version']) is int and value['schema_version']==1)
    _require(_enum(value['scope'],{'STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY'}) and _enum(value['status'],{'MATCH','BLOCKED','UNKNOWN'}))
    expected_sha=hashlib.sha256(job_id.encode('utf-8')).hexdigest()
    _require(type(value['request_job_sha256']) is str and len(value['request_job_sha256'])==64 and value['request_job_sha256']==expected_sha)
    for key in TOP_FALSE:_require(value[key] is False)
    _require(value['store_read_attempted'] is True and type(value['store_read_observed']) is bool)
    _require(type(value['store_get_calls']) is int and value['store_get_calls']==1)
    _require(type(value['resolver_pass_calls']) is int and value['resolver_pass_calls'] in (0,1))
    _require(_enum(value['store_status'],{'OBSERVED','NOT_FOUND','RESOURCE_UNAVAILABLE'}))
    _require(value['store_read_observed']==(value['store_status']=='OBSERVED'))
    _require(value['stored_capture_status'] is None or _enum(value['stored_capture_status'],{'RECORDED','UNAVAILABLE','LEGACY','INVALID'}))
    _require(_enum(value['current_resolution_status'],{'NOT_RUN','INTEGRITY_VERIFIED','BLOCKED','RESOURCE_UNAVAILABLE','INVALID'}))
    _require(_enum(value['current_capture_status'],{'NOT_RUN','RECORDED','UNAVAILABLE','INVALID'}))
    issues=value['issues'];_require(type(issues) is list and len(issues)<=1)
    for issue in issues:_exact(issue,{'code'});_require(_enum(issue['code'],TOP_CODES))
    code=issues[0]['code'] if issues else None
    current=value['current_resolution_status'];capture=value['current_capture_status'];stored=value['stored_capture_status']
    blockers=value['current_blockers'];_require(type(blockers) is list and len(blockers)<=768)
    known=current in {'INTEGRITY_VERIFIED','BLOCKED'}
    if known:
        n=value['current_input_count'];_require(_uint(n) and n>=1)
        _require(_uint(value['current_integrity_verified_count'],n) and _uint(value['current_quality_public_observed_count'],n))
        _require(_uint(value['current_blocker_count'],768) and value['current_blocker_count']==len(blockers))
        _require(type(value['current_quality_public_diagnostics_passed']) is bool)
        for issue in blockers:
            _exact(issue,{'code','input_index'});_require(_enum(issue['code'],_CODES) and _uint(issue['input_index'],n-1))
        quality_codes={'INPUT_ACL_NOT_IMPLEMENTED','INPUT_QUALITY_NOT_VALIDATED','INPUT_QUALITY_REJECTED'}
        missing_metadata_codes={'DATASET_RECORD_CORRUPT','DATASET_REGISTRY_UNAVAILABLE','DATASET_VERSION_NOT_FOUND',
                                'INPUT_INTEGRITY_FAILED','INPUT_REFS_REQUIRED','INPUT_REF_NOT_PINNED','INPUT_REF_SCHEMA_MISMATCH'}
        _require(len({(b['input_index'],b['code']) for b in blockers})==len(blockers) and len(blockers)<=n*len(_CODES))
        failed_indices={b['input_index'] for b in blockers if b['code'] not in quality_codes}
        missing_metadata_indices={b['input_index'] for b in blockers if b['code'] in missing_metadata_codes}
        _require(value['current_integrity_verified_count']==n-len(failed_indices))
        _require(value['current_quality_public_observed_count']==n-len(missing_metadata_indices))
        _require(value['current_integrity_verified_count']<=value['current_quality_public_observed_count'])
        _require(value['current_quality_public_diagnostics_passed']==
                 (value['current_quality_public_observed_count']==n and not any(b['code'] in quality_codes for b in blockers)))
        if current=='INTEGRITY_VERIFIED':
            _require(value['current_integrity_verified_count']==n and value['current_quality_public_observed_count']==n
                     and value['current_quality_public_diagnostics_passed'] is True and not blockers)
        else:_require(bool(blockers))
    else:
        _require(all(value[key] is None for key in COUNTS) and value['current_quality_public_diagnostics_passed'] is None and not blockers)
    comparison=value['binding_comparison']
    if comparison is not None:
        _require(known and capture=='RECORDED' and stored=='RECORDED')
        _require(value['current_integrity_verified_count']==value['current_input_count']==value['current_quality_public_observed_count'])
        _inner(comparison,expected_sha,value['current_input_count'])
    elif capture=='RECORDED':_require(False)
    if value['store_status']!='OBSERVED':
        _require(stored is None and value['resolver_pass_calls']==0 and current==capture=='NOT_RUN' and value['status']=='BLOCKED')
        _require(code==('JOB_NOT_FOUND' if value['store_status']=='NOT_FOUND' else 'RESOURCE_UNAVAILABLE'))
    elif stored in {'LEGACY','UNAVAILABLE','INVALID'}:
        _require(value['resolver_pass_calls']==0 and current==capture=='NOT_RUN')
        if stored=='INVALID':_require(value['status']=='BLOCKED' and code in {'STORED_JOB_INVALID','STORED_CAPTURE_INVALID'})
        else:_require(value['status']=='UNKNOWN' and code==('LEGACY_EXPECTED_BINDING_NOT_RECORDED' if stored=='LEGACY' else 'EXPECTED_BINDING_CAPTURE_UNAVAILABLE'))
    else:
        _require(stored=='RECORDED')
        if value['resolver_pass_calls']==0:_require(current==capture=='NOT_RUN' and value['status']=='BLOCKED' and code=='STORED_URI_UNSUPPORTED')
        elif current in {'RESOURCE_UNAVAILABLE','INVALID'}:
            _require(capture=='NOT_RUN' and value['status']=='BLOCKED' and code==('CURRENT_RESOLVER_RESOURCE_UNAVAILABLE' if current=='RESOURCE_UNAVAILABLE' else 'CURRENT_RESOLUTION_INVALID'))
        else:
            _require(known)
            if capture in {'INVALID','UNAVAILABLE'}:_require(value['status']=='BLOCKED' and code==('CURRENT_CAPTURE_INVALID' if capture=='INVALID' else 'CURRENT_CAPTURE_UNAVAILABLE'))
            else:
                _require(capture=='RECORDED' and comparison is not None)
                if current=='BLOCKED':_require(value['status']=='BLOCKED' and code=='CURRENT_INPUT_DIAGNOSTICS_BLOCKED')
                elif comparison['status']=='BLOCKED':_require(value['status']=='BLOCKED' and code=='CURRENT_BINDINGS_MISMATCH')
                else:_require(value['status']=='MATCH' and code is None)
    return value


def _object(properties):return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
_HASH={'anyOf':[{'type':'string','pattern':'^[a-f0-9]{64}$'},{'type':'null'}]}
_COUNT={'anyOf':[{'type':'integer','minimum':0,'maximum':64},{'type':'null'}]}
_ISSUE=_object({'side':{'enum':['expected','supplied','stored','comparison']},'input_index':{'anyOf':[{'type':'integer','minimum':0,'maximum':63},{'type':'null'}]},'code':{'enum':sorted(INNER_CODES)}})
COMPARISON_SCHEMA=_object({'schema_version':{'const':1},'scope':{'const':'STORED_EXPECTED_TO_SUPPLIED_DECLARATIONS_ONLY'},'status':{'enum':['MATCH','BLOCKED','UNKNOWN']},'stored_capture_status':{'enum':['RECORDED','UNAVAILABLE','LEGACY','INVALID']},'request_job_sha256':_HASH,'expected_bindings_sha256':_HASH,'supplied_bindings_sha256':_HASH,**{k:_COUNT for k in ['request_binding_count','stored_expected_binding_count','supplied_binding_count']},'declarations_match':{'type':'boolean'},'issues':{'type':'array','maxItems':512,'items':_ISSUE},**{k:{'const':False} for k in sorted(INNER_FALSE)},**{k:{'const':0} for k in sorted(INNER_IO)}})
RESPONSE_SCHEMA=_object({'schema_version':{'const':1},'scope':{'const':'STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY'},'status':{'enum':['MATCH','BLOCKED','UNKNOWN']},'store_status':{'enum':['INVALID_REQUEST','OBSERVED','NOT_FOUND','RESOURCE_UNAVAILABLE']},'store_read_attempted':{'type':'boolean'},'store_read_observed':{'type':'boolean'},'store_get_calls':{'type':'integer','minimum':0,'maximum':1},'request_job_sha256':_HASH,'stored_capture_status':{'enum':['RECORDED','UNAVAILABLE','LEGACY','INVALID',None]},'resolver_pass_calls':{'type':'integer','minimum':0,'maximum':1},'current_resolution_status':{'enum':['NOT_RUN','INTEGRITY_VERIFIED','BLOCKED','RESOURCE_UNAVAILABLE','INVALID']},'current_capture_status':{'enum':['NOT_RUN','RECORDED','UNAVAILABLE','INVALID']},**{k:_COUNT for k in sorted(COUNTS-{'current_blocker_count'})},'current_blocker_count':{'anyOf':[{'type':'integer','minimum':0,'maximum':768},{'type':'null'}]},'current_quality_public_diagnostics_passed':{'type':['boolean','null']},'current_blockers':{'type':'array','maxItems':768,'items':_object({'code':{'enum':sorted(_CODES)},'input_index':{'type':'integer','minimum':0,'maximum':63}})},'binding_comparison':{'anyOf':[COMPARISON_SCHEMA,{'type':'null'}]},'issues':{'type':'array','maxItems':1,'items':_object({'code':{'enum':sorted(TOP_CODES)}})},**{k:{'const':False} for k in sorted(TOP_FALSE)}})
ERROR_SCHEMA=_object({'error':_object({'code':{'enum':['INVALID_REQUEST','JOB_NOT_FOUND','PREFLIGHT_BUSY','RESOURCE_UNAVAILABLE']},'message':{'type':'string'},'retryable':{'type':'boolean'}})})


def _error(code,status):
    messages={'INVALID_REQUEST':'Invalid preflight request.','JOB_NOT_FOUND':'Job was not found.',
              'PREFLIGHT_BUSY':'An input preflight is already running.','RESOURCE_UNAVAILABLE':'Input preflight is unavailable.'}
    headers={'Cache-Control':'no-store'}
    if status==429:headers['Retry-After']='1'
    return JSONResponse({'error':{'code':code,'message':messages[code],'retryable':status==429}},status_code=status,headers=headers)


def create_stored_current_binding_preflight_router(get_store):
    router=APIRouter();gate=threading.BoundedSemaphore(1);busy=object()
    @router.get('/v1/jobs/{job_id}/input-preflight',responses={200:{'content':{'application/json':{'schema':RESPONSE_SCHEMA}}},**{code:{'description':'Safe input preflight error','content':{'application/json':{'schema':ERROR_SCHEMA}}} for code in [400,404,429,503]}})
    async def read(job_id:str):
        if not _text(job_id):return _error('INVALID_REQUEST',400)
        def worker():
            if not gate.acquire(blocking=False):return busy
            try:return validate_preflight_response(inspect_stored_current_binding_preflight(get_store(),job_id),job_id)
            finally:gate.release()
        try:result=await run_in_threadpool(worker)
        except Exception:return _error('RESOURCE_UNAVAILABLE',503)
        if result is busy:return _error('PREFLIGHT_BUSY',429)
        if result['store_status']=='NOT_FOUND':return _error('JOB_NOT_FOUND',404)
        if result['store_status']=='RESOURCE_UNAVAILABLE' or result['current_resolution_status']=='RESOURCE_UNAVAILABLE':return _error('RESOURCE_UNAVAILABLE',503)
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
    return router
