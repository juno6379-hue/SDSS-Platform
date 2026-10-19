"""FastAPI Router for LCLUC Multi-Format Export Service.

Provides endpoint:
GET /v1/lcluc/workflows/{id}/export/{format}
(format: tif, geojson, csv, html, json, zip)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, Tuple

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .ml.export_service_engine import LclucExportEngine

HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
ID_PATTERN = re.compile(r'^[a-f0-9]{64}$')
PAIR_PATTERN = re.compile(r'^[0-9]{4}-[0-9]{4}$')
SUPPORTED_FORMATS = {'tif', 'geotiff', 'geojson', 'csv', 'html', 'json', 'zip'}

FORMAT_MIME = {
    'tif': 'image/tiff',
    'geotiff': 'image/tiff',
    'geojson': 'application/geo+json',
    'csv': 'text/csv; charset=utf-8',
    'html': 'text/html; charset=utf-8',
    'json': 'application/json',
    'zip': 'application/zip',
}


def _error_response(code: str) -> JSONResponse:
    """Standard API error mapping."""
    messages = {
        'INVALID_REQUEST': (400, '내보내기 요청 형식 또는 파라미터가 올바르지 않습니다.'),
        'NOT_FOUND': (404, 'LCLUC Workflow 또는 요청한 분석 결과를 찾을 수 없습니다.'),
        'WORKFLOW_NOT_SUCCEEDED': (409, '완료된 Workflow의 분석 결과만 내보낼 수 있습니다.'),
        'RESOURCE_UNAVAILABLE': (503, '내보내기 파일 생성을 완료할 수 없습니다.'),
    }
    status, message = messages.get(code, (500, '서버 오류가 발생했습니다.'))
    return JSONResponse(
        {'error': {'code': code, 'message': message, 'retryable': False}},
        status_code=status,
        headers=HEADERS,
    )


def create_lcluc_export_router(get_store: Callable[[], object]) -> APIRouter:
    """Create FastAPI APIRouter for multi-format export service."""
    router = APIRouter()

    def _resolve_workflow_and_pair(identifier: str, pair_param: Optional[str]) -> Tuple[Path, str]:
        if not ID_PATTERN.match(identifier):
            raise ValueError('INVALID_REQUEST')

        store = get_store()
        root = Path(store.root).resolve()

        try:
            record = store.get('lcluc-workflows', identifier)
        except (KeyError, AttributeError):
            raise FileNotFoundError('NOT_FOUND')

        if not isinstance(record, dict) or record.get('status') != 'SUCCEEDED':
            raise PermissionError('WORKFLOW_NOT_SUCCEEDED')

        namespace = root / 'results' / 'lcluc-workflows' / identifier
        if not namespace.resolve().is_relative_to(root) or not namespace.is_dir():
            raise FileNotFoundError('NOT_FOUND')

        pair = pair_param
        if not pair:
            changes_dir = namespace / 'changes'
            if changes_dir.is_dir():
                subdirs = [p.name for p in changes_dir.iterdir() if p.is_dir() and PAIR_PATTERN.match(p.name)]
                if subdirs:
                    pair = sorted(subdirs)[0]

        if not pair or not PAIR_PATTERN.match(pair):
            raise ValueError('INVALID_REQUEST')

        pair_dir = namespace / 'changes' / pair
        if not pair_dir.is_dir():
            raise FileNotFoundError('NOT_FOUND')

        return namespace, pair

    @router.get('/v1/lcluc/workflows/{identifier}/export/{fmt}')
    async def export_format(
        identifier: str,
        fmt: str,
        pair: Optional[str] = Query(None),
        to_class: Optional[int] = Query(None, ge=0, le=8),
        from_class: Optional[int] = Query(None, ge=0, le=8),
        unit: str = Query('ha'),
        crs: Optional[str] = Query(None),
        changes_only: bool = Query(True),
    ):
        """Export workflow change detection results in requested format."""
        format_clean = fmt.lower()
        if format_clean not in SUPPORTED_FORMATS:
            return _error_response('INVALID_REQUEST')

        try:
            workflow_dir, selected_pair = await run_in_threadpool(
                lambda: _resolve_workflow_and_pair(identifier, pair)
            )
        except ValueError as exc:
            return _error_response(str(exc))
        except FileNotFoundError:
            return _error_response('NOT_FOUND')
        except PermissionError:
            return _error_response('WORKFLOW_NOT_SUCCEEDED')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

        try:
            engine = LclucExportEngine(
                workflow_id=identifier,
                pair=selected_pair,
                workflow_dir=workflow_dir,
            )

            if format_clean in ('tif', 'geotiff'):
                content = await run_in_threadpool(
                    lambda: engine.export_geotiff(
                        to_class=to_class,
                        from_class=from_class,
                        changes_only=changes_only,
                        target_crs=crs,
                    )
                )
                filename = f'lcluc_transitions_{selected_pair}.tif'
            elif format_clean == 'geojson':
                content = await run_in_threadpool(
                    lambda: engine.export_geojson(
                        to_class=to_class,
                        from_class=from_class,
                    )
                )
                filename = f'lcluc_changes_{selected_pair}.geojson'
            elif format_clean == 'csv':
                content = await run_in_threadpool(
                    lambda: engine.export_csv(unit=unit)
                )
                filename = f'lcluc_transition_matrix_{selected_pair}_{unit}.csv'
            elif format_clean == 'html':
                content = await run_in_threadpool(
                    lambda: engine.export_html_report(unit=unit)
                )
                filename = f'lcluc_summary_report_{selected_pair}.html'
            elif format_clean == 'json':
                content = await run_in_threadpool(
                    lambda: engine.export_json_report(unit=unit)
                )
                filename = f'lcluc_analytical_report_{selected_pair}.json'
            elif format_clean == 'zip':
                content = await run_in_threadpool(
                    lambda: engine.export_bundle_zip(unit=unit, target_crs=crs)
                )
                filename = f'lcluc_export_bundle_{identifier[:10]}_{selected_pair}.zip'
            else:
                return _error_response('INVALID_REQUEST')

            mime_type = FORMAT_MIME[format_clean]
            response_headers = {
                **HEADERS,
                'Content-Disposition': f'attachment; filename="{filename}"',
            }
            return Response(content=content, media_type=mime_type, headers=response_headers)
        except FileNotFoundError:
            return _error_response('NOT_FOUND')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    return router
