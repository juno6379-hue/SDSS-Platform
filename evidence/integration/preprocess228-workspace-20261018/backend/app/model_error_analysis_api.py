"""Authenticated, pinned reads of existing training-error exports; never generates them."""
import hashlib
import json
from pathlib import Path
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .model_reference_contract import model_reference_issue
from .model_registration_provenance import inspect_model_registration_provenance
from .ml.error_analysis import confusion_error_analysis

MAX_BODY = 16384
MAX_REPORT = 8 * 1024**2
MAX_CHECKPOINT = 64 * 1024**2
FILES = ('error-analysis.json', 'error-analysis-classes.csv', 'error-analysis-confusions.csv')
SCOPE = 'PINNED_TRAINING_ERROR_ANALYSIS_READ_ONLY'
ESCAPE = 'Leading = + - @ after whitespace is prefixed with apostrophe.'
CLAIM = '고정 best 모델의 참조 일치도 오류 분석입니다. 독립 정답·과학 정확도 인증이 아닙니다.'
HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}


class ReadIssue(Exception):
    def __init__(self, code):
        self.code = code


def _need(value, code='STORED_OUTPUT_CHANGED'):
    if not value:
        raise ReadIssue(code)


def _keys(v, keys):
    return type(v) is dict and len(v) == len(keys) and all(type(k) is str for k in v) and v.keys() == set(keys)


def _sha(v):
    return type(v) is str and re.fullmatch('[0-9a-f]{64}', v) is not None


def _canonical(v):
    return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate')
            result[k] = v
        return result
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
    _canonical(value)  # Also rejects exponent overflow, lone surrogates and nonfinite numbers.
    return value


def _request(value):
    _need(_keys(value, ('schema_version', 'model_ref', 'training_report_sha256')), 'INVALID_REQUEST')
    ref = value['model_ref']
    _need(type(value['schema_version']) is int and value['schema_version'] == 1
          and _keys(ref, ('id', 'version', 'sha256')) and model_reference_issue(ref) is None
          and re.fullmatch('[A-Za-z0-9_-]{1,100}', ref['id']) is not None
          and _sha(ref['sha256']) and _sha(value['training_report_sha256']), 'INVALID_REQUEST')
    return value


def _read(root, path, maximum):
    _need(path.is_relative_to(root) and path.resolve() == path)
    # Reject internal symlinks/junctions too, not merely escapes outside DATA.
    for part in (path, *path.parents):
        if part == root:
            break
        _need(not part.is_symlink() and not (hasattr(part, 'is_junction') and part.is_junction()))
    try:
        before = path.stat()
    except FileNotFoundError:
        return None
    _need(path.is_file() and before.st_size <= maximum)
    chunks, size = [], 0
    with path.open('rb') as stream:
        while chunk := stream.read(min(1024**2, maximum + 1 - size)):
            size += len(chunk)
            _need(size <= maximum)
            chunks.append(chunk)
    after = path.stat()
    _need(path.resolve() == path and before.st_size == after.st_size == size
          and before.st_mtime_ns == after.st_mtime_ns and before.st_ino == after.st_ino)
    return b''.join(chunks)


def read_model_error_analysis(store, request):
    """Return one bounded verified snapshot and copied artifact bytes. Store.get only."""
    value = _request(request)
    ref = value['model_ref']
    try:
        model = store.get('models', ref['id'])
    except KeyError:
        raise ReadIssue('NOT_FOUND') from None
    _need(type(model) is dict and model.get('id') == ref['id'])
    _need(model.get('checkpoint_sha256') == ref['sha256']
          and model.get('training_report_sha256') == value['training_report_sha256'], 'PIN_CONFLICT')
    response = {'schema_version': 1, 'scope': SCOPE, 'status': 'UNAVAILABLE', 'issue': None,
                'model_ref': dict(ref), 'training_report_sha256': value['training_report_sha256'],
                'analysis': None, 'artifacts': [], 'scientific_accuracy_validated': False, 'standard_gmais_result': False}
    if 'model_version_declaration' not in model:
        response['issue'] = 'MODEL_VERSION_DECLARATION_UNAVAILABLE'
        return response, []
    observation = inspect_model_registration_provenance(model)
    _need(observation['status'] == 'CONSISTENT_UNVERIFIED')
    _need(model['model_version_declaration']['version'] == ref['version'], 'PIN_CONFLICT')
    root = Path(store.root).resolve()
    directory = root / 'models' / ref['id']
    expected_checkpoint = f"models/{ref['id']}/best.pt"
    _need(type(model.get('checkpoint_path')) is str and model['checkpoint_path'].replace('\\', '/') == expected_checkpoint)
    checkpoint = _read(root, directory / 'best.pt', MAX_CHECKPOINT)
    raw_report = _read(root, directory / 'report.json', MAX_REPORT)
    if checkpoint is None or raw_report is None:
        response['issue'] = 'ERROR_ANALYSIS_UNAVAILABLE'
        return response, []
    _need(hashlib.sha256(checkpoint).hexdigest() == ref['sha256']
          and hashlib.sha256(raw_report).hexdigest() == value['training_report_sha256'])
    report = _json(raw_report)
    _need(type(report) is dict and report.get('training_state') == 'completed'
          and report.get('model_id') == ref['id'] and report.get('checkpoint_sha256') == ref['sha256'])
    if 'error_analysis' not in report:
        response['issue'] = 'ERROR_ANALYSIS_UNAVAILABLE'
        return response, []
    epoch, history = report.get('selected_epoch'), report.get('history')
    _need(type(epoch) is int and type(history) is list and 1 <= epoch <= len(history))
    validation, test = report.get('selected_validation_metrics'), report.get('test_metrics')
    _need(type(history[epoch-1]) is dict and type(validation) is dict and type(test) is dict
          and _canonical(history[epoch-1].get('val')) == _canonical(validation))
    kind = report.get('reference_kind', 'unverified_or_pseudo_label')
    _need(type(kind) is str and 1 <= len(kind) <= 128
          and all(ord(c) >= 32 and not 127 <= ord(c) <= 159 and not 0xD800 <= ord(c) <= 0xDFFF for c in kind))
    expected = {'schema_version': 1, 'scope': 'SELECTED_BEST_EPOCH_FINAL_ERROR_ANALYSIS',
        'selected_epoch': epoch, 'model_id': ref['id'], 'checkpoint_sha256': ref['sha256'],
        'reference_kind': kind, 'claim': CLAIM,
        'test_used_for_epoch_selection': False, 'training_policy_changed': False, 'scientific_accuracy_validated': False,
        'by_split': {split: confusion_error_analysis(metrics.get('confusion_matrix'), report.get('class_names'))
                     for split, metrics in (('val', validation), ('test', test))}}
    analysis = report['error_analysis']
    _need(type(analysis) is dict and set(analysis) == set(expected) | {'artifacts', 'csv_formula_escape'}
          and analysis['csv_formula_escape'] == ESCAPE
          and _canonical({k: v for k, v in analysis.items() if k in expected}) == _canonical(expected))
    artifacts = analysis['artifacts']
    _need(type(artifacts) is list and len(artifacts) == 3)
    payloads, descriptors = [], []
    for index, filename in enumerate(FILES):
        item = artifacts[index]
        _need(_keys(item, ('path', 'sha256', 'bytes')) and type(item['path']) is str
              and item['path'].replace('\\', '/') == f"models/{ref['id']}/{filename}"
              and _sha(item['sha256']) and type(item['bytes']) is int and 0 <= item['bytes'] <= MAX_REPORT)
        raw = _read(root, directory / filename, MAX_REPORT)
        if raw is None:
            response['issue'] = 'ERROR_ANALYSIS_UNAVAILABLE'
            return response, []
        _need(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'])
        payloads.append(raw)
        descriptors.append({'index': index, 'filename': filename, 'sha256': item['sha256'], 'bytes': item['bytes']})
    _need(_canonical(_json(payloads[0])) == _canonical(expected))
    response.update(status='AVAILABLE', analysis=expected, artifacts=descriptors)
    return response, payloads


def _error(code):
    status = {'INVALID_REQUEST': 400, 'REQUEST_TOO_LARGE': 413, 'NOT_FOUND': 404,
              'PIN_CONFLICT': 409, 'STORED_OUTPUT_CHANGED': 503, 'RESOURCE_UNAVAILABLE': 503}[code]
    return JSONResponse({'error': {'code': code, 'message': '고정 모델 오류 분석을 읽을 수 없습니다.', 'retryable': False}},
                        status_code=status, headers=HEADERS)


def create_model_error_analysis_router(get_store):
    router = APIRouter()

    async def handle(request, index=None):
        try:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BODY:
                    return _error('REQUEST_TOO_LARGE')
                chunks.append(chunk)
            try:
                value = _request(_json(b''.join(chunks)))
            except Exception:
                return _error('INVALID_REQUEST')
            if index is not None and index not in ('0', '1', '2'):
                return _error('NOT_FOUND')
            result, payloads = await run_in_threadpool(lambda: read_model_error_analysis(get_store(), value))
            if index is None:
                return JSONResponse(result, headers=HEADERS)
            if result['status'] != 'AVAILABLE':
                return _error('NOT_FOUND')
            position = int(index)
            return Response(payloads[position], media_type='application/json' if position == 0 else 'text/csv',
                            headers={**HEADERS, 'Content-Disposition': f'attachment; filename="{FILES[position]}"'})
        except ReadIssue as error:
            return _error(error.code)
        except (ValueError, UnicodeError, RecursionError):
            return _error('STORED_OUTPUT_CHANGED')
        except Exception:
            return _error('RESOURCE_UNAVAILABLE')

    @router.post('/v1/models/error-analysis')
    async def observe(request: Request):
        return await handle(request)

    @router.post('/v1/models/error-analysis/assets/{index}')
    async def asset(index: str, request: Request):
        return await handle(request, index)

    return router
