"""FastAPI Router for LCLUC Workflow Transitions & GeoServer-compliant WMS Raster Tiles.

Provides:
- GET /v1/lcluc/workflows/{id}/tiles/{pair}/{z}/{x}/{y}.png (Web Mercator XYZ Tiles)
- GET /v1/lcluc/workflows/{id}/tiles/{pair}/info (Spatial info & MapLibre source spec)
- GET /v1/lcluc/wms (WMS 1.3.0 GetMap & GetCapabilities with Nearest-Neighbor)
- GET /v1/lcluc/pixel (Authoritative GeoTIFF pixel query without screen RGB guessing)
"""
from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from .ml.raster_tile_engine import (
    CLASS_NAMES,
    EMPTY_TILE_PNG,
    WORKFLOW_CLASS_COLORS,
    RasterTileEngine,
    validate_tile_coords,
)

HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
CACHEABLE_HEADERS = {
    'Cache-Control': 'public, max-age=86400, immutable',
    'X-Content-Type-Options': 'nosniff',
}
ID_PATTERN = re.compile(r'^[a-f0-9]{64}$')
PAIR_PATTERN = re.compile(r'^[0-9]{4}-[0-9]{4}$')

FIRST_GROUP_PROVINCES = {
    'banten': 'banten-2021',
    'east_java': 'east_java-2021',
    'gorontalo': 'gorontalo-2021',
    'southeast_sulawesi': 'southeast_sulawesi-2021',
    'south_sulawesi': 'south_sulawesi-2021',
    'west_java': 'west_java-2021',
}


def _error_response(code: str) -> JSONResponse:
    """Standard LCLUC API error mapping."""
    messages = {
        'INVALID_REQUEST': (400, '요청 좌표, BBOX 또는 레이어 식별자 형식이 올바르지 않습니다.'),
        'NOT_FOUND': (404, 'LCLUC Workflow 또는 요청한 래스터 레이어가 없습니다.'),
        'WORKFLOW_NOT_SUCCEEDED': (409, '완료된 Workflow의 변화 래스터만 조회할 수 있습니다.'),
        'RESOURCE_UNAVAILABLE': (503, '래스터 서비스 처리를 완료할 수 없습니다.'),
    }
    status, message = messages.get(code, (500, '서버 오류가 발생했습니다.'))
    return JSONResponse(
        {'error': {'code': code, 'message': message, 'retryable': False}},
        status_code=status,
        headers=HEADERS,
    )


@functools.lru_cache(maxsize=32)
def _get_engine(tif_path_str: str) -> RasterTileEngine:
    """Cached RasterTileEngine instance per GeoTIFF file."""
    return RasterTileEngine(tif_path_str)


def create_lcluc_tile_router(
    get_store: Callable[[], object],
    cache_tiles: bool = False,
) -> APIRouter:
    """Create and configure the FastAPI router for LCLUC raster tiles and WMS service.

    Parameters:
        get_store: Callable returning the project Store instance (with .root).
        cache_tiles: Whether to return immutable public Cache-Control headers.
    """
    router = APIRouter()

    def _resolve_transitions_tif(identifier: str, pair: str) -> Path:
        """Validate workflow existence, status, and safely resolve transitions.tif."""
        if not ID_PATTERN.match(identifier):
            raise ValueError('INVALID_REQUEST')
        if not PAIR_PATTERN.match(pair):
            raise ValueError('INVALID_REQUEST')

        store = get_store()
        root = Path(store.root).resolve()

        # Check workflow record
        try:
            record = store.get('lcluc-workflows', identifier)
        except (KeyError, AttributeError):
            raise FileNotFoundError('NOT_FOUND')

        if not isinstance(record, dict) or record.get('status') != 'SUCCEEDED':
            raise PermissionError('WORKFLOW_NOT_SUCCEEDED')

        # Safe namespace path resolution
        namespace = root / 'results' / 'lcluc-workflows' / identifier
        tif_path = namespace / 'changes' / pair / 'transitions.tif'
        resolved = tif_path.resolve()

        # Guard against directory traversal or escaping namespace
        if not resolved.is_relative_to(namespace):
            raise FileNotFoundError('NOT_FOUND')
        if not resolved.is_file():
            # Check if artifact path is registered in record artifacts
            artifacts = record.get('artifacts', [])
            expected_suffix = f'changes/{pair}/transitions.tif'
            matching = [
                a for a in artifacts
                if a.get('path', '').replace('\\', '/').endswith(expected_suffix)
            ]
            if not matching:
                raise FileNotFoundError('NOT_FOUND')
            alt_path = root / matching[0]['path'].replace('\\', '/')
            if not alt_path.resolve().is_relative_to(namespace) or not alt_path.is_file():
                raise FileNotFoundError('NOT_FOUND')
            resolved = alt_path.resolve()

        return resolved

    def _resolve_layer_raster(
        layer_name: Optional[str] = None,
        province: Optional[str] = None,
        year: Optional[int] = None,
        workflow_id: Optional[str] = None,
        pair: Optional[str] = None,
    ) -> Tuple[Path, Dict[str, Any]]:
        """Resolve raster path and metadata for WMS layers or pixel queries."""
        store = get_store()
        root = Path(store.root).resolve()

        # 1. Workflow transition raster
        if workflow_id and pair:
            tif_path = _resolve_transitions_tif(workflow_id, pair)
            meta = {
                'source': 'workflow_transition',
                'workflow_id': workflow_id,
                'pair': pair,
                'reference_kind': 'model_prediction_change',
            }
            return tif_path, meta

        # Parse composite layer string: e.g. "workflow:<id>:<pair>" or "transitions:<id>:<pair>"
        if layer_name and (layer_name.startswith('workflow:') or layer_name.startswith('transitions:')):
            parts = layer_name.split(':')
            if len(parts) == 3:
                w_id, p_id = parts[1], parts[2]
                tif_path = _resolve_transitions_tif(w_id, p_id)
                meta = {
                    'source': 'workflow_transition',
                    'workflow_id': w_id,
                    'pair': p_id,
                    'reference_kind': 'model_prediction_change',
                }
                return tif_path, meta

        data_dir = root if root.name == 'data' else (root / 'data')

        # 2. First Group 2021 Reference Landcover by province / year
        clean_prov = (province or '').strip().lower().replace(' ', '_').replace('-', '_')
        if not clean_prov and layer_name:
            layer_clean = layer_name.lower().replace('first-group-2021:', '').replace('worldcover:', '')
            for p in FIRST_GROUP_PROVINCES:
                if p in layer_clean:
                    clean_prov = p
                    break

        target_year = year or 2021
        if clean_prov in FIRST_GROUP_PROVINCES:
            folder_name = FIRST_GROUP_PROVINCES[clean_prov]
            # Check annual mosaic folder first if available
            year_cand = data_dir / 'first-group-annual' / f'{clean_prov}_{target_year}' / 'label-worldcover.tif'
            if year_cand.is_file():
                meta = {
                    'source': 'worldcover_annual',
                    'province': clean_prov,
                    'year': target_year,
                    'reference_kind': 'reference_landcover',
                }
                return year_cand.resolve(), meta

            # Authoritative 2021 physical baseline raster
            candidate = data_dir / 'first-group-2021' / folder_name / 'label-worldcover.tif'
            if candidate.is_file():
                meta = {
                    'source': 'worldcover',
                    'province': clean_prov,
                    'year': 2021,
                    'requested_year': target_year,
                    'reference_kind': 'reference_landcover',
                    'license': 'CC-BY-4.0',
                    'original_product': 'ESA WorldCover 10m v200',
                }
                return candidate.resolve(), meta

        # 3. Baseline 2021 Candidates fallback
        if clean_prov:
            for baseline_dir in (data_dir / 'baseline2021').glob(f'*{clean_prov}*'):
                cand = baseline_dir / 'label-worldcover.tif'
                if cand.is_file():
                    meta = {
                        'source': 'worldcover_baseline',
                        'province': clean_prov,
                        'year': 2021,
                        'reference_kind': 'reference_landcover',
                    }
                    return cand.resolve(), meta

        # 4. Search by layer string inside data
        if layer_name:
            clean_str = layer_name.replace('\\', '/').strip()
            # Direct path check
            direct = root / clean_str if (root / clean_str).is_file() else (data_dir / clean_str)
            if direct.is_file() and direct.suffix.lower() in ('.tif', '.tiff'):
                meta = {'source': 'direct_path', 'layer': layer_name}
                return direct.resolve(), meta

            # Glob search under data/
            for matched in data_dir.glob(f'**/*{clean_str}*.tif'):
                if matched.is_file():
                    meta = {'source': 'matched_dataset', 'layer': layer_name}
                    return matched.resolve(), meta

        raise FileNotFoundError('NOT_FOUND')

    # -------------------------------------------------------------------------
    # 1. Existing Workflow XYZ Tiles & Info
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/tiles/{pair}/info')
    async def tile_info(identifier: str, pair: str):
        """Retrieve spatial metadata, bounds, and MapLibre configuration for transitions raster."""
        try:
            tif_path = await run_in_threadpool(
                lambda: _resolve_transitions_tif(identifier, pair)
            )
            engine = _get_engine(str(tif_path))
            info = engine.get_raster_info()
            tile_url = f'/v1/lcluc/workflows/{identifier}/tiles/{pair}/{{z}}/{{x}}/{{y}}.png'
            return JSONResponse(
                {
                    'workflow_id': identifier,
                    'pair': pair,
                    'tile_url_template': tile_url,
                    'raster_info': info,
                    'maplibre_source': {
                        'type': 'raster',
                        'tiles': [tile_url],
                        'tileSize': 256,
                        'bounds': info['bounds_wgs84'],
                    },
                },
                headers=HEADERS,
            )
        except ValueError as exc:
            return _error_response(str(exc))
        except FileNotFoundError:
            return _error_response('NOT_FOUND')
        except PermissionError:
            return _error_response('WORKFLOW_NOT_SUCCEEDED')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    @router.get('/v1/lcluc/workflows/{identifier}/tiles/{pair}/{z}/{x}/{y}.png')
    async def get_tile(
        identifier: str,
        pair: str,
        z: int,
        x: int,
        y: int,
        mode: str = Query('changes_only', pattern='^(changes_only|all|from_class)$'),
        to_class: Optional[int] = Query(None, ge=0, le=8),
        from_class: Optional[int] = Query(None, ge=0, le=8),
        opacity: float = Query(1.0, ge=0.0, le=1.0),
        tile_size: int = Query(256, ge=128, le=512),
    ):
        """Serve a standard Web Mercator PNG tile for the specified change pair."""
        try:
            validate_tile_coords(z, x, y)
        except (ValueError, TypeError):
            return _error_response('INVALID_REQUEST')

        try:
            tif_path = await run_in_threadpool(
                lambda: _resolve_transitions_tif(identifier, pair)
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
            engine = _get_engine(str(tif_path))
            png_bytes = await run_in_threadpool(
                lambda: engine.render_tile(
                    z=z,
                    x=x,
                    y=y,
                    mode=mode,
                    to_class=to_class,
                    from_class=from_class,
                    opacity=opacity,
                    tile_size=tile_size,
                )
            )

            res_headers = CACHEABLE_HEADERS if cache_tiles else HEADERS
            return Response(content=png_bytes, media_type='image/png', headers=res_headers)
        except ValueError as exc:
            return _error_response(str(exc))
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    @router.get('/v1/lcluc/tiles/{province}/{year}/{z}/{x}/{y}.png')
    @router.get('/geoserver/tiles/{province}/{year}/{z}/{x}/{y}.png')
    async def get_province_tile(
        province: str,
        year: int,
        z: int,
        x: int,
        y: int,
        mode: str = Query('all'),
        to_class: Optional[int] = Query(None, ge=0, le=8),
        from_class: Optional[int] = Query(None, ge=0, le=8),
        opacity: float = Query(1.0, ge=0.0, le=1.0),
        tile_size: int = Query(256, ge=128, le=512),
    ):
        """Serve a standard Web Mercator PNG tile for a province and year landcover raster."""
        try:
            validate_tile_coords(z, x, y)
        except (ValueError, TypeError):
            return _error_response('INVALID_REQUEST')

        try:
            tif_path, _ = await run_in_threadpool(
                lambda: _resolve_layer_raster(province=province, year=year)
            )
        except ValueError as exc:
            return _error_response(str(exc))
        except FileNotFoundError:
            return _error_response('NOT_FOUND')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

        try:
            engine = _get_engine(str(tif_path))
            png_bytes = await run_in_threadpool(
                lambda: engine.render_tile(
                    z=z,
                    x=x,
                    y=y,
                    mode=mode,
                    to_class=to_class,
                    from_class=from_class,
                    opacity=opacity,
                    tile_size=tile_size,
                )
            )
            res_headers = CACHEABLE_HEADERS if cache_tiles else HEADERS
            return Response(content=png_bytes, media_type='image/png', headers=res_headers)
        except ValueError as exc:
            return _error_response(str(exc))
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    # -------------------------------------------------------------------------
    # 2. GeoServer-compliant Endpoints (GetCapabilities & GetMap & Web Console)
    # -------------------------------------------------------------------------
    @router.get('/geoserver', response_class=HTMLResponse)
    @router.get('/geoserver/web', response_class=HTMLResponse)
    async def geoserver_web_admin(request: Request):
        """GeoServer Web Administration and Service Status Dashboard."""
        base_url = str(request.base_url).rstrip('/')
        html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>GeoServer Web Administration — GeoAI LCLUC</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 24px; background: #0b1120; color: #f8fafc; line-height: 1.5; }}
    .container {{ max-width: 1040px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 28px; border: 1px solid #334155; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
    .header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 18px; margin-bottom: 24px; }}
    h1 {{ margin: 0; color: #38bdf8; font-size: 22px; display: flex; align-items: center; gap: 10px; }}
    .status-badge {{ background: #065f46; color: #34d399; padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; }}
    .pulse {{ width: 8px; height: 8px; background: #34d399; border-radius: 50%; box-shadow: 0 0 8px #34d399; }}
    .section-title {{ font-size: 16px; font-weight: 700; color: #94a3b8; margin-top: 24px; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13.5px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #334155; }}
    th {{ background: #0f172a; color: #94a3b8; font-weight: 600; }}
    tr:hover td {{ background: #24344d; }}
    a.btn {{ display: inline-block; background: #0284c7; color: #ffffff; text-decoration: none; padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; margin-right: 4px; }}
    a.btn:hover {{ background: #0369a1; }}
    a.btn-secondary {{ background: #334155; color: #e2e8f0; }}
    a.btn-secondary:hover {{ background: #475569; }}
    .swatch {{ display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: middle; margin-right: 6px; }}
    .palette-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; }}
    .palette-item {{ background: #0f172a; padding: 8px 12px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; border: 1px solid #334155; }}
    .spec-card {{ background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid #334155; font-size: 13.5px; color: #cbd5e1; margin-bottom: 18px; }}
    .code {{ font-family: monospace; background: #1e293b; padding: 2px 6px; border-radius: 4px; color: #38bdf8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>GeoServer Web Administration</h1>
        <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">GeoAI LCLUC Discrete Classification Map & Authoritative Pixel Service</div>
      </div>
      <div class="status-badge"><span class="pulse"></span> ONLINE / ACTIVE</div>
    </div>

    <div class="spec-card">
      <strong>서비스 메타데이터 &amp; 규격:</strong>
      <ul style="margin: 6px 0 0 0; padding-left: 20px;">
        <li><strong>호환 버전:</strong> GeoServer 2.24+ / WMS 1.3.0 &amp; 1.1.1 (CODEX v1.0 준수)</li>
        <li><strong>작업공간(Workspaces):</strong> <span class="code">lcluc</span>, <span class="code">sdss_lcluc</span></li>
        <li><strong>리샘플링 정책:</strong> <span class="code">Nearest-Neighbor</span> (이산 9-클래스 경계 왜곡 0% 보존)</li>
        <li><strong>결측치(NoData):</strong> <span class="code">255 / 65535</span> (100% 완전 투명 처리)</li>
      </ul>
    </div>

    <div class="section-title">등록된 토지피복 레이어 (First Group 6개 주)</div>
    <table>
      <thead>
        <tr>
          <th>레이어 식별자 (Layer ID)</th>
          <th>지역명</th>
          <th>원천 자료</th>
          <th>좌표계 (CRS)</th>
          <th>서비스 링크</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>lcluc:south_sulawesi_2021</strong></td>
          <td>남부 술라웨시 (South Sulawesi)</td>
          <td>ESA WorldCover 10m</td>
          <td>EPSG:32750</td>
          <td>
            <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=lcluc:south_sulawesi_2021&SRS=EPSG:3857&BBOX=13340000,-450000,13360000,-430000&WIDTH=256&HEIGHT=256&FORMAT=image/png" target="_blank">타일 미리보기</a>
            <a class="btn btn-secondary" href="{base_url}/v1/lcluc/pixel?lng=119.9485&lat=-3.7902&layer=south_sulawesi" target="_blank">1x1 픽셀 검사</a>
          </td>
        </tr>
        <tr>
          <td><strong>lcluc:west_java_2021</strong></td>
          <td>서부 자바 (West Java)</td>
          <td>ESA WorldCover 10m</td>
          <td>EPSG:32748</td>
          <td>
            <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=lcluc:west_java_2021&SRS=EPSG:3857&BBOX=11970000,-780000,11990000,-760000&WIDTH=256&HEIGHT=256&FORMAT=image/png" target="_blank">타일 미리보기</a>
            <a class="btn btn-secondary" href="{base_url}/v1/lcluc/pixel?lng=107.6536&lat=-6.8674&layer=west_java" target="_blank">1x1 픽셀 검사</a>
          </td>
        </tr>
        <tr>
          <td><strong>lcluc:banten_2021</strong></td>
          <td>반텐 (Banten)</td>
          <td>ESA WorldCover 10m</td>
          <td>EPSG:32748</td>
          <td>
            <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=lcluc:banten_2021&SRS=EPSG:3857&BBOX=11800000,-720000,11820000,-700000&WIDTH=256&HEIGHT=256&FORMAT=image/png" target="_blank">타일 미리보기</a>
            <a class="btn btn-secondary" href="{base_url}/v1/lcluc/pixel?lng=106.1&lat=-6.4&layer=banten" target="_blank">1x1 픽셀 검사</a>
          </td>
        </tr>
        <tr>
          <td><strong>lcluc:east_java_2021</strong></td>
          <td>동부 자바 (East Java)</td>
          <td>ESA WorldCover 10m</td>
          <td>EPSG:32749</td>
          <td>
            <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=lcluc:east_java_2021&SRS=EPSG:3857&BBOX=12520000,-880000,12540000,-860000&WIDTH=256&HEIGHT=256&FORMAT=image/png" target="_blank">타일 미리보기</a>
            <a class="btn btn-secondary" href="{base_url}/v1/lcluc/pixel?lng=112.5&lat=-7.8&layer=east_java" target="_blank">1x1 픽셀 검사</a>
          </td>
        </tr>
        <tr>
          <td><strong>lcluc:gorontalo_2021</strong></td>
          <td>고론탈로 (Gorontalo)</td>
          <td>ESA WorldCover 10m</td>
          <td>EPSG:32651</td>
          <td>
            <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=lcluc:gorontalo_2021&SRS=EPSG:3857&BBOX=13680000,50000,13700000,70000&WIDTH=256&HEIGHT=256&FORMAT=image/png" target="_blank">타일 미리보기</a>
            <a class="btn btn-secondary" href="{base_url}/v1/lcluc/pixel?lng=122.5&lat=0.6&layer=gorontalo" target="_blank">1x1 픽셀 검사</a>
          </td>
        </tr>
        <tr>
          <td><strong>lcluc:southeast_sulawesi_2021</strong></td>
          <td>동남 술라웨시 (Southeast Sulawesi)</td>
          <td>ESA WorldCover 10m</td>
          <td>EPSG:32751</td>
          <td>
            <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=lcluc:southeast_sulawesi_2021&SRS=EPSG:3857&BBOX=13600000,-500000,13620000,-480000&WIDTH=256&HEIGHT=256&FORMAT=image/png" target="_blank">타일 미리보기</a>
            <a class="btn btn-secondary" href="{base_url}/v1/lcluc/pixel?lng=122.0&lat=-4.0&layer=southeast_sulawesi" target="_blank">1x1 픽셀 검사</a>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="section-title">공인 이산 9-클래스 범례 (Style: lcluc_discrete_9classes)</div>
    <div class="palette-grid">
      <div class="palette-item"><span class="swatch" style="background:#2563eb;"></span> <strong>0: Water (수역)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#15803d;"></span> <strong>1: Trees (수목·산림)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#84cc16;"></span> <strong>2: Grass (초지)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#14b8a6;"></span> <strong>3: Flooded veg (침수식생)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#eab308;"></span> <strong>4: Crops (농경지)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#a16207;"></span> <strong>5: Shrub &amp; scrub (관목)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#dc2626;"></span> <strong>6: Built area (시가지)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#a8a29e;"></span> <strong>7: Bare ground (나지)</strong></div>
      <div class="palette-item"><span class="swatch" style="background:#a5d8f3;"></span> <strong>8: Snow &amp; ice (설빙)</strong></div>
    </div>

    <div class="section-title">서비스 엔드포인트 바로가기</div>
    <div style="margin-top: 10px; display: flex; gap: 10px;">
      <a class="btn" href="{base_url}/geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities" target="_blank">WMS 1.3.0 GetCapabilities (XML)</a>
      <a class="btn btn-secondary" href="{base_url}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities" target="_blank">WMS 1.1.1 GetCapabilities</a>
      <a class="btn btn-secondary" href="http://127.0.0.1:5174/#/view/24?model=lcluc" target="_blank">LCLUC WebGIS 대시보드 바로가기</a>
    </div>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html_content, status_code=200)

    @router.get('/v1/lcluc/wms')
    @router.get('/geoserver/wms')
    @router.get('/geoserver/{workspace}/wms')
    async def wms_service(
        request: Request,
        workspace: Optional[str] = None,
        SERVICE: str = Query('WMS'),
        REQUEST: str = Query('GetMap'),
        VERSION: str = Query('1.3.0'),
        LAYERS: Optional[str] = Query(None),
        BBOX: Optional[str] = Query(None),
        WIDTH: int = Query(256, ge=64, le=4096),
        HEIGHT: int = Query(256, ge=64, le=4096),
        CRS: Optional[str] = Query(None),
        SRS: Optional[str] = Query(None),
        FORMAT: str = Query('image/png'),
        TRANSPARENT: bool = Query(True),
        STYLES: Optional[str] = Query(None),
        TIME: Optional[str] = Query(None),
        mode: str = Query('changes_only'),
        to_class: Optional[int] = Query(None, ge=0, le=8),
        from_class: Optional[int] = Query(None, ge=0, le=8),
        opacity: float = Query(1.0, ge=0.0, le=1.0),
    ):
        """WMS 1.3.0 / 1.1.1 compliant map service endpoint with Nearest-Neighbor rendering."""
        if SERVICE.upper() != 'WMS':
            return _error_response('INVALID_REQUEST')

        req_upper = REQUEST.upper()

        # 1. GetCapabilities
        if req_upper == 'GETCAPABILITIES':
            capabilities_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wms http://schemas.opengis.net/wms/1.3.0/capabilities_1_3_0.xsd">
  <Service>
    <Name>WMS</Name>
    <Title>GeoAI LCLUC Discrete Classification WMS Service</Title>
    <Abstract>Authoritative WMS 1.3.0 Service for LCLUC discrete 9-class land cover and change transitions with Nearest-Neighbor resampling</Abstract>
    <KeywordList>
      <Keyword>LCLUC</Keyword>
      <Keyword>LandCover</Keyword>
      <Keyword>GeoServer</Keyword>
      <Keyword>WMS</Keyword>
    </KeywordList>
    <OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="{request.base_url}v1/lcluc/wms"/>
  </Service>
  <Capability>
    <Request>
      <GetCapabilities>
        <Format>text/xml</Format>
        <DCPType><HTTP><Get><OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="{request.base_url}v1/lcluc/wms"/></Get></HTTP></DCPType>
      </GetCapabilities>
      <GetMap>
        <Format>image/png</Format>
        <DCPType><HTTP><Get><OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="{request.base_url}v1/lcluc/wms"/></Get></HTTP></DCPType>
      </GetMap>
    </Request>
    <Layer>
      <Title>LCLUC Root Layer</Title>
      <CRS>EPSG:3857</CRS>
      <CRS>EPSG:4326</CRS>
      <Style>
        <Name>lcluc_discrete_9classes</Name>
        <Title>LCLUC 9-Class Discrete Style</Title>
      </Style>
    </Layer>
  </Capability>
</WMS_Capabilities>"""
            return Response(content=capabilities_xml, media_type='text/xml', headers=HEADERS)

        # 2. GetMap
        if req_upper != 'GETMAP':
            return _error_response('INVALID_REQUEST')

        if not LAYERS or not BBOX:
            return _error_response('INVALID_REQUEST')

        # Parse BBOX
        try:
            bbox_parts = [float(p.strip()) for p in BBOX.split(',')]
            if len(bbox_parts) != 4:
                raise ValueError()
        except ValueError:
            return _error_response('INVALID_REQUEST')

        target_crs = CRS or SRS or 'EPSG:3857'

        # Handle WMS 1.3.0 EPSG:4326 axis order: (lat, lon, lat, lon)
        if target_crs.upper() == 'EPSG:4326' and VERSION == '1.3.0':
            min_y, min_x, max_y, max_x = bbox_parts
        else:
            min_x, min_y, max_x, max_y = bbox_parts

        if min_x >= max_x or min_y >= max_y:
            return _error_response('INVALID_REQUEST')

        # Resolve Layer GeoTIFF
        try:
            tif_path, _ = await run_in_threadpool(
                lambda: _resolve_layer_raster(layer_name=LAYERS, year=int(TIME) if (TIME and TIME.isdigit()) else None)
            )
        except (ValueError, FileNotFoundError):
            return _error_response('NOT_FOUND')
        except PermissionError:
            return _error_response('WORKFLOW_NOT_SUCCEEDED')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

        try:
            engine = _get_engine(str(tif_path))
            png_bytes = await run_in_threadpool(
                lambda: engine.render_bbox(
                    min_x=min_x,
                    min_y=min_y,
                    max_x=max_x,
                    max_y=max_y,
                    srs=target_crs,
                    width=WIDTH,
                    height=HEIGHT,
                    mode=mode,
                    to_class=to_class,
                    from_class=from_class,
                    opacity=opacity,
                )
            )
            return Response(content=png_bytes, media_type='image/png', headers=HEADERS)
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    # -------------------------------------------------------------------------
    # 3. Exact Point Pixel Query Endpoint
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/pixel')
    async def query_pixel(
        lat: float = Query(..., ge=-90.0, le=90.0),
        lng: float = Query(..., ge=-180.0, le=180.0),
        year: Optional[int] = Query(None),
        province: Optional[str] = Query(None),
        workflow_id: Optional[str] = Query(None),
        pair: Optional[str] = Query(None),
        layer: Optional[str] = Query(None),
    ):
        """Authoritative GeoTIFF pixel query returning exact integer class and metadata without screen RGB guessing."""
        try:
            tif_path, meta = await run_in_threadpool(
                lambda: _resolve_layer_raster(
                    layer_name=layer,
                    province=province,
                    year=year,
                    workflow_id=workflow_id,
                    pair=pair,
                )
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
            engine = _get_engine(str(tif_path))
            pixel_info = await run_in_threadpool(
                lambda: engine.query_pixel(lng=lng, lat=lat)
            )

            # Combine pixel info with layer provenance
            response_data = {
                **pixel_info,
                'query_params': {
                    'lat': lat,
                    'lng': lng,
                    'year': year,
                    'province': province,
                    'workflow_id': workflow_id,
                    'pair': pair,
                },
                'provenance': {
                    **meta,
                    'inspection_method': 'direct_geotiff_window_read_zero_screen_guessing',
                },
            }
            return JSONResponse(response_data, headers=HEADERS)
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    return router
