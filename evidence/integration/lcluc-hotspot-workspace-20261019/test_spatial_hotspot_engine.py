"""Unit tests for spatial hotspot analysis engine (Getis-Ord Gi*).

Verifies:
1. Synthetic uniform grid (z-scores near 0, 100% Not Significant).
2. High-density synthetic cluster (z-score > 2.58, 99% confidence Hotspot detected).
3. Border/boundary padding and NoData masking behavior.
4. Multi-scale spatial kernels (3x3, 5x5, 7x7; uniform, gaussian, inverse_distance).
5. Transition mask extraction (deforestation trees->non-trees, urbanization non-built->built).
6. Contiguous cluster vectorization and RFC 7946 GeoJSON output schema compliance.
7. GeoTIFF artifact generation, nodata preservation, and CRS integrity.
8. End-to-end raster pipeline execution and top priority intervention ranking.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin

import spatial_hotspot_engine as she


class TestSpatialHotspotEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_synthetic_uniform_grid_not_significant(self):
        """Uniform grid (zero variance) must produce z=0, p=1.0, and 100% Not Significant."""
        # Test both all-zeros and all-ones uniform grids
        for val in (0.0, 1.0, 0.42):
            grid = np.full((30, 30), val, dtype=np.float64)
            z, p, c = she.calculate_getis_ord_gi(grid, kernel_size=3, kernel_type='uniform')

            # All z-scores must be 0.0
            np.testing.assert_array_equal(z, np.zeros_like(grid))
            # All p-values must be 1.0
            np.testing.assert_array_equal(p, np.ones_like(grid))
            # Classification must be all 0 (CLASS_NOT_SIGNIFICANT)
            np.testing.assert_array_equal(c, np.zeros_like(grid, dtype=np.int8))

            summary = she.compute_summary_statistics(c, z, grid)
            self.assertEqual(summary["hotspots_total"]["pixels"], 0)
            self.assertEqual(summary["coldspots_total"]["pixels"], 0)
            self.assertEqual(summary["not_significant"]["pixels"], 900)
            self.assertEqual(summary["not_significant"]["pct"], 100.0)

    def test_02_high_density_synthetic_cluster(self):
        """Dense local cluster of change amidst background zeros must yield z > 2.58 (99% Hotspot)."""
        grid = np.zeros((40, 40), dtype=np.float64)
        # Place a 5x5 dense hotspot cluster at center (rows 18..22, cols 18..22)
        grid[18:23, 18:23] = 1.0

        z, p, c = she.calculate_getis_ord_gi(grid, kernel_size=3, kernel_type='uniform')

        # Center of cluster (row 20, col 20) should have high positive z-score (> 2.58)
        center_z = z[20, 20]
        self.assertGreater(center_z, 2.58, f"Expected center z > 2.58, got {center_z}")
        self.assertEqual(c[20, 20], she.CLASS_HOTSPOT_99)
        self.assertLess(p[20, 20], 0.01)

        # Far away corners should have slight negative or non-significant z-scores
        self.assertLess(z[0, 0], 0.0)
        self.assertIn(c[0, 0], (she.CLASS_NOT_SIGNIFICANT, she.CLASS_COLDSPOT_90, she.CLASS_COLDSPOT_95, she.CLASS_COLDSPOT_99))

        # Vectorization should extract this cluster
        geojson, feats = she.vectorize_hotspots(c, z, grid, pixel_area_m2=100.0)
        self.assertGreaterEqual(len(feats), 1)
        top_cl = feats[0]["properties"]
        self.assertEqual(top_cl["severity"], "hotspot_99")
        self.assertEqual(top_cl["confidence_level"], 99)
        self.assertGreater(top_cl["max_z_score"], 2.58)
        self.assertGreater(top_cl["area_ha"], 0.0)

    def test_03_border_and_boundary_padding(self):
        """Corner and edge cells must adapt local weight sums W_i without index errors or NaNs."""
        grid = np.zeros((20, 20), dtype=np.float64)
        # Cluster located right on the top-left corner
        grid[0:3, 0:3] = 1.0

        z, p, c = she.calculate_getis_ord_gi(grid, kernel_size=3, kernel_type='uniform')

        # Corner (0,0) has 4 valid neighbors in 3x3 window instead of 9
        self.assertFalse(np.isnan(z[0, 0]))
        self.assertGreater(z[0, 0], 2.58)
        self.assertEqual(c[0, 0], she.CLASS_HOTSPOT_99)

        # No NaNs anywhere in valid grid
        self.assertFalse(np.any(np.isnan(z)))
        self.assertFalse(np.any(np.isnan(p)))

    def test_04_nodata_masking(self):
        """Masked NoData pixels must remain NaN in z/p and -99 in classification, while neighboring valid cells exclude them."""
        grid = np.zeros((25, 25), dtype=np.float64)
        grid[10:15, 10:15] = 1.0

        # Mask out a band of pixels (e.g. water/cloud mask)
        mask = np.ones((25, 25), dtype=bool)
        mask[0:5, :] = False    # Top 5 rows invalid
        mask[12, 12] = False    # Hole right inside the hotspot

        z, p, c = she.calculate_getis_ord_gi(grid, valid_mask=mask, kernel_size=3)

        # Masked cells must be NaN and CLASS_NODATA
        self.assertTrue(np.isnan(z[0, 0]))
        self.assertTrue(np.isnan(p[0, 0]))
        self.assertEqual(c[0, 0], she.CLASS_NODATA)
        self.assertTrue(np.isnan(z[12, 12]))
        self.assertEqual(c[12, 12], she.CLASS_NODATA)

        # Surrounding valid hotspot cells should still be computed accurately
        self.assertFalse(np.isnan(z[11, 11]))
        self.assertGreater(z[11, 11], 2.0)
        self.assertIn(c[11, 11], (she.CLASS_HOTSPOT_95, she.CLASS_HOTSPOT_99))

        # Check summary counts
        summary = she.compute_summary_statistics(c, z, grid)
        self.assertEqual(summary["nodata_pixels"], 25 * 5 + 1)
        self.assertEqual(summary["valid_pixels"], 25 * 25 - (25 * 5 + 1))

    def test_05_multi_scale_kernels(self):
        """Kernel generators must produce correct shapes, symmetries, and mathematical properties."""
        for size in (3, 5, 7):
            for kind in ('uniform', 'gaussian', 'inverse_distance'):
                k = she.create_spatial_kernel(size=size, kind=kind)
                self.assertEqual(k.shape, (size, size))
                # Must be symmetric
                np.testing.assert_allclose(k, k.T)
                np.testing.assert_allclose(k, np.flip(k))
                # Center cell must be maximum
                center = size // 2
                self.assertEqual(k[center, center], np.max(k))

        # Test invalid size
        with self.assertRaises(ValueError):
            she.create_spatial_kernel(size=4)
        with self.assertRaises(ValueError):
            she.create_spatial_kernel(size=0)
        with self.assertRaises(ValueError):
            she.create_spatial_kernel(size=3, kind='invalid_kind')

    def test_06_transition_mask_extraction(self):
        """Extraction of deforestation and urbanization masks must correctly isolate respective transitions."""
        # T1: 9x9 grid with trees (1) and built (6)
        t1 = np.full((9, 9), 1, dtype=np.int16)  # all trees initially
        t2 = t1.copy()
        # Deforestation: rows 0..2 converted to crops (class 4)
        t2[0:3, :] = 4
        # Urbanization: rows 6..8 converted to built (class 6)
        t2[6:9, :] = 6

        # Test Deforestation: trees (1) -> non-trees (!= 1)
        defor_mask, v1 = she.extract_transition_mask(t1, t2, transition_type='deforestation')
        self.assertEqual(np.sum(defor_mask[0:3, :]), 27.0)
        self.assertEqual(np.sum(defor_mask[3:6, :]), 0.0)  # trees remained trees
        self.assertEqual(np.sum(defor_mask[6:9, :]), 27.0)  # trees converted to built is also forest loss
        self.assertTrue(np.all(v1))

        # Test Urbanization: non-built (!= 6) -> built (== 6)
        urban_mask, v2 = she.extract_transition_mask(t1, t2, transition_type='urbanization')
        self.assertEqual(np.sum(urban_mask[0:3, :]), 0.0)  # converted to crops, not built
        self.assertEqual(np.sum(urban_mask[3:6, :]), 0.0)  # stayed trees
        self.assertEqual(np.sum(urban_mask[6:9, :]), 27.0) # converted to built

        # Test custom transition
        custom_mask, v3 = she.extract_transition_mask(t1, t2, transition_type='custom', from_classes=[1], to_classes=[4])
        self.assertEqual(np.sum(custom_mask[0:3, :]), 27.0)
        self.assertEqual(np.sum(custom_mask[3:, :]), 0.0)

    def test_07_geojson_output_schema_and_vectorization(self):
        """GeoJSON vector features must adhere strictly to RFC 7946 with rich property attributes."""
        grid = np.zeros((30, 30), dtype=np.float64)
        # Cluster 1: 4x4 hotspot (top priority)
        grid[5:9, 5:9] = 1.0
        # Cluster 2: 2x2 hotspot
        grid[20:22, 20:22] = 1.0

        transform = from_origin(127.0, 37.5, 0.0001, 0.0001)
        z, p, c = she.calculate_getis_ord_gi(grid, kernel_size=3)
        geojson, feats = she.vectorize_hotspots(
            c, z, grid, transform=transform, crs='EPSG:4326', pixel_area_m2=100.0, transition_type='deforestation'
        )

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertGreaterEqual(len(geojson["features"]), 2)

        for feat in geojson["features"]:
            self.assertEqual(feat["type"], "Feature")
            self.assertIn("geometry", feat)
            geom = feat["geometry"]
            self.assertIn(geom["type"], ("Polygon", "MultiPolygon"))
            self.assertIsInstance(geom["coordinates"], (list, tuple))

            props = feat["properties"]
            self.assertIn("cluster_id", props)
            self.assertIn("severity", props)
            self.assertIn(props["severity"], ("hotspot_99", "hotspot_95", "hotspot_90"))
            self.assertIn("confidence_level", props)
            self.assertIn("mean_z_score", props)
            self.assertIn("max_z_score", props)
            self.assertIn("mean_change_intensity", props)
            self.assertIn("pixel_count", props)
            self.assertIn("area_ha", props)
            self.assertIn("priority_score", props)
            self.assertEqual(props["transition_type"], "deforestation")

        # Serializability check
        encoded = json.dumps(geojson)
        self.assertTrue(len(encoded) > 0)

    def test_08_geotiff_raster_generation_and_nodata_preservation(self):
        """GeoTIFF rasters must preserve floating point z-scores, integer classes, and nodata values."""
        grid = np.zeros((20, 20), dtype=np.float64)
        grid[5:10, 5:10] = 1.0
        mask = np.ones((20, 20), dtype=bool)
        mask[0, :] = False  # Top row nodata

        z, p, c = she.calculate_getis_ord_gi(grid, valid_mask=mask, kernel_size=3)

        transform = from_origin(500000.0, 4100000.0, 10.0, 10.0)
        profile = {
            'driver': 'GTiff',
            'height': 20,
            'width': 20,
            'count': 1,
            'crs': 'EPSG:32652',
            'transform': transform
        }

        z_path = self.workspace / "test_z.tif"
        c_path = self.workspace / "test_c.tif"

        she.export_geotiff(z_path, z, profile, dtype='float32', nodata=she.FLOAT_NODATA)
        she.export_geotiff(c_path, c, profile, dtype='int16', nodata=she.CLASS_NODATA)

        self.assertTrue(z_path.exists())
        self.assertTrue(c_path.exists())

        # Verify z-score raster reading
        with rasterio.open(z_path) as src_z:
            self.assertEqual(src_z.shape, (20, 20))
            self.assertEqual(src_z.dtypes[0], 'float32')
            self.assertEqual(src_z.nodata, she.FLOAT_NODATA)
            read_z = src_z.read(1)
            self.assertEqual(read_z[0, 0], she.FLOAT_NODATA)
            self.assertGreater(read_z[7, 7], 2.58)

        # Verify classification raster reading
        with rasterio.open(c_path) as src_c:
            self.assertEqual(src_c.shape, (20, 20))
            self.assertEqual(src_c.dtypes[0], 'int16')
            self.assertEqual(src_c.nodata, she.CLASS_NODATA)
            read_c = src_c.read(1)
            self.assertEqual(read_c[0, 0], she.CLASS_NODATA)
            self.assertEqual(read_c[7, 7], she.CLASS_HOTSPOT_99)

    def test_09_end_to_end_raster_pipeline(self):
        """SpatialHotspotEngine.analyze_rasters must execute end-to-end and output all 4 required artifacts."""
        t1_path = self.workspace / "t1_lulc.tif"
        t2_path = self.workspace / "t2_lulc.tif"
        out_dir = self.workspace / "results_hotspot"

        transform = from_origin(500000.0, 4100000.0, 10.0, 10.0)
        profile = {
            'driver': 'GTiff',
            'height': 30,
            'width': 30,
            'count': 1,
            'dtype': 'uint8',
            'crs': 'EPSG:32652',
            'transform': transform,
            'nodata': 255
        }

        t1_arr = np.full((30, 30), 1, dtype=np.uint8)  # trees
        t2_arr = t1_arr.copy()
        # Create a cluster of urbanization (class 6 built)
        t2_arr[10:16, 10:16] = 6

        with rasterio.open(t1_path, 'w', **profile) as d1:
            d1.write(t1_arr, 1)
        with rasterio.open(t2_path, 'w', **profile) as d2:
            d2.write(t2_arr, 1)

        engine = she.SpatialHotspotEngine(kernel_size=5, kernel_type='gaussian', sigma=1.5)
        results = engine.analyze_rasters(
            t1_path=t1_path,
            t2_path=t2_path,
            transition_type='urbanization',
            output_dir=out_dir
        )

        self.assertIn("artifacts", results)
        artifacts = results["artifacts"]

        self.assertTrue(Path(artifacts["zscores_geotiff"]).exists())
        self.assertTrue(Path(artifacts["classes_geotiff"]).exists())
        self.assertTrue(Path(artifacts["hotspots_geojson"]).exists())
        self.assertTrue(Path(artifacts["summary_json"]).exists())

        # Check summary content
        summary = results["summary"]
        self.assertEqual(summary["transition_type"], "urbanization")
        self.assertGreater(summary["hotspots_total"]["pixels"], 0)
        self.assertGreater(summary["cluster_count"], 0)
        self.assertGreater(len(summary["top_priority_intervention_zones"]), 0)

        top_zone = summary["top_priority_intervention_zones"][0]
        self.assertEqual(top_zone["rank"], 1)
        self.assertEqual(top_zone["severity"], "hotspot_99")
        self.assertGreater(top_zone["area_ha"], 0.0)

    def test_10_extreme_edge_cases(self):
        """Handle single-pixel grids, all-NoData grids, and tiny grids gracefully."""
        # Single pixel grid
        grid1 = np.array([[1.0]], dtype=np.float64)
        z1, p1, c1 = she.calculate_getis_ord_gi(grid1)
        self.assertEqual(z1[0, 0], 0.0)
        self.assertEqual(p1[0, 0], 1.0)
        self.assertEqual(c1[0, 0], she.CLASS_NOT_SIGNIFICANT)

        # All-masked grid
        grid_all_masked = np.ones((5, 5), dtype=np.float64)
        mask_all_false = np.zeros((5, 5), dtype=bool)
        z_m, p_m, c_m = she.calculate_getis_ord_gi(grid_all_masked, valid_mask=mask_all_false)
        self.assertTrue(np.all(np.isnan(z_m)))
        self.assertTrue(np.all(np.isnan(p_m)))
        self.assertTrue(np.all(c_m == she.CLASS_NODATA))


if __name__ == '__main__':
    unittest.main()
