"""제출 시 같은 resolve pass의 메타 pin을 저장하는 내부 capture. 실행 승인이 아니다."""
from datetime import datetime
from .execution_input_binding import compare_execution_input_bindings, _FALSE, _text


def _stamp(value):
    if not _text(value):
        return False
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False


def unavailable_capture(captured_at, code='CAPTURE_UNAVAILABLE', input_index=None):
    return dict(schema_version=1, extension='greenblue.execution-input-binding-capture.rfc1',
                approval_status='INTERNAL_REVIEW', scope='SUBMISSION_EXPECTED_BINDING_METADATA',
                captured_at=captured_at if _stamp(captured_at) else None, status='UNAVAILABLE',
                expected_envelope=None, expected_bindings_sha256=None,
                issues=[{'code': code, 'input_index': input_index}],
                pin_source='SAME_RESOLVE_VERSION_RETURN', additional_registry_queries=0,
                additional_artifact_reads=0, additional_database_writes=0,
                **{key: False for key in _FALSE})


def build_submission_binding_capture(rows, *, job_id, agent_id, trace_id, captured_at):
    """Pure builder; rows are selected snapshots from the same resolver pass, not Registry reads."""
    if not _stamp(captured_at):
        return unavailable_capture(captured_at, 'CAPTURE_TIME_INVALID')
    if type(rows) is not list or not 1 <= len(rows) <= 64:
        return unavailable_capture(captured_at, 'CAPTURE_ROWS_UNAVAILABLE')
    bindings = []
    for index, row in enumerate(rows):
        required = {'input_index', 'id', 'version', 'sha256', 'manifest_sha256', 'integrity_verified'}
        if (type(row) is not dict or not 6 <= len(row) <= 7 or not required <= set(row)
                or set(row) - (required | {'role'}) or row['integrity_verified'] is not True):
            return unavailable_capture(captured_at, 'CAPTURE_ROW_UNAVAILABLE', index)
        # Only selected scalar claims are copied; no URI or manifest object survives.
        binding = {key: row[key] for key in ('input_index', 'id', 'version', 'sha256', 'manifest_sha256')}
        if 'role' in row:
            binding['role'] = row['role']
        bindings.append(binding)
    envelope = {'job_id': job_id, 'agent_id': agent_id, 'trace_id': trace_id, 'bindings': bindings}
    comparison = compare_execution_input_bindings(envelope, envelope)
    if comparison['status'] != 'MATCH':
        return unavailable_capture(captured_at, 'CAPTURE_BINDING_INVALID')
    capture = unavailable_capture(captured_at)
    capture.update(status='RECORDED', expected_envelope=envelope,
                   expected_bindings_sha256=comparison['expected_bindings_sha256'], issues=[])
    return capture
