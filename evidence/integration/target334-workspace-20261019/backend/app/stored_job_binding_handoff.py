"""검증된 저장 expected binding과 caller supplied 선언의 순수 대조. 실행 승인이 아니다."""
from .execution_input_binding import compare_execution_input_bindings, _FALSE
from .job_execution_binding_capture import project_job_execution_binding_capture, _selected_request


def compare_stored_job_binding_handoff(job, requested_job_id, supplied_envelope):
    """Caller cannot inject expected; no Registry backfill, IO, or real executor capture."""
    stored=project_job_execution_binding_capture(job,requested_job_id)
    supplied=compare_execution_input_bindings(supplied_envelope,supplied_envelope)
    valid_supplied=supplied['status'] in {'MATCH','UNKNOWN'}
    result=dict(schema_version=1,scope='STORED_EXPECTED_TO_SUPPLIED_DECLARATIONS_ONLY',status='BLOCKED',
                stored_capture_status=stored['status'],request_job_sha256=stored['request_job_sha256'],
                expected_bindings_sha256=stored['expected_bindings_sha256'],
                supplied_bindings_sha256=supplied['expected_bindings_sha256'] if valid_supplied else None,
                request_binding_count=stored['request_binding_count'],
                stored_expected_binding_count=stored['capture_binding_count'],
                supplied_binding_count=supplied['expected_binding_count'] if valid_supplied else None,
                declarations_match=False,issues=[],
                current_files_revalidated=False,executor_bindings_compared=False,stored_job_origin_verified=False,
                network_requests=0,source_files_read=0,source_files_written=0,database_calls=0,
                registry_calls=0,resolver_calls=0,executor_calls=0,
                **{key:False for key in _FALSE})
    if not valid_supplied:
        # Self-compare repeats validation on both sides; preserve only one bounded set.
        result['issues'].extend({'side':'supplied','input_index':issue['input_index'],'code':issue['code']}
                                for issue in supplied['issues'] if issue['side']=='expected')
    if stored['status']=='INVALID':
        result['issues'].append({'side':'stored','input_index':None,'code':stored['issues'][0]['code']})
    if result['issues']:
        return result
    if stored['status']=='RECORDED':
        expected=job['execution_input_binding_capture']['expected_envelope']
        compared=compare_execution_input_bindings(expected,supplied_envelope)
        result.update(status=compared['status'],declarations_match=compared['status']=='MATCH',issues=compared['issues'])
        return result
    # Legacy/unavailable has no stored manifest pin. Still reject visible request-link drift.
    selected=_selected_request(job,requested_job_id)
    compared=compare_execution_input_bindings(selected,supplied_envelope)
    if compared['status']=='BLOCKED':
        result['issues']=compared['issues']
        return result
    result.update(status='UNKNOWN',issues=[{'side':'stored','input_index':None,
        'code':'LEGACY_EXPECTED_BINDING_NOT_RECORDED' if stored['status']=='LEGACY'
               else 'EXPECTED_BINDING_CAPTURE_UNAVAILABLE'}])
    return result
