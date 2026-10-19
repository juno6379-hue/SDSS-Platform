"""네트워크 장애와 실제 STAC 계약 오류를 별도로 판정하는지 확인한다."""
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diagnose_stac


class DiagnosticTests(unittest.TestCase):
    def test_offline_performs_no_network_and_claims_no_success(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(diagnose_stac.socket, "getaddrinfo") as dns:
            report = diagnose_stac.diagnose(Path(temp), offline=True)
            dns.assert_not_called()
            self.assertFalse(report["real_search_verified"])
            self.assertFalse(report["real_download_verified"])
            self.assertTrue((Path(temp) / "diagnosis.json").is_file())

    def test_dns_failure_blocks_api_without_claiming_code_failure(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(diagnose_stac.socket, "getaddrinfo",
                side_effect=socket.gaierror(11001, "mock DNS failure")), patch.object(diagnose_stac.service, "search_stac") as search:
            report = diagnose_stac.diagnose(Path(temp))
            search.assert_not_called()
            self.assertEqual(report["stages"][0]["category"], "dns_resolution")
            self.assertEqual(report["stages"][1]["status"], "blocked_by_dns")

    def test_http_error_means_server_reached(self):
        error = HTTPError("https://example.org", 400, "Bad Request", {}, None)
        result = diagnose_stac.classify_error(error)
        self.assertEqual(result["http_status"], 400)
        self.assertTrue(result["server_reached"])
        dns = diagnose_stac.classify_error(URLError(socket.gaierror(11001, "failure")))
        self.assertEqual(dns["category"], "dns_resolution")

    def test_exception_messages_redact_urls_and_sas_and_limit_length(self):
        error = RuntimeError("read failed https://example.org/file.tif?sig=secret-value sig=another-secret " + "x" * 1000)
        result = diagnose_stac.classify_error(error)
        self.assertNotIn("secret", result["sanitized_message"])
        self.assertNotIn("https://", result["sanitized_message"])
        self.assertLessEqual(len(result["sanitized_message"]), 500)


if __name__ == "__main__":
    unittest.main()
