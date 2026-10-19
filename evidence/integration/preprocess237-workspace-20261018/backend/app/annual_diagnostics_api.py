"""Authenticated manual read-only diagnostics, bounded transport and one worker."""
import asyncio
import hmac
import json
import os
from functools import lru_cache
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from jsonschema import Draft202012Validator
from starlette.concurrency import run_in_threadpool

from .annual_diagnostics_service import MAX_REQUEST_BYTES, read_annual_diagnostic_service
from .ml.annual_mask_policy import _counts

HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
_SLOT = BoundedSemaphore(1)
HTTP_SCOPE = 'LCLUC_ANNUAL_DIAGNOSTIC_HTTP_ERROR'


def _error(code, status):
    headers = {**HEADERS, **({'Retry-After': '1'} if code == 'DIAGNOSTIC_BUSY' else {})}
    return JSONResponse({'schema_version': 1, 'scope': HTTP_SCOPE, 'error': {'code': code}}, status_code=status, headers=headers)


@lru_cache(maxsize=1)
def _validator():
    path = Path(__file__).resolve().parents[2] / 'contracts/internal/lcluc-annual-diagnostics-response.schema.json'
    if path.stat().st_size > 65536: raise ValueError('schema limit')
    return Draft202012Validator(json.loads(path.read_text(encoding='utf-8')))


def _response(value):
    # Check builtins/budgets before serialization or schema callbacks.
    stack = [(value, 0)]; nodes = 0
    while stack:
        item, depth = stack.pop(); nodes += 1
        if nodes > 512 or depth > 8: raise ValueError('response budget')
        if type(item) is dict:
            if len(item) > 32 or not all(type(k) is str and len(k) <= 256
                and not any(0xD800 <= ord(c) <= 0xDFFF for c in k) for k in item): raise ValueError('response object')
            stack.extend((child, depth+1) for child in item.values())
        elif type(item) is list:
            if len(item) > 6: raise ValueError('response list')
            stack.extend((child, depth+1) for child in item)
        elif type(item) is str:
            if len(item) > 256 or any(0xD800 <= ord(c) <= 0xDFFF for c in item): raise ValueError('response string')
        elif type(item) is int:
            if abs(item) > 2**53-1: raise ValueError('response int')
        elif type(item) not in (bool, type(None)): raise ValueError('response type')
    _validator().validate(value)
    status = value['status']; rows = value['per_year_observations']; issue = value['issue']
    flags = (value['caller_policy_evaluated'], value['caller_policy_met'], value['artifact_bytes_verified'])
    if any(type(flag) is not bool for flag in flags): raise ValueError('response flags')
    if status == 'INVALID_REQUEST':
        if value['request_sha256'] is not None or rows or flags != (False, False, False) or value['blocking_stage'] != 'REQUEST' or issue != {'code':'INVALID_REQUEST','year':None}:
            raise ValueError('invalid request response')
    elif status == 'OUTPUT_INVALID':
        if value['request_sha256'] is None or rows or flags != (False, False, False) or value['blocking_stage'] != 'OUTPUT' or issue != {'code':'OUTPUT_INVALID','year':None}:
            raise ValueError('invalid output response')
    else:
        if value['request_sha256'] is None or not 2 <= len(rows) <= 6: raise ValueError('summary identity')
        previous = 0
        for row in rows:
            if type(row['year']) is not int or row['year'] <= previous: raise ValueError('summary year')
            previous = row['year']
            if status == 'SOURCE_BLOCKED':
                if row['status'] != 'NOT_CHECKED' or row['counts'] is not None or row['policy_met'] is not None: raise ValueError('source rows')
            else:
                _counts(row['counts'])
                if type(row['policy_met']) is not bool or row['status'] != ('MET' if row['policy_met'] else 'NOT_MET'): raise ValueError('policy rows')
        if status == 'SOURCE_BLOCKED':
            if flags != (False,False,False) or value['blocking_stage'] not in ('ANNUAL','COUNTS') or issue is None or issue['code'] != 'SOURCE_BLOCKED': raise ValueError('source summary')
            if issue['year'] is not None and (type(issue['year']) is not int or issue['year'] not in [row['year'] for row in rows]): raise ValueError('source issue year')
        elif status == 'CALLER_POLICY_MET_UNVERIFIED':
            if flags != (True,True,True) or issue is not None or value['blocking_stage'] is not None or not all(row['policy_met'] for row in rows): raise ValueError('met summary')
        elif status == 'CALLER_POLICY_NOT_MET':
            first = next((row['year'] for row in rows if row['policy_met'] is False), None)
            if flags != (True,False,False) or first is None or value['blocking_stage'] != 'POLICY' or issue != {'code':'CALLER_POLICY_NOT_MET','year':first}: raise ValueError('not met summary')
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > 16384: raise ValueError('response bytes')
    code = 422 if status == 'INVALID_REQUEST' else 503 if status == 'OUTPUT_INVALID' else 200
    return Response(raw, status_code=code, media_type='application/json', headers=HEADERS)


def create_annual_diagnostics_router(get_store):
    router = APIRouter()

    @router.post('/v1/lcluc/input-diagnostics')
    async def diagnose(request: Request):
        token = os.environ.get('GEOAI_API_TOKEN')
        if not token or not token.strip(): return _error('AUTH_CONFIGURATION_REQUIRED', 503)
        authorization = request.headers.get('authorization', '')
        try: authorized = hmac.compare_digest(authorization.encode('utf-8'), ('Bearer '+token).encode('utf-8'))
        except Exception: authorized = False
        if not authorized: return _error('AUTH_REQUIRED', 401)
        if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/json':
            return _error('UNSUPPORTED_MEDIA_TYPE', 415)
        try:
            length = request.headers.get('content-length')
            if length is not None and (not length.isascii() or not length.isdigit()): return _error('RESOURCE_UNAVAILABLE', 503)
            if length is not None and int(length) > MAX_REQUEST_BYTES: return _error('REQUEST_TOO_LARGE', 413)
            chunks = []; size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_REQUEST_BYTES: return _error('REQUEST_TOO_LARGE', 413)
                chunks.append(chunk)
            raw = b''.join(chunks)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)
        if not _SLOT.acquire(blocking=False): return _error('DIAGNOSTIC_BUSY', 429)

        def worker():
            try:
                return _response(read_annual_diagnostic_service(get_store(), raw))
            except Exception:
                return _error('RESOURCE_UNAVAILABLE', 503)
            finally:
                _SLOT.release()
        try:
            task = asyncio.create_task(run_in_threadpool(worker))
        except BaseException:
            _SLOT.release()
            raise
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        # Disconnect/cancellation does not release a still-running CPU worker slot.
        return await asyncio.shield(task)

    return router
