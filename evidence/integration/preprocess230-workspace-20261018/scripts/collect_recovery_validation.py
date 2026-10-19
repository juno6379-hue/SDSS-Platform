"""기존 실패 원장을 보존하며 별도32MiB 예산으로 검증/시험 지역을 순차 수집한다."""
import argparse
import copy
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collect_samples import load_config, collect_windows
from diagnose_stac import classify_error
from app.data import service


def dns_handoff_allowed(previous):
    error = previous.get("error", {})
    metadata = previous.get("metadata_budget", {})
    return (previous.get("status") == "failed" and error.get("category") == "dns_resolution"
        and error.get("http_status") is None and previous.get("new_cog_charged_bytes") == 0
        and previous.get("new_charged_upper_bound_bytes") == 0
        and metadata.get("charged_bytes") == 0 and metadata.get("read_body_bytes") == 0
        and previous.get("old_ledger_unchanged") is True and not previous.get("manifests"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/first-group-recovery32")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--handoff-after-dns", action="store_true", help="서버접촉전 DNS실패/COG·메타0증거일때만 기존예산을 root환경에 1회 인계")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / "data/first-group-annual/run-result.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    historical_charge = old["reserved_or_transferred_bytes_including_prior"]
    supplementary = 32 * 1024 ** 2
    plan = {"created_at": datetime.now(timezone.utc).isoformat(), "executed": False,
        "historical_ledger": str(old_path), "historical_charged_upper_bound_bytes": historical_charge,
        "historical_ledger_modified": False, "new_supplementary_budget_bytes": supplementary,
        "cog_body_budget_bytes": 31 * 1024 ** 2, "metadata_body_budget_bytes": 1024 ** 2,
        "combined_maximum_charged_upper_bound_bytes": historical_charge + supplementary,
        "stored_data_bytes_before": sum(p.stat().st_size for p in (ROOT / "data").rglob("*") if p.is_file()),
        "disk_free_bytes_before": shutil.disk_usage(ROOT).free,
        "priority": ["banten/2021(validation)", "west_java/2021(test)"],
        "interval_seconds": 2, "concurrency": 1, "first_429_stops_all": True,
        "old_retry_after": "unknown_not_preserved_in_historical_run",
        "scope": "new explicitly bounded experiment under user's continue/data acquisition instruction; old2GiB ledger unchanged",
        "learning_ready": False, "model_training_requested": False}
    config = json.loads((ROOT / "configs/first-group.collection.json").read_text(encoding="utf-8"))
    config = copy.deepcopy(config)
    config.update(aois=[a for a in config["aois"] if a["id"] in ("banten", "west_java")], years=[2021],
        bands=["blue", "green", "red", "nir", "swir16", "swir22"],
        max_total_bytes=plan["cog_body_budget_bytes"], prior_download_budget_bytes=0,
        prior_budget_note="separate supplemental experiment; historical charge reported in recovery-plan.json, never refunded",
        candidate_limit=5, min_valid_fraction=.8, candidate_valid_fraction=.85,
        verify_product_metadata=True, preserve_source_crops=True, transient_asset_retries=0)
    config_path = output / "recovery-config.json"
    plan_path = output / "recovery-plan.json"
    if not (output / "network-attempt.json").exists():
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.execute:
        print(json.dumps({"status": "planned", "output": str(output), "supplementary_bytes": supplementary,
                          "combined_upper_bound_bytes": historical_charge + supplementary}))
        return 0
    if (output / "network-attempt.json").exists():
        previous_path = output / "run-result.json"
        previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
        marker = output / "dns-handoff-started.json"
        if not args.handoff_after_dns or marker.exists() or not dns_handoff_allowed(previous):
            raise RuntimeError("기존실행을반복하지않습니다. DNS이전0바이트실패증거에한해1회인계가능하며HTTP429는인계불가입니다")
        if previous.get("historical_charged_upper_bound_bytes") != historical_charge:
            raise RuntimeError("원래예산원장과인계전증거가다릅니다")
        archived = output / "dns-attempt-result.json"
        archived.write_bytes(previous_path.read_bytes())
        marker.write_text(json.dumps({"started_at": datetime.now(timezone.utc).isoformat(),
            "source_result_sha256": hashlib.sha256(archived.read_bytes()).hexdigest(),
            "existing_supplementary_budget_continued": True, "extra_budget_added": False}, indent=2), encoding="utf-8")
    else:
        if args.handoff_after_dns:
            raise RuntimeError("인계할DNS실패기록이없습니다")
        (output / "network-attempt.json").write_text(json.dumps({"started_at": datetime.now(timezone.utc).isoformat(), "maximum_new_bytes": supplementary}), encoding="utf-8")
    service.configure_request_spacing(2)
    service.configure_metadata_budget(plan["metadata_body_budget_bytes"])
    result = {"executed": True, "status": "checking_server", "learning_ready": False,
              "maximum_total_bytes": historical_charge + supplementary, "new_supplementary_budget_bytes": supplementary,
              "historical_charged_upper_bound_bytes": historical_charge,
              "combined_maximum_charged_upper_bound_bytes": historical_charge + supplementary, "manifests": []}
    try:
        catalogue = service._json_response(Request(service.PC_STAC_URL.removesuffix("/search"), headers={"Accept": "application/json"}))
        result["server_check"] = {"status": "passed", "stac_version": catalogue.get("stac_version")}
        print(json.dumps({"status": "server_check_passed", "metadata": service.metadata_budget_status()}), flush=True)
        report = collect_windows(load_config(config_path), output, execute=True)
        result.update(status="stopped_rate_limit" if report.get("batch_circuit_breaker") else "finished_bounded_experiment",
            manifests=[str(output / "annual-window-report.json")], complete_window_count=report["complete_window_count"],
            label_window_count=report["label_window_count"], quality_eligible_window_count=report.get("quality_eligible_window_count", 0),
            new_cog_charged_bytes=report["http_body_bytes_upper_bound"], circuit_breaker=report.get("batch_circuit_breaker"))
    except Exception as exc:
        error = classify_error(exc)
        result.update(status="stopped_rate_limit" if error.get("http_status") == 429 else "failed", error=error)
    finally:
        metadata = service.metadata_budget_status()
        state_path = output / "window-state.json"
        cog_charge = json.loads(state_path.read_text(encoding="utf-8")).get("http_body_bytes", 0) if state_path.exists() else 0
        result.update(metadata_budget=metadata, new_cog_charged_bytes=cog_charge,
            new_charged_upper_bound_bytes=metadata["charged_bytes"] + cog_charge,
            reserved_or_transferred_bytes_including_prior=historical_charge + metadata["charged_bytes"] + cog_charge,
            combined_historical_and_new_charged_upper_bound_bytes=historical_charge + metadata["charged_bytes"] + cog_charge,
            budget_within_limit=metadata["charged_bytes"] + cog_charge <= supplementary,
            old_ledger_unchanged=json.loads(old_path.read_text(encoding="utf-8")) == old)
        (output / "run-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result["status"] == "finished_bounded_experiment" and result.get("complete_window_count") == 2 else 2


if __name__ == "__main__":
    raise SystemExit(main())
