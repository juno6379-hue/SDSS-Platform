"""Comprehensive Unit Tests and Benchmarks for LCLUC Multi-Format Export Service.

Tests:
1. GeoTIFF Exporter: Colormap fidelity, metadata tags, filtering, reprojection.
2. GeoJSON Exporter: Property enrichment, area_ha calculation, filtering.
3. CSV Exporter: 9x9 matrix, row/col margins, gains/losses, mathematical balance, unit conversion.
4. JSON & HTML Exporters: Machine-readable JSON and self-contained executive HTML with SVG charts.
5. ZIP Bundle Exporter: Archive integrity, directory containment, MANIFEST.json checksums.
6. FastAPI Router Endpoints: MIME types, attachment filenames, security validation, HTTP status codes.
"""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from .export_service_engine import (
        DEFAULT_CLASS_NAMES,
        LclucExportEngine,
        RGB_PALETTE,
        WORKFLOW_CLASS_COLORS,
    )
    from .export_router import create_lcluc_export_router
except ImportError:
    from export_service_engine import (
        DEFAULT_CLASS_NAMES,
        LclucExportEngine,
        RGB_PALETTE,
        WORKFLOW_CLASS_COLORS,
    )
    from export_router import create_lcluc_export_router


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


class ExportServiceEngineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        cls.workflow_id = 'e' * 64
        cls.pair = '2020-2021'

        cls.workflow_dir = cls.root / 'results' / 'lcluc-workflows' / cls.workflow_id
        cls.change_dir = cls.workflow_dir / 'changes' / cls.pair
        cls.change_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create synthetic transitions.tif (64x64)
        transform = from_origin(11570000.0, 150000.0, 20.0, 20.0)
        # Codes:
        # 0: water->water (unchanged)
        # 10: trees->trees (unchanged)
        # 15: trees->built (1*9 + 6 = 15, deforestation to urban)
        # 19: grass->trees (2*9 + 1 = 19, afforestation)
        data = np.full((64, 64), 65535, dtype=np.uint16)
        data[0:32, 0:32] = 0     # water->water
        data[0:32, 32:64] = 15   # trees->built
        data[32:64, 0:32] = 19   # grass->trees
        data[32:64, 32:64] = 10  # trees->trees

        cls.tif_path = cls.change_dir / 'transitions.tif'
        with rasterio.open(
            cls.tif_path,
            'w',
            driver='GTiff',
            width=64,
            height=64,
            count=1,
            dtype='uint16',
            crs='EPSG:3857',
            transform=transform,
            nodata=65535,
        ) as dst:
            dst.write(data, 1)

        # 2. Create synthetic changes.geojson
        geojson_features = [
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[[103.9, 1.3], [103.95, 1.3], [103.95, 1.35], [103.9, 1.35], [103.9, 1.3]]]
                },
                'properties': {
                    'from_class': 1,
                    'to_class': 6,
                    'transition_code': 15,
                    'area_m2': 409600.0,
                    'quality': 'comparison_of_classifications',
                }
            },
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[[103.95, 1.3], [104.0, 1.3], [104.0, 1.35], [103.95, 1.35], [103.95, 1.3]]]
                },
                'properties': {
                    'from_class': 2,
                    'to_class': 1,
                    'transition_code': 19,
                    'area_m2': 409600.0,
                    'quality': 'comparison_of_classifications',
                }
            }
        ]
        cls.geojson_path = cls.change_dir / 'changes.geojson'
        cls.geojson_path.write_text(json.dumps({'type': 'FeatureCollection', 'features': geojson_features}), encoding='utf-8')

        # 3. Create synthetic report.json
        # Transition matrix in m2 (each quadrant is 32*32 = 1024 pixels * 400m2 = 409600 m2)
        trans_m2 = np.zeros((9, 9), dtype=float)
        trans_m2[0, 0] = 409600.0  # water->water
        trans_m2[1, 6] = 409600.0  # trees->built
        trans_m2[2, 1] = 409600.0  # grass->trees
        trans_m2[1, 1] = 409600.0  # trees->trees
        pixels = np.zeros((9, 9), dtype=int)
        pixels[0, 0] = 1024
        pixels[1, 6] = 1024
        pixels[2, 1] = 1024
        pixels[1, 1] = 1024

        report_data = {
            'transition_pixels': pixels.tolist(),
            'transition_area_m2': trans_m2.tolist(),
            'valid_pixels': 4096,
            'total_area_m2': float(trans_m2.sum()),
            'changed_area_m2': float(409600.0 * 2),
            'change_rate': 0.5,
            'area_method': 'projected_grid_area_m2',
            'class_names': DEFAULT_CLASS_NAMES,
        }
        cls.report_path = cls.change_dir / 'report.json'
        cls.report_path.write_text(json.dumps(report_data), encoding='utf-8')

        cls.engine = LclucExportEngine(
            workflow_id=cls.workflow_id,
            pair=cls.pair,
            workflow_dir=cls.workflow_dir,
            class_names=DEFAULT_CLASS_NAMES,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_geotiff_export_structure_and_colormap(self):
        """Verify GeoTIFF export generates valid TIFF with embedded colormap and metadata tags."""
        tif_bytes = self.engine.export_geotiff(changes_only=True)
        self.assertTrue(tif_bytes.startswith(b'II*\x00') or tif_bytes.startswith(b'MM\x00*'))

        with rasterio.open(io.BytesIO(tif_bytes)) as src:
            self.assertEqual(src.profile['driver'], 'GTiff')
            self.assertEqual(src.profile['dtype'], 'uint8')
            self.assertEqual(src.profile['nodata'], 255)
            self.assertEqual(src.width, 64)
            self.assertEqual(src.height, 64)

            # Check colormap
            cmap = src.colormap(1)
            self.assertEqual(len(cmap), 256)
            self.assertEqual(cmap[255], (0, 0, 0, 0))  # Nodata is transparent

            # Changed code 15 (trees->built: to_class=6)
            built_rgb = RGB_PALETTE[6]
            self.assertEqual(cmap[15], (built_rgb[0], built_rgb[1], built_rgb[2], 255))

            # Unchanged pixels in changes_only are masked to nodata 255 (transparent)
            data = src.read(1)
            self.assertEqual(data[0, 0], 255)
            self.assertEqual(cmap[255], (0, 0, 0, 0))

            # Check tags
            tags = src.tags()
            self.assertEqual(tags.get('workflow_id'), self.workflow_id)
            self.assertEqual(tags.get('date_range'), self.pair)
            self.assertIn('water', tags.get('classes', ''))

    def test_geotiff_filter_and_reprojection(self):
        """Test GeoTIFF export with to_class filter and reprojection to EPSG:4326."""
        # 1. Filter to_class = 6 (Urban only)
        tif_filtered = self.engine.export_geotiff(to_class=6)
        with rasterio.open(io.BytesIO(tif_filtered)) as src:
            data = src.read(1)
            # Only code 15 should remain, all other pixels should be 255
            self.assertTrue(np.any(data == 15))
            self.assertFalse(np.any(data == 19))  # grass->trees filtered out

        # 2. Reprojection to EPSG:4326
        tif_reprojected = self.engine.export_geotiff(target_crs='EPSG:4326')
        with rasterio.open(io.BytesIO(tif_reprojected)) as src:
            self.assertIn('EPSG:4326', str(src.crs))

    def test_geojson_export_enrichment(self):
        """Verify GeoJSON export enriches features with area_ha and class names."""
        geojson_bytes = self.engine.export_geojson()
        doc = json.loads(geojson_bytes.decode('utf-8'))

        self.assertEqual(doc['type'], 'FeatureCollection')
        self.assertEqual(len(doc['features']), 2)
        feat0 = doc['features'][0]
        props = feat0['properties']
        self.assertEqual(props['from_class_name'], 'trees')
        self.assertEqual(props['to_class_name'], 'built')
        self.assertEqual(props['transition_name'], 'trees -> built')
        self.assertAlmostEqual(props['area_ha'], 40.96, places=2)
        self.assertEqual(props['workflow_id'], self.workflow_id)
        self.assertEqual(props['pair'], self.pair)

        # Test filtering by to_class
        geojson_filtered = self.engine.export_geojson(to_class=1)
        doc_filtered = json.loads(geojson_filtered.decode('utf-8'))
        self.assertEqual(len(doc_filtered['features']), 1)
        self.assertEqual(doc_filtered['features'][0]['properties']['to_class'], 1)

    def test_csv_export_matrix_balance(self):
        """Verify 9x9 CSV export mathematical integrity and unit conversion."""
        csv_bytes = self.engine.export_csv(unit='ha')
        text = csv_bytes.decode('utf-8-sig')
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Verify header block
        self.assertTrue(any('LCLUC Land Cover Transition Matrix Report' in line for line in lines))
        self.assertTrue(any(f'# Workflow ID,{self.workflow_id}' in line for line in lines))

        # Check table columns
        header_idx = next(i for i, line in enumerate(lines) if 'From Class / To Class' in line)
        headers = [col.strip() for col in lines[header_idx].split(',')]
        self.assertIn('To_water', headers)
        self.assertIn('To_built', headers)
        self.assertIn('Initial Total (ha)', headers)
        self.assertIn('Gross Loss (ha)', headers)

        # Verify net change balance: sum of net changes across all classes must be 0
        net_change_line = next(line for line in lines if line.startswith('Net Change (ha)'))
        net_values = [float(v) for v in net_change_line.split(',')[1:10]]
        self.assertAlmostEqual(sum(net_values), 0.0, places=3)

    def test_json_and_html_report_export(self):
        """Verify analytical JSON and self-contained executive HTML report generation."""
        # 1. JSON Report
        json_bytes = self.engine.export_json_report(unit='ha')
        doc = json.loads(json_bytes.decode('utf-8'))
        self.assertEqual(doc['workflow_id'], self.workflow_id)
        self.assertEqual(doc['pair'], self.pair)
        self.assertEqual(len(doc['class_metrics']), 9)
        self.assertGreater(len(doc['top_transitions']), 0)
        self.assertEqual(doc['summary']['change_rate_pct'], 50.0)

        # 2. HTML Report
        html_bytes = self.engine.export_html_report(unit='ha')
        html_str = html_bytes.decode('utf-8')
        self.assertTrue(html_str.startswith('<!DOCTYPE html>'))
        self.assertIn('LCLUC 토지피복 변화 분석 요약 보고서', html_str)
        self.assertIn('<svg', html_str)  # Embedded SVG chart
        self.assertIn('trees', html_str)
        self.assertIn('built', html_str)
        self.assertIn('법적·운영 책임 고지', html_str)

    def test_zip_bundle_export(self):
        """Verify ZIP bundle packaging, directory containment, and MANIFEST checksums."""
        zip_bytes = self.engine.export_bundle_zip(unit='ha')
        self.assertTrue(zip_bytes.startswith(b'PK\x03\x04'))

        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            namelist = zf.namelist()
            prefix = f'export_bundle_{self.workflow_id[:12]}_{self.pair}'

            # Strict directory containment
            for name in namelist:
                self.assertTrue(name.startswith(prefix + '/'))
                self.assertNotIn('..', name)

            # Check expected files
            expected_files = [
                f'{prefix}/transitions.tif',
                f'{prefix}/changes.geojson',
                f'{prefix}/transition_matrix.csv',
                f'{prefix}/report.json',
                f'{prefix}/summary_report.html',
                f'{prefix}/MANIFEST.json',
            ]
            for exp in expected_files:
                self.assertIn(exp, namelist)

            # Check MANIFEST contents
            manifest_raw = zf.read(f'{prefix}/MANIFEST.json')
            manifest = json.loads(manifest_raw.decode('utf-8'))
            self.assertEqual(manifest['workflow_id'], self.workflow_id)
            self.assertEqual(manifest['file_count'], 5)

            # Verify checksums of bundled files match manifest
            import hashlib
            for item in manifest['files']:
                fname = f"{prefix}/{item['name']}"
                content = zf.read(fname)
                self.assertEqual(hashlib.sha256(content).hexdigest(), item['sha256'])


class ExportRouterApiTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = MockStore(self.root)
        self.workflow_id = 'f' * 64
        self.pair = '2020-2021'

        self.workflow_dir = self.root / 'results' / 'lcluc-workflows' / self.workflow_id
        self.change_dir = self.workflow_dir / 'changes' / self.pair
        self.change_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal transitions.tif, changes.geojson, report.json
        transform = from_origin(11570000.0, 150000.0, 20.0, 20.0)
        data = np.full((16, 16), 15, dtype=np.uint16)
        with rasterio.open(
            self.change_dir / 'transitions.tif',
            'w',
            driver='GTiff',
            width=16,
            height=16,
            count=1,
            dtype='uint16',
            crs='EPSG:3857',
            transform=transform,
            nodata=65535,
        ) as dst:
            dst.write(data, 1)

        (self.change_dir / 'changes.geojson').write_text(
            json.dumps({'type': 'FeatureCollection', 'features': []}), encoding='utf-8'
        )
        (self.change_dir / 'report.json').write_text(
            json.dumps({'transition_area_m2': [[0.0]*9]*9, 'valid_pixels': 256}), encoding='utf-8'
        )

        # Register in store
        self.store.put('lcluc-workflows', {
            'id': self.workflow_id,
            'status': 'SUCCEEDED',
            'artifacts': [],
        })

        self.app = FastAPI()
        self.app.include_router(create_lcluc_export_router(lambda: self.store))
        self.client = TestClient(self.app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_router_export_all_formats(self):
        """Test GET /export/{format} for tif, geojson, csv, html, json, and zip."""
        formats = [
            ('tif', 'image/tiff', '.tif'),
            ('geotiff', 'image/tiff', '.tif'),
            ('geojson', 'application/geo+json', '.geojson'),
            ('csv', 'text/csv; charset=utf-8', '.csv'),
            ('html', 'text/html; charset=utf-8', '.html'),
            ('json', 'application/json', '.json'),
            ('zip', 'application/zip', '.zip'),
        ]

        for fmt, expected_mime, ext in formats:
            url = f'/v1/lcluc/workflows/{self.workflow_id}/export/{fmt}?pair={self.pair}'
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f'Failed on format {fmt}: {res.text}')
            self.assertEqual(res.headers['content-type'], expected_mime)
            self.assertIn(f'attachment; filename="', res.headers['content-disposition'])
            self.assertTrue(res.headers['content-disposition'].endswith(f'{ext}"'))
            self.assertGreater(len(res.content), 0)

    def test_router_invalid_format(self):
        """Unsupported format returns 400 INVALID_REQUEST."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/export/pdf?pair={self.pair}'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['code'], 'INVALID_REQUEST')

    def test_router_not_found_workflow(self):
        """Non-existent workflow returns 404 NOT_FOUND."""
        bad_id = '0' * 64
        url = f'/v1/lcluc/workflows/{bad_id}/export/csv?pair={self.pair}'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()['error']['code'], 'NOT_FOUND')

    def test_router_workflow_not_succeeded(self):
        """Workflow not in SUCCEEDED state returns 409 WORKFLOW_NOT_SUCCEEDED."""
        running_id = '1' * 64
        self.store.put('lcluc-workflows', {
            'id': running_id,
            'status': 'RUNNING',
            'artifacts': [],
        })
        url = f'/v1/lcluc/workflows/{running_id}/export/zip?pair={self.pair}'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['error']['code'], 'WORKFLOW_NOT_SUCCEEDED')

    def test_router_auto_pair_discovery(self):
        """Omitting pair param should auto-discover available pair."""
        url = f'/v1/lcluc/workflows/{self.workflow_id}/export/csv'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.pair, res.headers['content-disposition'])

    def test_router_query_params(self):
        """Test query filters on router."""
        # GeoTIFF with to_class filter and changes_only=False
        url = f'/v1/lcluc/workflows/{self.workflow_id}/export/tif?pair={self.pair}&to_class=6&changes_only=false'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['content-type'], 'image/tiff')

        # CSV with km2 unit
        url_csv = f'/v1/lcluc/workflows/{self.workflow_id}/export/csv?pair={self.pair}&unit=km2'
        res_csv = self.client.get(url_csv)
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('km²', res_csv.text)

    def test_router_invalid_id_or_pair(self):
        """Invalid ID or pair format returns 400 INVALID_REQUEST."""
        res1 = self.client.get(f'/v1/lcluc/workflows/short_id/export/csv?pair={self.pair}')
        self.assertEqual(res1.status_code, 400)
        res2 = self.client.get(f'/v1/lcluc/workflows/{self.workflow_id}/export/csv?pair=bad-pair')
        self.assertEqual(res2.status_code, 400)


if __name__ == '__main__':
    unittest.main()
