"""저장 제출 binding의 안전 projection. 현재 Registry/자산/executor를 확인하지 않는다."""
import hashlib
from .execution_input_binding import compare_execution_input_bindings, _FALSE, _text
from .execution_binding_capture import _stamp

ISSUE_CODES = {'CAPTURE_UNAVAILABLE', 'CAPTURE_TIME_INVALID', 'CAPTURE_ROWS_UNAVAILABLE',
               'CAPTURE_ROW_UNAVAILABLE', 'CAPTURE_BINDING_INVALID', 'CAPTURE_BOUNDARY_FAILURE'}
_CAPTURE_KEYS = {'schema_version','extension','approval_status','scope','captured_at','status',
                 'expected_envelope','expected_bindings_sha256','issues','pin_source',
                 'additional_registry_queries','additional_artifact_reads','additional_database_writes'} | set(_FALSE)


def _require(value):
    if not value:
        raise ValueError('Stored binding capture invalid.')


def _selected_request(job, job_id):
    _require(type(job) is dict)
    status, request = job.get('status'), job.get('request')
    _require(type(status) is dict and type(request) is dict)
    _require(all(_text(value) for value in (job.get('id'),job.get('job_id'),status.get('job_id'))))
    _require(job.get('id') == job.get('job_id') == status.get('job_id') == job_id)
    agent=job.get('agent_id')
    _require(all(_text(value) for value in (agent,status.get('agent_id'),request.get('agent_id'))))
    _require(agent == status.get('agent_id') == request.get('agent_id'))
    context=request.get('execution_context')
    _require(type(context) is dict)
    _require(all(_text(value) for value in (status.get('trace_id'),context.get('trace_id'))))
    _require(status['trace_id']==context.get('trace_id'))
    refs=request.get('input_refs')
    _require(type(refs) is list and 1 <= len(refs) <= 64)
    rows=[]
    for index, ref in enumerate(refs):
        _require(type(ref) is dict and 3 <= len(ref) <= 5
                 and {'id','version','sha256'} <= set(ref)
                 and not set(ref)-{'id','version','sha256','role','uri'})
        _require('uri' not in ref or type(ref['uri']) is str)
        row={key:ref[key] for key in ('id','version','sha256')}
        row['input_index']=index
        if 'role' in ref: row['role']=ref['role']
        rows.append(row)
    selected={'job_id':job_id,'agent_id':agent,'trace_id':status['trace_id'],'bindings':rows}
    _require(compare_execution_input_bindings(selected,selected)['status']=='UNKNOWN')
    return selected


def _capture(capture, selected):
    _require(type(capture) is dict and len(capture)==len(_CAPTURE_KEYS) and set(capture)==_CAPTURE_KEYS)
    for key, value in {'schema_version':1,'extension':'greenblue.execution-input-binding-capture.rfc1',
                       'approval_status':'INTERNAL_REVIEW','scope':'SUBMISSION_EXPECTED_BINDING_METADATA',
                       'pin_source':'SAME_RESOLVE_VERSION_RETURN'}.items():
        _require(type(capture.get(key)) is type(value) and capture[key]==value)
    for key in _FALSE: _require(capture[key] is False)
    for key in ('additional_registry_queries','additional_artifact_reads','additional_database_writes'):
        _require(type(capture[key]) is int and capture[key]==0)
    state=capture['status'];_require(type(state) is str and state in {'RECORDED','UNAVAILABLE'})
    issues=capture['issues'];_require(type(issues) is list and len(issues)<=1)
    if state=='UNAVAILABLE':
        _require(capture['captured_at'] is None or _stamp(capture['captured_at']))
        _require(capture['expected_envelope'] is None and capture['expected_bindings_sha256'] is None and len(issues)==1)
        issue=issues[0]
        _require(type(issue) is dict and len(issue)==2 and set(issue)=={'code','input_index'})
        code,index=issue['code'],issue['input_index']
        _require(type(code) is str and code in ISSUE_CODES)
        if code=='CAPTURE_ROW_UNAVAILABLE':
            _require(type(index) is int and 0 <= index < len(selected['bindings']))
        else: _require(index is None)
        return state,[{'code':code,'input_index':index}],None,None
    _require(_stamp(capture['captured_at']) and issues==[])
    envelope=capture['expected_envelope']
    comparison=compare_execution_input_bindings(envelope,envelope)
    _require(comparison['status']=='MATCH' and type(capture['expected_bindings_sha256']) is str
             and capture['expected_bindings_sha256']==comparison['expected_bindings_sha256'])
    # Selected request omits manifest pins; UNKNOWN is expected only for their absence.
    _require(compare_execution_input_bindings(selected,envelope)['status']=='UNKNOWN')
    return state,[],comparison['expected_binding_count'],comparison['expected_bindings_sha256']


def project_job_execution_binding_capture(job, job_id):
    """Bounded selected metadata only. Malformed Job wins over absent capture."""
    valid_literal=_text(job_id)
    result=dict(schema_version=1,extension='greenblue.stored-execution-input-binding.rfc1',
                approval_status='INTERNAL_REVIEW',scope='STORED_SUBMISSION_BINDING_ONLY',status='INVALID',
                request_job_sha256=hashlib.sha256(job_id.encode('utf-8')).hexdigest() if valid_literal else None,
                request_binding_count=None,capture_binding_count=None,manifest_pin_count=None,
                expected_bindings_sha256=None,stored_binding_integrity_match=False,
                issues=[{'code':'STORED_JOB_INVALID','input_index':None}],
                current_files_revalidated=False,executor_bindings_compared=False,
                **{key:False for key in _FALSE})
    try:
        _require(valid_literal)
        selected=_selected_request(job,job_id)
    except (KeyError,TypeError,ValueError,OverflowError): return result
    result['request_binding_count']=len(selected['bindings'])
    if 'execution_input_binding_capture' not in job:
        result.update(status='LEGACY',issues=[{'code':'LEGACY_CAPTURE_NOT_RECORDED','input_index':None}])
        return result
    try:
        state,issues,count,digest=_capture(job['execution_input_binding_capture'],selected)
        result.update(status=state,issues=issues,capture_binding_count=count,manifest_pin_count=count,
                      expected_bindings_sha256=digest,stored_binding_integrity_match=state=='RECORDED')
    except (KeyError,TypeError,ValueError,OverflowError):
        result['issues']=[{'code':'STORED_CAPTURE_INVALID','input_index':None}]
    return result
