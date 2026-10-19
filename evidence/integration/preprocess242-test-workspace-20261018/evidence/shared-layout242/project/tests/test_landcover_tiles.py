"""연차 누락·참조 클래스·PNG 투명도·잘못된 타일을 검증한다."""
import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from app.landcover_tiles import inventory, palette_for, render_tile, tile, series_index


class LandcoverTileTests(unittest.TestCase):
    def raster(self, path, values, nodata=0):
        half = 20037508.342789244
        path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(path, 'w', driver='GTiff', width=2, height=2, count=1, dtype='uint8',
                           crs='EPSG:3857', transform=from_bounds(-half,-half,half,half,2,2),nodata=nodata) as target:
            target.write(np.asarray(values,dtype='uint8'),1)

    def test_only_existing_years_are_grouped_and_missing_years_stay_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for year in (2020,2021,2023):
                path = root / f'{year}.tif'
                self.raster(path, [[1,2],[5,7]])
                rows.append({'year':year,'aoi':'fixture','province':'fixture','label_source':'esri_io',
                             'label_path':str(path),'bbox':[106,-7,107,-6]})
            report = root / 'first-group-fixture' / 'annual-window-report.json'
            report.parent.mkdir()
            report.write_text(json.dumps({'synthetic':True,'scenes':rows}),encoding='utf-8')
            public, layers = inventory(root)
            self.assertEqual(len(public['series']),1)
            group = public['series'][0]
            self.assertEqual([item['year'] for item in group['years']],[2020,2021,2023])
            self.assertEqual(group['missing_years'],[2022,2024,2025])
            self.assertTrue(group['synthetic'])
            self.assertEqual(len(layers),3)

    def test_esri_cloud_and_nodata_are_transparent_but_water_is_blue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'esri.tif'
            self.raster(path, [[1,0],[10,2]])
            png = render_tile(str(path),path.stat().st_mtime_ns,path.stat().st_size,json.dumps(palette_for('esri_io')),0,0,0)
            with MemoryFile(png) as memory, memory.open() as image:
                rgba = image.read()
            self.assertEqual(rgba[:,64,64].tolist(),[65,155,223,255])
            self.assertEqual(int(rgba[3,64,192]),0)
            self.assertEqual(int(rgba[3,192,64]),0)
            self.assertEqual(rgba[:,192,192].tolist(),[57,125,73,255])

    def test_model_class_zero_is_water_and_ignore255_is_transparent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.tif'
            self.raster(path, [[0,255],[1,2]],nodata=255)
            png = render_tile(str(path),path.stat().st_mtime_ns,path.stat().st_size,json.dumps(palette_for('model_prediction')),0,0,0)
            with MemoryFile(png) as memory, memory.open() as image:
                rgba = image.read()
            self.assertEqual(rgba[:,64,64].tolist(),[65,155,223,255])
            self.assertEqual(int(rgba[3,64,192]),0)

    def test_unknown_layer_and_invalid_xyz_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KeyError):
                tile(Path(directory),'not-a-local-layer',0,0,0)
            with self.assertRaises(ValueError):
                tile(Path(directory),'none',0,1,0)

    def test_external_reference_path_is_not_exposed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            path = Path(external) / 'outside.tif'
            self.raster(path, [[1,2],[5,7]])
            report = root / 'first-group-fixture' / 'annual-window-report.json'
            report.parent.mkdir()
            report.write_text(json.dumps({'scenes':[{'year':2020,'label_source':'esri_io','label_path':str(path)}]}))
            self.assertEqual(inventory(root)[0]['series'],[])
