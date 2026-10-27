"""Deterministic tests for the fail-closed acquisition planner."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.ml.province_year_coverage import PinnedFile, sha256_file
from app.ml.province_year_gap_acquisition_planner import (
    BOUNDARY_SCHEMA_VERSION, CAUSE_MASK_POLICY_VERSION, CAUSE_MASK_SEMANTICS,
    ESRI_PROVENANCE_SCHEMA_VERSION, GISTARU_REFERENCE_SCHEMA_VERSION,
    OBSERVED_MASK_POLICY_VERSION,
    OBSERVED_MASK_SEMANTICS, PLAN_SCHEMA_VERSION, PROVINCES, ROLE_CONTRACT,
    SENTINEL_PROVENANCE_SCHEMA_VERSION, SOURCE_SCHEMA_VERSION, YEARS,
    GapPlanningEvidenceError,
    build_gap_acquisition_plan,
)
from plan_province_year_gap_acquisition import main as cli_main


class PlannerFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.observed = self.root / "observed.tif"
        self.cause = self.root / "cause.tif"
        self.boundaries = self.root / "boundaries.geojson"
        self.gistaru = self.root / "gistaru-reference.json"
        self.source = self.root / "source.json"
        self.comparison = self.root / "gistaru-comparison.json"
        self.service_metadata = self.root / "gistaru-service-metadata.json"
        self.sentinel = self.root / "sentinel-source.json"
        self.esri = self.root / "esri-weak-label.json"
        self._write_masks()
        self._write_support_files()
        self._write_boundaries()
        self._write_gistaru()
        self._write_source()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_masks(self, *, cause_transform=None, cause_values=None):
        transform = from_origin(0, 20, 10, 10)
        profile = dict(driver="GTiff", height=2, width=3, count=1, dtype="uint8",
                       crs="EPSG:6933", transform=transform)
        with rasterio.open(self.observed, "w", **profile) as ds:
            ds.write(np.array([[1, 0, 0], [0, 0, 1]], dtype="uint8"), 1)
        profile["transform"] = cause_transform or transform
        values = cause_values if cause_values is not None else np.array([[0, 1, 2], [3, 4, 0]], dtype="uint8")
        with rasterio.open(self.cause, "w", **profile) as ds:
            ds.write(values, 1)

    def _write_support_files(self):
        self.comparison.write_text(json.dumps({"comparison": "fixture"}), encoding="utf-8")
        self.service_metadata.write_text(json.dumps({
            "currentVersion": 11.1,
            "mapName": "Synthetic GISTARU boundary comparison fixture",
            "layers": [{"id": 0, "name": "Synthetic province boundary"}],
        }), encoding="utf-8")
        self.sentinel.write_text(json.dumps({
            "schema_version": SENTINEL_PROVENANCE_SCHEMA_VERSION,
            "evidence_status": "TESTED_SYNTHETIC",
            "role": ROLE_CONTRACT["sentinel2"], "collection": "sentinel-2-l2a",
            "scl_policy": "fixture-only", "scl_used_for_cause": True,
            "fixture_only": True, "observations_verified": False,
        }), encoding="utf-8")
        self.esri.write_text(json.dumps({
            "schema_version": ESRI_PROVENANCE_SCHEMA_VERSION,
            "evidence_status": "TESTED_SYNTHETIC",
            "role": ROLE_CONTRACT["esri"], "use": "training-reference-only",
            "used_for_gap_detection": False, "used_as_independent_ground_truth": False,
        }), encoding="utf-8")

    def _write_boundaries(self, mutate=None):
        inv = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
        ring = [inv.transform(x, y) for x, y in [(0, 0), (30, 0), (30, 20), (0, 20), (0, 0)]]
        doc = {
            "type": "FeatureCollection", "schema_version": BOUNDARY_SCHEMA_VERSION,
            "evidence_status": "TESTED_SYNTHETIC",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "authority": {
                "legal_status": "AUTHORITATIVE_ADMINISTRATIVE_BOUNDARY",
                "approved_for_statistics": True,
                "organization": "Synthetic competent authority",
                "publication_id": "fixture-boundary-v1",
                "effective_date": "2025-01-01",
                "source_url": "https://example.test/boundary",
            },
            "features": [{
                "type": "Feature", "properties": {"province_id": province},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            } for province in PROVINCES],
        }
        if mutate:
            mutate(doc)
        self.boundaries.write_text(json.dumps(doc), encoding="utf-8")

    def _write_gistaru(self, mutate=None):
        doc = {
            "schema_version": GISTARU_REFERENCE_SCHEMA_VERSION,
            "evidence_status": "TESTED_SYNTHETIC",
            "portal_url": "https://gistaru.atrbpn.go.id",
            "service_url": "https://gistaru.atrbpn.go.id/arcgis/rest/services/fixture/MapServer",
            "layer_id": 0,
            "layer_name": "Synthetic province boundary",
            "query_where": "province_id IS NOT NULL",
            "out_sr": 4326,
            "retrieved_at": "2026-10-21T00:00:00Z",
            "role": ROLE_CONTRACT["gistaru"],
            "checked_at": "2026-10-21T00:00:00Z",
            "boundary_sha256": sha256_file(self.boundaries),
            "comparison_status": "VERIFIED_MATCH",
            "service_metadata_evidence": {
                "path": self.service_metadata.name,
                "sha256": sha256_file(self.service_metadata),
            },
            "comparison_evidence": {
                "path": self.comparison.name, "sha256": sha256_file(self.comparison),
            },
        }
        if mutate:
            mutate(doc)
        self.gistaru.write_text(json.dumps(doc), encoding="utf-8")

    def _write_source(self, mutate=None):
        observed_ref = {"path": self.observed.name, "sha256": sha256_file(self.observed)}
        cause_ref = {"path": self.cause.name, "sha256": sha256_file(self.cause)}
        cells = [{
            "province_id": province, "year": year,
            "observed_mosaic": dict(observed_ref),
            "observed_contract": {
                "semantics": OBSERVED_MASK_SEMANTICS,
                "version": OBSERVED_MASK_POLICY_VERSION, "nodata": None,
            },
            "cause_mosaic": dict(cause_ref),
            "cause_contract": {
                "semantics": CAUSE_MASK_SEMANTICS,
                "version": CAUSE_MASK_POLICY_VERSION, "nodata": None,
            },
        } for province in PROVINCES for year in YEARS]
        doc = {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "evidence_status": "TESTED_SYNTHETIC",
            "boundary_sha256": sha256_file(self.boundaries),
            "gistaru_reference_sha256": sha256_file(self.gistaru),
            "roles": dict(ROLE_CONTRACT),
            "esri_used_for_gap_detection": False,
            "esri_used_for_boundary": False,
            "sentinel2_used_for_gap_detection": True,
            "sentinel2_source_manifest": {
                "path": self.sentinel.name, "sha256": sha256_file(self.sentinel),
            },
            "esri_weak_label_manifest": {
                "path": self.esri.name, "sha256": sha256_file(self.esri),
            },
            "cells": cells,
        }
        if mutate:
            mutate(doc)
        self.source.write_text(json.dumps(doc), encoding="utf-8")

    def build(self):
        return build_gap_acquisition_plan(
            root=self.root,
            source=PinnedFile(self.source, sha256_file(self.source)),
            boundaries=PinnedFile(self.boundaries, sha256_file(self.boundaries)),
            gistaru_reference=PinnedFile(self.gistaru, sha256_file(self.gistaru)),
            evidence_status="TESTED_SYNTHETIC",
        )

    def build_provisional(self, *, mutate_decision=None):
        boundary_doc = json.loads(self.boundaries.read_text(encoding="utf-8"))
        boundary_doc.update(
            schema_version="province-boundary-candidate/1.0",
            evidence_status="IMPLEMENTED_UNVERIFIED",
            status="CANDIDATE_PENDING_COMPETENT_AUTHORITY_AND_STATISTICAL_APPROVAL",
        )
        boundary_doc["authority"] = {
            "organization": "Badan Informasi Geospasial (BIG)",
            "official_public_service": True,
            "layer_id": 12,
            "approved_for_project_statistics": False,
            "source_url": "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_WILAYAH/MapServer/12",
        }
        self.boundaries.write_text(json.dumps(boundary_doc), encoding="utf-8")
        decision = self.root / "cross-check-decision.json"
        decision_doc = {
            "schema_version": "spatial-plan-cross-check-decision/1.0",
            "decision": "SKIP_GISTARU_BY_USER_DECISION",
            "scope": "PROVISIONAL_SENTINEL_PILOT_ONLY",
            "authorized_by": "USER_EXPLICIT_INSTRUCTION",
            "risk_acknowledged": True,
            "recorded_at": "2026-10-27T07:00:00Z",
            "boundary_sha256": sha256_file(self.boundaries),
            "remaining_blockers": [
                "BOUNDARY_APPROVAL_PENDING", "NOT_AUTHORIZED_FOR_TRAINING_OR_DEPLOYMENT",
            ],
        }
        if mutate_decision:
            mutate_decision(decision_doc)
        decision.write_text(json.dumps(decision_doc), encoding="utf-8")
        mosaic = self.root / "mosaic-manifest.json"
        cells = [{
            "province_id": province,
            "year": year,
            "observed_path": self.observed.name,
            "observed_sha256": sha256_file(self.observed),
            "cause_path": self.cause.name,
            "cause_sha256": sha256_file(self.cause),
        } for province in PROVINCES for year in YEARS]
        mosaic.write_text(json.dumps({
            "schema_version": "province-year-scl-mosaic-manifest/1.0",
            "evidence_status": "IMPLEMENTED_UNVERIFIED",
            "boundary": {"path": str(self.boundaries), "sha256": sha256_file(self.boundaries)},
            "cells": cells,
            "source_assets": [{"path": str(self.observed), "sha256": sha256_file(self.observed)}],
        }), encoding="utf-8")
        return build_gap_acquisition_plan(
            root=self.root,
            source=PinnedFile(mosaic, sha256_file(mosaic)),
            boundaries=PinnedFile(self.boundaries, sha256_file(self.boundaries)),
            cross_check_decision=PinnedFile(decision, sha256_file(decision)),
            evidence_status="PROVISIONAL_REAL",
        )


class TestGapAcquisitionPlanner(PlannerFixture):
    def test_provisional_pilot_skips_gistaru_only_with_pinned_user_decision(self):
        plan = self.build_provisional()
        self.assertEqual(plan.planning_status, "PROVISIONAL_PILOT_PLANNED_NO_EXECUTION")
        self.assertEqual(plan.cross_check_status, "SKIPPED_BY_USER_DECISION")
        self.assertIsNone(plan.gistaru_reference_sha256)
        self.assertIsNotNone(plan.cross_check_decision_sha256)
        self.assertIn("BOUNDARY_APPROVAL_PENDING", plan.mlops_handoff.blockers)
        self.assertFalse(plan.execution_authorized)

    def test_provisional_pilot_rejects_decision_for_different_boundary(self):
        with self.assertRaisesRegex(
            GapPlanningEvidenceError, "CROSS_CHECK_DECISION_BOUNDARY_SHA256_MISMATCH"
        ):
            self.build_provisional(
                mutate_decision=lambda doc: doc.update(boundary_sha256="0" * 64)
            )

    def test_valid_36_cell_fixture_produces_non_executing_targets(self):
        plan = self.build()
        self.assertEqual(plan.schema_version, PLAN_SCHEMA_VERSION)
        self.assertEqual(plan.planning_status, "TESTED_SYNTHETIC_NO_EXECUTION")
        self.assertEqual(len(plan.cells), 36)
        self.assertEqual(plan.target_count, 144)
        self.assertEqual({t.gap_cause for t in plan.targets},
                         {"CLOUD", "SHADOW", "NODATA", "OUTSIDE_FOOTPRINT"})
        self.assertTrue(all(c.total_boundary_pixels == 6 and c.observed_pixels == 2 and c.gap_pixels == 4
                            for c in plan.cells))
        self.assertFalse(plan.execution_authorized)
        self.assertFalse(plan.collector_invoked)
        self.assertFalse(plan.ledger_written)
        self.assertFalse(plan.execution_lock_acquired)
        self.assertFalse(plan.remote_downloads_performed)
        self.assertTrue(all(not target.remote_request_created for target in plan.targets))
        self.assertFalse(plan.mlops_handoff.retraining_ready)
        self.assertIsNone(plan.mlops_handoff.immutable_dataset_pin)

    def test_plan_never_opens_retraining_before_execution_qa_and_dataset_pin(self):
        handoff = self.build().mlops_handoff
        self.assertEqual(handoff.status, "BLOCKED_PENDING_ACQUISITION_AND_DATASET_PIN")
        by_id = {gate.gate_id: gate for gate in handoff.required_gates}
        self.assertEqual(by_id["coverage_boundary_cause_evidence"].status, "TESTED_SYNTHETIC")
        self.assertEqual(by_id["acquisition_execution"].status, "BLOCKED")
        self.assertEqual(by_id["acquisition_quality_qa"].status, "BLOCKED")
        self.assertEqual(by_id["immutable_dataset_pin"].status, "BLOCKED")
        self.assertEqual(by_id["retraining_readiness"].status, "BLOCKED")
        self.assertIn("ACQUISITION_NOT_EXECUTED", handoff.blockers)
        self.assertIn("IMMUTABLE_DATASET_NOT_PINNED", handoff.blockers)
        self.assertIn("SYNTHETIC_INPUT_NOT_OPERATIONAL_EVIDENCE", handoff.blockers)

    def test_non_authoritative_boundary_blocks_before_targets(self):
        self._write_boundaries(lambda doc: doc["authority"].update(
            legal_status="REFERENCE_ONLY", approved_for_statistics=False))
        with self.assertRaisesRegex(GapPlanningEvidenceError, "BOUNDARY_NOT_AUTHORITATIVE"):
            self.build()

    def test_gistaru_reference_must_be_pinned_and_verified(self):
        self._write_gistaru(lambda doc: doc.update(comparison_status="UNVERIFIED"))
        self._write_source()
        with self.assertRaisesRegex(GapPlanningEvidenceError, "GISTARU_COMPARISON_NOT_VERIFIED"):
            self.build()

    def test_gistaru_reference_requires_exact_service_and_layer_metadata(self):
        self._write_gistaru(lambda doc: doc.pop("service_metadata_evidence"))
        self._write_source()
        with self.assertRaisesRegex(
            GapPlanningEvidenceError, "GISTARU_SERVICE_METADATA_EVIDENCE_REQUIRED"
        ):
            self.build()

        self._write_gistaru(lambda doc: doc.update(
            service_url="https://gistaru.atrbpn.go.id/not-an-arcgis-mapserver"
        ))
        self._write_source()
        with self.assertRaisesRegex(GapPlanningEvidenceError, "GISTARU_MAPSERVER_URL_REQUIRED"):
            self.build()

    def test_esri_cannot_be_promoted_from_weak_label_to_gap_evidence(self):
        self._write_source(lambda doc: doc.update(esri_used_for_gap_detection=True))
        with self.assertRaisesRegex(GapPlanningEvidenceError, "ESRI_WEAK_LABEL_CANNOT_DEFINE_GAPS"):
            self.build()

    def test_observed_and_cause_mosaics_must_share_exact_grid(self):
        self._write_masks(cause_transform=from_origin(5, 20, 10, 10))
        self._write_source()
        with self.assertRaisesRegex(GapPlanningEvidenceError, "SAME_GRID_MOSAICS_REQUIRED"):
            self.build()

    def test_every_gap_pixel_requires_a_measured_cause(self):
        values = np.array([[0, 0, 2], [3, 4, 0]], dtype="uint8")
        self._write_masks(cause_values=values)
        self._write_source()
        with self.assertRaisesRegex(GapPlanningEvidenceError, "UNCLASSIFIED_GAP_PIXEL"):
            self.build()

    def test_exact_36_cell_scope_is_required(self):
        self._write_source(lambda doc: doc["cells"].pop())
        with self.assertRaisesRegex(GapPlanningEvidenceError, "SOURCE_EXACT_36_CELL_SCOPE_REQUIRED"):
            self.build()

    def test_sha_mismatch_blocks(self):
        with self.assertRaisesRegex(GapPlanningEvidenceError, "SOURCE_SHA256_MISMATCH"):
            build_gap_acquisition_plan(
                root=self.root,
                source=PinnedFile(self.source, "0" * 64),
                boundaries=PinnedFile(self.boundaries, sha256_file(self.boundaries)),
                gistaru_reference=PinnedFile(self.gistaru, sha256_file(self.gistaru)),
                evidence_status="TESTED_SYNTHETIC",
            )

    def test_missing_input_is_a_fail_closed_evidence_error(self):
        with self.assertRaisesRegex(GapPlanningEvidenceError, "SOURCE_FILE_MISSING"):
            build_gap_acquisition_plan(
                root=self.root,
                source=PinnedFile(self.root / "missing-source.json", "0" * 64),
                boundaries=PinnedFile(self.boundaries, sha256_file(self.boundaries)),
                gistaru_reference=PinnedFile(self.gistaru, sha256_file(self.gistaru)),
                evidence_status="TESTED_SYNTHETIC",
            )

    def test_cli_writes_only_after_success_and_never_overwrites(self):
        output = self.root / "out" / "plan.json"
        args = [
            "--root", str(self.root), "--source", str(self.source),
            "--source-sha256", sha256_file(self.source),
            "--boundaries", str(self.boundaries),
            "--boundaries-sha256", sha256_file(self.boundaries),
            "--gistaru-reference", str(self.gistaru),
            "--gistaru-reference-sha256", sha256_file(self.gistaru),
            "--output", str(output), "--evidence-status", "TESTED_SYNTHETIC",
        ]
        self.assertEqual(cli_main(args), 0)
        self.assertTrue(output.is_file())
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["target_count"], 144)
        self.assertEqual(cli_main(args), 2)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["target_count"], 144)

    def test_cli_failure_does_not_create_output(self):
        output = self.root / "blocked.json"
        result = cli_main([
            "--root", str(self.root), "--source", str(self.source),
            "--source-sha256", "0" * 64,
            "--boundaries", str(self.boundaries),
            "--boundaries-sha256", sha256_file(self.boundaries),
            "--gistaru-reference", str(self.gistaru),
            "--gistaru-reference-sha256", sha256_file(self.gistaru),
            "--output", str(output), "--evidence-status", "TESTED_SYNTHETIC",
        ])
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
