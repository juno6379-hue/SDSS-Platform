"""실제 패치화·전역 예산·행정경계 공간 분산을 오프라인으로 검증한다."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collect_training_grid import spatial_centers, materialize_patches, build_batches, candidate_coverage
from app.data.budget import CollectionLedger
from app.data.references import esri_annual_plan
import collect_samples


class TrainingGridTests(unittest.TestCase):
    def ledger(self, directory):
        old = directory / "old.json"
        old.write_text(json.dumps({"reserved_or_transferred_bytes_including_prior": 200}), encoding="utf-8")
        return CollectionLedger(directory / "ledger.json", [old], 1000)

    def test_reservation_survives_unknown_interruption_and_cannot_be_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = self.ledger(Path(temp))
            self.assertTrue(ledger.reserve("cell", 500, "sameconfig"))
            self.assertEqual(ledger.snapshot()["new_charged_bytes"], 500)
            with self.assertRaises(RuntimeError):
                ledger.reserve("cell", 500, "sameconfig")
            with self.assertRaises(ValueError):
                ledger.reserve("next", 501, "other")
            ledger.settle("cell", 100)
            self.assertEqual(ledger.snapshot()["new_charged_bytes"], 100)
            self.assertFalse(ledger.reserve("cell", 500, "sameconfig"))
            with self.assertRaises(RuntimeError):
                ledger.reserve("cell", 500, "changed")

    def test_first_429_stops_other_batches_and_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = self.ledger(Path(temp))
            old = (Path(temp) / "old.json").read_bytes()
            ledger.reserve("cell", 500, "same")
            ledger.settle("cell", 20, rate_limit={"http_status": 429})
            with self.assertRaises(RuntimeError):
                ledger.reserve("otherprovince", 100, "new")
            self.assertEqual(old, (Path(temp) / "old.json").read_bytes())

    def test_historical_charge_is_already_combined_and_sha_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / "old.json", root / "recovery.json"
            first.write_text('{"reserved_or_transferred_bytes_including_prior":200}')
            second.write_text('{"reserved_or_transferred_bytes_including_prior":250}')
            ledger = CollectionLedger(root / "ledger.json", [first, second], 1000)
            ledger.reserve("cell", 100, "same")
            self.assertEqual(ledger.snapshot()["historical_charged_bytes"], 250)
            first.write_text('{"reserved_or_transferred_bytes_including_prior":0}')
            with self.assertRaises(RuntimeError):
                ledger.snapshot()

    def test_grid_has_nonoverlap_spacing_and_province_interior(self):
        geometry = {"type": "Polygon", "coordinates": [[[106, -7], [107, -7], [107, -6], [106, -6], [106, -7]]]}
        centers = spatial_centers(geometry, 16)
        self.assertEqual(len(centers), 16)
        for i, point in enumerate(centers):
            self.assertTrue(106 < point["lon"] < 107 and -7 < point["lat"] < -6)
            for other in centers[:i]:
                distance = ((point["grid_easting"] - other["grid_easting"]) ** 2 + (point["grid_northing"] - other["grid_northing"]) ** 2) ** .5
                self.assertGreaterEqual(distance, 10400)

    def test_annual_label_filename_uses_actual_scene_tile_and_year(self):
        scene = "S2B_MSIL2A_20210827T025539_R032_T48MYT_20210827T134055"
        self.assertTrue(esri_annual_plan(2025, scene)["url"].endswith("lc2025/48M_20250101-20251231.tif"))
        self.assertTrue(esri_annual_plan(2020, scene)["url"].endswith("lc2020/48M_20200101-20210101.tif"))
        self.assertFalse(esri_annual_plan(2025, scene)["availability_verified"])
        with self.assertRaises(ValueError):
            esri_annual_plan(2025, "invented")
        with self.assertRaises(ValueError):
            esri_annual_plan(2026, scene)

    def test_many_tree_patches_do_not_satisfy_required_class_coverage(self):
        rows = [{"quality_status": "quality_eligible", "province": "south_sulawesi", "year": "2021",
            "split": "train", "scene_id": "source", "spatial_location_id": f"position-{i}",
            "sample_class_coverage": {"10": 65536}} for i in range(1200)]
        metrics = candidate_coverage(rows)
        self.assertEqual(metrics["eligible_patch_count"], 1200)
        self.assertFalse(metrics["candidate_target_met"])
        self.assertEqual(metrics["required_class_pixel_counts"]["train"]["80"], 0)

    def test_2025_esri_pixels_are_downloaded_with_2025_source_and_never_wc2021(self):
        import numpy as np
        from rasterio.transform import from_origin
        config = collect_samples.load_config(ROOT / "configs/collection.example.json")
        config.update(aois=config["aois"][:1], bands=["blue", "green", "red", "nir", "swir16", "swir22"],
            periods={"2025": {"start_date": "2025-06-01", "end_date": "2025-09-30"}}, annual_reference="esri_io", label_first=True)
        item = {"id": "S2B_MSIL2A_20250827T025539_R032_T48MYT_20250827T134055", "datetime": "2025-08-27T02:55:39Z",
            "cloud_cover": 0, "properties": {}, "license": "CC0-test-fixture",
            "assets": {b: {"href": b} for b in ("B02","B03","B04","B08","B11","B12","SCL")}}
        observed_urls = []
        def read(url, bbox, side, maximum):
            observed_urls.append(url)
            value = 4 if url == "SCL" else 11 if "lulctimeseries" in url else 100
            pixels = np.full((1, 4, 4), value, dtype="uint16")
            return pixels, {"driver":"GTiff", "dtype":"uint16", "count":1,"height":4,"width":4,
                "crs":"EPSG:32748","transform":from_origin(600000,9300000,10,10),"nodata":0}, {"http_body_bytes":100}
        with tempfile.TemporaryDirectory() as temp, patch.object(collect_samples.service,"search_stac",return_value={"items":[item]}), patch.object(collect_samples.service,"read_cog_window",side_effect=read):
            report = collect_samples.collect_windows(config, Path(temp), execute=True)
            row = report["scenes"][0]
            self.assertEqual(row["label_year"], 2025)
            self.assertEqual(row["label_source"], "esri_io")
            self.assertEqual(row["label_dataset_version"], "EsriIOv003-2025")
            self.assertEqual(report["label_window_count"], 1)
            self.assertTrue(row["reference_metadata"]["availability_verified"])
            self.assertTrue(row["label_source_url"].endswith("lc2025/48M_20250101-20251231.tif"))
            self.assertFalse(any("WorldCover" in url for url in observed_urls))
            self.assertLess(next(i for i,url in enumerate(observed_urls) if "lulctimeseries" in url), observed_urls.index("B02"))
            self.assertEqual(sum("lulctimeseries" in url for url in observed_urls),1)

    def test_actual_512_source_produces_four_nonoverlap_256_files(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = {"driver": "GTiff", "width": 512, "height": 512, "crs": "EPSG:4326",
                       "transform": from_origin(106, -6, .0001, .0001), "dtype": "uint16"}
            for name, count, value in (("image", 6, 1000), ("label", 1, 10), ("quality", 1, 1)):
                with rasterio.open(root / f"{name}.tif", "w", **{**profile, "count": count}) as dataset:
                    dataset.write(np.full((count, 512, 512), value, dtype="uint16"))
            source = {"status": "rgb_window_downloaded", "scene_id": "real-source-placeholder", "year": "2021",
                "image_path": str(root / "image.tif"), "label_path": str(root / "label.tif"), "quality_mask_path": str(root / "quality.tif")}
            batch = {"province": "banten", "split": "val", "key": "grid-banten-2021-g00",
                "geometry": {"type": "Polygon", "coordinates": [[[105,-7],[107,-7],[107,-5],[105,-5],[105,-7]]]}}
            rows = materialize_patches({"scenes": [source]}, batch, root)
            self.assertEqual(len(rows), 4)
            self.assertEqual(len({r["spatial_location_id"] for r in rows}), 4)
            self.assertTrue(all(r["valid_pixel_ratio"] == 1 and r["province_inside_fraction"] == 1 for r in rows))
            for row in rows:
                with rasterio.open(row["image_path"]) as dataset:
                    self.assertEqual((dataset.count, dataset.width, dataset.height), (6,256,256))
                self.assertEqual(row["source_group"], "banten/real-source-placeholder")


if __name__ == "__main__":
    unittest.main()
