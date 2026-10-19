"""FastAPI Router for LCLUC Workflow Multi-Layer Raster Tiles and Map Services.

Provides standard Web Mercator raster tile and WMS endpoints supporting 5 layer types:
1. 'classification': Annual 9-class discrete land cover (0..8)
2. 'quality_mask': Binary validity mask (0: Cloud/Invalid, 1: Valid)
3. 'observation_count': Pixel-wise valid observation count (0..N)
4. 'common_valid': T1/T2 Common Valid Mask (1: Valid in both T1 and T2, 0: Cloud gap/Invalid)
5. 'transitions': Multi-temporal change transitions (uint16 codes 0..80, 65536 LUT mapping)

Endpoints:
- GET /v1/lcluc/workflows/{id}/tiles/{pair}/info
- GET /v1/lcluc/workflows/{id}/tiles/{pair}/{layer_type}/info
- GET /v1/lcluc/workflows/{id}/tiles/{pair}/{z}/{x}/{y}.png (with optional ?layer_type=...)
- GET /v1/lcluc/workflows/{id}/tiles/{pair}/{layer_type}/{z}/{x}/{y}.png
- GET /v1/lcluc/workflows/{id}/tiles/annual/{year}/{layer_type}/{z}/{x}/{y}.png
- GET /v1/lcluc/workflows/{id}/wms (WMS 1.3.0 GetCapabilities and GetMap)
- GET /v1/lcluc/workflows/{id}/pixel (Authoritative native pixel inspection)
"""
from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

try:
    from .raster_tile_engine import (
        EMPTY_TILE_PNG,
        LAYER_CLASSIFICATION,
        LAYER_COMMON_VALID,
        LAYER_OBSERVATION_COUNT,
        LAYER_QUALITY_MASK,
        LAYER_TRANSITIONS,
        SUPPORTED_LAYER_TYPES,
        RasterTileEngine,
        validate_tile_coords,
    )
except ImportError:
    from raster_tile_engine import (
        EMPTY_TILE_PNG,
        LAYER_CLASSIFICATION,
        LAYER_COMMON_VALID,
        LAYER_OBSERVATION_COUNT,
        LAYER_QUALITY_MASK,
        LAYER_TRANSITIONS,
        SUPPORTED_LAYER_TYPES,
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


def _error_response(code: str) -> JSONResponse:
    """Standard LCLUC API error mapping."""
    messages = {
        'INVALID_REQUEST': (400, '타일 요청 좌표, 레이어 타입 또는 식별자 형식이 올바르지 않습니다.'),
        'NOT_FOUND': (404, 'LCLUC Workflow 또는 요청된 레이어 래스터 파일이 없습니다.'),
        'WORKFLOW_NOT_SUCCEEDED': (409, '완료된 Workflow의 래스터만 타일로 읽을 수 있습니다.'),
        'RESOURCE_UNAVAILABLE': (503, '래스터 타일 렌더링을 완료할 수 없습니다.'),
    }
    status, message = messages.get(code, (500, '서버 오류가 발생했습니다.'))
    return JSONResponse(
        {'error': {'code': code, 'message': message, 'retryable': False}},
        status_code=status,
        headers=HEADERS,
    )


@functools.lru_cache(maxsize=32)
def _get_engine(
    tif_path_str: str,
    tif_path_t2_str: Optional[str] = None,
    layer_type: str = LAYER_TRANSITIONS,
) -> RasterTileEngine:
    """Cached RasterTileEngine instance per raster path and layer configuration."""
    return RasterTileEngine(
        tif_path_str,
        tif_path_t2=tif_path_t2_str,
        layer_type=layer_type,
    )


def create_lcluc_tile_router(
    get_store: Callable[[], object],
    cache_tiles: bool = False,
) -> APIRouter:
    """Create and configure the FastAPI router for multi-layer LCLUC raster tiles."""
    router = APIRouter()

    def _resolve_layer_raster(
        identifier: str,
        pair: str,
        layer_type: str = LAYER_TRANSITIONS,
        year: Optional[int] = None,
    ) -> Union[Path, Tuple[Path, Path]]:
        """Validate workflow existence, status, and safely resolve the raster file(s)."""
        if not ID_PATTERN.match(identifier):
            raise ValueError('INVALID_REQUEST')
        if not PAIR_PATTERN.match(pair):
            raise ValueError('INVALID_REQUEST')
        if layer_type not in SUPPORTED_LAYER_TYPES:
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
        t1, t2 = pair.split('-')
        target_year = str(year) if year is not None else t1

        # 1. Transitions Layer
        if layer_type == LAYER_TRANSITIONS:
            candidates = [
                namespace / 'changes' / pair / 'transitions.tif',
                namespace / 'changes' / pair / 'transitions_annual.tif',
            ]
            for c in candidates:
                if c.resolve().is_file() and c.resolve().is_relative_to(namespace):
                    return c.resolve()

            # Search in declared record artifacts
            for a in record.get('artifacts', []):
                p = a.get('path', '').replace('\\', '/')
                if f'changes/{pair}/transitions' in p:
                    cand = (root / p).resolve()
                    if cand.is_file() and cand.is_relative_to(namespace):
                        return cand
            raise FileNotFoundError('NOT_FOUND')

        # 2. Common Valid Mask Layer (T1 AND T2)
        elif layer_type == LAYER_COMMON_VALID:
            candidates = [
                namespace / 'changes' / pair / 'common_valid.tif',
                namespace / 'changes' / pair / 'common_mask.tif',
            ]
            for c in candidates:
                if c.resolve().is_file() and c.resolve().is_relative_to(namespace):
                    return c.resolve()

            # Search in declared record artifacts
            for a in record.get('artifacts', []):
                p = a.get('path', '').replace('\\', '/')
                if f'changes/{pair}/common_valid' in p:
                    cand = (root / p).resolve()
                    if cand.is_file() and cand.is_relative_to(namespace):
                        return cand

            # Try dual annual quality mask resolution for on-the-fly computation
            m1_candidates = [
                namespace / 'annual' / t1 / 'quality_mask.tif',
                namespace / 'annual' / t1 / 'valid_mask.tif',
            ]
            m2_candidates = [
                namespace / 'annual' / t2 / 'quality_mask.tif',
                namespace / 'annual' / t2 / 'valid_mask.tif',
            ]
            p1 = next((c.resolve() for c in m1_candidates if c.resolve().is_file() and c.resolve().is_relative_to(namespace)), None)
            p2 = next((c.resolve() for c in m2_candidates if c.resolve().is_file() and c.resolve().is_relative_to(namespace)), None)
            if p1 is not None and p2 is not None:
                return (p1, p2)

            raise FileNotFoundError('NOT_FOUND')

        # 3. Classification Layer
        elif layer_type == LAYER_CLASSIFICATION:
            candidates = [
                namespace / 'annual' / target_year / 'classification.tif',
                namespace / 'annual' / target_year / 'landcover.tif',
                namespace / 'annual' / target_year / 'label-worldcover.tif',
                namespace / 'changes' / pair / 'classification.tif',
                namespace / 'changes' / pair / 'landcover.tif',
            ]
            for c in candidates:
                if c.resolve().is_file() and c.resolve().is_relative_to(namespace):
                    return c.resolve()

            for a in record.get('artifacts', []):
                p = a.get('path', '').replace('\\', '/')
                if (f'annual/{target_year}' in p or f'changes/{pair}' in p) and ('classification' in p or 'landcover' in p or 'worldcover' in p):
                    cand = (root / p).resolve()
                    if cand.is_file() and cand.is_relative_to(namespace):
                        return cand
            raise FileNotFoundError('NOT_FOUND')

        # 4. Quality Mask Layer
        elif layer_type == LAYER_QUALITY_MASK:
            candidates = [
                namespace / 'annual' / target_year / 'quality_mask.tif',
                namespace / 'annual' / target_year / 'valid_mask.tif',
                namespace / 'changes' / pair / 'quality_mask.tif',
            ]
            for c in candidates:
                if c.resolve().is_file() and c.resolve().is_relative_to(namespace):
                    return c.resolve()

            for a in record.get('artifacts', []):
                p = a.get('path', '').replace('\\', '/')
                if (f'annual/{target_year}' in p or f'changes/{pair}' in p) and ('quality_mask' in p or 'valid_mask' in p):
                    cand = (root / p).resolve()
                    if cand.is_file() and cand.is_relative_to(namespace):
                        return cand
            raise FileNotFoundError('NOT_FOUND')

        # 5. Observation Count Layer
        elif layer_type == LAYER_OBSERVATION_COUNT:
            candidates = [
                namespace / 'annual' / target_year / 'observation_count.tif',
                namespace / 'annual' / target_year / 'valid_count.tif',
                namespace / 'changes' / pair / 'observation_count.tif',
            ]
            for c in candidates:
                if c.resolve().is_file() and c.resolve().is_relative_to(namespace):
                    return c.resolve()

            for a in record.get('artifacts', []):
                p = a.get('path', '').replace('\\', '/')
                if (f'annual/{target_year}' in p or f'changes/{pair}' in p) and ('observation_count' in p or 'valid_count' in p):
                    cand = (root / p).resolve()
                    if cand.is_file() and cand.is_relative_to(namespace):
                        return cand
            raise FileNotFoundError('NOT_FOUND')

        raise FileNotFoundError('NOT_FOUND')

    def _render_tile_helper(
        identifier: str,
        pair: str,
        z: int,
        x: int,
        y: int,
        layer_type: str = LAYER_TRANSITIONS,
        year: Optional[int] = None,
        mode: Optional[str] = None,
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        opacity: float = 1.0,
        tile_size: int = 256,
    ) -> Response:
        try:
            validate_tile_coords(z, x, y)
        except (ValueError, TypeError):
            return _error_response('INVALID_REQUEST')

        try:
            resolved = _resolve_layer_raster(identifier, pair, layer_type=layer_type, year=year)
        except ValueError as exc:
            return _error_response(str(exc))
        except FileNotFoundError:
            return _error_response('NOT_FOUND')
        except PermissionError:
            return _error_response('WORKFLOW_NOT_SUCCEEDED')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

        try:
            if isinstance(resolved, tuple):
                p1, p2 = resolved
                engine = _get_engine(str(p1), tif_path_t2_str=str(p2), layer_type=layer_type)
            else:
                engine = _get_engine(str(resolved), layer_type=layer_type)

            png_bytes = engine.render_tile(
                z=z,
                x=x,
                y=y,
                layer_type=layer_type,
                mode=mode,
                to_class=to_class,
                from_class=from_class,
                opacity=opacity,
                tile_size=tile_size,
            )
            response_headers = CACHEABLE_HEADERS if cache_tiles else HEADERS
            return Response(content=png_bytes, media_type='image/png', headers=response_headers)
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    def _info_helper(
        identifier: str,
        pair: str,
        layer_type: str = LAYER_TRANSITIONS,
        year: Optional[int] = None,
    ) -> JSONResponse:
        try:
            resolved = _resolve_layer_raster(identifier, pair, layer_type=layer_type, year=year)
            if isinstance(resolved, tuple):
                p1, p2 = resolved
                engine = _get_engine(str(p1), tif_path_t2_str=str(p2), layer_type=layer_type)
            else:
                engine = _get_engine(str(resolved), layer_type=layer_type)

            info = engine.get_raster_info()
            tile_url = f'/v1/lcluc/workflows/{identifier}/tiles/{pair}/{layer_type}/{{z}}/{{x}}/{{y}}.png'
            return JSONResponse(
                {
                    'workflow_id': identifier,
                    'pair': pair,
                    'layer_type': layer_type,
                    'year': year if year is not None else int(pair.split('-')[0]),
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

    # -------------------------------------------------------------------------
    # Route 1: Tiles Info (Default transitions or query ?layer_type=...)
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/tiles/{pair}/info')
    async def tile_info(
        identifier: str,
        pair: str,
        layer_type: str = Query(LAYER_TRANSITIONS, pattern='^(transitions|classification|quality_mask|observation_count|common_valid)$'),
        year: Optional[int] = Query(None),
    ):
        return await run_in_threadpool(lambda: _info_helper(identifier, pair, layer_type=layer_type, year=year))

    # -------------------------------------------------------------------------
    # Route 2: Tiles Info (Explicit path layer_type)
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/tiles/{pair}/{layer_type}/info')
    async def tile_info_layer(
        identifier: str,
        pair: str,
        layer_type: str,
        year: Optional[int] = Query(None),
    ):
        return await run_in_threadpool(lambda: _info_helper(identifier, pair, layer_type=layer_type, year=year))

    # -------------------------------------------------------------------------
    # Route 3: Standard Slippy Tile Endpoint (Default transitions or query ?layer_type=...)
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/tiles/{pair}/{z}/{x}/{y}.png')
    async def get_tile(
        identifier: str,
        pair: str,
        z: int,
        x: int,
        y: int,
        layer_type: str = Query(LAYER_TRANSITIONS, pattern='^(transitions|classification|quality_mask|observation_count|common_valid)$'),
        year: Optional[int] = Query(None),
        mode: Optional[str] = Query(None),
        to_class: Optional[int] = Query(None, ge=0, le=8),
        from_class: Optional[int] = Query(None, ge=0, le=8),
        opacity: float = Query(1.0, ge=0.0, le=1.0),
        tile_size: int = Query(256, ge=128, le=512),
    ):
        return await run_in_threadpool(
            lambda: _render_tile_helper(
                identifier=identifier,
                pair=pair,
                z=z,
                x=x,
                y=y,
                layer_type=layer_type,
                year=year,
                mode=mode,
                to_class=to_class,
                from_class=from_class,
                opacity=opacity,
                tile_size=tile_size,
            )
        )

    # -------------------------------------------------------------------------
    # Route 4: Explicit Layer Tile Endpoint (Path-based layer_type)
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/tiles/{pair}/{layer_type}/{z}/{x}/{y}.png')
    async def get_tile_layer(
        identifier: str,
        pair: str,
        layer_type: str,
        z: int,
        x: int,
        y: int,
        year: Optional[int] = Query(None),
        mode: Optional[str] = Query(None),
        to_class: Optional[int] = Query(None, ge=0, le=8),
        from_class: Optional[int] = Query(None, ge=0, le=8),
        opacity: float = Query(1.0, ge=0.0, le=1.0),
        tile_size: int = Query(256, ge=128, le=512),
    ):
        return await run_in_threadpool(
            lambda: _render_tile_helper(
                identifier=identifier,
                pair=pair,
                z=z,
                x=x,
                y=y,
                layer_type=layer_type,
                year=year,
                mode=mode,
                to_class=to_class,
                from_class=from_class,
                opacity=opacity,
                tile_size=tile_size,
            )
        )

    # -------------------------------------------------------------------------
    # Route 5: Annual Tile Endpoint (Dedicated annual route)
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/tiles/annual/{year}/{layer_type}/{z}/{x}/{y}.png')
    async def get_annual_tile(
        identifier: str,
        year: int,
        layer_type: str,
        z: int,
        x: int,
        y: int,
        mode: Optional[str] = Query(None),
        opacity: float = Query(1.0, ge=0.0, le=1.0),
        tile_size: int = Query(256, ge=128, le=512),
    ):
        pair = f'{year}-{year + 1}'
        return await run_in_threadpool(
            lambda: _render_tile_helper(
                identifier=identifier,
                pair=pair,
                z=z,
                x=x,
                y=y,
                layer_type=layer_type,
                year=year,
                mode=mode,
                opacity=opacity,
                tile_size=tile_size,
            )
        )

    # -------------------------------------------------------------------------
    # Route 6: Native Coordinate Pixel Inspection
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/pixel')
    async def query_pixel(
        identifier: str,
        lng: float = Query(..., ge=-180.0, le=180.0),
        lat: float = Query(..., ge=-90.0, le=90.0),
        pair: str = Query('2020-2021'),
        layer_type: str = Query(LAYER_CLASSIFICATION),
        year: Optional[int] = Query(None),
    ):
        def _exec():
            resolved = _resolve_layer_raster(identifier, pair, layer_type=layer_type, year=year)
            if isinstance(resolved, tuple):
                p1, p2 = resolved
                engine = _get_engine(str(p1), tif_path_t2_str=str(p2), layer_type=layer_type)
            else:
                engine = _get_engine(str(resolved), layer_type=layer_type)
            return engine.query_pixel(lng, lat, layer_type=layer_type)

        try:
            res = await run_in_threadpool(_exec)
            return JSONResponse(res, headers=HEADERS)
        except ValueError as exc:
            return _error_response(str(exc))
        except FileNotFoundError:
            return _error_response('NOT_FOUND')
        except PermissionError:
            return _error_response('WORKFLOW_NOT_SUCCEEDED')
        except Exception:
            return _error_response('RESOURCE_UNAVAILABLE')

    # -------------------------------------------------------------------------
    # Route 7: GeoServer WMS 1.3.0 GetCapabilities & GetMap
    # -------------------------------------------------------------------------
    @router.get('/v1/lcluc/workflows/{identifier}/wms')
    async def wms_endpoint(
        request: Request,
        identifier: str,
    ):
        params = {k.upper(): v for k, v in request.query_params.items()}
        service = params.get('SERVICE', 'WMS')
        req_upper = params.get('REQUEST', 'GETCAPABILITIES').upper()
        version = params.get('VERSION', '1.3.0')
        layers = params.get('LAYERS')
        pair = params.get('PAIR', '2020-2021')
        layer_type = params.get('LAYER_TYPE', LAYER_TRANSITIONS)
        year_str = params.get('YEAR')
        year = int(year_str) if year_str else None
        crs = params.get('CRS') or params.get('SRS') or 'EPSG:3857'
        bbox = params.get('BBOX')
        width = int(params.get('WIDTH', 256))
        height = int(params.get('HEIGHT', 256))
        format = params.get('FORMAT', 'image/png')
        transparent = params.get('TRANSPARENT', 'true').lower() in ('true', '1')

        if req_upper == 'GETCAPABILITIES':
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms">
  <Service>
    <Name>WMS</Name>
    <Title>LCLUC Multi-Layer GeoServer Map Service</Title>
    <Abstract>High-performance discrete multi-layer WMS 1.3.0 service for LCLUC classification, quality mask, observation count, and transitions.</Abstract>
  </Service>
  <Capability>
    <Request>
      <GetCapabilities>
        <Format>text/xml</Format>
      </GetCapabilities>
      <GetMap>
        <Format>image/png</Format>
      </GetMap>
    </Request>
    <Layer>
      <Title>LCLUC Workflow {identifier}</Title>
      <CRS>EPSG:4326</CRS>
      <CRS>EPSG:3857</CRS>
      <Layer queryable="1">
        <Name>classification</Name>
        <Title>Annual Discrete 9-Class Land Cover</Title>
      </Layer>
      <Layer queryable="1">
        <Name>quality_mask</Name>
        <Title>Binary Quality Mask (0: Cloud/Invalid, 1: Valid)</Title>
      </Layer>
      <Layer queryable="1">
        <Name>observation_count</Name>
        <Title>Annual Pixel Observation Count</Title>
      </Layer>
      <Layer queryable="1">
        <Name>common_valid</Name>
        <Title>T1/T2 Common Valid Mask</Title>
      </Layer>
      <Layer queryable="1">
        <Name>transitions</Name>
        <Title>LCLUC Categorical Transitions Map</Title>
      </Layer>
    </Layer>
  </Capability>
</WMS_Capabilities>"""
            return Response(content=xml, media_type='text/xml; charset=utf-8', headers=HEADERS)

        elif req_upper == 'GETMAP':
            if not bbox:
                return _error_response('INVALID_REQUEST')

            eff_layer = layers or layer_type
            if eff_layer not in SUPPORTED_LAYER_TYPES:
                eff_layer = LAYER_TRANSITIONS

            target_crs = crs or srs or 'EPSG:3857'

            def _render_wms():
                resolved = _resolve_layer_raster(identifier, pair, layer_type=eff_layer, year=year)
                if isinstance(resolved, tuple):
                    p1, p2 = resolved
                    engine = _get_engine(str(p1), tif_path_t2_str=str(p2), layer_type=eff_layer)
                else:
                    engine = _get_engine(str(resolved), layer_type=eff_layer)

                coords = [float(v.strip()) for v in bbox.split(',')]
                if len(coords) != 4:
                    raise ValueError('INVALID_REQUEST')

                if '4326' in target_crs and version == '1.3.0':
                    miny, minx, maxy, maxx = coords
                else:
                    minx, miny, maxx, maxy = coords

                return engine.render_bbox(
                    min_x=minx,
                    min_y=miny,
                    max_x=maxx,
                    max_y=maxy,
                    srs=target_crs,
                    layer_type=eff_layer,
                    width=width,
                    height=height,
                    format=format,
                    transparent=transparent,
                )

            try:
                png_bytes = await run_in_threadpool(_render_wms)
                return Response(content=png_bytes, media_type=format, headers=HEADERS)
            except ValueError as exc:
                return _error_response(str(exc))
            except FileNotFoundError:
                return _error_response('NOT_FOUND')
            except PermissionError:
                return _error_response('WORKFLOW_NOT_SUCCEEDED')
            except Exception:
                return _error_response('RESOURCE_UNAVAILABLE')

        else:
            return _error_response('INVALID_REQUEST')

    return router
