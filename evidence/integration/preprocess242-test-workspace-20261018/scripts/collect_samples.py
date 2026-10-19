"""연구 후보 AOI/T1/T2의 수집 계획과 예산 제한 실행. 기본은 계획 전용이다."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from app.data import service
from diagnose_stac import classify_error


def now():
    return datetime.now(timezone.utc).isoformat()


def load_config(path):
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    service.stac_endpoint(config.get("endpoint", "earth-search"))
    if config.get("collection") not in service.COLLECTIONS:
        raise ValueError("지원하지 않는 STAC collection")
    service._number(config.get("cloud_cover", 20), "cloud_cover", 0, 100)
    service._integer(config.get("max_total_bytes"), "max_total_bytes", 1, 20 * 1024 ** 3)
    service._integer(config.get("max_asset_bytes"), "max_asset_bytes", 1, service.HARD_MAX_BYTES)
    if not isinstance(config.get("bands"), list) or not config["bands"] or len(config["bands"]) > 12:
        raise ValueError("bands는 1~12개 자산 키 목록이어야 합니다")
    for band in config["bands"]:
        if not isinstance(band, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", band):
            raise ValueError("잘못된 band 키")
    if not isinstance(config.get("aois"), list) or not 1 <= len(config["aois"]) <= 10:
        raise ValueError("AOI는 1~10개 필요합니다")
    ids = set()
    for aoi in config["aois"]:
        service._bbox(aoi)
        name = aoi.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", name) or name in ids:
            raise ValueError("AOI id는 중복 없는 안전한 파일명이어야 합니다")
        ids.add(name)
    if config.get("years"):
        for year in config["years"]:
            service._integer(year, "year", 2015, 2026)
        config["periods"] = {str(year): {"start_date": f"{year}-{config.get('season_start', '06-01')}",
                                      "end_date": f"{year}-{config.get('season_end', '09-30')}"} for year in config["years"]}
    for dates in config["periods"].values():
        service._dates(dates)
    service._integer(config.get("minimum_complete_scenes", 6), "minimum_complete_scenes", 1, 20)
    return config


def budget_used(root):
    directory = root / "downloads"
    return sum(p.stat().st_size for p in directory.glob("*") if p.is_file()) if directory.exists() else 0


def record_event(root, event):
    with (root / "collection-history.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"time": now(), **event}, ensure_ascii=False) + "\n")


def valid_existing(record, root):
    if not isinstance(record, dict) or not record.get("path") or not record.get("sha256"):
        return False
    path = service._inside(root, Path(record["path"]))
    return path.is_file() and service._sha(path) == record["sha256"]


def download_with_budget(asset, key, state, config, root):
    existing = state["assets"].get(key)
    if valid_existing(existing, root):
        record_event(root, {"event": "skip_existing_sha256_verified", "key": key})
        return existing
    remaining = config["max_total_bytes"] - budget_used(root)
    if remaining <= 0:
        raise ValueError("전체 다운로드 디스크 예산 소진")
    # 부분파일도 누적 예산에 포함한다. 재개는 보수적으로 잔여 예산 이내로 제한한다.
    limit = min(config["max_asset_bytes"], remaining)
    record_event(root, {"event": "download_started", "key": key, "max_bytes": limit})
    record = service.download_asset({**asset, "max_bytes": limit, "retries": 1}, root)
    state["assets"][key] = record
    record_event(root, {"event": "download_completed", "key": key,
                        "bytes": record["bytes"], "sha256": record["sha256"]})
    return record


def bbox_coverage(aoi, scene_bbox):
    """사각형 메타데이터의 상한 지표이며 실제 유효 픽셀 비율이 아니다."""
    if not scene_bbox or len(scene_bbox) != 4:
        return None
    w, s, e, n = aoi
    x0, y0, x1, y1 = scene_bbox
    overlap = max(0, min(e, x1) - max(w, x0)) * max(0, min(n, y1) - max(s, y0))
    return round(overlap / ((e - w) * (n - s)), 6)


def select_quality_candidate(items, fetch, aoi, side, directory, root, minimum=.85):
    """20m SCL의 실제 중심창으로 후보를 사전 검사한다. 최종10m QA와 구분한다."""
    import numpy as np
    import rasterio
    candidates = sorted(items, key=lambda item: item.get("cloud_cover", 100))
    audit = []
    for index, item in enumerate(candidates):
        scl_key = "SCL" if "SCL" in item["assets"] else "scl"
        entry = {"scene_id": item["id"], "cloud_cover": item.get("cloud_cover"), "status": "unverified"}
        audit.append(entry)
        if scl_key not in item["assets"]:
            entry["reason"] = "SCL 자산 없음"
            continue
        try:
            values, profile = fetch(item["assets"][scl_key]["href"], aoi["bbox"], max(1, (side + 1) // 2))
            if abs(abs(profile["transform"].a) - 20) > 1e-6 or not profile["crs"].is_projected:
                raise ValueError("후보QA의 20m SCL/10m 목표격자 조건이 충족되지 않습니다")
            valid = ~np.isin(values[0], [0, 1, 3, 8, 9, 10, 11])
            fraction = float(valid.mean())
            path = directory / f"qa-candidate-{index:02d}-SCL.tif"
            with rasterio.open(path, "w", **profile) as dst:
                dst.write(values)
            metadata = service.register_local({"path": str(path), "source": item["assets"][scl_key]["href"].split("?", 1)[0], "license": item.get("license", "UNVERIFIED")}, root)
            entry.update(status="eligible" if fraction >= minimum else "quality_insufficient", estimated_valid_fraction=fraction,
                         raw_scl_path=str(path), raw_scl_sha256=metadata["sha256"], minimum_fraction=minimum,
                         note="20m 중심 SCL 예비값이며 최종10m 전체밴드/NoData QA와 다를 수 있음")
            if fraction >= minimum:
                return item, (values, profile), audit
        except Exception as exc:
            error = classify_error(exc)
            entry.update(status="failed", error=error)
            if error.get("http_status") == 429 or error.get("category") == "shared_collection_stop" or "예산" in error.get("sanitized_message", ""):
                raise
    return None, None, audit


def collect(config, root, execute=False):
    if config.get("collection_mode") == "bounded_windows":
        return collect_windows(config, root, execute)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    config_digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    state_path = root / "collection-state.json"
    state = {"config_sha256": config_digest, "assets": {}}
    if execute and state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("config_sha256") != config_digest:
            raise ValueError("기존 실행과 설정이 다릅니다. 별도 --output을 지정하세요")
    report = {"created_at": now(), "status": "executing" if execute else "planned",
              "executed": execute, "boundary_status": "research_candidates_unconfirmed",
              "maximum_download_bytes": config["max_total_bytes"], "scenes": [], "labels": [],
              "complete_scene_count": 0, "minimum_complete_scenes": config.get("minimum_complete_scenes", 6),
              "minimum_scene_goal_met": False, "learning_ready": False,
              "valid_pixel_ratio": None, "sample_class_coverage": None,
              "verified_patch_count": 0, "patch_target_range": config.get("target_verified_patches", [1000, 3000]),
              "patch_goal_met": False,
              "note": "원본 해상도/구름/유효 픽셀/라벨/공간분할 검사 전 패치 수를 예측하거나 학습준비로 판정하지 않습니다"}
    for aoi in config["aois"]:
        for period, dates in config["periods"].items():
            row = {"aoi": aoi["id"], "period": period, "bbox": aoi["bbox"],
                   "status": "planned", "required_bands": config["bands"], "assets": {},
                   "bbox_coverage_upper_bound": None, "valid_pixel_ratio": None,
                   "class_coverage": None, "verified_patches": 0}
            report["scenes"].append(row)
            if not execute:
                continue
            search_key = f"{aoi['id']}-{period}"
            record_event(root, {"event": "search_started", "key": search_key})
            try:
                result = service.search_stac({**dates, "bbox": aoi["bbox"], "collection": config["collection"],
                                              "endpoint": config.get("endpoint", "earth-search"),
                                              "cloud_cover": config.get("cloud_cover", 20), "limit": 1})
                if not result["items"]:
                    row["status"] = "no_scene_found"
                    record_event(root, {"event": "no_scene_found", "key": search_key})
                    continue
                item = result["items"][0]
                row["scene_id"] = item["id"]
                row["cloud_cover_metadata"] = item["cloud_cover"]
                row["bbox_coverage_upper_bound"] = bbox_coverage(aoi["bbox"], item["bbox"])
                for band in config["bands"]:
                    # 카탈로그별 이름 차이만 매핑하고 실제 자산 존재는 별도로 확인한다.
                    pc_keys = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir16": "B11", "swir22": "B12"}
                    asset_key = band
                    if service.stac_endpoint(config.get("endpoint", "earth-search")) == service.PC_STAC_URL and config["collection"] == "sentinel-2-l2a":
                        asset_key = pc_keys.get(band, band)
                    if asset_key not in item["assets"]:
                        row["assets"][band] = {"status": "missing_asset"}
                        continue
                    key = f"{search_key}/{item['id']}/{band}"
                    try:
                        asset = item["assets"][asset_key]
                        record = download_with_budget({"url": asset["href"], "license": item["license"]}, key, state, config, root)
                        row["assets"][band] = {"status": "verified_download", "path": record["path"], "sha256": record["sha256"]}
                    except Exception as exc:
                        row["assets"][band] = {"status": "failed", **classify_error(exc)}
                        record_event(root, {"event": "asset_failed", "key": key, **classify_error(exc)})
                    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
                complete = all(row["assets"].get(band, {}).get("status") == "verified_download" for band in config["bands"])
                row["status"] = "bands_downloaded_quality_unverified" if complete else "incomplete_bands"
                report["complete_scene_count"] += int(complete)
            except Exception as exc:
                row.update(status="search_failed", error=classify_error(exc))
                record_event(root, {"event": "search_failed", "key": search_key, **classify_error(exc)})
        label_plan = service.worldcover_plan({"bbox": aoi["bbox"], "year": config.get("worldcover_year", 2021)})
        label = {"aoi": aoi["id"], "source": "ESA WorldCover", "year": label_plan["year"],
                 "status": "candidate_only", "temporal_match_verified": False, "tiles": []}
        report["labels"].append(label)
        for tile in label_plan["tiles"]:
            tile_row = {"tile": tile["tile"], "status": "planned"}
            label["tiles"].append(tile_row)
            if execute and config.get("download_worldcover", False):
                key = f"worldcover/{label_plan['year']}/{tile['tile']}"
                try:
                    record = download_with_budget(tile, key, state, config, root)
                    tile_row.update(status="downloaded_alignment_unverified", path=record["path"], sha256=record["sha256"])
                except Exception as exc:
                    tile_row.update(status="failed", error=classify_error(exc))
                    record_event(root, {"event": "label_failed", "key": key, **classify_error(exc)})
                state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    report["download_disk_bytes"] = budget_used(root)
    report["minimum_scene_goal_met"] = report["complete_scene_count"] >= report["minimum_complete_scenes"]
    report["status"] = "executed_readiness_unverified" if execute else "planned"
    report["blockers"] = ["클래스 체계 매핑/시기 일치 미검증", "구름/그림자/유효 픽셀 비율 미검증",
                          "밴드 정합 및 원본 공간해상도 미검증", "독립 AOI 공간분할 및 1000~3000 패치 미확보"]
    if not report["minimum_scene_goal_met"]:
        report["blockers"].insert(0, "최소 6개 완전 밴드 장면 미확보")
    filename = "collection-report.json" if execute else "collection-plan.json"
    (root / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def collect_windows(config, root, execute=False, selection_context=None, collection_guard=None):
    """연차별 실제 RGB/SCL/라벨 창을 수집하되 연차 라벨 부재와 품질을 분리한다."""
    if execute:
        import numpy as np
        import rasterio
        from rasterio.warp import reproject, Resampling
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    side = service._integer(config.get("window_size", 256), "window_size", 1, 1024)
    minimum_valid = service._number(config.get("min_valid_fraction", .8), "min_valid_fraction", 0, 1)
    candidate_limit = service._integer(config.get("candidate_limit", 1), "candidate_limit", 1, 5)
    search_limit = service._integer(config.get("search_limit", candidate_limit), "search_limit", candidate_limit, 50)
    reference_kind = config.get("annual_reference", "worldcover")
    if reference_kind not in ("worldcover", "esri_io"):
        raise ValueError("지원하는 연차 참조는 worldcover/esri_io 입니다")
    report = {"status": "planned", "executed": execute, "boundary_status": "research_candidates_unconfirmed",
              "years": list(config["periods"]), "expected_aoi_year_cells": len(config["aois"]) * len(config["periods"]),
              "full_scene_count": 0, "complete_scene_count": 0, "minimum_scene_goal_met": False,
              "complete_window_count": 0, "label_window_count": 0, "verified_patch_count": 0,
              "patch_target_range": [1000, 3000], "learning_ready": False, "scenes": [],
              "missing_aoi_years": [], "http_body_bytes": 0, "maximum_http_body_bytes": config["max_total_bytes"],
              "year_pairs": [], "common_bands": list(config["bands"])}
    grid = config.get("window_grid_plan", {"rows": 8, "cols": 8, "spacing_m": 2560})
    grid_rows = service._integer(grid.get("rows", 8), "grid_rows", 1, 32)
    grid_cols = service._integer(grid.get("cols", 8), "grid_cols", 1, 32)
    report.update(valid_pixel_ratio=None, sample_class_coverage=None,
                  nominal_max_patches=len(config["aois"]) * len(config["periods"]),
                  nominal_patch_size=side,
                  common_bands_status="requested_unverified_across_years",
                  grid_plan={"rows": grid_rows, "cols": grid_cols, "spacing_m": grid.get("spacing_m", 2560),
                             "nominal_candidate_count": len(config["aois"]) * len(config["periods"]) * grid_rows * grid_cols,
                             "executed": False, "quality_verified_count": 0,
                             "note": "상한 후보 계획이며 1000개 유효 패치 확보를 보장하지 않음"},
                  collection_purpose="smoke_small_annual_windows")
    years = sorted(config["periods"])
    report["year_pairs"] = [{"from": a, "to": b, "type": "adjacent"} for a, b in zip(years, years[1:])]
    report["year_pairs"] += [{"from": years[0], "to": year, "type": "baseline"} for year in years[1:]]
    history_path = root / "window-state.json"
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    state = {"config_sha256": digest, "http_body_bytes": 0, "cells": {}}
    if execute and history_path.exists():
        state = json.loads(history_path.read_text(encoding="utf-8"))
        if state["config_sha256"] != digest:
            raise ValueError("수집 설정 변경 시 별도 --output 경로를 지정하세요")
    # 구버전의 예약/실측이 섞인 숫자를 근거 없이 환불하거나 실수신량으로 바꾸지 않는다.
    state.setdefault("legacy_charged_bytes_preserved", state["http_body_bytes"])
    state.setdefault("http_body_bytes_measured", 0)
    circuit_breaker = {}
    def trip_rate_limit(error):
        if error.get("http_status") == 429 and not circuit_breaker:
            circuit_breaker.update({"reason": "provider_http_429", "recorded_at": now(),
                "request_host": error.get("request_host"), "request_path": error.get("request_path"),
                "retry_after": error.get("retry_after")})
            state["last_rate_limit"] = circuit_breaker.copy()
            history_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            record_event(root, {"event": "batch_circuit_open_rate_limit", **circuit_breaker})
    def fetch(url, bbox, pixels):
        retries = service._integer(config.get("transient_asset_retries", 1), "transient_asset_retries", 0, 2)
        for attempt in range(retries + 1):
            remaining = config["max_total_bytes"] - config.get("prior_download_budget_bytes", 0) - state["http_body_bytes"]
            if remaining < 65536:
                raise ValueError("전체 HTTP 본문 예산 소진")
            reservation = min(32 * 1024 ** 2, remaining)
            # 장애/강제종료에도 전송 예산이 초기화되지 않도록 먼저 상한을 예약한다.
            state["http_body_bytes"] += reservation
            history_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                if collection_guard is None:
                    values, profile, stats = service.read_cog_window(url, bbox, pixels, reservation)
                else:
                    values, profile, stats = service.read_cog_window(
                        url, bbox, pixels, reservation,
                        window_guard=lambda geometry: collection_guard.on_window(url, geometry))
                state["http_body_bytes"] -= reservation - stats["http_body_bytes"]
                state["http_body_bytes_measured"] += stats["http_body_bytes"]
                history_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
                return values, profile
            except Exception as exc:
                error = classify_error(exc)
                measured = getattr(exc, "http_body_bytes", None) if getattr(exc, "transfer_measurement_known", False) else None
                if measured is not None and 0 <= measured <= reservation:
                    state["http_body_bytes"] -= reservation - measured
                    state["http_body_bytes_measured"] += measured
                else:
                    measured = None
                history_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
                trip_rate_limit(error)
                record_event(root, {"event": "cog_range_attempt_failed", "attempt": attempt + 1,
                                    "reserved_bytes_charged": measured if measured is not None else reservation,
                                    "http_body_bytes_measured": measured, "measurement_scope": service.RANGE_MEASUREMENT_SCOPE, **error})
                if error.get("http_status") == 429 or error.get("category") == "shared_collection_stop" or attempt >= retries or error["category"] == "payload_or_response_contract":
                    raise
    for aoi in config["aois"]:
        for year, dates in config["periods"].items():
            key = f"{aoi['id']}-{year}"
            row = {"aoi": aoi["id"], "province": aoi.get("province_id", aoi["id"]), "year": year, "bbox": aoi["bbox"], "status": "planned",
                   "valid_pixel_ratio": None, "sample_class_coverage": None,
                   "verified_patches": 0, "incomplete_year": year == "2026",
                   "label_status": "Esri 동년 참조 후보" if reference_kind == "esri_io" else "WorldCover 후보" if year in ("2020", "2021") else "Dynamic World 계획; 미실행"}
            report["scenes"].append(row)
            if not execute:
                continue
            previous = state["cells"].get(key)
            if previous and valid_existing(previous.get("image"), root) and (not previous.get("label") or valid_existing(previous["label"], root)):
                row.update(previous["row"])
                record_event(root, {"event": "window_skip_existing_sha256_verified", "key": key})
                continue
            if circuit_breaker:
                row.update(status="deferred_rate_limit", defer_reason=circuit_breaker.copy())
                continue
            record_event(root, {"event": "window_collection_started", "key": key})
            try:
                result = service.search_stac({**dates, "bbox": aoi["bbox"], "endpoint": config.get("endpoint", "planetary-computer"),
                    "collection": config["collection"], "cloud_cover": config.get("cloud_cover", 20), "limit": search_limit,
                    "sort_by_cloud": config.get("sort_by_cloud", False), "include_raw": True})
                row["stac_response_filter"] = {"filtered_count": result.get("filtered_count", 0),
                    "filtered_items": result.get("filtered_items", []), "cloud_cover_response_verified": result.get("cloud_cover_response_verified", False)}
                if not result["items"]:
                    raise ValueError("해당 AOI/연도/계절의 장면 없음")
                directory = root / key
                directory.mkdir(exist_ok=True)
                selected_scl = None
                if candidate_limit > 1:
                    pool = sorted(result["items"], key=lambda value: value.get("cloud_cover", 101))[:candidate_limit]
                    item, selected_scl, candidates = select_quality_candidate(pool, fetch, aoi, side, directory, root,
                        service._number(config.get("candidate_valid_fraction", .85), "candidate_valid_fraction", 0, 1))
                    row["candidate_selection"] = candidates
                    if item is None:
                        row.update(status="quality_insufficient", quality_status="quality_insufficient")
                        record_event(root, {"event": "all_candidates_quality_insufficient", "key": key})
                        continue
                else:
                    item = result["items"][0]
                # Candidate SCL reads may already have occurred during selection.
                # Reject before selected-scene metadata and remaining pixel reads.
                if collection_guard is not None:
                    collection_guard.on_scene(item, aoi, year)
                row.update(scene_id=item["id"], source_group=f"{aoi.get('province_id', aoi['id'])}/{item['id']}", datetime=item["datetime"], cloud_cover=item["cloud_cover"],
                           source_properties=item.get("properties", {}),
                           source_band_metadata={key: {"raster:bands": value.get("raster:bands"), "eo:bands": value.get("eo:bands")} for key, value in item["assets"].items()})
                def redact_signed_urls(value):
                    if isinstance(value, dict):
                        return {k: redact_signed_urls(v) for k, v in value.items()}
                    if isinstance(value, list):
                        return [redact_signed_urls(v) for v in value]
                    if isinstance(value, str) and value.startswith("https://") and re.search(r"[?&](sig|token|access_token|api_key)=", value, re.IGNORECASE):
                        return value.split("?", 1)[0]
                    return value
                original_stac = item.get("stac_feature", item)
                public_stac = redact_signed_urls(original_stac)
                stac_path = directory / "stac-item.json"
                stac_path.write_text(json.dumps(public_stac, ensure_ascii=False, indent=2), encoding="utf-8")
                row["stac_item"] = {"path": str(stac_path), "sha256": service._sha(stac_path),
                    "raw_feature_available": "stac_feature" in item, "signed_query_redacted": public_stac != original_stac}
                if config.get("verify_product_metadata", False):
                    metadata_assets = original_stac.get("assets", {})
                    product_assets = [(name, asset) for name, asset in metadata_assets.items() if "product" in name.lower() and "metadata" in name.lower()]
                    if product_assets:
                        from app.data.calibration import parse_product_calibration
                        metadata_url = product_assets[0][1]["href"]
                        raw_xml = service._metadata_response(Request(service.resolve_asset_url(metadata_url)))
                        xml_path = directory / "product-metadata.xml"
                        xml_path.write_bytes(raw_xml)
                        pc_map = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir16": "B11", "swir22": "B12"}
                        calibration = parse_product_calibration(raw_xml, [pc_map.get(b, b) for b in config["bands"]], item.get("properties", {}).get("s2:processing_baseline"))
                        expected_uri = item.get("properties", {}).get("s2:product_uri")
                        calibration["product_identity_verified"] = bool(expected_uri and calibration.get("xml_product_uri") == expected_uri)
                        if not calibration["product_identity_verified"]:
                            calibration.update(verified=False, reason="STAC product_uri와제품XML PRODUCT_URI의일치를확인하지못함")
                        calibration.update(source_xml_path=str(xml_path), source_xml_sha256=service._sha(xml_path), source_url=metadata_url.split("?", 1)[0])
                        source_band_names = [pc_map.get(b, b) for b in config["bands"]]
                        calibration.update(status="verified_product_metadata" if calibration["verified"] else "unverified_product_metadata",
                            product_id=item["id"], band_names=source_band_names,
                            source_metadata_path=xml_path.relative_to(PROJECT_ROOT / "data").as_posix(),
                            source_metadata_sha256=service._sha(xml_path))
                        if calibration["verified"]:
                            calibration["scale"] = [calibration["bands"][b]["scale"] for b in source_band_names]
                            calibration["offset"] = [calibration["bands"][b]["offset"] for b in source_band_names]
                        calibration_path = directory / "calibration.json"
                        calibration_path.write_text(json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
                        row["calibration"] = {"path": str(calibration_path), "sha256": service._sha(calibration_path), "metadata_verified": calibration["verified"], "applied_to_image": False}
                        if calibration["verified"]:
                            row["normalization"] = {"scale": calibration["scale"], "offset": calibration["offset"],
                                "evidence_path": calibration_path.relative_to(PROJECT_ROOT / "data").as_posix(),
                                "evidence_sha256": service._sha(calibration_path)}
                    else:
                        row["calibration"] = {"metadata_verified": False, "reason": "STAC product-metadata 자산 없음"}
                source_crops = {}
                row["source_crops"] = source_crops
                def preserve_source_crop(filename, values, source_profile, source_url, license_value):
                    if config.get("preserve_source_crops", True) is not True:
                        return
                    target = directory / filename
                    raw_profile = {**source_profile, "count": values.shape[0], "width": values.shape[2], "height": values.shape[1]}
                    with rasterio.open(target, "w", **raw_profile) as dst:
                        dst.write(values)
                    registered = service.register_local({"path": str(target), "source": redact_signed_urls(source_url), "license": license_value}, root)
                    source_crops[filename] = {"path": str(target), "sha256": registered["sha256"],
                        "source": registered["source"], "metadata": registered["metadata"],
                        "transform": list(source_profile["transform"]), "resampling_applied": False}
                pc = service.stac_endpoint(config.get("endpoint", "planetary-computer")) == service.PC_STAC_URL
                pc_band_keys = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir16": "B11", "swir22": "B12"}
                bands = [pc_band_keys.get(band, band) if pc else band for band in config["bands"]]
                early_reference = None
                if reference_kind == "esri_io" and config.get("label_first", False):
                    from app.data.references import esri_annual_plan
                    early_tile = esri_annual_plan(int(year), item["id"])
                    early_values, early_profile = fetch(early_tile["url"], aoi["bbox"], min(2048, side * 2))
                    preserve_source_crop("raw-esri_io.tif", early_values, early_profile, early_tile["url"], "CC-BY-4.0")
                    classes, counts = np.unique(early_values, return_counts=True)
                    histogram = {str(int(c)): int(n) for c,n in zip(classes,counts)}
                    if not {int(c) for c in histogram}.issubset({0, 1, 2, 4, 5, 7, 8, 9, 10, 11}):
                        raise ValueError("Esri예비원본공식분류코드불일치")
                    context = selection_context or {}
                    row["label_first_preview"] = {"source_url": early_tile["url"], "year": int(year),
                        "class_counts": histogram, "selection_context": context,
                        "note": "확대원본범위예비분포이며최종256/SCL/polygon필터후분포와다름"}
                    priorities = context.get("priority_source_classes", [])
                    total = max(int(early_values.size),1)
                    if context.get("allow_dominant_class_deferral") and priorities and max(histogram.values(),default=0)/total >= .98 and sum(histogram.get(str(code),0) for code in priorities)/total < .002:
                        row.update(status="reference_diversity_deferred", label_status="reference_preview_only")
                        record_event(root,{"event":"reference_dominance_deferred_before_six_bands","key":key})
                        continue
                    early_reference = (early_values, early_profile, early_tile)
                arrays, profile, band_processing = [], None, []
                for band in bands:
                    # SWIR 원본은 20m이므로 필요한 물리 범위만 읽는다. 여유 2픽셀은
                    # 서로 다른 원점/픽셀 경계에서 bilinear 보간의 가장자리를 보존한다.
                    native_side = (side + 1) // 2 + 2 if band in ("B11", "B12", "swir16", "swir22") else side
                    values, current = fetch(item["assets"][band]["href"], aoi["bbox"], native_side)
                    preserve_source_crop(f"raw-{band}.tif", values, current, item["assets"][band]["href"], item["license"])
                    if profile is None:
                        profile = current
                    different_grid = current["transform"] != profile["transform"] or current["crs"] != profile["crs"] or values.shape[1:] != (profile["height"], profile["width"])
                    if different_grid:
                        # 연속형 반사도/DN 밴드는 기준 밴드의 10m 격자에 bilinear 정합한다.
                        aligned_band = np.zeros((profile["height"], profile["width"]), dtype="float32")
                        reproject(values[0], aligned_band, src_transform=current["transform"], src_crs=current["crs"],
                            src_nodata=current.get("nodata", 0), dst_transform=profile["transform"], dst_crs=profile["crs"],
                            dst_nodata=0, resampling=Resampling.bilinear)
                        arrays.append(aligned_band)
                    else:
                        arrays.append(values[0])
                    band_processing.append({"asset": band, "source_resolution": [abs(current["transform"].a), abs(current["transform"].e)],
                        "resampling": "bilinear" if different_grid else "native", "scale_offset_applied": False,
                        "units": "source_DN_unverified_reflectance", "raster:bands": item["assets"][band].get("raster:bands")})
                image_path = directory / "image.tif"
                if any(array.dtype.kind == "f" for array in arrays):
                    arrays = [array.astype("float32") for array in arrays]
                    profile.update(dtype="float32")
                profile.update(count=len(bands), nodata=0)
                stack = np.stack(arrays)
                with rasterio.open(image_path, "w", **profile) as dst:
                    dst.write(stack)
                    for index, asset in enumerate(bands, 1):
                        dst.set_band_description(index, pc_band_keys.get(asset, asset))
                valid = np.all(np.isfinite(stack) & (stack != 0), axis=0)
                scl_key = "SCL" if pc else "scl"
                if scl_key in item["assets"]:
                    scl, scl_profile = selected_scl if selected_scl is not None else fetch(item["assets"][scl_key]["href"], aoi["bbox"], side)
                    preserve_source_crop("raw-SCL.tif", scl, scl_profile, item["assets"][scl_key]["href"], item["license"])
                    aligned = np.zeros(arrays[0].shape, dtype="uint8")
                    reproject(scl[0], aligned, src_transform=scl_profile["transform"], src_crs=scl_profile["crs"],
                              dst_transform=profile["transform"], dst_crs=profile["crs"], resampling=Resampling.nearest)
                    valid &= ~np.isin(aligned, [0, 1, 3, 8, 9, 10, 11])
                    row["quality_mask"] = "SCL: nodata/saturated/shadow/cloud/cirrus/snow excluded"
                else:
                    row["quality_mask"] = "nodata_only_cloud_unverified"
                quality_path = directory / "quality-mask.tif"
                with rasterio.open(quality_path, "w", **{**profile, "count": 1, "dtype": "uint8", "nodata": None}) as dst:
                    dst.write(valid.astype("uint8"), 1)
                    dst.set_band_description(1, "binary_validity")
                row.update(status="rgb_window_downloaded", image_path=str(image_path), bands=bands,
                           logical_bands=list(config["bands"]), band_processing=band_processing,
                           reflectance_conversion_verified=False, quality_mask_path=str(quality_path),
                           quality_mask_semantics={"schema_version": 1, "kind": "binary_validity", "valid_value": 1, "invalid_value": 0},
                           valid_pixel_ratio=float(valid.mean()), pixel_count=int(valid.size),
                           minimum_valid_fraction=minimum_valid,
                           quality_status=("quality_unverified" if scl_key not in item["assets"] else
                                           "quality_eligible" if float(valid.mean()) >= minimum_valid else "quality_insufficient"),
                           invalid_pixel_count=int((~valid).sum()), spatial_resolution=list(profile["transform"])[0])
                image_record = service.register_local({"path": str(image_path), "source": item["id"], "license": item["license"]}, root)
                saved = {"image": image_record, "row": row.copy()}
                if (reference_kind == "esri_io" or year in ("2020", "2021")) and config.get("download_worldcover", True):
                    try:
                        if reference_kind == "esri_io":
                            from app.data.references import esri_annual_plan
                            tile = esri_annual_plan(int(year), item["id"])
                            row["reference_metadata"] = tile
                        else:
                            tile = service.worldcover_plan({"bbox": aoi["bbox"], "year": int(year)})["tiles"][0]
                        if early_reference is not None:
                            labels, label_profile, tile = early_reference
                            row["reference_metadata"] = tile
                        else:
                            labels, label_profile = fetch(tile["url"], aoi["bbox"], min(2048, side * 2))
                        if reference_kind == "esri_io":
                            observed = [int(value) for value in np.unique(labels)]
                            if not set(observed).issubset({0, 1, 2, 4, 5, 7, 8, 9, 10, 11}):
                                raise ValueError("Esri원본에서공식분류코드이외값관찰;임의crosswalk금지")
                            tile.update(availability_verified=True, observed_source_classes=observed,
                                class_code_set_verified=True, class_semantics_source="official Esri Explorer/IO classification definitions")
                        preserve_source_crop(f"raw-{reference_kind}.tif", labels, label_profile, tile["url"], "CC-BY-4.0")
                        aligned = np.zeros(arrays[0].shape, dtype="uint8")
                        reproject(labels[0], aligned, src_transform=label_profile["transform"], src_crs=label_profile["crs"],
                                  src_nodata=0, dst_transform=profile["transform"], dst_crs=profile["crs"],
                                  dst_nodata=0, resampling=Resampling.nearest)
                        aligned[~valid] = 0
                        if reference_kind == "esri_io":
                            aligned[np.isin(aligned, [0, 10])] = 0
                            row["taxonomy_signature"] = tile["taxonomy_signature"]
                        label_path = directory / f"label-{reference_kind}.tif"
                        label_out = {**profile, "count": 1, "dtype": "uint8", "nodata": 0}
                        with rasterio.open(label_path, "w", **label_out) as dst:
                            dst.write(aligned, 1)
                        classes, counts = np.unique(aligned[aligned != 0], return_counts=True)
                        row.update(label_status=f"{reference_kind}_aligned_weak_labels", label_path=str(label_path), label_source=reference_kind,
                            label_year=int(year), label_dataset_version=tile["version"] if reference_kind == "esri_io" else f"WorldCover{year}{'v100' if year == '2020' else 'v200'}",
                            label_source_url=tile["url"], label_temporal_match="same_year_weak_label_not_acquisition_date_ground_truth",
                            sample_class_coverage={str(int(c)): int(n) for c, n in zip(classes, counts)},
                            label_valid_pixel_ratio=float((aligned != 0).mean()))
                        saved["label"] = service.register_local({"path": str(label_path), "source": tile["url"], "license": "CC-BY-4.0"}, root)
                    except Exception as exc:
                        error = classify_error(exc)
                        trip_rate_limit(error)
                        row.update(label_status="deferred_rate_limit" if error.get("http_status") == 429 else "label_collection_failed", label_error=error)
                saved["row"] = row.copy()
                state["cells"][key] = saved
                record_event(root, {"event": "window_completed", "key": key, "label_status": row["label_status"]})
            except Exception as exc:
                error = classify_error(exc)
                trip_rate_limit(error)
                row.update(status="rate_limited" if error.get("http_status") == 429 else "deferred_shared_circuit" if error.get("category") == "shared_collection_stop" else "search_failed" if "scene_id" not in row else "failed", error=error)
                record_event(root, {"event": "window_failed", "key": key, **error})
            history_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            (root / "annual-window-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["complete_window_count"] = sum(row["status"] == "rgb_window_downloaded" for row in report["scenes"])
    report["label_window_count"] = sum(row["label_status"] in ("worldcover_aligned_weak_labels", "esri_io_aligned_weak_labels") for row in report["scenes"])
    report["quality_eligible_window_count"] = sum(row.get("quality_status") == "quality_eligible" for row in report["scenes"])
    report["missing_aoi_years"] = [f"{r['aoi']}/{r['year']}" for r in report["scenes"] if r["status"] != "rgb_window_downloaded"]
    report["missing_years"] = sorted({r["year"] for r in report["scenes"] if r["status"] != "rgb_window_downloaded"})
    report["http_body_bytes_upper_bound"] = state["http_body_bytes"]
    report["http_body_bytes_measured"] = state["http_body_bytes_measured"]
    report["legacy_charged_bytes_preserved"] = state["legacy_charged_bytes_preserved"]
    report["measurement_scope"] = service.RANGE_MEASUREMENT_SCOPE
    report["batch_circuit_breaker"] = circuit_breaker.copy() if circuit_breaker else None
    report["deferred_rate_limit_count"] = sum(row["status"] == "deferred_rate_limit" for row in report["scenes"])
    report["prior_download_budget_bytes"] = config.get("prior_download_budget_bytes", 0)
    report["combined_budget_charged_bytes"] = config.get("prior_download_budget_bytes", 0) + state["http_body_bytes"]
    report["http_body_bytes"] = state["http_body_bytes_measured"] if state["legacy_charged_bytes_preserved"] == 0 and state["http_body_bytes"] == state["http_body_bytes_measured"] else None
    report["status"] = "executed_windows_readiness_unverified" if execute else "planned"
    report["blockers"] = ["1000~3000 패치 미확보", "지상정답/연차별 독립 검증 미확보", "연도간 방사보정 및 클래스 매핑 검증 필요"]
    (root / ("annual-window-report.json" if execute else "collection-plan.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "collection.example.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "collection")
    parser.add_argument("--execute", action="store_true", help="명시한 경우에만 네트워크 검색/다운로드 실행")
    parser.add_argument("--years", nargs="+", type=int, help="연차 계획 중 선택한 연도만 별도 출력에 수집")
    parser.add_argument("--search-only", action="store_true", help="영상 바이트 없이 연차별 실제 STAC 메타데이터만 확보")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.years:
        config["periods"] = {str(y): config["periods"][str(y)] for y in args.years}
    result = search_annual(config, args.output, args.execute) if args.search_only else collect(config, args.output, args.execute)
    print(json.dumps({"status": result["status"], "complete_scene_count": result["complete_scene_count"],
                      "learning_ready": result["learning_ready"], "output": str(args.output)}, ensure_ascii=False))
    if not args.execute:
        return 0
    if args.search_only:
        return 0 if result["successful_search_cells"] == len(config["aois"]) * len(config["periods"]) else 2
    if config.get("collection_mode") == "bounded_windows":
        return 0 if result["complete_window_count"] == result["expected_aoi_year_cells"] else 2
    return 0 if result["minimum_scene_goal_met"] else 2


def search_annual(config, root, execute=False):
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    report = {"status": "searched" if execute else "planned", "executed": execute,
              "complete_scene_count": 0, "minimum_scene_goal_met": False, "learning_ready": False,
              "years": list(config["periods"]), "items": [], "missing_aoi_years": [],
              "raw_scale_offset_preserved": True, "actual_image_bytes_downloaded": 0}
    for aoi in config["aois"]:
        for year, dates in config["periods"].items():
            key = f"{aoi['id']}-{year}"
            row = {"aoi": aoi["id"], "year": year, "bbox": aoi["bbox"], "status": "planned"}
            if execute:
                try:
                    result = service.search_stac({**dates, "bbox": aoi["bbox"], "endpoint": config.get("endpoint", "planetary-computer"),
                        "collection": config["collection"], "cloud_cover": config.get("cloud_cover", 20), "limit": 1})
                    row.update(status="searched", items=result["items"], count=result["count"])
                    if not result["items"]:
                        report["missing_aoi_years"].append(key)
                except Exception as exc:
                    row.update(status="failed", error=classify_error(exc))
                    report["missing_aoi_years"].append(key)
            report["items"].append(row)
            (root / "annual-search-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["successful_search_cells"] = sum(r.get("count", 0) > 0 for r in report["items"])
    (root / "annual-search-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    raise SystemExit(main())
