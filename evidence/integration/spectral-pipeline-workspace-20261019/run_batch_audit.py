"""CLI runner for the spectral batch audit across all 1,407 eligible patches.

Saves structured audit results and prints a complete summary including:
- 10m precision verification across 6 provinces
- 6-band full BOA availability
- Radiometric scaling (0-10,000 DN to 0.0-1.0 BOA)
- Saturation & distortion prevention flagging for LCLUC classification
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = WORKSPACE_DIR.parents[2]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from spectral_validator import audit_annual_window_report


def main():
    report_path = PROJECT_ROOT / 'data/first-group-training-esri-v1/annual-window-report.json'
    output_json = WORKSPACE_DIR / 'spectral_audit_results_1407.json'
    
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting spectral batch audit on: {report_path}")
    start_time = time.monotonic()
    
    results = audit_annual_window_report(
        report_path=report_path,
        limit=None,  # All 1,407 eligible patches
        verify_only_eligible=True
    )
    
    elapsed = round(time.monotonic() - start_time, 2)
    summary = results['summary']
    summary['audit_duration_seconds'] = elapsed
    summary['audited_at_utc'] = datetime.now(timezone.utc).isoformat()
    
    with output_json.open('w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- SPECTRAL BATCH AUDIT COMPLETE ({elapsed}s) ---")
    print(f"Total eligible patches audited: {summary['total_audited']}")
    print(f"Spatial Resolution 10m Verified: {summary['spatial_resolution_10m_verified_count']} / {summary['total_audited']} ({summary['spatial_resolution_10m_verified_ratio']*100:.1f}%)")
    print(f"Spectral Readiness Breakdown:")
    for k, v in summary['spectral_readiness'].items():
        print(f"  - {k}: {v}")
    print(f"Radiometric Scaling Breakdown:")
    for k, v in summary['scale_status'].items():
        print(f"  - {k}: {v}")
    print(f"Offset Rule Breakdown:")
    for k, v in summary['offset_rules'].items():
        print(f"  - {k}: {v}")
    
    dist = summary['distortion_and_saturation']
    print(f"\nDistortion & Saturation Analysis (LCLUC Protection):")
    print(f"  - Total inspected pixels: {dist['total_inspected_pixels']}")
    print(f"  - Clean LCLUC pixels: {dist['total_clean_lcluc_pixels']} ({dist['overall_clean_lcluc_ratio']*100:.3f}%)")
    print(f"  - Patches with saturated pixels (> 1.0 BOA): {dist['patches_with_saturation']} / {summary['total_audited']}")
    print(f"  - Total saturated pixels: {dist['total_saturated_pixels']} ({dist['overall_saturated_pixel_ratio']*100:.4f}%)")
    print(f"  - Patches with negative anomaly (< 0.0 BOA): {dist['patches_with_negative']} / {summary['total_audited']}")
    print(f"  - Total negative anomaly pixels: {dist['total_negative_pixels']} ({dist['overall_negative_pixel_ratio']*100:.4f}%)")
    print(f"  - Distortion masking contract: {dist['distortion_masking_contract_defined']}")
    
    print(f"\nProvince Breakdown:")
    for prov, p_stat in summary['province_metrics'].items():
        print(f"  - {prov}: {p_stat['total_patches']} patches | 10m: {p_stat['resolution_10m_verified']} | Clean: {p_stat['clean_pixel_ratio']*100:.2f}% | Sat: {p_stat['saturated_pixels']} px")
        
    print(f"\nMutations Detected: {summary['mutations_detected']}")
    print(f"Reflectance Physically Plausible: {summary['reflectance_physically_plausible_count']} / {summary['total_audited']}")
    print(f"Conforming Valid Patches: {summary['valid_conforming_count']} / {summary['total_audited']}")
    print(f"Contract Status: {summary['contract_verification_status']}")
    print(f"Audit output saved to: {output_json}")


if __name__ == '__main__':
    main()
