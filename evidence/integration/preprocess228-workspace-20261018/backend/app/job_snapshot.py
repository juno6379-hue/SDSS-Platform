"""제출 시 저장한 입력 진단의 안전한 읽기 투영. 현재 파일 검증이나 실행 승인이 아니다."""
from datetime import datetime
import re


_CODES = frozenset({
    'INPUT_REFS_REQUIRED', 'INPUT_REF_SCHEMA_MISMATCH', 'INPUT_REF_NOT_PINNED',
    'INPUT_REF_CONFLICT', 'DATASET_VERSION_NOT_FOUND', 'DATASET_RECORD_CORRUPT',
    'DATASET_REGISTRY_UNAVAILABLE', 'INPUT_INTEGRITY_FAILED', 'INPUT_URI_MISMATCH',
    'INPUT_QUALITY_REJECTED', 'INPUT_QUALITY_NOT_VALIDATED', 'INPUT_ACL_NOT_IMPLEMENTED',
})
_QUALITY = {'RAW', 'STAGED', 'STANDARDIZED', 'VALIDATED', 'REJECTED'}
_ACCESS = {'PUBLIC', 'RESTRICTED', 'CONFIDENTIAL'}


def _text(value):
    return isinstance(value, str) and bool(value)


def _require(condition):
    if not condition:
        raise ValueError('저장 snapshot 형식 또는 신원이 올바르지 않습니다.')


def _identity(job, job_id):
    status, request = job['status'], job['request']
    _require(isinstance(status, dict) and isinstance(request, dict))
    _require(job['id'] == job_id == job['job_id'] == status['job_id'])
    _require(_text(job['agent_id']) and job['agent_id'] == status['agent_id'] == request['agent_id'])
    context = request['execution_context']
    _require(isinstance(context, dict) and _text(status['trace_id']) and status['trace_id'] == context['trace_id'])
    refs = request['input_refs']
    _require(isinstance(refs, list) and bool(refs))
    for ref in refs:
        _require(isinstance(ref, dict) and _text(ref.get('id')) and _text(ref.get('version'))
                 and isinstance(ref.get('sha256'), str) and re.fullmatch('[a-f0-9]{64}', ref['sha256']) is not None)
        _require(not (set(ref) - {'id', 'version', 'sha256', 'uri', 'role'}))
        _require('uri' not in ref or isinstance(ref['uri'], str))
        _require('role' not in ref or _text(ref['role']))
    return status['trace_id'], refs


def _project_snapshot(stored, refs):
    _require(isinstance(stored, dict))
    fixed = {
        'extension': 'greenblue.job-input-resolution.rfc1', 'approval_status': 'INTERNAL_REVIEW',
        'schema_version': 1, 'scope': 'INPUT_INTEGRITY_ONLY',
        'evaluation_scope': 'SUBMISSION_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION',
    }
    for key, expected in fixed.items():
        _require(type(stored.get(key)) is type(expected) and stored[key] == expected)
    assessed = stored['evaluated_at']
    _require(isinstance(assessed, str))
    parsed = datetime.fromisoformat(assessed.replace('Z', '+00:00'))
    _require(parsed.tzinfo is not None)
    _require(stored.get('status') in ('BLOCKED', 'INTEGRITY_VERIFIED'))
    for key in ('input_integrity_verified', 'ready_for_execution', 'scientific_approval'):
        _require(type(stored.get(key)) is bool)
    for key in ('network_requests', 'source_files_written'):
        _require(type(stored.get(key)) is int and stored[key] == 0)
    entries, issues = stored.get('resolved'), stored.get('blockers')
    _require(isinstance(entries, list) and len(entries) == len(refs) and isinstance(issues, list))
    projected = []
    expected_issues = []
    identities = {}
    for ref in refs:
        identities.setdefault((ref['id'], ref['version']), set()).add(ref['sha256'])
    for index, entry in enumerate(entries):
        _require(isinstance(entry, dict) and type(entry.get('input_index')) is int and entry['input_index'] == index)
        for key in ('id', 'version', 'sha256'):
            _require(entry.get(key) == refs[index][key])
        _require(type(entry.get('integrity_verified')) is bool and type(entry.get('authorization_verified')) is bool)
        codes = entry.get('blocker_codes')
        _require(isinstance(codes, list) and all(isinstance(code, str) and code in _CODES for code in codes))
        _require(len(codes) == len(set(codes)))
        _require(entry.get('status') in ('BLOCKED', 'VERIFIED'))
        _require((entry['status'] == 'VERIFIED') == (not codes and entry['integrity_verified']))
        _require(bool(codes) or entry['integrity_verified'])
        _require(('quality_status' in entry) == ('access_class' in entry))
        _require(not entry['integrity_verified'] or 'quality_status' in entry)
        ref = refs[index]
        pinned = bool(ref['id'].strip() and ref['version'].strip()) and ref['version'].strip().lower() not in {'latest', 'current'}
        conflicting = len(identities[(ref['id'], ref['version'])]) > 1
        _require(('INPUT_REF_NOT_PINNED' in codes) == (not pinned))
        if pinned:
            _require(('INPUT_REF_CONFLICT' in codes) == conflicting)
        if not pinned:
            _require(codes == ['INPUT_REF_NOT_PINNED'] and 'quality_status' not in entry)
        elif 'quality_status' in entry:
            _require(set(codes) <= {'INPUT_REF_CONFLICT', 'INPUT_URI_MISMATCH', 'INPUT_ACL_NOT_IMPLEMENTED',
                                    'INPUT_QUALITY_NOT_VALIDATED', 'INPUT_QUALITY_REJECTED'})
            _require(entry['integrity_verified'] == (not conflicting and 'INPUT_URI_MISMATCH' not in codes))
            _require('INPUT_URI_MISMATCH' not in codes or 'uri' in ref)
        else:
            failures = {'DATASET_VERSION_NOT_FOUND', 'DATASET_RECORD_CORRUPT', 'DATASET_REGISTRY_UNAVAILABLE', 'INPUT_INTEGRITY_FAILED'}
            _require(len(set(codes) & failures) == 1 and set(codes) <= failures | {'INPUT_REF_CONFLICT'})
        output = {key: entry[key] for key in ('input_index', 'id', 'version', 'sha256', 'integrity_verified', 'status')}
        output.update(authorization_verified=False, blocker_codes=list(codes))
        if 'quality_status' in entry:
            _require(entry['quality_status'] in _QUALITY)
            output['quality_status'] = entry['quality_status']
        if 'access_class' in entry:
            _require(entry['access_class'] in _ACCESS)
            output['access_class'] = entry['access_class']
            # 품질·ACL 차단이 빠진 모순된 기록을 검증 성공으로 재표시하지 않는다.
            _require(('INPUT_ACL_NOT_IMPLEMENTED' in codes) == (entry['access_class'] != 'PUBLIC'))
            _require(('INPUT_QUALITY_REJECTED' in codes) == (entry['quality_status'] == 'REJECTED'))
            _require(('INPUT_QUALITY_NOT_VALIDATED' in codes) == (entry['quality_status'] not in {'VALIDATED', 'REJECTED'}))
        projected.append(output)
        expected_issues.extend({'input_index': index, 'code': code} for code in codes)
    clean_issues = []
    for issue in issues:
        _require(isinstance(issue, dict) and type(issue.get('input_index')) is int
                 and 0 <= issue['input_index'] < len(refs) and issue.get('code') in _CODES)
        clean_issues.append({'input_index': issue['input_index'], 'code': issue['code']})
    _require(clean_issues == expected_issues)
    _require(stored['input_integrity_verified'] == all(entry['integrity_verified'] for entry in projected))
    _require((stored['status'] == 'INTEGRITY_VERIFIED') == (not clean_issues))
    return dict(fixed, evaluated_at=assessed, status=stored['status'],
        input_integrity_verified=stored['input_integrity_verified'], resolved=projected, blockers=clean_issues,
        ready_for_execution=False, scientific_approval=False, network_requests=0, source_files_written=0)


def project_job_input_snapshot(job, job_id):
    """필수 형식·저장 신원을 검증하며 추가 필드는 중첩 단계마다 제거한다."""
    response = {'extension': 'greenblue.job-input-snapshot.rfc1', 'approval_status': 'INTERNAL_REVIEW',
        'job_id': job_id, 'trace_id': 'unknown', 'available': False, 'reason': 'SNAPSHOT_INVALID',
        'snapshot': None, 'current_files_revalidated': False, 'execution_authorized': False,
        'scientific_approval': False}
    try:
        _require(isinstance(job, dict))
        trace, refs = _identity(job, job_id)
        response['trace_id'] = trace
        if 'input_resolution' not in job:
            response['reason'] = 'LEGACY_SNAPSHOT_NOT_RECORDED'
            return response
        snapshot = _project_snapshot(job['input_resolution'], refs)
        response.update(available=True, reason='RECORDED_SNAPSHOT', snapshot=snapshot)
    except (KeyError, TypeError, ValueError, OverflowError):
        # 원본 예외·요청·URI·경로를 응답에 담지 않는다.
        pass
    return response
