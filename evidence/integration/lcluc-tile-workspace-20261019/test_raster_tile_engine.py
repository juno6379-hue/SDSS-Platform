"""Comprehensive Unit Tests and Benchmarks for LCLUC Raster Tile Engine and Router.

Tests:
1. Tile coordinate validation and Slippy map bounds computation.
2. RasterTileEngine spatial bounds and intersection detection.
3. Out-of-bounds tile fast transparent PNG return.
4. Color mapping fidelity (nodata, unchanged transparency, changed RGB accuracy).
5. Filter modes (changes_only, all, to_class, opacity).
6. Performance benchmarks (< 50ms per tile).
7. FastAPI router endpoints (GET tile, GET info, error handling, security constraints).
"""
import io
import math
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from .raster_tile_engine import (
        EARTH_RADIUS,
        EMPTY_TILE_PNG,
        NODATA_VALUE,
        ORIGIN_SHIFT,
        WORKFLOW_CLASS_COLORS,
        LAYER_CLASSIFICATION,
        LAYER_QUALITY_MASK,
        LAYER_OBSERVATION_COUNT,
        LAYER_COMMON_VALID,
        LAYER_TRANSITIONS,
        SUPPORTED_LAYER_TYPES,
        RasterTileEngine,
        hex_to_rgb,
        tile_bounds_3857,
        validate_tile_coords,
        get_classification_lut,
        get_quality_mask_lut,
        get_observation_count_lut,
        get_common_valid_lut,
        get_layer_lut,
    )
    from .tile_router import create_lcluc_tile_router
except ImportError:
    from raster_tile_engine import (
        EARTH_RADIUS,
        EMPTY_TILE_PNG,
        NODATA_VALUE,
        ORIGIN_SHIFT,
        WORKFLOW_CLASS_COLORS,
        LAYER_CLASSIFICATION,
        LAYER_QUALITY_MASK,
        LAYER_OBSERVATION_COUNT,
        LAYER_COMMON_VALID,
        LAYER_TRANSITIONS,
        SUPPORTED_LAYER_TYPES,
        RasterTileEngine,
        hex_to_rgb,
        tile_bounds_3857,
        validate_tile_coords,
        get_classification_lut,
        get_quality_mask_lut,
        get_observation_count_lut,
        get_common_valid_lut,
        get_layer_lut,
    )
    from tile_router import create_lcluc_tile_router


class MockStore:
    """Minimal mock store simulating the project Store for testing."""

    def __init__(self, root: Path):
        self.root = root
        self._data = {}

    def put(self, kind: str, record: dict):
        self._data[(kind, record['id'])] = record

    def get(self, kind: str, identifier: str) -> dict:
        key = (kind, identifier)
        if key not in self._data:
            raise KeyError(identifier)
        return self._data[key]


class RasterTileEngineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)

        # Create a synthetic transitions.tif in EPSG:3857
        # Region: Singapore / equatorial region around (11570000, 150000)
        # Width: 128, Height: 128, Pixel size: 10m x 10m
        cls.origin_x = 11570000.0
        cls.origin_y = 150000.0
        cls.pixel_size = 20.0
        cls.width = 128
        cls.height = 128
        cls.transform = from_origin(cls.origin_x, cls.origin_y, cls.pixel_size, cls.pixel_size)

        # Transition codes matrix:
        # 0: Water->Water (unchanged)
        # 10: Forest->Forest (unchanged)
        # 6: Water->Urban (changed to Urban=6)
        # 15: Forest->Urban (changed to Urban=6)
        # 19: Grassland->Forest (changed to Forest=1)
        # 65535: NODATA
        data = np.full((cls.height, cls.width), NODATA_VALUE, dtype=np.uint16)
        # Top-left quadrant: Water->Water (0)
        data[0:64, 0:64] = 0
        # Top-right quadrant: Forest->Urban (15: 1*9 + 6)
        data[0:64, 64:128] = 15
        # Bottom-left quadrant: Grassland->Forest (19: 2*9 + 1)
        data[64:128, 0:64] = 19
        # Bottom-right quadrant: NODATA (65535)

        cls.tif_path = cls.root / 'transitions.tif'
        with rasterio.open(
            cls.tif_path,
            'w',
            driver='GTiff',
            width=cls.width,
            height=cls.height,
            count=1,
            dtype='uint16',
            crs='EPSG:3857',
            transform=cls.transform,
            nodata=NODATA_VALUE,
        ) as dst:
            dst.write(data, 1)

        # Find intersecting tile coordinate at zoom 14
        # (x, y) = int((coord + ORIGIN_SHIFT) / span)
        span_z14 = (2.0 * ORIGIN_SHIFT) / (1 << 14)
        center_x = cls.origin_x + (cls.width * cls.pixel_size) / 2
        center_y = cls.origin_y - (cls.height * cls.pixel_size) / 2
        cls.z14_x = int((center_x + ORIGIN_SHIFT) / span_z14)
        cls.z14_y = int((ORIGIN_SHIFT - center_y) / span_z14)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_tile_coord_validation(self):
        """Test strict validation of z, x, y coordinates."""
        # Valid coordinates
        validate_tile_coords(0, 0, 0)
        validate_tile_coords(14, self.z14_x, self.z14_y)
        validate_tile_coords(24, (1 << 24) - 1, (1 << 24) - 1)

        # Out of bounds zoom
        with self.assertRaises(ValueError):
            validate_tile_coords(-1, 0, 0)
        with self.assertRaises(ValueError):
            validate_tile_coords(25, 0, 0)

        # Out of bounds x and y
        with self.assertRaises(ValueError):
            validate_tile_coords(2, 4, 0)  # max x for z=2 is 3
        with self.assertRaises(ValueError):
            validate_tile_coords(2, 0, 4)
        with self.assertRaises(ValueError):
            validate_tile_coords(2, -1, 0)

        # Invalid type
        with self.assertRaises(TypeError):
            validate_tile_coords('14', 10, 10)  # type: ignore

    def test_tile_bounds_3857(self):
        """Test calculation of tile bounds in EPSG:3857."""
        # Zoom 0 covers world
        min_x, min_y, max_x, max_y = tile_bounds_3857(0, 0, 0)
        self.assertAlmostEqual(min_x, -ORIGIN_SHIFT, places=3)
        self.assertAlmostEqual(max_x, ORIGIN_SHIFT, places=3)
        self.assertAlmostEqual(min_y, -ORIGIN_SHIFT, places=3)
        self.assertAlmostEqual(max_y, ORIGIN_SHIFT, places=3)

        # Zoom 1 tile (0, 0) covers northwest quadrant
        z1_minx, z1_miny, z1_maxx, z1_maxy = tile_bounds_3857(1, 0, 0)
        self.assertAlmostEqual(z1_minx, -ORIGIN_SHIFT, places=3)
        self.assertAlmostEqual(z1_maxx, 0.0, places=3)
        self.assertAlmostEqual(z1_miny, 0.0, places=3)
        self.assertAlmostEqual(z1_maxy, ORIGIN_SHIFT, places=3)

    def test_out_of_bounds_fast_return(self):
        """Out of bounds tile should immediately return transparent PNG."""
        engine = RasterTileEngine(self.tif_path)
        # Tile (14, 0, 0) is in northwestern Alaska/Bering Strait, far from Singapore
        self.assertFalse(engine.intersects(*tile_bounds_3857(14, 0, 0)))

        png_bytes = engine.render_tile(14, 0, 0)
        self.assertEqual(png_bytes, EMPTY_TILE_PNG)

        # Inspect PNG
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (256, 256))
        self.assertEqual(img.mode, 'RGBA')
        # All pixels must have alpha = 0
        arr = np.array(img)
        self.assertTrue(np.all(arr[:, :, 3] == 0))

    def test_color_mapping_fidelity(self):
        """Verify color mapping for changes_only mode vs all mode."""
        engine = RasterTileEngine(self.tif_path)
        self.assertTrue(engine.intersects(*tile_bounds_3857(14, self.z14_x, self.z14_y)))

        # 1. Mode: changes_only
        png_bytes = engine.render_tile(14, self.z14_x, self.z14_y, mode='changes_only')
        img = Image.open(io.BytesIO(png_bytes))
        arr = np.array(img)
        self.assertEqual(arr.shape, (256, 256, 4))

        # Check colors:
        # Target urban color is WORKFLOW_CLASS_COLORS[6] ('#dc2626' -> RGB(220, 38, 38))
        urban_rgb = hex_to_rgb(WORKFLOW_CLASS_COLORS[6])
        # Target forest color is WORKFLOW_CLASS_COLORS[1] ('#15803d' -> RGB(21, 128, 61))
        forest_rgb = hex_to_rgb(WORKFLOW_CLASS_COLORS[1])

        # Pixels with alpha > 0 must be changed pixels matching urban_rgb or forest_rgb
        visible_mask = arr[:, :, 3] > 0
        self.assertTrue(np.any(visible_mask), "Should contain visible changed pixels")

        visible_pixels = arr[visible_mask]
        rgb_tuples = set(map(tuple, visible_pixels[:, :3]))
        self.assertIn(urban_rgb, rgb_tuples)
        self.assertIn(forest_rgb, rgb_tuples)

        # 2. Mode: filter to_class = 6 (Urban only)
        png_urban = engine.render_tile(
            14, self.z14_x, self.z14_y, mode='changes_only', to_class=6
        )
        arr_urban = np.array(Image.open(io.BytesIO(png_urban)))
        urban_mask = arr_urban[:, :, 3] > 0
        self.assertTrue(np.any(urban_mask))
        urban_visible = arr_urban[urban_mask]
        for p in urban_visible:
            self.assertEqual(tuple(p[:3]), urban_rgb)

        # 3. Opacity scaling
        png_half_opacity = engine.render_tile(
            14, self.z14_x, self.z14_y, mode='changes_only', opacity=0.5
        )
        arr_half = np.array(Image.open(io.BytesIO(png_half_opacity)))
        half_visible = arr_half[arr_half[:, :, 3] > 0]
        # Alpha should be round(0.5 * 255) = 128
        self.assertAlmostEqual(int(half_visible[0, 3]), 128, delta=2)

    def test_epsg4326_reprojection_tiling(self):
        """Verify seamless reprojection and tile rendering for datasets in EPSG:4326."""
        wgs_tif = self.root / 'transitions_wgs84.tif'
        # Geographic bounds around Central Sulawesi, Indonesia: lon 120.0, lat -1.0
        wgs_transform = from_origin(120.0, -1.0, 0.001, 0.001)
        wgs_data = np.full((64, 64), 6, dtype=np.uint16)  # Water->Urban (code 6)
        with rasterio.open(
            wgs_tif,
            'w',
            driver='GTiff',
            width=64,
            height=64,
            count=1,
            dtype='uint16',
            crs='EPSG:4326',
            transform=wgs_transform,
            nodata=NODATA_VALUE,
        ) as dst:
            dst.write(wgs_data, 1)

        engine_wgs = RasterTileEngine(wgs_tif)
        info = engine_wgs.get_raster_info()
        self.assertIn('EPSG:4326', info['crs'])

        # Calculate intersecting tile at zoom 12
        # EPSG:3857 coords for (120.0, -1.0):
        # x = 120 * ORIGIN_SHIFT / 180
        # y = log(tan((90 + (-1)) * pi / 360)) / (pi / 180) * ORIGIN_SHIFT / 180
        lat_rad = math.radians(-1.0)
        merc_x = 120.0 * ORIGIN_SHIFT / 180.0
        merc_y = math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0)) * EARTH_RADIUS
        span_z12 = (2.0 * ORIGIN_SHIFT) / (1 << 12)
        z12_x = int((merc_x + ORIGIN_SHIFT) / span_z12)
        z12_y = int((ORIGIN_SHIFT - merc_y) / span_z12)

        self.assertTrue(engine_wgs.intersects(*tile_bounds_3857(12, z12_x, z12_y)))
        png_bytes = engine_wgs.render_tile(12, z12_x, z12_y, mode='changes_only')
        self.assertTrue(png_bytes.startswith(b'\x89PNG\r\n\x1a\n'))
        arr = np.array(Image.open(io.BytesIO(png_bytes)))
        # Must contain urban red pixels (220, 38, 38)
        self.assertTrue(np.any(arr[:, :, 3] > 0))
        visible = arr[arr[:, :, 3] > 0]
        self.assertEqual(tuple(visible[0, :3]), hex_to_rgb(WORKFLOW_CLASS_COLORS[6]))

    def test_performance_benchmark(self):
        """Verify tile generation finishes within 50ms (benchmarked over 50 renders)."""
        engine = RasterTileEngine(self.tif_path)

        # Warm-up run
        _ = engine.render_tile(14, self.z14_x, self.z14_y)

        # Benchmark 50 iterations on intersecting tile
        iterations = 50
        start = time.perf_counter()
        for _ in range(iterations):
            tile = engine.render_tile(14, self.z14_x, self.z14_y)
            self.assertTrue(len(tile) > 0)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000.0

        print(f"\n[BENCHMARK] Average in-bounds tile render time: {avg_ms:.2f} ms")
        self.assertLess(avg_ms, 50.0, f"Average tile rendering exceeded 50ms limit: {avg_ms:.2f} ms")

        # Benchmark out-of-bounds tile (< 1ms)
        start_oob = time.perf_counter()
        for _ in range(100):
            _ = engine.render_tile(14, 0, 0)
        elapsed_oob = time.perf_counter() - start_oob
        avg_oob_ms = (elapsed_oob / 100) * 1000.0
        print(f"[BENCHMARK] Average out-of-bounds tile time: {avg_oob_ms:.3f} ms")
        self.assertLess(avg_oob_ms, 2.0)


class TileRouterApiTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = MockStore(self.root)

        # Workflow ID & pair
        self.workflow_id = 'a' * 64
        self.pair = '2020-2021'

        # Set up folder structure matching lcluc-workflows
        change_dir = self.root / 'results' / 'lcluc-workflows' / self.workflow_id / 'changes' / self.pair
        change_dir.mkdir(parents=True, exist_ok=True)
        self.tif_path = change_dir / 'transitions.tif'

        # Create dummy transitions.tif
        transform = from_origin(11570000.0, 150000.0, 20.0, 20.0)
        data = np.full((64, 64), 15, dtype=np.uint16)  # Forest->Urban
        with rasterio.open(
            self.tif_path,
            'w',
            driver='GTiff',
            width=64,
            height=64,
            count=1,
            dtype='uint16',
            crs='EPSG:3857',
            transform=transform,
            nodata=NODATA_VALUE,
        ) as dst:
            dst.write(data, 1)

        # Register workflow in store with SUCCEEDED status
        self.store.put('lcluc-workflows', {
            'id': self.workflow_id,
            'status': 'SUCCEEDED',
            'artifacts': [
                {'path': f'results/lcluc-workflows/{self.workflow_id}/changes/{self.pair}/transitions.tif',
                 'sha256': 'mock-sha'}
            ],
        })

        # Set up FastAPI test client
        self.app = FastAPI()
        self.app.include_router(create_lcluc_tile_router(lambda: self.store, cache_tiles=True))
        self.client = TestClient(self.app)

        # Intersecting tile coords
        span_z14 = (2.0 * ORIGIN_SHIFT) / (1 << 14)
        self.z14_x = int((11570000.0 + ORIGIN_SHIFT) / span_z14)
        self.z14_y = int((ORIGIN_SHIFT - 150000.0) / span_z14)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tile_info_endpoint(self):
        """GET /v1/lcluc/workflows/{id}/tiles/{pair}/info returns MapLibre source configuration."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/info'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data['workflow_id'], self.workflow_id)
        self.assertEqual(data['pair'], self.pair)
        self.assertIn('maplibre_source', data)
        self.assertEqual(data['maplibre_source']['type'], 'raster')
        self.assertEqual(data['maplibre_source']['tileSize'], 256)
        self.assertEqual(len(data['maplibre_source']['bounds']), 4)

    def test_get_tile_success(self):
        """GET /v1/lcluc/workflows/{id}/tiles/{pair}/{z}/{x}/{y}.png returns PNG image."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/14/{self.z14_x}/{self.z14_y}.png'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.headers['content-type'], 'image/png')
        self.assertIn('public, max-age=86400, immutable', res.headers['cache-control'])
        self.assertTrue(res.content.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_get_tile_query_params(self):
        """Test query parameters mode, to_class, opacity."""
        # 1. to_class matching (Urban = 6) -> has visible pixels
        url = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/14/{self.z14_x}/{self.z14_y}.png?to_class=6'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        arr = np.array(Image.open(io.BytesIO(res.content)))
        self.assertTrue(np.any(arr[:, :, 3] > 0))

        # 2. to_class mismatching (Water = 0) -> all transparent
        url_water = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/14/{self.z14_x}/{self.z14_y}.png?to_class=0'
        res_water = self.client.get(url_water)
        self.assertEqual(res_water.status_code, 200)
        arr_water = np.array(Image.open(io.BytesIO(res_water.content)))
        self.assertTrue(np.all(arr_water[:, :, 3] == 0))

    def test_get_tile_out_of_bounds_returns_transparent_png(self):
        """Out of bounds tile coordinate should return 200 OK with transparent PNG."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/14/0/0.png'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, EMPTY_TILE_PNG)

    def test_get_tile_invalid_coords(self):
        """Invalid coordinate returns 400 INVALID_REQUEST."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/2/10/10.png'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['code'], 'INVALID_REQUEST')

    def test_get_tile_invalid_id_or_pair(self):
        """Invalid ID or pair format returns 400 INVALID_REQUEST."""
        res1 = self.client.get(f'/v1/lcluc/workflows/short_id/tiles/{self.pair}/14/0/0.png')
        self.assertEqual(res1.status_code, 400)
        res2 = self.client.get(f'/v1/lcluc/workflows/{self.workflow_id}/tiles/bad-pair/14/0/0.png')
        self.assertEqual(res2.status_code, 400)

    def test_get_tile_workflow_not_found(self):
        """Non-existent workflow returns 404 NOT_FOUND."""
        bad_id = 'b' * 64
        url = f'/v1/lcluc/workflows/{bad_id}/tiles/{self.pair}/14/{self.z14_x}/{self.z14_y}.png'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()['error']['code'], 'NOT_FOUND')

    def test_get_tile_workflow_not_succeeded(self):
        """Workflow not in SUCCEEDED state returns 409 WORKFLOW_NOT_SUCCEEDED."""
        running_id = 'c' * 64
        self.store.put('lcluc-workflows', {
            'id': running_id,
            'status': 'RUNNING',
            'artifacts': [],
        })
        url = f'/v1/lcluc/workflows/{running_id}/tiles/{self.pair}/14/{self.z14_x}/{self.z14_y}.png'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['error']['code'], 'WORKFLOW_NOT_SUCCEEDED')


class MultiLayerRasterTileEngineTests(unittest.TestCase):
    """Unit tests for the 5 LCLUC layer types and their LUT mappings."""

    def test_classification_lut_and_transparency(self):
        """Test classification LUT for 9 classes, WorldCover codes, and transparent NoData."""
        lut = get_classification_lut(alpha=255, num_classes=9)
        # 0: Water (#2563eb -> 37, 99, 235)
        self.assertEqual(tuple(lut[0]), (37, 99, 235, 255))
        # 1: Trees (#15803d -> 21, 128, 61)
        self.assertEqual(tuple(lut[1]), (21, 128, 61, 255))
        # WorldCover code 10 -> Trees
        self.assertEqual(tuple(lut[10]), (21, 128, 61, 255))
        # WorldCover code 80 -> Water
        self.assertEqual(tuple(lut[80]), (37, 99, 235, 255))
        # NoData: 255 and 65535 must be completely transparent
        self.assertEqual(tuple(lut[255]), (0, 0, 0, 0))
        self.assertEqual(tuple(lut[65535]), (0, 0, 0, 0))

    def test_quality_mask_lut_and_modes(self):
        """Test quality mask LUT: 0=Cloud/Red, 1=Valid/Green, and transparent NoData."""
        lut_all = get_quality_mask_lut(mode='all', alpha=255)
        # 0: Cloud / Invalid (#ef4444 -> 239, 68, 68)
        self.assertEqual(tuple(lut_all[0]), (239, 68, 68, 255))
        # 1: Valid (#22c55e -> 34, 197, 94)
        self.assertEqual(tuple(lut_all[1]), (34, 197, 94, 255))
        # NoData transparent
        self.assertEqual(tuple(lut_all[255]), (0, 0, 0, 0))
        self.assertEqual(tuple(lut_all[65535]), (0, 0, 0, 0))

        # Mode 'invalid_only': 1 is transparent, 0 is red
        lut_inv = get_quality_mask_lut(mode='invalid_only', alpha=200)
        self.assertEqual(tuple(lut_inv[0]), (239, 68, 68, 200))
        self.assertEqual(tuple(lut_inv[1]), (0, 0, 0, 0))

        # Mode 'valid_only': 0 is transparent, 1 is green
        lut_val = get_quality_mask_lut(mode='valid_only', alpha=200)
        self.assertEqual(tuple(lut_val[0]), (0, 0, 0, 0))
        self.assertEqual(tuple(lut_val[1]), (34, 197, 94, 200))

    def test_observation_count_lut(self):
        """Test observation count LUT: 0..6+ ramp and transparent NoData."""
        lut = get_observation_count_lut(mode='all', alpha=255)
        # 0 obs: dark red (153, 27, 27)
        self.assertEqual(tuple(lut[0]), (153, 27, 27, 255))
        # 1 obs: red (239, 68, 68)
        self.assertEqual(tuple(lut[1]), (239, 68, 68, 255))
        # 6 obs: deep green (21, 128, 61)
        self.assertEqual(tuple(lut[6]), (21, 128, 61, 255))
        # 12 obs: saturated deep green
        self.assertEqual(tuple(lut[12]), (21, 128, 61, 255))
        # NoData transparent
        self.assertEqual(tuple(lut[255]), (0, 0, 0, 0))
        self.assertEqual(tuple(lut[65535]), (0, 0, 0, 0))

    def test_common_valid_lut_and_dual_raster_rendering(self):
        """Test common valid LUT and on-the-fly dual raster common valid rendering."""
        lut = get_common_valid_lut(mode='all', alpha=255)
        # 0: Invalid / gap (239, 68, 68)
        self.assertEqual(tuple(lut[0]), (239, 68, 68, 255))
        # 1: Common Valid (59, 130, 246)
        self.assertEqual(tuple(lut[1]), (59, 130, 246, 255))
        # NoData transparent
        self.assertEqual(tuple(lut[255]), (0, 0, 0, 0))
        self.assertEqual(tuple(lut[65535]), (0, 0, 0, 0))

        # Create dual synthetic quality masks in temp dir
        with tempfile.TemporaryDirectory() as td:
            t_dir = Path(td)
            t1_path = t_dir / 't1_quality_mask.tif'
            t2_path = t_dir / 't2_quality_mask.tif'

            transform = from_origin(11570000.0, 150000.0, 20.0, 20.0)
            data1 = np.full((64, 64), 1, dtype=np.uint8)  # all valid
            data2 = np.full((64, 64), 1, dtype=np.uint8)
            # Quadrant 2: T2 has cloud (0) -> common valid should be 0 (Red)
            data2[0:32, 32:64] = 0
            # Quadrant 4: T1 has NoData (255) -> common valid should be NoData (transparent)
            data1[32:64, 32:64] = 255

            for p, d in [(t1_path, data1), (t2_path, data2)]:
                with rasterio.open(
                    p, 'w', driver='GTiff', width=64, height=64, count=1,
                    dtype='uint8', crs='EPSG:3857', transform=transform, nodata=255
                ) as dst:
                    dst.write(d, 1)

            # Test dual raster engine
            engine = RasterTileEngine(t1_path, tif_path_t2=t2_path, layer_type=LAYER_COMMON_VALID)
            span_z14 = (2.0 * ORIGIN_SHIFT) / (1 << 14)
            z14_x = int((11570000.0 + ORIGIN_SHIFT) / span_z14)
            z14_y = int((ORIGIN_SHIFT - 150000.0) / span_z14)

            png_bytes = engine.render_tile(14, z14_x, z14_y, layer_type=LAYER_COMMON_VALID)
            arr = np.array(Image.open(io.BytesIO(png_bytes)))

            # Check that valid common pixels are colored Blue (R=59, G=130, B=246)
            self.assertTrue(np.any((arr[:, :, 0] == 59) & (arr[:, :, 1] == 130) & (arr[:, :, 2] == 246)))
            # Check that cloud gap pixels are colored Red (R=239, G=68, B=68)
            self.assertTrue(np.any((arr[:, :, 0] == 239) & (arr[:, :, 1] == 68) & (arr[:, :, 2] == 68)))
            # Check that NoData quadrant has transparent pixels
            self.assertTrue(np.any(arr[:, :, 3] == 0))


class MultiLayerTileRouterApiTests(unittest.TestCase):
    """API endpoint tests for all 5 layer types, WMS 1.3.0, and pixel query."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = MockStore(self.root)
        self.workflow_id = 'd' * 64
        self.pair = '2020-2021'

        ns = self.root / 'results' / 'lcluc-workflows' / self.workflow_id
        changes_dir = ns / 'changes' / self.pair
        annual_2020_dir = ns / 'annual' / '2020'
        annual_2021_dir = ns / 'annual' / '2021'
        changes_dir.mkdir(parents=True, exist_ok=True)
        annual_2020_dir.mkdir(parents=True, exist_ok=True)
        annual_2021_dir.mkdir(parents=True, exist_ok=True)

        transform = from_origin(11570000.0, 150000.0, 20.0, 20.0)

        # 1. transitions.tif
        with rasterio.open(
            changes_dir / 'transitions.tif', 'w', driver='GTiff',
            width=64, height=64, count=1, dtype='uint16', crs='EPSG:3857',
            transform=transform, nodata=NODATA_VALUE
        ) as dst:
            dst.write(np.full((64, 64), 15, dtype=np.uint16), 1)

        # 2. common_valid.tif
        with rasterio.open(
            changes_dir / 'common_valid.tif', 'w', driver='GTiff',
            width=64, height=64, count=1, dtype='uint8', crs='EPSG:3857',
            transform=transform, nodata=255
        ) as dst:
            dst.write(np.full((64, 64), 1, dtype=np.uint8), 1)

        # 3. classification.tif (2020)
        with rasterio.open(
            annual_2020_dir / 'classification.tif', 'w', driver='GTiff',
            width=64, height=64, count=1, dtype='uint8', crs='EPSG:3857',
            transform=transform, nodata=255
        ) as dst:
            dst.write(np.full((64, 64), 1, dtype=np.uint8), 1)  # Trees

        # 4. quality_mask.tif (2020)
        with rasterio.open(
            annual_2020_dir / 'quality_mask.tif', 'w', driver='GTiff',
            width=64, height=64, count=1, dtype='uint8', crs='EPSG:3857',
            transform=transform, nodata=255
        ) as dst:
            dst.write(np.full((64, 64), 1, dtype=np.uint8), 1)  # Valid

        # 5. observation_count.tif (2020)
        with rasterio.open(
            annual_2020_dir / 'observation_count.tif', 'w', driver='GTiff',
            width=64, height=64, count=1, dtype='uint8', crs='EPSG:3857',
            transform=transform, nodata=255
        ) as dst:
            dst.write(np.full((64, 64), 5, dtype=np.uint8), 1)  # 5 observations

        self.store.put('lcluc-workflows', {
            'id': self.workflow_id,
            'status': 'SUCCEEDED',
            'artifacts': [],
        })

        self.app = FastAPI()
        self.app.include_router(create_lcluc_tile_router(lambda: self.store))
        self.client = TestClient(self.app)

        span_z14 = (2.0 * ORIGIN_SHIFT) / (1 << 14)
        self.z14_x = int((11570000.0 + ORIGIN_SHIFT) / span_z14)
        self.z14_y = int((ORIGIN_SHIFT - 150000.0) / span_z14)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_five_layer_tile_endpoints(self):
        """Test GET tiles for classification, quality_mask, observation_count, common_valid, transitions."""
        for layer in SUPPORTED_LAYER_TYPES:
            # Query param syntax
            res1 = self.client.get(
                f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/14/{self.z14_x}/{self.z14_y}.png?layer_type={layer}'
            )
            self.assertEqual(res1.status_code, 200, f'Failed for layer {layer}: {res1.text}')
            self.assertEqual(res1.headers['content-type'], 'image/png')
            self.assertTrue(res1.content.startswith(b'\x89PNG\r\n\x1a\n'))

            # Path syntax
            res2 = self.client.get(
                f'/v1/lcluc/workflows/{self.workflow_id}/tiles/{self.pair}/{layer}/14/{self.z14_x}/{self.z14_y}.png'
            )
            self.assertEqual(res2.status_code, 200, f'Failed for path layer {layer}: {res2.text}')

    def test_annual_tile_endpoint(self):
        """Test GET /v1/lcluc/workflows/{id}/tiles/annual/{year}/{layer_type}/{z}/{x}/{y}.png."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/tiles/annual/2020/quality_mask/14/{self.z14_x}/{self.z14_y}.png'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.headers['content-type'], 'image/png')

    def test_pixel_query_endpoint(self):
        """Test GET /v1/lcluc/workflows/{id}/pixel for native raster query."""
        # Query center coordinate of test raster in EPSG:3857 -> WGS84
        lng, lat = transform_bounds('EPSG:3857', 'EPSG:4326', 11570640.0, 149360.0, 11570640.0, 149360.0)[:2]
        url = f'/v1/lcluc/workflows/{self.workflow_id}/pixel?lng={lng}&lat={lat}&layer_type=classification&year=2020'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['class_id'], 1)
        self.assertEqual(data['class_name'], 'Trees')
        self.assertFalse(data['is_nodata'])

    def test_wms_capabilities_and_getmap(self):
        """Test WMS 1.3.0 GetCapabilities and GetMap."""
        # GetCapabilities
        cap_res = self.client.get(f'/v1/lcluc/workflows/{self.workflow_id}/wms?REQUEST=GetCapabilities')
        self.assertEqual(cap_res.status_code, 200)
        self.assertIn('text/xml', cap_res.headers['content-type'])
        self.assertIn('WMS_Capabilities', cap_res.text)
        self.assertIn('quality_mask', cap_res.text)

        # GetMap
        bbox = f'{11570000.0},{148000.0},{11571000.0},{150000.0}'
        map_url = (
            f'/v1/lcluc/workflows/{self.workflow_id}/wms?REQUEST=GetMap&LAYERS=quality_mask'
            f'&CRS=EPSG:3857&BBOX={bbox}&WIDTH=256&HEIGHT=256&FORMAT=image/png'
        )
        map_res = self.client.get(map_url)
        self.assertEqual(map_res.status_code, 200, map_res.text)
        self.assertEqual(map_res.headers['content-type'], 'image/png')


if __name__ == '__main__':
    unittest.main()

