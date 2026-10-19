"""충분한 자료 확보 계획이 실수집/학습 준비로 오인되지 않도록 검증한다."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect_samples


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.config = collect_samples.load_config(ROOT / "configs" / "collection.example.json")

    def test_default_plan_has_six_candidates_and_no_network(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(collect_samples.service, "search_stac") as search:
            report = collect_samples.collect(self.config, Path(temp))
            search.assert_not_called()
        self.assertEqual(len(report["scenes"]), 18)
        self.assertFalse(report["executed"])
        self.assertEqual(report["complete_scene_count"], 0)
        self.assertFalse(report["learning_ready"])
        self.assertEqual(report["verified_patch_count"], 0)
        self.assertIsNone(report["valid_pixel_ratio"])
        self.assertEqual(report["nominal_max_patches"], 18)
        self.assertEqual(report["grid_plan"]["nominal_candidate_count"], 1152)
        self.assertFalse(report["grid_plan"]["executed"])

    def test_total_budget_includes_partial_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "downloads").mkdir()
            (root / "downloads" / "unfinished.part").write_bytes(b"12345678")
            config = {**self.config, "max_total_bytes": 10, "max_asset_bytes": 10}
            with patch.object(collect_samples.service, "download_asset", return_value={"bytes": 1, "sha256": "x"}) as download:
                collect_samples.download_with_budget({"url": "x"}, "key", {"assets": {}}, config, root)
                self.assertEqual(download.call_args.args[0]["max_bytes"], 2)

    def test_429_circuit_stops_batch_and_refunds_only_known_current_reservation(self):
        from urllib.error import HTTPError
        import hashlib
        service = collect_samples.service
        config = {**self.config, "aois": self.config["aois"][:1],
                  "periods": {"2021": {"start_date": "2021-06-01", "end_date": "2021-09-30"},
                              "2022": {"start_date": "2022-06-01", "end_date": "2022-09-30"}}}
        item = {"id": "mock-scene", "datetime": "2021-01-01", "cloud_cover": 0,
                "license": "test", "assets": {"B02": {"href": "https://example.org/a.tif"}}}
        failure = service.AssetTransferError("sas_token", 0, True)
        failure.__cause__ = HTTPError("https://planetarycomputer.microsoft.com/api/sas/v1/token/account/container?sig=secret", 429,
                                     "Too Many Requests", {"Retry-After": "120"}, None)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {"config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
                     "http_body_bytes": 123456, "cells": {}}
            (root / "window-state.json").write_text(json.dumps(state), encoding="utf-8")
            with patch.object(service, "search_stac", return_value={"items": [item]}) as search, patch.object(service, "read_cog_window", side_effect=failure) as read:
                report = collect_samples.collect_windows(config, root, execute=True)
            self.assertEqual(search.call_count, 1)
            self.assertEqual(read.call_count, 1)
            self.assertEqual(report["scenes"][0]["status"], "rate_limited")
            self.assertEqual(report["scenes"][1]["status"], "deferred_rate_limit")
            self.assertEqual(report["http_body_bytes_upper_bound"], 123456)
            self.assertEqual(report["http_body_bytes_measured"], 0)
            self.assertIsNone(report["http_body_bytes"])
            self.assertEqual(report["batch_circuit_breaker"]["retry_after"], "120")
            self.assertNotIn("sig", report["batch_circuit_breaker"]["request_path"])

    def test_existing_sha_verified_skips_download(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "asset.tif"
            path.write_bytes(b"data")
            existing = {"path": str(path), "sha256": collect_samples.service._sha(path)}
            with patch.object(collect_samples.service, "download_asset") as download:
                result = collect_samples.download_with_budget({}, "key", {"assets": {"key": existing}}, self.config, root)
                download.assert_not_called()
                self.assertEqual(result, existing)

    def test_search_failures_leave_zero_readiness_and_history(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(collect_samples.service, "search_stac", side_effect=RuntimeError("offline")), patch.object(collect_samples.service, "download_asset", side_effect=RuntimeError("offline")):
            report = collect_samples.collect(self.config, Path(temp), execute=True)
            self.assertEqual(report["complete_scene_count"], 0)
            self.assertTrue((Path(temp) / "collection-history.jsonl").exists())
            self.assertFalse(report["learning_ready"])
            self.assertTrue(all(scene["status"] == "search_failed" for scene in report["scenes"]))

    def test_six_bands_align_20m_swir_to_10m_reference_and_track_label_year(self):
        try:
            import numpy as np
            import rasterio
            from rasterio.transform import from_origin
        except ImportError:
            self.skipTest("선택 래스터 의존성 미설치")
        bands = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]
        item = {"id": "real-contract-mocked-network", "datetime": "2021-09-21T00:00:00Z", "cloud_cover": 0,
                "properties": {"s2:processing_baseline": "03.00"}, "license": "test-input-only",
                "assets": {b: {"href": b, "raster:bands": [{"scale": .0001, "offset": 0}]} for b in bands}}
        def fake_window(url, bbox, side, max_bytes):
            resolution = 20 if url in ("B11", "B12", "SCL") else 10
            size = 2 if resolution == 20 else 4
            value = 4 if url == "SCL" else 40 if "WorldCover" in url else 100
            values = np.full((1, size, size), value, dtype="uint16")
            profile = {"driver": "GTiff", "dtype": "uint16", "count": 1, "height": size, "width": size,
                       "crs": "EPSG:32748", "nodata": 0, "transform": from_origin(600000, 9300000, resolution, resolution)}
            return values, profile, {"http_body_bytes": 100}
        config = {**self.config, "aois": self.config["aois"][:1],
                  "bands": ["blue", "green", "red", "nir", "swir16", "swir22"],
                  "periods": {"2021": {"start_date": "2021-06-01", "end_date": "2021-09-30"}}}
        with tempfile.TemporaryDirectory() as temp, patch.object(collect_samples.service, "search_stac", return_value={"items": [item]}), patch.object(collect_samples.service, "read_cog_window", side_effect=fake_window):
            report = collect_samples.collect_windows(config, Path(temp), execute=True)
            row = report["scenes"][0]
            with rasterio.open(row["image_path"]) as src:
                self.assertEqual((src.count, src.height, src.width), (6, 4, 4))
                self.assertEqual(src.dtypes[0], "float32")
                self.assertTrue(np.all(src.read(5) == 100))
            self.assertEqual(row["label_year"], 2021)
            self.assertEqual(row["label_dataset_version"], "WorldCover2021v200")
            self.assertEqual(row["valid_pixel_ratio"], 1.0)
            self.assertEqual(row["quality_status"], "quality_eligible")
            self.assertTrue(Path(row["source_crops"]["raw-worldcover.tif"]["path"]).is_file())
            self.assertEqual(row["source_crops"]["raw-B11.tif"]["metadata"]["resolution"], [20.0, 20.0])
            self.assertEqual(row["band_processing"][4]["resampling"], "bilinear")
            self.assertFalse(row["reflectance_conversion_verified"])


if __name__ == "__main__":
    unittest.main()
