"""새보충예산/씬품질선정/제품별보정 검증은 외부접속 없이 수행한다."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.data import service
from app.data.calibration import parse_product_calibration
from collect_samples import select_quality_candidate
from collect_recovery_validation import dns_handoff_allowed


class Response(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.headers = {"Content-Length": str(len(raw))}


class RecoveryTests(unittest.TestCase):
    def tearDown(self):
        service.configure_metadata_budget(None)
        service.configure_request_spacing(0)

    def test_metadata_budget_is_cumulative_and_stops_before_third_request(self):
        service.configure_metadata_budget(10)
        with patch.object(service, "_open", side_effect=[Response(b'{"ok":1}'), Response(b'{}')]) as network:
            self.assertEqual(service._json_response(Request(service.STAC_URL)), {"ok": 1})
            service._json_response(Request(service.STAC_URL))
            with self.assertRaises(RuntimeError):
                service._json_response(Request(service.STAC_URL))
            self.assertEqual(network.call_count, 2)
        self.assertEqual(service.metadata_budget_status()["charged_bytes"], 10)
        self.assertEqual(service.metadata_budget_status()["read_body_bytes"], 10)

    def test_handoff_requires_dns_zero_measurement_and_unchanged_ledger(self):
        evidence = {"status": "failed", "error": {"category": "dns_resolution"}, "new_cog_charged_bytes": 0,
                    "new_charged_upper_bound_bytes": 0, "metadata_budget": {"charged_bytes": 0, "read_body_bytes": 0},
                    "old_ledger_unchanged": True, "manifests": []}
        self.assertTrue(dns_handoff_allowed(evidence))
        self.assertFalse(dns_handoff_allowed({**evidence, "error": {"category": "http_response", "http_status": 429}}))
        self.assertFalse(dns_handoff_allowed({**evidence, "metadata_budget": {"charged_bytes": 1, "read_body_bytes": 1}}))
        self.assertFalse(dns_handoff_allowed({**evidence, "old_ledger_unchanged": False}))

    def test_baseline04_requires_explicit_offset_and_year_does_not_decide(self):
        pre = b'<Product><PROCESSING_BASELINE>03.00</PROCESSING_BASELINE><BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE></Product>'
        report = parse_product_calibration(pre, ["B02", "B11"])
        self.assertTrue(report["verified"])
        self.assertEqual(report["bands"]["B02"]["offset"], 0)
        post = pre.replace(b"03.00", b"05.00")
        self.assertFalse(parse_product_calibration(post, ["B02"])["verified"])
        post = post.replace(b'</Product>', b'<BOA_ADD_OFFSET band_id="1">-1000</BOA_ADD_OFFSET></Product>')
        corrected = parse_product_calibration(post, ["B02"])
        self.assertEqual(corrected["bands"]["B02"]["scale"], .0001)
        self.assertEqual(corrected["bands"]["B02"]["offset"], -.1)
        self.assertFalse(corrected["scale_offset_applied_to_image"])

    def test_quality_candidate_rejects_cloudy_local_window_despite_low_scene_cloud(self):
        try:
            import numpy as np
            import rasterio
        except ImportError:
            self.skipTest("선택 래스터 의존성 미설치")
        items = [{"id": "clear-local", "cloud_cover": 5, "license": "test", "assets": {"SCL": {"href": "clear"}}},
                 {"id": "cloudy-local", "cloud_cover": 1, "license": "test", "assets": {"SCL": {"href": "cloudy"}}}]
        def fetch(url, bbox, side):
            values = np.full((1, 4, 4), 9 if url == "cloudy" else 4, dtype="uint8")
            profile = {"driver": "GTiff", "count": 1, "dtype": "uint8", "width": 4, "height": 4,
                "crs": rasterio.CRS.from_epsg(32748), "transform": rasterio.transform.from_origin(600000, 9300000, 20, 20), "nodata": 0}
            return values, profile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chosen, raw, audit = select_quality_candidate(items, fetch, {"bbox": [106, -7, 107, -6]}, 256, root, root)
            self.assertEqual(chosen["id"], "clear-local")
            self.assertEqual([a["status"] for a in audit], ["quality_insufficient", "eligible"])
            self.assertTrue(Path(audit[0]["raw_scl_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
