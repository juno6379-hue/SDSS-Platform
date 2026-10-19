"""Standalone GeoServer WMS 1.3.0 / 1.1.1 Microservice for LCLUC Map & Pixel Service.

Launches a dedicated GeoServer-compatible service instance on port 8088 (or specified port)
serving discrete 9-class land cover GeoTIFF rasters and authoritative 1x1 pixel inspection.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / 'backend')]
sys.path.append(str(PROJECT_ROOT / '.runtime'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import uvicorn

from app.store import Store
from app.tile_router import create_lcluc_tile_router


def create_standalone_geoserver_app(data_root: Path | None = None) -> FastAPI:
    """Create dedicated standalone GeoServer FastAPI application."""
    root = data_root or (PROJECT_ROOT / 'data')
    store = Store(root, recover_jobs=False)

    app = FastAPI(
        title="GeoAI LCLUC GeoServer Service",
        description="GeoServer 2.24+ compatible WMS 1.3.0 and Authoritative Pixel Service",
        version="1.0.0",
    )

    # CORS configuration
    cors_origins = os.getenv(
        'GEOAI_CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://127.0.0.1:8002'
    ).split(',')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=['*'],
    )

    # Mount GeoServer and WMS router
    app.include_router(create_lcluc_tile_router(lambda: store))

    @app.get('/', include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url='/geoserver/web')

    return app


def main():
    parser = argparse.ArgumentParser(description="GeoAI LCLUC Dedicated GeoServer Service")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8088, help='Port to bind (default: 8088)')
    args = parser.parse_args()

    print("=" * 80)
    print(f" [GeoServer] GeoAI LCLUC Discrete Classification WMS Service")
    print(f" [GeoServer] Web Administration Console: http://{args.host}:{args.port}/geoserver/web")
    print(f" [GeoServer] WMS 1.3.0 GetCapabilities:  http://{args.host}:{args.port}/geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities")
    print(f" [GeoServer] WMS 1.1.1 GetCapabilities:  http://{args.host}:{args.port}/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities")
    print(f" [GeoServer] Authoritative Pixel API:    http://{args.host}:{args.port}/v1/lcluc/pixel")
    print("=" * 80)

    app = create_standalone_geoserver_app()
    uvicorn.run(app, host=args.host, port=args.port, log_level='info')


if __name__ == '__main__':
    main()
