"""Unit Tests for GeoServer WMS, SLD, Discrete 9-Class Rendering, and Exact Pixel Query.

Verifies:
1. Authoritative SLD structure: ColorMap type="values", 9 hex colors, transparent NoData (255, 65535), nearest resampling VendorOption.
2. RasterTileEngine discrete classification LUT and nearest-neighbor bbox rendering.
3. Exact pixel query accuracy on real First Group GeoTIFF (banten-2021/label-worldcover.tif) without screen RGB guessing.
4. FastAPI WMS GetCapabilities and GetMap endpoints.
5. FastAPI /v1/lcluc/pixel endpoint with coordinates, class IDs, and provenance.
"""
import io
import math
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.ml.raster_tile_engine import (
    CLASS_NAMES,
    WORKFLOW_CLASS_COLORS,
    WORLDCOVER_TO_CLASS,
    RasterTileEngine,
    get_discrete_lut,
    hex_to_rgb,
)
from backend.app.tile_router import create_lcluc_tile_router


class MockStore:
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


class GeoServerSldAndDiscreteServiceTests(unittest.TestCase):

    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]
        self.sld_path = self.project_root / 'evidence' / 'geoserver' / 'sld' / 'lcluc_discrete_9classes.sld'
        self.real_banten_tif = self.project_root / 'data' / 'first-group-2021' / 'banten-2021' / 'label-worldcover.tif'

    def test_sld_file_structure_and_discrete_rules(self):
        """Verify SLD file contains discrete ColorMap type='values', 9 colors, transparent NoData, and nearest vendor option."""
        self.assertTrue(self.sld_path.is_file(), f'SLD file not found at {self.sld_path}')

        tree = ET.parse(self.sld_path)
        root = tree.getroot()

        # Check namespaces
        ns = {'sld': 'http://www.opengis.net/sld'}

        # Find ColorMap element
        color_maps = root.findall('.//sld:ColorMap', ns)
        self.assertEqual(len(color_maps), 1, 'Should have exactly one ColorMap')
        cmap = color_maps[0]
        self.assertEqual(cmap.get('type'), 'values', 'ColorMap must have type="values" for discrete classes')

        # Check ColorMapEntry elements
        entries = cmap.findall('sld:ColorMapEntry', ns)
        entry_map = {}
        for entry in entries:
            qty = entry.get('quantity')
            color = entry.get('color')
            opacity = entry.get('opacity', '1.0')
            entry_map[qty] = {'color': color.lower() if color else None, 'opacity': opacity}

        # Verify 9 standard classes (0..8)
        expected_colors = {
            '0': '#2563eb',  # Water
            '1': '#15803d',  # Trees
            '2': '#84cc16',  # Grass
            '3': '#14b8a6',  # Flooded vegetation
            '4': '#eab308',  # Crops
            '5': '#a16207',  # Shrub & scrub
            '6': '#dc2626',  # Built area
            '7': '#a8a29e',  # Bare ground
            '8': '#a5d8f3',  # Snow & ice
        }
        for q, hex_val in expected_colors.items():
            self.assertIn(q, entry_map, f'Missing quantity {q} in SLD')
            self.assertEqual(entry_map[q]['color'], hex_val, f'Color mismatch for quantity {q}')
            self.assertEqual(entry_map[q]['opacity'], '1.0', f'Opacity should be 1.0 for valid class {q}')

        # Verify transparent NoData entries
        self.assertIn('255', entry_map)
        self.assertEqual(float(entry_map['255']['opacity']), 0.0)
        self.assertIn('65535', entry_map)
        self.assertEqual(float(entry_map['65535']['opacity']), 0.0)

        # Verify Nearest Neighbor vendor option
        vendor_options = root.findall('.//sld:VendorOption', ns)
        resampling_opt = [vo for vo in vendor_options if vo.get('name') == 'resampling']
        self.assertTrue(len(resampling_opt) >= 1, 'Must have VendorOption name="resampling"')
        self.assertEqual(resampling_opt[0].text.strip(), 'nearest', 'VendorOption resampling must be nearest')

    def test_discrete_classification_lut_fidelity(self):
        """Verify discrete classification LUT properly maps 0..8 to RGB_PALETTE and nodata to transparent."""
        # 1. Project 9-class discrete LUT
        lut_9 = get_discrete_lut(scheme='project_9class', alpha=255)
        self.assertEqual(lut_9.shape, (65536, 4))

        for c in range(9):
            rgb = hex_to_rgb(WORKFLOW_CLASS_COLORS[c])
            self.assertEqual(tuple(lut_9[c, :3]), rgb)
            self.assertEqual(lut_9[c, 3], 255)

        # NoData entries
        self.assertEqual(lut_9[255, 3], 0)
        self.assertEqual(lut_9[65535, 3], 0)

        # 2. WorldCover discrete LUT
        lut_wc = get_discrete_lut(scheme='worldcover', alpha=255)
        # 10 is Tree cover -> Trees (1) -> #15803d
        self.assertEqual(tuple(lut_wc[10, :3]), hex_to_rgb(WORKFLOW_CLASS_COLORS[1]))
        self.assertEqual(lut_wc[10, 3], 255)
        # 50 is Built-up -> Built area (6) -> #dc2626
        self.assertEqual(tuple(lut_wc[50, :3]), hex_to_rgb(WORKFLOW_CLASS_COLORS[6]))
        # 80 is Water -> Water (0) -> #2563eb
        self.assertEqual(tuple(lut_wc[80, :3]), hex_to_rgb(WORKFLOW_CLASS_COLORS[0]))
        # 0 is NoData in WorldCover
        self.assertEqual(lut_wc[0, 3], 0)

    def test_real_geotiff_exact_pixel_query(self):
        """Authoritative pixel query on real Banten 2021 WorldCover GeoTIFF without screen RGB guessing."""
        if not self.real_banten_tif.is_file():
            self.skipTest(f'Real file {self.real_banten_tif} not available')

        engine = RasterTileEngine(self.real_banten_tif)
        self.assertEqual(engine.scheme, 'worldcover')

        # Center coordinate of Banten 2021
        lon_center = 106.1343
        lat_center = -6.4375

        res = engine.query_pixel(lng=lon_center, lat=lat_center)
        self.assertTrue(res['valid'])
        self.assertFalse(res['nodata'])
        self.assertEqual(res['raw_value'], 10)  # WorldCover Tree cover code
        self.assertEqual(res['class_id'], 1)   # Project class 1 (Trees)
        self.assertEqual(res['class_name'], 'Trees')
        self.assertEqual(res['color'], '#15803d')
        self.assertEqual(res['native_crs'], 'EPSG:32748')
        self.assertEqual(res['pixel_resolution_m'], [10.0, 10.0])

        # Query point completely outside raster bounds (e.g. London: lon 0.0, lat 51.5)
        res_oob = engine.query_pixel(lng=0.0, lat=51.5)
        self.assertFalse(res_oob['valid'])
        self.assertTrue(res_oob['nodata'])
        self.assertEqual(res_oob['reason'], 'outside_raster_bounds')

    def test_wms_getmap_render_bbox(self):
        """Verify WMS render_bbox outputs discrete PNG with Nearest-Neighbor sampling."""
        if not self.real_banten_tif.is_file():
            self.skipTest('Real banten tif required')

        engine = RasterTileEngine(self.real_banten_tif)
        info = engine.get_raster_info()
        wgs_bounds = info['bounds_wgs84']

        # Render bbox in EPSG:4326 covering Banten
        png_bytes = engine.render_bbox(
            min_x=wgs_bounds[0],
            min_y=wgs_bounds[1],
            max_x=wgs_bounds[2],
            max_y=wgs_bounds[3],
            srs='EPSG:4326',
            width=256,
            height=256,
        )
        self.assertTrue(png_bytes.startswith(b'\x89PNG\r\n\x1a\n'))
        arr = np.array(Image.open(io.BytesIO(png_bytes)))
        self.assertEqual(arr.shape, (256, 256, 4))
        # Must contain green tree pixels (21, 128, 61)
        visible = arr[arr[:, :, 3] > 0]
        self.assertTrue(len(visible) > 0)
        tree_rgb = hex_to_rgb(WORKFLOW_CLASS_COLORS[1])
        visible_tuples = set(map(tuple, visible[:, :3]))
        self.assertIn(tree_rgb, visible_tuples)


class TileRouterWmsAndPixelApiTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Set up mock store with root pointing to project root so it can resolve real data/
        self.project_root = Path(__file__).resolve().parents[1]
        self.store = MockStore(self.project_root)

        self.app = FastAPI()
        self.app.include_router(create_lcluc_tile_router(lambda: self.store))
        self.client = TestClient(self.app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_wms_getcapabilities(self):
        """GET /v1/lcluc/wms?SERVICE=WMS&REQUEST=GetCapabilities returns valid WMS 1.3.0 XML."""
        res = self.client.get('/v1/lcluc/wms?SERVICE=WMS&REQUEST=GetCapabilities')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/xml', res.headers['content-type'])
        self.assertIn('WMS_Capabilities', res.text)
        self.assertIn('lcluc_discrete_9classes', res.text)

    def test_wms_getmap_success(self):
        """GET /v1/lcluc/wms?SERVICE=WMS&REQUEST=GetMap returns discrete PNG."""
        # Query Banten 2021 layer
        url = (
            '/v1/lcluc/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0'
            '&LAYERS=banten-2021&CRS=EPSG:4326'
            '&BBOX=-6.5,106.0,-6.3,106.3&WIDTH=256&HEIGHT=256&FORMAT=image/png'
        )
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.headers['content-type'], 'image/png')
        self.assertTrue(res.content.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_pixel_query_endpoint_success(self):
        """GET /v1/lcluc/pixel returns exact integer class ID and provenance without screen guessing."""
        url = '/v1/lcluc/pixel?lat=-6.4375&lng=106.1343&province=banten&year=2021'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data['valid'])
        self.assertFalse(data['nodata'])
        self.assertEqual(data['class_id'], 1)
        self.assertEqual(data['class_name'], 'Trees')
        self.assertEqual(data['color'], '#15803d')
        self.assertEqual(data['native_crs'], 'EPSG:32748')
        self.assertIn('provenance', data)
        self.assertEqual(data['provenance']['source'], 'worldcover')
        self.assertEqual(
            data['provenance']['inspection_method'],
            'direct_geotiff_window_read_zero_screen_guessing',
        )

    def test_pixel_query_outside_bounds(self):
        """GET /v1/lcluc/pixel outside raster returns nodata=true."""
        url = '/v1/lcluc/pixel?lat=51.5&lng=0.0&province=banten&year=2021'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['valid'])
        self.assertTrue(data['nodata'])
        self.assertEqual(data['reason'], 'outside_raster_bounds')

    def test_pixel_query_invalid_coords(self):
        """GET /v1/lcluc/pixel with invalid latitude returns 422/400."""
        res = self.client.get('/v1/lcluc/pixel?lat=120.0&lng=106.0&province=banten')
        self.assertEqual(res.status_code, 422)


if __name__ == '__main__':
    unittest.main()
