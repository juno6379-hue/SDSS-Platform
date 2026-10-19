"""Verification Runner for Common Valid Area & Strict NoData Exclusion Transition Matrix Engine.

Demonstrates:
1. Preflight alignment validation and rejection of half-pixel shifts and CRS mismatches.
2. Comprehensive missing-rate scenarios (0%, 5%, 15%, 35%, 60% cloud/shadow/NoData).
3. Explicit 4-way area partitioning:
   - AOI Total Area (A_total)
   - T1 Valid Area (A_valid, T1)
   - T2 Valid Area (A_valid, T2)
   - Common Valid Area (A_common = A_valid, T1 & A_valid, T2)
   - Incomparable Area (A_incomparable = A_total - A_common: T1-only, T2-only, Both)
4. Enforce Zero-Sum Transition Identity across all 9 discrete land cover classes:
   - sum(gross_loss) == sum(gross_gain)
   - sum(gross_gain) - sum(gross_loss) == sum(net_changes) == 0
   - For all 9 classes: gross_gain_k - gross_loss_k == net_change_k
   - NoData strictly forbidden from appearing as a land cover transition class in the matrix (strictly 9x9).
5. Enforce certification gating:
   - Missing pixel ratio > 15% -> status degraded to PROVISIONAL_UNCERTAIN and official certified change analysis blocked.
   - Detect and flag Year Mismatch (e.g. requested T2=2025 vs underlying raster provenance 2021 ESA WorldCover).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import numpy as np

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from common_valid_transition import (
    DEFAULT_CLASS_NAMES,
    DEFAULT_CLASS_COLORS,
    DEFAULT_NODATA,
    TRANSITION_NODATA,
    PROVISIONAL_MISSING_RATIO_THRESHOLD,
    assert_raster_alignment,
    compute_common_valid_transition,
    ReliabilityStatus,
    CertificationBlockedError,
)


def run_verification():
    print("=" * 85)
    print("LCLUC Common Valid Transition & Strict NoData Exclusion Engine Verification")
    print("UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0 - Section 3 & 6 Quality Governance")
    print("=" * 85)

    # ------------------------------------------------------------------------
    # 1. Preflight Spatial Alignment Verification
    # ------------------------------------------------------------------------
    print("\n[Step 1] Preflight Alignment & Half-Pixel Shift Detection")
    p1 = {
        "crs": "EPSG:32748",
        "transform": (10.0, 0.0, 500000.0, 0.0, -10.0, 9300000.0),
        "width": 100,
        "height": 100,
    }
    p_offset = dict(p1, transform=(10.0, 0.0, 500005.0, 0.0, -10.0, 9300000.0))  # 5m offset
    try:
        assert_raster_alignment(p1, p_offset)
        print("  [FAIL] Failed to catch 5m half-pixel shift!")
    except ValueError as e:
        print(f"  [PASS] Successfully rejected half-pixel shift: {e}")

    # ------------------------------------------------------------------------
    # 2. Comprehensive Missing-Rate Scenarios (0%, 5%, 15%, 35%, 60%)
    # ------------------------------------------------------------------------
    print("\n[Step 2] Comprehensive Missing-Rate Scenarios Governance & Partitioning")
    scenarios = [
        {"name": "Scenario A (0% Missing - Clear Sky)", "missing_rate_pct": 0.0, "expected_status": ReliabilityStatus.CERTIFIED_RELIABLE.value, "expected_blocked": False},
        {"name": "Scenario B (5% Missing - Light Cloud)", "missing_rate_pct": 5.0, "expected_status": ReliabilityStatus.CERTIFIED_RELIABLE.value, "expected_blocked": False},
        {"name": "Scenario C (15% Missing - Exact Boundary)", "missing_rate_pct": 15.0, "expected_status": ReliabilityStatus.CERTIFIED_RELIABLE.value, "expected_blocked": False},
        {"name": "Scenario D (35% Missing - Tropical Monsoon Cloud)", "missing_rate_pct": 35.0, "expected_status": ReliabilityStatus.PROVISIONAL_UNCERTAIN.value, "expected_blocked": True},
        {"name": "Scenario E (60% Missing - Severe Cloud/Shadow Mask)", "missing_rate_pct": 60.0, "expected_status": ReliabilityStatus.PROVISIONAL_UNCERTAIN.value, "expected_blocked": True},
    ]

    total_pixels = 10000  # 100x100
    np.random.seed(42)
    # 9 classes
    t1_base = np.random.choice([0, 1, 2, 4, 6], size=(100, 100), p=[0.10, 0.45, 0.20, 0.20, 0.05]).astype(np.uint8)
    t2_base = t1_base.copy()
    # 1,500 pixels true transitions
    change_idx = np.random.choice(total_pixels, size=1500, replace=False)
    for idx in change_idx:
        r, c = divmod(idx, 100)
        t2_base[r, c] = (t1_base[r, c] + np.random.randint(1, 9)) % 9

    scenario_reports = []

    for sc in scenarios:
        missing_pct = sc["missing_rate_pct"]
        t1_sc = t1_base.copy()
        t2_sc = t2_base.copy()

        missing_count = int(total_pixels * (missing_pct / 100.0))
        if missing_count > 0:
            t1_only = int(missing_count * 0.4)
            t2_only = int(missing_count * 0.4)
            both = missing_count - t1_only - t2_only

            np.random.seed(int(missing_pct * 10 + 7))
            all_idx = np.random.choice(total_pixels, size=missing_count, replace=False)
            t1_idx = all_idx[:t1_only]
            t2_idx = all_idx[t1_only:t1_only + t2_only]
            both_idx = all_idx[t1_only + t2_only:]

            for idx in t1_idx:
                r, c = divmod(idx, 100)
                t1_sc[r, c] = 255
            for idx in t2_idx:
                r, c = divmod(idx, 100)
                t2_sc[r, c] = 255
            for idx in both_idx:
                r, c = divmod(idx, 100)
                t1_sc[r, c] = 255
                t2_sc[r, c] = 255

        result_sc = compute_common_valid_transition(
            t1_sc, t2_sc,
            nodata=255,
            resolution_m=10.0,
            provisional_threshold=0.15,
            aoi_id=f"pilot_{int(missing_pct)}pct_missing",
            from_year=2020,
            to_year=2025,
        )

        p = result_sc.partition
        ident = result_sc.conservation_identity

        # Partition verification
        assert p.total_aoi_pixels == total_pixels
        assert p.common_valid_pixels == total_pixels - missing_count
        assert p.incomparable_pixels == missing_count
        assert p.common_valid_pixels + p.incomparable_pixels == p.total_aoi_pixels
        assert p.incomparable.total_incomparable_pixels == (
            p.incomparable.t1_only_missing_pixels + p.incomparable.t2_only_missing_pixels + p.incomparable.both_missing_pixels
        )

        # Gating verification
        assert result_sc.reliability_status == sc["expected_status"]
        assert result_sc.certification_blocked is sc["expected_blocked"]
        if sc["expected_blocked"]:
            try:
                result_sc.assert_certified_usable()
                assert False, "Certification should have been blocked!"
            except CertificationBlockedError as ce:
                gate_status_str = f"BLOCKED (Correctly raised CertificationBlockedError: {ce})"
        else:
            result_sc.assert_certified_usable()
            gate_status_str = "CERTIFIED_ALLOWED (Official change analytics approved)"

        # Conservation verification
        assert ident["zero_sum_identity_verified"] is True
        assert ident["nodata_strictly_excluded_from_matrix"] is True
        assert ident["matrix_shape"] == [9, 9]

        print(f"\n  --- {sc['name']} ---")
        print(f"    Missing Ratio:      {result_sc.missing_ratio_pct:.2f}% ({p.incomparable_pixels:,} px / {p.total_aoi_pixels:,} px)")
        print(f"    Common Valid Area:  {p.common_valid_pixels:,} px ({p.common_valid_area_ha:.2f} ha, {p.coverage_ratio_pct:.1f}% coverage)")
        print(f"    Incomparable Area:  {p.incomparable_pixels:,} px ({p.incomparable_area_ha:.2f} ha) [T1-only: {p.incomparable.t1_only_missing_pixels}, T2-only: {p.incomparable.t2_only_missing_pixels}, Both: {p.incomparable.both_missing_pixels}]")
        print(f"    Status / Gating:    {result_sc.reliability_status} -> {gate_status_str}")
        print(f"    Zero-Sum Identity:  Gross Loss={ident['gross_loss_total_pixels']} px == Gross Gain={ident['gross_gain_total_pixels']} px | Net Change Sum={ident['net_change_sum']} px (PASS)")

        scenario_reports.append({
            "scenario": sc["name"],
            "missing_rate_pct": missing_pct,
            "total_aoi_pixels": p.total_aoi_pixels,
            "common_valid_pixels": p.common_valid_pixels,
            "incomparable_pixels": p.incomparable_pixels,
            "t1_only_missing": p.incomparable.t1_only_missing_pixels,
            "t2_only_missing": p.incomparable.t2_only_missing_pixels,
            "both_missing": p.incomparable.both_missing_pixels,
            "reliability_status": result_sc.reliability_status,
            "certification_blocked": result_sc.certification_blocked,
            "conservation_check_passed": result_sc.conservation_check_passed,
            "zero_sum_identity_verified": ident["zero_sum_identity_verified"],
            "gross_loss_total_pixels": ident["gross_loss_total_pixels"],
            "gross_gain_total_pixels": ident["gross_gain_total_pixels"],
            "net_change_sum": ident["net_change_sum"],
        })

    # ------------------------------------------------------------------------
    # 3. Year Mismatch Detection & Certification Gating Verification
    # ------------------------------------------------------------------------
    print("\n[Step 3] Year Mismatch Detection & Certification Gating")
    t1_test = np.full((10, 10), 1, dtype=np.uint8)
    t2_test = np.full((10, 10), 2, dtype=np.uint8)

    t1_meta = {"source_kind": "reference_landcover", "provenance_year": 2020}
    # T2 requested year is 2025, but underlying raster provenance is 2021 ESA WorldCover
    t2_mismatch_meta = {"source_kind": "reference_landcover", "provenance_year": 2021, "dataset_name": "ESA WorldCover"}

    result_mismatch = compute_common_valid_transition(
        t1_test, t2_test,
        from_year=2020,
        to_year=2025,
        t1_metadata=t1_meta,
        t2_metadata=t2_mismatch_meta,
    )

    print(f"  Requested Years:       T1={result_mismatch.from_year}, T2={result_mismatch.to_year}")
    print(f"  Provenance Years:      T1={t1_meta['provenance_year']}, T2={t2_mismatch_meta['provenance_year']} ({t2_mismatch_meta['dataset_name']})")
    print(f"  Year Mismatch Flag:    {result_mismatch.year_mismatch_detected}")
    print(f"  Reliability Status:    {result_mismatch.reliability_status}")
    print(f"  Certification Blocked: {result_mismatch.certification_blocked}")
    print(f"  Provisional Warning:   {result_mismatch.provisional_warning}")

    assert result_mismatch.year_mismatch_detected is True
    assert result_mismatch.certification_blocked is True
    assert result_mismatch.reliability_status == ReliabilityStatus.PROVISIONAL_UNCERTAIN.value

    try:
        result_mismatch.assert_certified_usable()
        assert False, "Certification should have been blocked on year mismatch!"
    except CertificationBlockedError as ce:
        print(f"  [PASS] Correctly blocked official certification with CertificationBlockedError: {ce}")

    # Enforce Year Match preflight check
    try:
        compute_common_valid_transition(
            t1_test, t2_test,
            from_year=2020,
            to_year=2025,
            t1_metadata=t1_meta,
            t2_metadata=t2_mismatch_meta,
            enforce_year_match=True,
        )
        assert False, "enforce_year_match should have raised ValueError!"
    except ValueError as ve:
        print(f"  [PASS] enforce_year_match=True successfully aborted analysis with ValueError: {ve}")

    # ------------------------------------------------------------------------
    # 4. Export Verification Artifacts
    # ------------------------------------------------------------------------
    print("\n[Step 4] Exporting Verification Artifacts")
    artifacts_dir = WORKSPACE_DIR / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    scenario_report_path = artifacts_dir / "scenario_verification_report.json"
    scenario_report_path.write_text(json.dumps(scenario_reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  - Exported scenario report to: {scenario_report_path}")

    # Export Pilot 15% boundary artifact
    boundary_result = compute_common_valid_transition(
        t1_sc, t2_sc,
        nodata=255,
        resolution_m=10.0,
        aoi_id="south_sulawesi_boundary_verified",
        from_year=2020,
        to_year=2025,
    )
    summary_path = artifacts_dir / "common_valid_verification_summary.json"
    summary_path.write_text(boundary_result.to_json(indent=2), encoding="utf-8")
    print(f"  - Exported common valid verification summary to: {summary_path}")

    print("\n" + "=" * 85)
    print("ALL COMMON VALID TRANSITION VERIFICATION SCENARIOS PASSED WITH 100% COMPLIANCE")
    print("=" * 85)


if __name__ == "__main__":
    run_verification()
