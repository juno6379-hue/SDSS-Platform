"""새 공간후보는 로컬 기하/SHA를 확인하며 실제 클래스 확보로 오인하지 않는다."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "backend"))
from app.data.candidates import validate_candidate_plan


class CandidateTests(unittest.TestCase):
    def fixture(self, directory):
        boundary = directory / "boundary.json"
        boundary.write_text(json.dumps({"features":[{"properties":{"province_id":"banten"},"geometry":{
            "type":"Polygon","coordinates":[[[105,-7],[107,-7],[107,-5],[105,-5],[105,-7]]]}}]}),encoding="utf-8")
        candidate = {"province":"banten","spatial_window_id":"v2-laneB-test","lon":106,"lat":-6,
            "grid_crs":"EPSG:32748","window_size":1024,"years":[2020,2021,2022,2023,2024,2025],
            "reference":"esri_io","boundary_sha256":hashlib.sha256(boundary.read_bytes()).hexdigest()}
        path = directory / "candidates.json"
        document = {"schema_version":1,"executed_network":False,"collector_consumption_approved":False,"candidates":[candidate]}
        path.write_text(json.dumps(document),encoding="utf-8")
        return path,boundary,document

    def test_local_candidate_keeps_class_presence_unverified(self):
        with tempfile.TemporaryDirectory() as temp:
            path,boundary,_ = self.fixture(Path(temp))
            result = validate_candidate_plan(path,boundary)
            self.assertEqual(len(result["candidates"]),1)
            self.assertFalse(result["class_presence_verified"])
            self.assertFalse(result["source_proposal_consumption_flag"])

    def test_new_id_does_not_allow_overlapping_previous_window(self):
        with tempfile.TemporaryDirectory() as temp:
            path,boundary,_ = self.fixture(Path(temp))
            with self.assertRaises(ValueError):
                validate_candidate_plan(path,boundary,[{"province":"banten","lon":106.001,"lat":-6,"grid_crs":"EPSG:32748"}])

    def test_boundary_digest_and_outside_point_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path,boundary,document = self.fixture(Path(temp))
            document["candidates"][0]["boundary_sha256"] = "wrong"
            path.write_text(json.dumps(document))
            with self.assertRaises(ValueError):
                validate_candidate_plan(path,boundary)
            document["candidates"][0]["boundary_sha256"] = hashlib.sha256(boundary.read_bytes()).hexdigest()
            document["candidates"][0]["lon"] = 110
            path.write_text(json.dumps(document))
            with self.assertRaises(ValueError):
                validate_candidate_plan(path,boundary)


if __name__ == "__main__":
    unittest.main()
