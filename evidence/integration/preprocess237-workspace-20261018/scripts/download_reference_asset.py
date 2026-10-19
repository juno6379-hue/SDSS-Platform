"""이미 수집한 장면의 단일 원본 밴드 파일 전체를 엄격한 예산 안에서 검증한다."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.data import service
from collect_samples import budget_used
from diagnose_stac import classify_error


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "data/baseline2021/annual-window-report.json")
    parser.add_argument("--aoi", default="west_java_candidate")
    parser.add_argument("--band", default="B04")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw-reference")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    source = json.loads(args.report.read_text(encoding="utf-8"))
    row = next(r for r in source["scenes"] if r["aoi"] == args.aoi and r["status"] == "rgb_window_downloaded")
    args.output.mkdir(parents=True, exist_ok=True)
    known_body_bytes = source.get("http_body_bytes_upper_bound", source.get("http_body_bytes", 0)) or 0
    report = {"executed": args.execute, "source_scene_id": row["scene_id"], "asset": args.band,
              "full_asset_downloaded": False, "all_scene_bands_downloaded": False,
              "maximum_asset_bytes": 256 * 1024 ** 2, "maximum_total_bytes": 2 * 1024 ** 3,
              "prior_collection_http_body_bytes": known_body_bytes, "status": "planned"}
    if args.execute:
        try:
            year = int(row["year"])
            result = service.search_stac({"bbox": row["bbox"], "start_date": f"{year}-06-01", "end_date": f"{year}-09-30",
                 "cloud_cover": 20, "limit": 1, "collection": "sentinel-2-l2a", "endpoint": "planetary-computer"})
            item = next(i for i in result["items"] if i["id"] == row["scene_id"])
            report["source_properties"] = item.get("properties", {})
            report["source_asset_metadata"] = item["assets"][args.band]
            remaining = 2 * 1024 ** 3 - known_body_bytes - budget_used(args.output)
            if remaining <= 0:
                raise ValueError("전체 2GiB 예산 소진")
            record = service.download_asset({"url": item["assets"][args.band]["href"], "license": item["license"],
                "max_bytes": min(256 * 1024 ** 2, remaining), "retries": 1}, args.output)
            registered = service.register_local({"path": record["path"], "source": record["source"], "license": item["license"]}, args.output)
            report.update(status="downloaded_full_single_band", full_asset_downloaded=True, record=record,
                          raster_metadata=registered["metadata"],
                          combined_stored_and_prior_transfer_bytes=known_body_bytes + budget_used(args.output))
        except Exception as exc:
            report.update(status="failed", error=classify_error(exc))
    (args.output / "reference-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not args.execute or report["full_asset_downloaded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
