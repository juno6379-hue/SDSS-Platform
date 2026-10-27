"""실제 외부 호출 없이 수집의 입력/전송/출처 계약을 검증한다."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.data import service


class Response(io.BytesIO):
    def __init__(self, content, status=200, headers=None):
        super().__init__(content)
        self.status = status
        self.headers = headers or {"Content-Length": str(len(content))}


class DataServiceTests(unittest.TestCase):
    def setUp(self):
        service._PC_TOKEN_CACHE.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.query = {"bbox": [106, -7, 107, -6], "start_date": "2024-01-01", "end_date": "2024-02-01"}
        self.url = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/test.tif"

    def tearDown(self):
        self.temp.cleanup()

    def test_search_filters_and_asset_selection(self):
        scene = {"id": "scene", "properties": {"eo:cloud_cover": 5}, "assets": {
            "red": {"href": self.url, "type": "image/tiff; application=geotiff"},
            "thumbnail": {"href": "https://example.org/thumb.jpg", "type": "image/jpeg"}}}
        with patch.object(service, "_json_response", return_value={"features": [scene]}) as mocked:
            result = service.search_stac({**self.query, "cloud_cover": 10})
        self.assertEqual(result["count"], 1)
        self.assertEqual(set(result["items"][0]["assets"]), {"red"})
        request = mocked.call_args.args[0]
        self.assertEqual(json.loads(request.data)["query"]["eo:cloud_cover"], {"lte": 10})

    def test_planetary_computer_endpoint_is_fixed_and_validated(self):
        with patch.object(service, "_json_response", return_value={"features": []}) as mocked:
            result = service.search_stac({**self.query, "endpoint": "planetary-computer"})
        self.assertEqual(mocked.call_args.args[0].full_url, service.PC_STAC_URL)
        self.assertEqual(result["source"], service.PC_STAC_URL)
        with self.assertRaises(ValueError):
            service.stac_endpoint("https://127.0.0.1/v1")

    def test_pc_signer_validates_same_asset(self):
        url = "https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/scene/B04.tif"
        with patch.object(service, "_json_response", return_value={"token": "sig=mock", "msft:expiry": "2050-01-01T00:00:00Z"}) as request:
            self.assertEqual(service.resolve_asset_url(url), url + "?sig=mock")
            self.assertEqual(service.resolve_asset_url(url.replace("B04", "B03")), url.replace("B04", "B03") + "?sig=mock")
            self.assertEqual(request.call_count, 1)
            self.assertIn("/token/sentinel2l2a01/sentinel2-l2", request.call_args.args[0].full_url)
        service._PC_TOKEN_CACHE.clear()
        with patch.object(service, "_json_response", return_value={"token": "sig=mock", "msft:expiry": "2000-01-01T00:00:00Z"}):
            with self.assertRaises(RuntimeError):
                service.resolve_asset_url(url)

    def test_server_cloud_filter_is_revalidated_on_client(self):
        values = [20.909931, None, True, float("nan"), float("inf"), -1, 101, "5", 19.5]
        features = [{"id": str(i), "properties": {"eo:cloud_cover": value}} for i, value in enumerate(values)]
        with patch.object(service, "_json_response", return_value={"features": features}):
            result = service.search_stac({**self.query, "cloud_cover": 20, "limit": 10})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["cloud_cover"], 19.5)
        self.assertEqual(result["filtered_count"], 8)

    def test_head_http_failure_reports_known_zero_cog_body(self):
        from urllib.error import HTTPError
        try:
            import rasterio
        except ImportError:
            self.skipTest("선택 rasterio 미설치")
        error = HTTPError(self.url, 429, "Too Many Requests", {"Retry-After": "60"}, None)
        with patch.object(service, "HTTPRangeReader", side_effect=error):
            with self.assertRaises(service.AssetTransferError) as caught:
                service.read_cog_window(self.url, self.query["bbox"])
        self.assertEqual(caught.exception.http_body_bytes, 0)
        self.assertTrue(caught.exception.transfer_measurement_known)
        self.assertEqual(caught.exception.stage, "head_metadata")

    def test_gdal_wrapped_error_retains_original_http_cause_and_measured_bytes(self):
        from types import SimpleNamespace
        from urllib.error import HTTPError
        original = HTTPError(self.url, 429, "Too Many Requests", {"Retry-After": "60"}, None)
        def failed_impl(url, bbox, side, cap, holder):
            holder.update(stage="range_raster_read", reader=SimpleNamespace(measurement_known=True, transferred=123, last_error=original))
            raise RuntimeError("mock CPL wrapper")
        with patch.object(service, "_read_cog_window_impl", side_effect=failed_impl):
            with self.assertRaises(service.AssetTransferError) as caught:
                service.read_cog_window(self.url, self.query["bbox"])
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(caught.exception.http_body_bytes, 123)

    def test_full_tile_reader_propagates_stage_and_measured_bytes(self):
        from types import SimpleNamespace
        original = RuntimeError("mock full-tile range failure")

        def failed_impl(url, cap, max_side, holder):
            holder.update(
                stage="range_raster_read",
                reader=SimpleNamespace(
                    measurement_known=True, transferred=456, last_error=original,
                ),
            )
            raise RuntimeError("mock CPL wrapper")

        with patch.object(service, "_read_cog_full_tile_impl", side_effect=failed_impl):
            with self.assertRaises(service.AssetTransferError) as caught:
                service.read_cog_full_tile(self.url)
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(caught.exception.stage, "range_raster_read")
        self.assertEqual(caught.exception.http_body_bytes, 456)

    def test_full_tile_reader_rejects_policy_values_before_network(self):
        with patch.object(service, "resolve_asset_url") as network:
            with self.assertRaises(service.AssetTransferError):
                service.read_cog_full_tile(self.url, max_transfer_bytes=0)
            with self.assertRaises(service.AssetTransferError):
                service.read_cog_full_tile(self.url, max_side=8193)
        network.assert_not_called()

    def test_full_download_does_not_retry_provider_429(self):
        from urllib.error import HTTPError
        original = HTTPError(self.url, 429, "Too Many Requests", {"Retry-After": "60"}, None)
        with patch.object(service, "_open", side_effect=original) as request, patch.object(service.time, "sleep") as sleep:
            with self.assertRaises(RuntimeError):
                service.download_asset({"url": self.url, "retries": 5}, self.root)
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()

    def test_partial_range_read_retains_measured_bytes(self):
        from http.client import IncompleteRead
        partial = Response(b"", 206, {"Content-Range": "bytes 0-3/100"})
        partial.read = lambda amount: (_ for _ in ()).throw(IncompleteRead(b"ab", 2))
        with patch.object(service, "_open", side_effect=[Response(b"", headers={"Content-Length": "100"}), partial]):
            reader = service.HTTPRangeReader(self.url, block_size=1)
            with self.assertRaises(IncompleteRead):
                reader.read(4)
        self.assertEqual(reader.transferred, 2)
        self.assertTrue(reader.measurement_known)

    def test_http_range_reader_enforces_bounds_and_transfer_budget(self):
        responses = [Response(b"", headers={"Content-Length": "100", "ETag": '"v1"'}),
                     Response(b"abcd", 206, {"Content-Range": "bytes 10-13/100"})]
        with patch.object(service, "_open", side_effect=responses):
            reader = service.HTTPRangeReader(self.url, max_transfer_bytes=5, block_size=1)
            reader.seek(10)
            self.assertEqual(reader.read(4), b"abcd")
            self.assertEqual(reader.transferred, 4)
            with self.assertRaises(ValueError):
                reader.read(2)

    def test_invalid_queries_fail_before_network(self):
        invalid = [{"bbox": [107, -7, 106, -6]}, {"bbox": [True, -7, 107, -6]},
                   {"cloud_cover": 101}, {"limit": 1.2}, {"start_date": "2024-02-30"},
                   {"end_date": "2023-01-01"}, {"collection": "unknown"}]
        with patch.object(service, "_open") as mocked:
            for update in invalid:
                with self.subTest(update=update), self.assertRaises(ValueError):
                    service.search_stac({**self.query, **update})
            mocked.assert_not_called()

    def test_download_hash_manifest_and_duplicate(self):
        with patch.object(service, "_open", side_effect=lambda request: Response(b"raster")):
            first = service.download_asset({"url": self.url, "license": "CC-BY-4.0"}, self.root)
            second = service.download_asset({"url": self.url, "filename": "other.tif"}, self.root)
        self.assertEqual(first["sha256"], hashlib.sha256(b"raster").hexdigest())
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["path"], second["path"])
        self.assertEqual(json.loads(Path(first["manifest"]).read_text(encoding="utf-8"))["license"], "CC-BY-4.0")

    def test_host_and_filename_security(self):
        for url in ("http://example.org/a", "https://127.0.0.1/a", "https://user:pw@esa-worldcover.s3.eu-central-1.amazonaws.com/a", "file:///etc/passwd"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                service.download_asset({"url": url}, self.root)
        with self.assertRaises(ValueError):
            service.download_asset({"url": self.url, "filename": "../escape.tif"}, self.root)
        with self.assertRaises(ValueError):
            service.register_local({"path": "../escape.tif"}, self.root)
        redirect = service._SafeRedirect()
        with self.assertRaises(ValueError):
            redirect.redirect_request(None, None, 302, "", {}, "https://127.0.0.1/private")

    def test_download_limit_even_without_length(self):
        with patch.object(service, "_open", return_value=Response(b"too long", headers={"ETag": '"v1"'})):
            with self.assertRaises(ValueError):
                service.download_asset({"url": self.url, "max_bytes": 3}, self.root)
        self.assertFalse(list(self.root.glob("manifests/*.json")))

    def test_download_checksum_mismatch(self):
        with patch.object(service, "_open", return_value=Response(b"data")):
            with self.assertRaisesRegex(ValueError, "SHA256"):
                service.download_asset({"url": self.url, "sha256": "0" * 64}, self.root)
        self.assertFalse(list(self.root.glob("downloads/*.part")))

    def test_retry_resumes_with_if_range(self):
        key = hashlib.sha256(self.url.encode()).hexdigest()
        directory = self.root / "downloads"
        directory.mkdir()
        (directory / f"{key}.part").write_bytes(b"abc")
        (directory / f"{key}.validator").write_text('"v1"')
        with patch.object(service, "_open", return_value=Response(b"def", 206,
                {"Content-Length": "3", "Content-Range": "bytes 3-5/6", "ETag": '"v1"'})) as mocked:
            result = service.download_asset({"url": self.url}, self.root)
        self.assertEqual(Path(result["path"]).read_bytes(), b"abcdef")
        self.assertEqual(mocked.call_args.args[0].get_header("Range"), "bytes=3-")
        self.assertEqual(mocked.call_args.args[0].get_header("If-range"), '"v1"')

    def test_ignored_range_restarts_instead_of_appending(self):
        key = hashlib.sha256(self.url.encode()).hexdigest()
        directory = self.root / "downloads"
        directory.mkdir()
        (directory / f"{key}.part").write_bytes(b"old")
        (directory / f"{key}.validator").write_text('"old"')
        with patch.object(service, "_open", return_value=Response(b"new content")):
            result = service.download_asset({"url": self.url}, self.root)
        self.assertEqual(Path(result["path"]).read_bytes(), b"new content")

    def test_resume_rejects_incomplete_range(self):
        key = hashlib.sha256(self.url.encode()).hexdigest()
        directory = self.root / "downloads"
        directory.mkdir()
        (directory / f"{key}.part").write_bytes(b"abc")
        (directory / f"{key}.validator").write_text('"v1"')
        with patch.object(service, "_open", return_value=Response(b"def", 206,
                {"Content-Length": "3", "Content-Range": "bytes 3-5/99", "ETag": '"v1"'})):
            with self.assertRaises(RuntimeError):
                service.download_asset({"url": self.url}, self.root)
        self.assertFalse(list(self.root.glob("manifests/*.json")))

    def test_retry_network_error(self):
        with patch.object(service, "_open", side_effect=[OSError("offline"), Response(b"ok")]), patch.object(service.time, "sleep"):
            result = service.download_asset({"url": self.url, "retries": 1}, self.root)
        self.assertEqual(result["bytes"], 2)

    def test_worldcover_boundary_and_negative_coordinates(self):
        result = service.worldcover_plan({"bbox": [106, -7, 108, -6], "year": 2021})
        self.assertEqual(len(result["tiles"]), 1)
        self.assertEqual(result["tiles"][0]["tile"], "S09E105")
        self.assertFalse(result["executed"])
        self.assertIn("v200/2021/map", result["tiles"][0]["url"])

    def test_dynamic_world_plan_is_not_execution(self):
        with patch.object(service.importlib, "import_module") as mocked:
            result = service.dynamic_world_export(self.query)
        mocked.assert_not_called()
        self.assertFalse(result["executed"])
        self.assertEqual(len(result["bands"]), 9)
        self.assertEqual(result["reducer"], "mean_probabilities")
        with patch.dict(service.os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "실행되지"):
            service.dynamic_world_export({**self.query, "execute": True})

    def test_manual_geotiff_metadata_if_rasterio_installed(self):
        try:
            import rasterio
            import numpy as np
        except ImportError:
            self.skipTest("선택 의존성 rasterio/numpy 미설치")
        path = self.root / "labels.tif"
        with rasterio.open(path, "w", driver="GTiff", width=2, height=2, count=1,
                dtype="uint8", crs="EPSG:4326", transform=rasterio.transform.from_origin(106, -6, .01, .01), nodata=255) as dst:
            dst.write(np.array([[1, 2], [2, 255]], dtype="uint8"), 1)
        result = service.register_local({"path": "labels.tif", "license": "own-data"}, self.root)
        self.assertEqual(result["metadata"]["crs"], "EPSG:4326")
        aligned = self.root / "aligned.tif"
        service.align_labels(path, path, aligned)
        with rasterio.open(aligned) as src:
            self.assertEqual(set(src.read(1).flatten()), {1, 2, 255})


if __name__ == "__main__":
    unittest.main()
