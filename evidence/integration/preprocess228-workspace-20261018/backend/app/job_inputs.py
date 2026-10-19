"""불변 Dataset 참조의 읽기 전용 점검. Job 실행·기관 권한·과학 승인을 부여하지 않는다."""
import copy
import json
import sqlite3
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .dataset_registry import resolve_version, version_key
from .sdss_results import local_asset


@lru_cache(maxsize=1)
def _ref_validator():
    path=Path(__file__).resolve().parents[2]/'contracts/upstream/GMAIS-v0.2/schemas/job-request.schema.json'
    schema=json.loads(path.read_text(encoding='utf-8'))
    return Draft202012Validator(schema['properties']['input_refs']['items'])


def _resolve_job_inputs(store, input_refs, capture_rows=None):
    """모든 참조를 점검하며 제한자료의 경로/URI/manifest와 내부 예외를 반환하지 않는다."""
    response={'schema_version':1,'scope':'INPUT_INTEGRITY_ONLY','status':'BLOCKED',
              'input_integrity_verified':False,'resolved':[],'blockers':[],
              'ready_for_execution':False,'scientific_approval':False,
              'network_requests':0,'source_files_written':0}
    if not isinstance(input_refs,list) or not input_refs:
        response['blockers'].append({'input_index':None,'code':'INPUT_REFS_REQUIRED'})
        return response
    refs=copy.deepcopy(input_refs)
    valid=[];identities={}
    for index,ref in enumerate(refs):
        entry={'input_index':index,'integrity_verified':False,'authorization_verified':False,
               'status':'BLOCKED','blocker_codes':[]}
        response['resolved'].append(entry)
        if not _ref_validator().is_valid(ref):
            entry['blocker_codes'].append('INPUT_REF_SCHEMA_MISMATCH')
            continue
        entry.update({key:ref[key] for key in ('id','version','sha256')})
        try:
            version_key(ref['id'],ref['version'])
        except ValueError:
            entry['blocker_codes'].append('INPUT_REF_NOT_PINNED')
            continue
        # 같은 Dataset의 여러 고정 연차/버전은 정상 비교 입력이다.
        identities.setdefault((ref['id'],ref['version']),set()).add(ref['sha256'])
        valid.append(index)
    for index in valid:
        ref=refs[index];entry=response['resolved'][index]
        conflicting=len(identities[(ref['id'],ref['version'])])>1
        if conflicting:
            entry['blocker_codes'].append('INPUT_REF_CONFLICT')
        try:
            record=resolve_version(store,ref['id'],ref['version'],ref['sha256'])
        except KeyError as error:
            code='DATASET_VERSION_NOT_FOUND' if error.args==(version_key(ref['id'],ref['version']),) else 'DATASET_RECORD_CORRUPT'
            entry['blocker_codes'].append(code)
            continue
        except sqlite3.Error:
            entry['blocker_codes'].append('DATASET_REGISTRY_UNAVAILABLE')
            continue
        except (ValueError,TypeError,OSError):
            entry['blocker_codes'].append('INPUT_INTEGRITY_FAILED')
            continue
        manifest=record['manifest']
        uri_matches=True
        if 'uri' in ref:
            try:
                # 요청 URI가 등록 자산을 대체하지 않으며 네트워크를 사용하지 않는다.
                uri_matches=local_asset(store.root,ref['uri'])==local_asset(store.root,manifest['artifact_uri'])
            except (ValueError,TypeError,OSError):
                uri_matches=False
            if not uri_matches:
                entry['blocker_codes'].append('INPUT_URI_MISMATCH')
        entry['integrity_verified']=uri_matches and not conflicting
        entry['quality_status']=manifest['quality_status']
        entry['access_class']=manifest['access_class']
        if manifest['quality_status']=='REJECTED':
            entry['blocker_codes'].append('INPUT_QUALITY_REJECTED')
        elif manifest['quality_status']!='VALIDATED':
            entry['blocker_codes'].append('INPUT_QUALITY_NOT_VALIDATED')
        if manifest['access_class']!='PUBLIC':
            entry['blocker_codes'].append('INPUT_ACL_NOT_IMPLEMENTED')
        if not entry['blocker_codes']:
            entry['status']='VERIFIED'
        if capture_rows is not None:
            try:
                selected = {key: ref[key] for key in ('id', 'version', 'sha256')}
                selected.update(input_index=index, integrity_verified=entry['integrity_verified'],
                                manifest_sha256=record['manifest_sha256'])
                if 'role' in ref:
                    selected['role'] = ref['role']
                capture_rows.append(selected)
            except Exception:
                # Optional metadata failure must not alter legacy resolution or catch process exits.
                capture_rows.append({'input_index': index})
    for entry in response['resolved']:
        response['blockers'].extend({'input_index':entry['input_index'],'code':code} for code in entry['blocker_codes'])
    response['input_integrity_verified']=all(entry['integrity_verified'] for entry in response['resolved'])
    if not response['blockers']:
        response['status']='INTEGRITY_VERIFIED'
    return response


def resolve_job_inputs(store, input_refs):
    """기존 호출/반환 계약. 선택 capture를 수행하지 않는다."""
    return _resolve_job_inputs(store, input_refs)


def _capture_failure():
    # Import/build failures are isolated even when the optional module cannot load.
    result = dict(schema_version=1, extension='greenblue.execution-input-binding-capture.rfc1',
                  approval_status='INTERNAL_REVIEW', scope='SUBMISSION_EXPECTED_BINDING_METADATA',
                  captured_at=None, status='UNAVAILABLE', expected_envelope=None,
                  expected_bindings_sha256=None,
                  issues=[{'code': 'CAPTURE_BOUNDARY_FAILURE', 'input_index': None}],
                  pin_source='SAME_RESOLVE_VERSION_RETURN', additional_registry_queries=0,
                  additional_artifact_reads=0, additional_database_writes=0)
    for key in ('execution_authorized', 'ready_for_execution', 'ready_for_training',
                'scientific_approval', 'acl_verified', 'registry_verified', 'training_authorized',
                'pixels_verified', 'toc_tou_protected', 'executor_connected',
                'artifact_bytes_verified', 'manifest_bytes_verified'):
        result[key] = False
    return result


def resolve_job_inputs_with_capture(store, input_refs, *, job_id, agent_id, trace_id, captured_at):
    """같은 resolve pass의 추가 pin snapshot만 캡처. 기존 pass 예외는 그대로 전파한다."""
    rows = [] if type(input_refs) is list and 1 <= len(input_refs) <= 64 else None
    resolution = _resolve_job_inputs(store, input_refs, rows)
    # Never wrap legacy resolution in the optional diagnostic exception boundary.
    try:
        from .execution_binding_capture import build_submission_binding_capture
        if rows is None or len(rows) != len(input_refs):
            rows = None
        capture = build_submission_binding_capture(rows, job_id=job_id, agent_id=agent_id,
                                                   trace_id=trace_id, captured_at=captured_at)
        return resolution, capture
    except Exception:
        return resolution, _capture_failure()
