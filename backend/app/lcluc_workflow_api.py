"""Explicit local LCLUC dispatch and authenticated historical artifact reads.

Authentication is inherited from the hosting FastAPI application. No main import,
Store construction, generic Job execution, retry, or Result publication occurs.
"""
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .lcluc_workflow import (
    KIND, WorkflowError, _canonical, _keys, _request, _sha,
    execute_lcluc_workflow, strict_request_json,
)

MAX_BODY = 16384
MAX_ASSET = 64 * 1024**2
MAX_TOTAL = 256 * 1024**2
MAX_REPORT = 8 * 1024**2
HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
MIME = {'.json': 'application/json', '.geojson': 'application/geo+json',
        '.csv': 'text/csv', '.tif': 'image/tiff'}
ISSUES = frozenset(('FILE_LIMIT_OR_INTEGRITY', 'OUTPUT_NAMESPACE_UNAVAILABLE', 'MODEL_IDENTITY_MISMATCH',
    'MODEL_NOT_DEPLOYED_OR_EVALUATED', 'MODEL_EVALUATION_MISMATCH', 'MODEL_VERSION_NOT_BOUND',
    'CHECKPOINT_MISMATCH', 'TRAINING_REPORT_MISMATCH', 'MODEL_ARCHITECTURE_UNSUPPORTED',
    'SYNTHETIC_MODEL_BLOCKED', 'NORMALIZATION_MODE_UNSUPPORTED', 'MODEL_BAND_SIGNATURE_INVALID',
    'MODEL_CLASSES_INVALID', 'MODEL_PATCH_LIMIT', 'MODEL_METADATA_LIMIT', 'DATASET_QUALITY_OR_ACCESS_BLOCKED',
    'DATASET_YEAR_MISMATCH', 'INPUT_INTEGRITY_MISMATCH', 'QUALITY_REPORT_MISMATCH', 'RASTER_LIMIT_OR_BANDS',
    'RASTER_BAND_SIGNATURE_MISMATCH', 'RASTER_READ_BUDGET_EXCEEDED', 'ADMISSION_GATE_BLOCKED',
    'ADMISSION_CHANGED_AFTER_CLAIM', 'RUNNER_REPORT_MISMATCH', 'OUTPUT_PATH_CHANGED', 'OUTPUT_LIMIT',
    'LOCAL_EXECUTION_FAILED'))
BASE = frozenset(('schema_version', 'scope', 'id', 'trace_id', 'request_sha256', 'request_snapshot',
    'status', 'created_at', 'issue', 'artifacts', 'scientific_accuracy_validated', 'standard_gmais_result'))


class ApiIssue(Exception):
    def __init__(self, code):
        self.code = code


def _need(value):
    if not value:
        raise ApiIssue('RESOURCE_UNAVAILABLE')


def _error(code):
    messages = {
        'INVALID_REQUEST': (400, 'LCLUC Workflow 요청 형식이 올바르지 않습니다.'),
        'REQUEST_TOO_LARGE': (413, 'LCLUC Workflow 요청 크기가 제한을 초과했습니다.'),
        'NOT_FOUND': (404, 'LCLUC Workflow 또는 산출물이 없습니다.'),
        'IDEMPOTENCY_CONFLICT': (409, '같은 키에 다른 Workflow 요청을 사용할 수 없습니다.'),
        'WORKFLOW_NOT_SUCCEEDED': (409, '완료된 Workflow 산출물만 읽을 수 있습니다.'),
        'STORED_OUTPUT_CHANGED': (503, '저장된 Workflow 산출물을 검증할 수 없습니다.'),
        'RESOURCE_UNAVAILABLE': (503, 'LCLUC Workflow 처리를 완료할 수 없습니다.'),
    }
    status, message = messages[code]
    return JSONResponse({'error': {'code': code, 'message': message, 'retryable': False}},
                        status_code=status, headers=HEADERS)


def _namespace(root, identifier):
    path = root / 'results' / 'lcluc-workflows' / identifier
    _need(path.resolve() == path)
    return path


def _relative(value, identifier):
    _need(type(value) is str and len(value) <= 512)
    parts = value.replace('\\', '/').split('/')
    _need(len(parts) >= 4 and parts[:3] == ['results', 'lcluc-workflows', identifier]
          and all(p not in ('.', '..') and re.fullmatch('[A-Za-z0-9_.-]{1,128}', p) is not None for p in parts))
    _need(Path(parts[-1]).suffix in MIME)
    return '/'.join(parts)


def _record(value, identifier, root):
    _need(type(value) is dict and value.get('status') in ('RUNNING', 'FAILED', 'SUCCEEDED'))
    status = value['status']
    fields = BASE | ({'finished_at', 'report_path', 'admission_pins'} if status == 'SUCCEEDED'
                     else {'finished_at'} if status == 'FAILED' else set())
    _need(_keys(value, fields) and type(value['schema_version']) is int and value['schema_version'] == 1
          and value['scope'] == 'LOCAL_LCLUC_WORKFLOW_ONLY' and value['id'] == identifier
          and _sha(identifier) and _sha(value['request_sha256'])
          and value['scientific_accuracy_validated'] is False and value['standard_gmais_result'] is False)
    snapshot = value['request_snapshot']
    _need(_keys(snapshot, ('schema_version', 'capability', 'trace_id', 'model_ref', 'images')))
    try:
        clean, _ = _request({**snapshot, 'idempotency_key': 'historical-snapshot'})
    except Exception:
        raise ApiIssue('RESOURCE_UNAVAILABLE') from None
    _need(clean['trace_id'] == value['trace_id'])
    for key in ('created_at', 'finished_at'):
        if key in value:
            _need(type(value[key]) is str and 1 <= len(value[key]) <= 64
                  and re.fullmatch('[0-9T:+.Z-]+', value[key]) is not None)
            _need(datetime.fromisoformat(value[key].replace('Z', '+00:00')).tzinfo is not None)
    _need(value['issue'] in ISSUES if status == 'FAILED' else value['issue'] is None)
    artifacts = value['artifacts']
    _need(type(artifacts) is list and (1 <= len(artifacts) <= 128 if status == 'SUCCEEDED' else artifacts == []))
    seen = set()
    for item in artifacts:
        _need(_keys(item, ('path', 'sha256')) and _sha(item['sha256']))
        path = _relative(item['path'], identifier)
        _need(path not in seen)
        seen.add(path)
    if status == 'SUCCEEDED':
        _need(_relative(value['report_path'], identifier) == f'results/lcluc-workflows/{identifier}/timeseries.json'
              and _relative(value['report_path'], identifier) in seen)
        pins = value['admission_pins']
        _need(_keys(pins, ('model', *(str(i['year']) for i in snapshot['images'])))
              and all(_sha(v) for v in pins.values()))
    _namespace(root, identifier)
    # Detach the record returned by a custom getter; no mutable Store alias escapes.
    _need(len(_canonical(value).encode()) <= 256 * 1024)
    return json.loads(_canonical(value))


def _load(store, identifier):
    if not _sha(identifier):
        raise ApiIssue('INVALID_REQUEST')
    try:
        record = store.get(KIND, identifier)
    except KeyError:
        raise ApiIssue('NOT_FOUND') from None
    return _record(record, identifier, Path(store.root).resolve())


def _artifact(root, identifier, item, *, copy_bytes, maximum=MAX_ASSET):
    relative = _relative(item['path'], identifier)
    namespace = _namespace(root, identifier)
    lexical = root.joinpath(*relative.split('/'))
    try:
        path = lexical.resolve()
        _need(path == lexical and path.is_relative_to(namespace) and path.is_file() and not path.is_symlink())
        before = path.stat()
        _need(before.st_size <= maximum)
        digest, count, chunks = hashlib.sha256(), 0, []
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(min(1024**2, maximum-count+1)), b''):
                count += len(chunk)
                _need(count <= maximum)
                digest.update(chunk)
                if copy_bytes:
                    chunks.append(chunk)
        after = path.stat()
        _need(path.resolve() == lexical and _namespace(root, identifier) == namespace
              and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
              == (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
              and digest.hexdigest() == item['sha256'])
        return (b''.join(chunks) if copy_bytes else None), count, relative
    except Exception:
        raise ApiIssue('STORED_OUTPUT_CHANGED') from None


def _status(store, identifier):
    record = _load(store, identifier)
    total = 0
    if record['status'] == 'SUCCEEDED':
        for item in record['artifacts']:
            _, size, _ = _artifact(Path(store.root).resolve(), identifier, item, copy_bytes=False,
                                    maximum=min(MAX_ASSET, MAX_TOTAL-total))
            total += size
    return {**record, 'replayed': True}


def _report(store, identifier):
    record = _load(store, identifier)
    if record['status'] != 'SUCCEEDED':
        raise ApiIssue('WORKFLOW_NOT_SUCCEEDED')
    relative = _relative(record['report_path'], identifier)
    item = next(a for a in record['artifacts'] if _relative(a['path'], identifier) == relative)
    raw, _, _ = _artifact(Path(store.root).resolve(), identifier, item, copy_bytes=True, maximum=MAX_REPORT)
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result)
            result[key] = value
        return result
    def constant(_):
        raise ApiIssue('STORED_OUTPUT_CHANGED')
    def number(text):
        result = float(text)
        _need(math.isfinite(result))
        return result
    report = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)
    _need(type(report) is dict and type(report.get('years')) is list and all(type(y) is int for y in report['years'])
          and report['years'] == [i['year'] for i in record['request_snapshot']['images']]
          and report.get('checkpoint_sha256') == record['request_snapshot']['model_ref']['sha256']
          and _relative(report.get('report_path'), identifier) == relative)
    return raw


def _download(store, identifier, index):
    record = _load(store, identifier)
    if record['status'] != 'SUCCEEDED':
        raise ApiIssue('WORKFLOW_NOT_SUCCEEDED')
    if type(index) is not str or re.fullmatch('0|[1-9][0-9]{0,2}', index) is None or int(index) >= len(record['artifacts']):
        raise ApiIssue('NOT_FOUND')
    raw, _, relative = _artifact(Path(store.root).resolve(), identifier, record['artifacts'][int(index)], copy_bytes=True, maximum=MAX_ASSET)
    return raw, Path(relative).name, MIME[Path(relative).suffix]


def _post(store, value):
    request, digest = _request(value)
    identifier = hashlib.sha256(request['idempotency_key'].encode()).hexdigest()
    result = execute_lcluc_workflow(store, request)
    _need(type(result) is dict and type(result.get('replayed')) is bool)
    if result.get('status') == 'BLOCKED':
        _need(_keys(result, ('schema_version', 'scope', 'status', 'trace_id', 'id', 'issue', 'replayed',
                            'scientific_accuracy_validated', 'standard_gmais_result'))
              and type(result['schema_version']) is int and result['schema_version'] == 1
              and result['scope'] == 'LOCAL_LCLUC_WORKFLOW_ONLY' and result['id'] == identifier
              and result['trace_id'] == request['trace_id'] and result['issue'] in ISSUES
              and result['replayed'] is False and result['scientific_accuracy_validated'] is False
              and result['standard_gmais_result'] is False)
        return result, 409
    record = _record({k: v for k, v in result.items() if k != 'replayed'}, identifier, Path(store.root).resolve())
    _need(record['request_sha256'] == digest and record['request_snapshot'] == {k: v for k, v in request.items() if k != 'idempotency_key'})
    return {**record, 'replayed': result['replayed']}, 200


def create_lcluc_workflow_router(get_store):
    router = APIRouter()

    @router.post('/v1/lcluc/workflows')
    async def dispatch(request: Request):
        try:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BODY:
                    return _error('REQUEST_TOO_LARGE')
                chunks.append(chunk)
            value = strict_request_json(b''.join(chunks))
            _request(value)  # Reject invalid requests before acquiring the caller Store.
            result, status = await run_in_threadpool(lambda: _post(get_store(), value))
            return JSONResponse(result, status_code=status, headers=HEADERS)
        except WorkflowError as error:
            code = str(error)
            return _error(code if code in ('INVALID_REQUEST', 'IDEMPOTENCY_CONFLICT', 'STORED_OUTPUT_CHANGED') else 'RESOURCE_UNAVAILABLE')
        except ApiIssue as error:
            return _error(error.code)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE')

    @router.get('/v1/lcluc/workflows/{identifier}')
    async def status(identifier: str):
        try:
            result = await run_in_threadpool(lambda: _status(get_store(), identifier))
            return JSONResponse(result, headers=HEADERS)
        except ApiIssue as error:
            return _error(error.code)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE')

    @router.get('/v1/lcluc/workflows/{identifier}/report')
    async def report(identifier: str):
        try:
            raw = await run_in_threadpool(lambda: _report(get_store(), identifier))
            return Response(raw, media_type='application/json', headers=HEADERS)
        except ApiIssue as error:
            return _error(error.code)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE')

    @router.get('/v1/lcluc/workflows/{identifier}/assets/{index}')
    async def asset(identifier: str, index: str):
        try:
            raw, name, mime = await run_in_threadpool(lambda: _download(get_store(), identifier, index))
            return Response(raw, media_type=mime, headers={**HEADERS, 'Content-Disposition': f'attachment; filename="{name}"'})
        except ApiIssue as error:
            return _error(error.code)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE')

    return router
