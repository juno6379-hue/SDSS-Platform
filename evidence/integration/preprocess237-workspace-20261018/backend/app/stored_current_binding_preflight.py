"""저장 pin 대 현재 직접입력 resolver의 비실행 preflight. 실행/전이계보 승인이 아니다."""
import hashlib
import sqlite3
from datetime import datetime, timezone
from .execution_input_binding import _FALSE, _text
from .job_execution_binding_capture import project_job_execution_binding_capture, _selected_request, _capture
from .job_snapshot import _project_snapshot, _CODES
from .job_inputs import resolve_job_inputs_with_capture
from .stored_job_binding_handoff import compare_stored_job_binding_handoff

_RESOURCE=(sqlite3.Error,UnicodeError,OSError,TypeError,ValueError,OverflowError,RecursionError,MemoryError)
_RESOLUTION_KEYS={'schema_version','scope','status','input_integrity_verified','resolved','blockers',
                  'ready_for_execution','scientific_approval','network_requests','source_files_written'}


def _require(value):
    if not value:raise ValueError('Current input metadata invalid.')


def _resolution_snapshot(raw,refs,stamp):
    _require(type(raw) is dict and len(raw)==10 and set(raw)==_RESOLUTION_KEYS)
    for key in ('ready_for_execution','scientific_approval'):_require(raw[key] is False)
    for key in ('network_requests','source_files_written'):_require(type(raw[key]) is int and raw[key]==0)
    _require(type(raw['schema_version']) is int and raw['schema_version']==1 and type(raw['scope']) is str and len(raw['scope'])<=64 and raw['scope']=='INPUT_INTEGRITY_ONLY')
    _require(type(raw['status']) is str and len(raw['status'])<=64 and raw['status'] in {'BLOCKED','INTEGRITY_VERIFIED'} and type(raw['input_integrity_verified']) is bool)
    entries,issues=raw['resolved'],raw['blockers']
    _require(type(entries) is list and len(entries)==len(refs) and type(issues) is list and len(issues)<=64*len(_CODES))
    for entry in entries:
        required={'input_index','integrity_verified','authorization_verified','status','blocker_codes','id','version','sha256'}
        _require(type(entry) is dict and 8 <= len(entry) <= 10 and required<=set(entry) and not set(entry)-(required|{'quality_status','access_class'}))
        _require(entry['authorization_verified'] is False)
        codes=entry.get('blocker_codes')
        _require(type(codes) is list and len(codes)<=len(_CODES))
        _require(all(type(code) is str and 1<=len(code)<=64 and code in _CODES for code in codes))
        for key in ('id','version','sha256'):
            _require(key not in entry or _text(entry[key]))
        _require(_text(entry.get('status')) and entry['status'] in {'BLOCKED','VERIFIED'})
        for key in ('quality_status','access_class'):
            _require(key not in entry or _text(entry[key]))
    for issue in issues:
        _require(type(issue) is dict and len(issue)==2 and set(issue)=={'input_index','code'})
        _require(type(issue['input_index']) is int and 0<=issue['input_index']<len(refs)
                 and type(issue['code']) is str and 1<=len(issue['code'])<=64 and issue['code'] in _CODES)
    wrapped=dict(raw)
    wrapped.update(extension='greenblue.job-input-resolution.rfc1',approval_status='INTERNAL_REVIEW',
                   evaluated_at=stamp,evaluation_scope='SUBMISSION_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION')
    return _project_snapshot(wrapped,refs)


def inspect_stored_current_binding_preflight(store,requested_job_id):
    valid=_text(requested_job_id)
    result=dict(schema_version=1,scope='STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY',status='BLOCKED',
                store_status='INVALID_REQUEST',store_read_attempted=False,store_read_observed=False,store_get_calls=0,
                request_job_sha256=hashlib.sha256(requested_job_id.encode('utf-8')).hexdigest() if valid else None,
                stored_capture_status=None,resolver_pass_calls=0,current_resolution_status='NOT_RUN',current_capture_status='NOT_RUN',
                current_input_count=None,current_integrity_verified_count=None,current_quality_public_observed_count=None,
                current_quality_public_diagnostics_passed=None,current_blocker_count=None,current_blockers=[],
                binding_comparison=None,issues=[{'code':'INVALID_JOB_ID'}],executor_bindings_compared=False,
                stored_job_origin_verified=False,transitive_lineage_verified=False,
                **{key:False for key in _FALSE})
    if not valid:return result
    result.update(store_read_attempted=True,store_get_calls=1)
    try:job=store.get('gmais_jobs',requested_job_id)
    except KeyError as error:
        missing=len(error.args)==1 and type(error.args[0]) is str and len(error.args[0])==len(requested_job_id) and error.args[0]==requested_job_id
        result.update(store_status='NOT_FOUND' if missing else 'RESOURCE_UNAVAILABLE',issues=[{'code':'JOB_NOT_FOUND' if missing else 'RESOURCE_UNAVAILABLE'}])
        return result
    except _RESOURCE:
        result.update(store_status='RESOURCE_UNAVAILABLE',issues=[{'code':'RESOURCE_UNAVAILABLE'}]);return result
    result.update(store_status='OBSERVED',store_read_observed=True,issues=[])
    stored=project_job_execution_binding_capture(job,requested_job_id)
    result['stored_capture_status']=stored['status']
    if stored['status']=='INVALID':
        result['issues']=[{'code':stored['issues'][0]['code']}];return result
    if stored['status'] in {'LEGACY','UNAVAILABLE'}:
        result.update(status='UNKNOWN',issues=[{'code':'LEGACY_EXPECTED_BINDING_NOT_RECORDED' if stored['status']=='LEGACY' else 'EXPECTED_BINDING_CAPTURE_UNAVAILABLE'}]);return result
    selected=_selected_request(job,requested_job_id)
    refs=job['request']['input_refs']
    if any('uri' in ref and not _text(ref['uri']) for ref in refs):
        result['issues']=[{'code':'STORED_URI_UNSUPPORTED'}];return result
    # All selected scalars/URI were bounded before copying or entering the legacy I/O pass.
    refs=[dict(ref) for ref in refs]
    stamp=datetime.now(timezone.utc).isoformat()
    result['resolver_pass_calls']=1
    try:
        pair=resolve_job_inputs_with_capture(store,refs,job_id=selected['job_id'],agent_id=selected['agent_id'],
                                            trace_id=selected['trace_id'],captured_at=stamp)
    except _RESOURCE:
        result.update(current_resolution_status='RESOURCE_UNAVAILABLE',issues=[{'code':'CURRENT_RESOLVER_RESOURCE_UNAVAILABLE'}]);return result
    try:
        _require(type(pair) is tuple and len(pair)==2)
        resolution=_resolution_snapshot(pair[0],refs,stamp)
    except (KeyError,TypeError,ValueError,OverflowError):
        result.update(current_resolution_status='INVALID',issues=[{'code':'CURRENT_RESOLUTION_INVALID'}]);return result
    entries=resolution['resolved']
    observed=[entry for entry in entries if 'quality_status' in entry]
    result.update(current_resolution_status=resolution['status'],current_input_count=len(entries),
                  current_integrity_verified_count=sum(entry['integrity_verified'] for entry in entries),
                  current_quality_public_observed_count=len(observed),
                  current_quality_public_diagnostics_passed=len(observed)==len(entries) and all(e['quality_status']=='VALIDATED' and e['access_class']=='PUBLIC' for e in observed),
                  current_blocker_count=len(resolution['blockers']),
                  current_blockers=[{'code':issue['code'],'input_index':issue['input_index']} for issue in resolution['blockers']])
    try:state,_,_,_=_capture(pair[1],selected)
    except (KeyError,TypeError,ValueError,OverflowError):
        result.update(current_capture_status='INVALID',issues=[{'code':'CURRENT_CAPTURE_INVALID'}]);return result
    result['current_capture_status']=state
    if state!='RECORDED':
        result['issues']=[{'code':'CURRENT_CAPTURE_UNAVAILABLE'}];return result
    result['binding_comparison']=compare_stored_job_binding_handoff(job,requested_job_id,pair[1]['expected_envelope'])
    if resolution['status']=='BLOCKED':result['issues']=[{'code':'CURRENT_INPUT_DIAGNOSTICS_BLOCKED'}]
    elif result['binding_comparison']['status']!='MATCH':result['issues']=[{'code':'CURRENT_BINDINGS_MISMATCH'}]
    else:result.update(status='MATCH',issues=[])
    return result
