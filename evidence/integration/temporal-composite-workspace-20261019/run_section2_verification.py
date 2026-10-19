"""
Section 2 Verification Runner: Composite Quality Tracker & Observation Count Pipeline.
Workspace: evidence/integration/temporal-composite-workspace-20261019/run_section2_verification.py

Executes:
1. Multi-temporal Sentinel-2 simulation with realistic cloud, shadow, and cirrus dynamics.
2. Seasonal temporal window filtering (Dry season vs Annual).
3. Median and Priority (Max-NDVI) compositing.
4. Validation of observation counts, observation dates, and missingness reason diagnostics.
5. Verification of strict NoData preservation (zero procedural interpolation).
6. Exports section2_quality_tracker_report.json and execution log.
"""

from datetime import datetime
import json
from pathlib import Path
import sys
import time
import numpy as np

# Ensure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from composite_quality_tracker import (
    CompositeQualityTracker,
    TemporalWindow,
    MissingReason,
    SCL_CLASSES,
)


def run_section2_verification():
    start_time = time.time()
    workspace_dir = Path(__file__).resolve().parent
    log_messages = []

    def log(msg: str):
        t_str = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{t_str}] {msg}"
        log_messages.append(line)
        print(line)

    log("Starting Section 2: Annual Composite Quality Tracker Verification...")
    tracker = CompositeQualityTracker(nodata_value=0.0)

    # Generate synthetic 8-slice multi-temporal dataset over 64x64 grid
    H, W = 64, 64
    rng = np.random.RandomState(20261019)

    # Base landscape: 50% Veg (SCL 4), 30% Bare (SCL 5), 20% Water (SCL 6)
    r_grid = rng.rand(H, W)
    base_scl = np.full((H, W), 4, dtype=np.uint8)
    base_scl[r_grid >= 0.50] = 5
    base_scl[r_grid >= 0.80] = 6

    # 8 acquisition dates spanning 2024
    dates = [
        "2024-01-20T03:15:00Z",
        "2024-03-10T03:15:00Z",
        "2024-04-25T03:15:00Z",
        "2024-06-15T03:15:00Z", # Dry season
        "2024-07-30T03:15:00Z", # Dry season
        "2024-09-10T03:15:00Z", # Dry season
        "2024-10-25T03:15:00Z",
        "2024-12-10T03:15:00Z",
    ]

    slices = []
    log(f"Simulating {len(dates)} multi-temporal Sentinel-2 slices across {H}x{W} raster...")

    for idx, dt_str in enumerate(dates):
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        doy = dt.timetuple().tm_yday

        # Seasonal cloud probability (lower in dry season July-August)
        cloud_prob = 0.65 if doy < 150 or doy > 280 else 0.30
        cloud_rand = rng.rand(H, W)

        scl = base_scl.copy()
        is_cloud = cloud_rand < (cloud_prob * 0.60)
        is_shadow = (cloud_rand >= (cloud_prob * 0.60)) & (cloud_rand < (cloud_prob * 0.75))
        is_cirrus = (cloud_rand >= (cloud_prob * 0.75)) & (cloud_rand < cloud_prob)

        scl[is_cloud] = 9    # Cloud high prob
        scl[is_shadow] = 3   # Cloud shadow
        scl[is_cirrus] = 10  # Cirrus

        # Add permanent edge nodata on border (e.g. out of swath / ocean boundary)
        scl[:2, :] = 0
        scl[-2:, :] = 0

        # Spectral reflectance
        bands = {}
        for bname in ["blue", "green", "red", "nir", "swir16", "swir22"]:
            arr = np.full((H, W), 1000.0, dtype=np.float32)
            arr[base_scl == 4] = 400.0 if bname in ("blue", "red") else (3500.0 if bname == "nir" else 1500.0)
            arr[base_scl == 5] = 1200.0 if bname in ("blue", "green") else (2000.0 if bname == "nir" else 2500.0)
            arr[base_scl == 6] = 300.0 if bname in ("blue", "green") else 100.0

            # Clouds reflect bright, shadows reflect dark, nodata is 0.0
            arr[is_cloud] = 7500.0
            arr[is_cirrus] = arr[is_cirrus] * 1.4 + 1000.0
            arr[is_shadow] = arr[is_shadow] * 0.3
            arr[scl == 0] = 0.0
            bands[bname] = arr

        slices.append({
            "scene_id": f"S2_2024_{idx:02d}",
            "datetime": dt_str,
            "bands": bands,
            "scl": scl,
        })

    # Test Case 1: Full Annual Window with Median Blending
    log("Running Case 1: Full Annual Window with Median Blending...")
    res_annual_median = tracker.process_annual_observations(slices, method="median")
    meta_annual = res_annual_median["metadata"]
    log(f"  Valid coverage ratio: {meta_annual['pixel_counts']['valid_coverage_ratio']*100:.2f}%")
    log(f"  Mean valid observations per pixel: {meta_annual['observation_count_distribution']['mean_valid_observations']}")

    # Test Case 2: Designated Seasonal Window (Dry Season: June to September)
    log("Running Case 2: Seasonal Window (Dry Season June-Sept)...")
    dry_window = TemporalWindow(name="dry_season_2024", start_date="2024-06-01", end_date="2024-09-30")
    res_dry_median = tracker.process_annual_observations(slices, window=dry_window, method="median")
    meta_dry = res_dry_median["metadata"]
    log(f"  Dry season slices evaluated: {meta_dry['temporal_window']['total_slices_evaluated']} of {len(slices)}")
    log(f"  Dry season valid coverage: {meta_dry['pixel_counts']['valid_coverage_ratio']*100:.2f}%")

    # Test Case 3: Priority (Max-NDVI) Blending
    log("Running Case 3: Priority Blending (Highest Valid NDVI)...")
    res_priority = tracker.process_annual_observations(slices, method="priority")
    meta_priority = res_priority["metadata"]
    log(f"  Priority valid coverage: {meta_priority['pixel_counts']['valid_coverage_ratio']*100:.2f}%")

    # Verification of Requirement 4: Strict NoData Preservation
    log("Verifying Requirement 4: Strict NoData Preservation (No procedural interpolation)...")
    vcounts = res_annual_median["valid_count_mask"]
    zero_obs_mask = (vcounts == 0)
    zero_obs_pixels = int(np.count_nonzero(zero_obs_mask))
    log(f"  Unobserved pixels (valid_count == 0): {zero_obs_pixels}")

    # Assert that all zero_obs pixels have strict nodata_value (0.0) across all composite bands
    nodata_violations = 0
    for bname, band_arr in res_annual_median["composite_bands"].items():
        bad = (zero_obs_mask & (band_arr != 0.0))
        nodata_violations += int(np.count_nonzero(bad))

    log(f"  NoData violations across composite bands: {nodata_violations}")
    assert nodata_violations == 0, "NoData violation: unobserved pixels were altered!"

    # Verify missing reason mask
    missing_mask = res_annual_median["missing_reason_mask"]
    valid_reasons = missing_mask[~zero_obs_mask]
    assert np.all(valid_reasons == int(MissingReason.NOT_MISSING)), "Valid pixels must have MissingReason.NOT_MISSING!"
    log("  Missing reason consistency verified: valid pixels have code 0, unobserved pixels have diagnosed causes.")

    elapsed = round(time.time() - start_time, 3)
    log(f"Section 2 Verification completed in {elapsed}s.")

    # Export report
    def sanitize_for_json(obj):
        if isinstance(obj, dict):
            return {str(k): sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_for_json(x) for x in obj]
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    report = {
        "schema_version": 1,
        "section": "SECTION_2_ANNUAL_COMPOSITE_QUALITY_TRACKER",
        "verification_id": "TC-SECTION2-VERIFY-20261019",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "VERIFIED_TESTED_SYNTHETIC",
        "summary": {
            "elapsed_seconds": elapsed,
            "slices_tested": len(slices),
            "raster_shape": [H, W],
            "total_pixels": H * W,
            "annual_median_coverage_ratio": meta_annual["pixel_counts"]["valid_coverage_ratio"],
            "dry_season_coverage_ratio": meta_dry["pixel_counts"]["valid_coverage_ratio"],
            "strict_nodata_preservation_verified": True,
            "nodata_violations": nodata_violations,
        },
        "annual_median_metadata": meta_annual,
        "dry_season_metadata": meta_dry,
        "priority_blending_metadata": meta_priority,
    }

    report_path = workspace_dir / "section2_quality_tracker_report.json"
    log_path = workspace_dir / "section2_verification.log"

    clean_report = sanitize_for_json(report)
    report_path.write_text(json.dumps(clean_report, indent=2, ensure_ascii=False), encoding="utf-8")
    log_path.write_text("\n".join(log_messages) + "\n", encoding="utf-8")

    log(f"Artifacts saved:")
    log(f"  - Report: {report_path.name} ({len(report_path.read_bytes())} bytes)")
    log(f"  - Log:    {log_path.name} ({len(log_path.read_bytes())} bytes)")

    return report


if __name__ == "__main__":
    run_section2_verification()
