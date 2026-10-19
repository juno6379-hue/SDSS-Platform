"""Configured Store의 Job 단일조회와 순수 handoff 대조를 연결한다. 실행 승인이 아니다."""
import hashlib
import sqlite3
from .execution_input_binding import _FALSE, _text
from .stored_job_binding_handoff import compare_stored_job_binding_handoff


def inspect_stored_job_binding_handoff(store, requested_job_id, supplied_envelope):
    """No caller Job/expected. Store.get errors only are converted; comparison bugs propagate."""
    valid=_text(requested_job_id)
    result=dict(schema_version=1,scope='CONFIGURED_STORE_BINDING_HANDOFF_ONLY',
                store_status='INVALID_REQUEST',request_job_sha256=hashlib.sha256(requested_job_id.encode('utf-8')).hexdigest() if valid else None,
                store_read_attempted=False,store_read_observed=False,store_get_calls=0,comparison=None,
                issues=[{'code':'INVALID_JOB_ID'}],current_files_revalidated=False,
                executor_bindings_compared=False,stored_job_origin_verified=False,
                **{key:False for key in _FALSE})
    if not valid:return result
    result.update(store_read_attempted=True,store_get_calls=1)
    try:
        job=store.get('gmais_jobs',requested_job_id)
    except KeyError as error:
        # Guard arity/type/length before equality, including malicious nested/custom keys.
        missing=(len(error.args)==1 and type(error.args[0]) is str
                 and len(error.args[0])==len(requested_job_id) and error.args[0]==requested_job_id)
        result.update(store_status='NOT_FOUND' if missing else 'RESOURCE_UNAVAILABLE',
                      issues=[{'code':'JOB_NOT_FOUND' if missing else 'RESOURCE_UNAVAILABLE'}])
        return result
    except (sqlite3.Error,UnicodeError,OSError,TypeError,ValueError,OverflowError,RecursionError,MemoryError):
        # json.JSONDecodeError is ValueError; no raw exception is exposed.
        result.update(store_status='RESOURCE_UNAVAILABLE',issues=[{'code':'RESOURCE_UNAVAILABLE'}])
        return result
    result.update(store_status='OBSERVED',store_read_observed=True,issues=[])
    result['comparison']=compare_stored_job_binding_handoff(job,requested_job_id,supplied_envelope)
    return result
