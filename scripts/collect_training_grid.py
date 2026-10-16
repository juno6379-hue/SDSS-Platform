"""4주 2021 보충 수집과 2020/2021 다공간 실제 패치 수집. 기본은 계획 전용."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.data import service
from app.data.budget import CollectionLedger
from collect_samples import collect_windows, load_config, now
from diagnose_stac import classify_error

BANDS = ["blue", "green", "red", "nir", "swir16", "swir22"]
TRAIN = ["south_sulawesi", "gorontalo", "southeast_sulawesi", "east_java"]
ORDER = TRAIN + ["banten", "west_java"]
SPLITS = {p: "train" for p in TRAIN} | {"banten": "val", "west_java": "test"}
ADDITIONAL = 4 * 1024 ** 3
COG_BATCH = 64 * 1024 ** 2
METADATA_BATCH = 1024 ** 2


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def candidate_coverage(scenes, reference="worldcover", years=(2020, 2021)):
    """개수만 채우지 않고 분할별 필수 클래스와 실제 공간 위치를 확인한다."""
    eligible = [s for s in scenes if s.get("quality_status") == "quality_eligible"]
    required = (80, 10, 30, 40, 50, 60) if reference == "worldcover" else (1, 2, 11, 5, 7, 8)
    split_counts = {name: sum(s.get("split") == name for s in eligible) for name in ("train", "val", "test")}
    histogram = {split: {str(code): sum(s.get("sample_class_coverage", {}).get(str(code), 0)
        for s in eligible if s.get("split") == split) for code in required} for split in split_counts}
    coverage = {(s["province"], str(s["year"])) for s in eligible}
    province_counts = {p: sum(s.get("province") == p for s in eligible) for p in TRAIN}
    unique_locations = {p: len({s.get("spatial_location_id") for s in eligible if s.get("province") == p}) for p in TRAIN}
    scene_splits = {}
    for row in eligible:
        scene_splits.setdefault(row["scene_id"], set()).add(row.get("split"))
    conflicts = sorted(scene for scene, splits in scene_splits.items() if len(splits) > 1)
    enough = (len(eligible) >= 1200 and split_counts["train"] >= 600 and min(split_counts["val"], split_counts["test"]) >= 100
        and all((p, str(y)) in coverage for p in ORDER for y in years)
        and all(n >= 256 for counts in histogram.values() for n in counts.values())
        and min(province_counts.values()) >= 50 and min(unique_locations.values()) >= 32 and not conflicts)
    return {"candidate_target_met": enough, "eligible_patch_count": len(eligible), "split_counts": split_counts,
        "required_class_pixel_counts": histogram, "train_province_counts": province_counts,
        "train_unique_locations": unique_locations, "scene_split_conflicts": conflicts,
        "learning_ready": False, "full_2020_2025_goal_met": False}


def reference_preview(batch, directory):
    """S2 6밴드보다 먼저 WC를 소량 읽어 실제 클래스 편중을 기록한다.

    ESRI는 실제 선택된 scene tile을 기준으로 주소를 결정하므로 이 사전검사는
    2020/2021 WorldCover에만 적용한다. 예산 8MiB를 미리 파일에 예약한다.
    """
    import numpy as np
    import rasterio
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / "reference-preview.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") == "completed" and service._sha(Path(state["path"])) == state.get("sha256"):
            return state
        raise RuntimeError("미측정/불완전 preview가 남아 있어 원장 초기화 없이 중단합니다")
    tile = service.worldcover_plan({"bbox": batch["config"]["aois"][0]["bbox"], "year": batch["year"]})["tiles"][0]
    limit = 8 * 1024 ** 2
    state = {"status": "pending", "charged_bytes": limit, "year": batch["year"], "source_url": tile["url"]}
    write_json(state_path, state)
    try:
        values, profile, stats = service.read_cog_window(tile["url"], batch["config"]["aois"][0]["bbox"], 1024, limit)
        raw_path = directory / "reference-preview-raw.tif"
        with rasterio.open(raw_path, "w", **profile) as dst:
            dst.write(values)
        classes, counts = np.unique(values, return_counts=True)
        state.update(status="completed", charged_bytes=stats["http_body_bytes"], path=str(raw_path),
            sha256=service._sha(raw_path), class_counts={str(int(c)): int(n) for c, n in zip(classes, counts)},
            pixel_count=int(values.size), preview_only=True, training_patch_count=0)
        return state
    except Exception as exc:
        if getattr(exc, "transfer_measurement_known", False):
            state["charged_bytes"] = exc.http_body_bytes
        state.update(status="failed", error=classify_error(exc))
        raise
    finally:
        write_json(state_path, state)


def preview_is_redundant(preview, batch, scenes):
    """공간/분할 최소량이 확보된 후 부족클래스에 기여하지 않는 순림창을 보류한다."""
    metrics = candidate_coverage(scenes)
    split = batch["split"]
    required_count = 600 if split == "train" else 100
    if metrics["split_counts"][split] < required_count:
        return False
    if split == "train" and (metrics["train_province_counts"][batch["province"]] < 50 or metrics["train_unique_locations"][batch["province"]] < 32):
        return False
    if not any(s.get("province") == batch["province"] and str(s.get("year")) == str(batch["year"]) and s.get("quality_status") == "quality_eligible" for s in scenes):
        return False
    deficient = {code for code, count in metrics["required_class_pixel_counts"][split].items() if count < 256}
    counts = preview.get("class_counts", {})
    total = max(preview.get("pixel_count", 1), 1)
    contribution = sum(counts.get(code, 0) for code in deficient) / total
    dominance = max(counts.values(), default=0) / total
    return bool(deficient and contribution < .002 and dominance >= .98)


def spatial_centers(geometry, count=16, side=1024):
    """행정경계 내부의 10.4km 격자에서 멀리 떨어진 후보를 결정적으로 고른다.

    주 전체 면적을 영상 한 장으로 간주하지 않는다. 후보 원본창의 외접원을
    경계 내부에 제한하되 최종 패치도 별도 polygon 마스크로 다시 검사한다.
    """
    from pyproj import Transformer
    from shapely.geometry import Point, shape
    from shapely.ops import transform
    polygon = shape(geometry)
    representative = polygon.representative_point()
    zone = int((representative.x + 180) // 6) + 1
    epsg = (32600 if representative.y >= 0 else 32700) + zone
    forward = Transformer.from_crs(4326, epsg, always_xy=True)
    inverse = Transformer.from_crs(epsg, 4326, always_xy=True)
    projected = transform(forward.transform, polygon)
    spacing = side * 10 + 160
    interior = projected.buffer(-(side * 10 / math.sqrt(2) + 100))
    if interior.is_empty:
        return []
    xmin, ymin, xmax, ymax = interior.bounds
    candidates = []
    for ix in range(math.floor(xmin / spacing), math.ceil(xmax / spacing) + 1):
        for iy in range(math.floor(ymin / spacing), math.ceil(ymax / spacing) + 1):
            point = Point(ix * spacing, iy * spacing)
            if interior.covers(point):
                candidates.append((point.x, point.y))
    # 첫 지점은 대표 내부점에 가깝게, 이후 farthest-point로 주 안에 분산한다.
    rx, ry = forward.transform(representative.x, representative.y)
    candidates.sort(key=lambda p: ((p[0] - rx) ** 2 + (p[1] - ry) ** 2, p))
    selected = []
    while candidates and len(selected) < count:
        index = 0 if not selected else max(range(len(candidates)), key=lambda i: min(
            (candidates[i][0] - x) ** 2 + (candidates[i][1] - y) ** 2 for x, y in selected))
        selected.append(candidates.pop(index))
    return [{"lon": inverse.transform(x, y)[0], "lat": inverse.transform(x, y)[1],
             "grid_easting": x, "grid_northing": y, "grid_crs": f"EPSG:{epsg}",
             "minimum_center_spacing_m": spacing} for x, y in selected]


def build_batches(base, stage, per_province=16, reference="worldcover", years=(2020, 2021)):
    features = json.loads((ROOT / "data/first-group-boundaries/selected-six.geojson").read_text(encoding="utf-8"))["features"]
    geometries = {f["properties"]["province_id"]: f["geometry"] for f in features}
    by_id = {a["id"]: a for a in base["aois"]}
    batches = []
    for province in TRAIN if stage == "smoke" else ORDER:
        centers = [{"lon": sum(by_id[province]["bbox"][::2]) / 2,
                    "lat": sum(by_id[province]["bbox"][1::2]) / 2}] if stage == "smoke" else spatial_centers(geometries[province], per_province)
        for year in [2021] if stage == "smoke" else years:
            for index, center in enumerate(centers):
                key = f"{stage}-{'esri_io-' if reference == 'esri_io' else ''}{province}-{year}-g{index:02d}"
                aoi = copy.deepcopy(by_id[province])
                aoi.update(province_id=province, id=f"{province}-g{index:02d}",
                           bbox=[center["lon"] - .004, center["lat"] - .004, center["lon"] + .004, center["lat"] + .004])
                config = copy.deepcopy(base)
                config.update(aois=[aoi], years=[year], bands=BANDS, window_size=256 if stage == "smoke" else 1024,
                    max_total_bytes=COG_BATCH, prior_download_budget_bytes=0,
                    candidate_limit=5, min_valid_fraction=.8, candidate_valid_fraction=.85,
                    verify_product_metadata=True, preserve_source_crops=True, transient_asset_retries=0,
                    minimum_complete_scenes=1)
                if stage == "grid":
                    config.update(search_limit=20, sort_by_cloud=True, annual_reference=reference)
                batches.append({"key": key, "province": province, "year": year, "split": SPLITS[province],
                    "center": center, "geometry": geometries[province], "config": config,
                    "nominal_patches": 1 if stage == "smoke" else 16})
    # 먼저 모든 주·연도를 한 번씩 방문하고 다음 공간창으로 넘어간다.
    # 한 훈련주만으로 패치 목표를 소진해 검증/시험주가 비는 것을 피한다.
    return sorted(batches, key=lambda b: (b["key"].rsplit("-g", 1)[-1], b["year"], ORDER.index(b["province"])))


def materialize_patches(report, batch, output):
    """이미 수신한 원본창을 비중복 256 패치로 나누고 출처·정규화 근거를 잇는다."""
    import numpy as np
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    from rasterio.windows import Window
    patches = []
    for source in report.get("scenes", []):
        if source.get("status") != "rgb_window_downloaded" or not source.get("label_path") or not source.get("quality_mask_path"):
            continue
        with rasterio.open(source["image_path"]) as image, rasterio.open(source["label_path"]) as label, rasterio.open(source["quality_mask_path"]) as quality:
            if (image.width, image.height, image.transform, image.crs) != (label.width, label.height, label.transform, label.crs) or (image.width, image.height, image.transform, image.crs) != (quality.width, quality.height, quality.transform, quality.crs):
                raise ValueError("원본 image/label/quality 격자가 일치하지 않습니다")
            polygon = transform_geom("EPSG:4326", image.crs, batch["geometry"])
            source_record = {"path": source["image_path"], "sha256": service._sha(Path(source["image_path"])),
                "quality_mask_path": source["quality_mask_path"], "quality_mask_sha256": service._sha(Path(source["quality_mask_path"])),
                "boundary_path": str(ROOT / "data/first-group-boundaries/selected-six.geojson"),
                "boundary_sha256": service._sha(ROOT / "data/first-group-boundaries/selected-six.geojson"),
                "raw_source_crops": source.get("source_crops", {}), "stac_item": source.get("stac_item"),
                "calibration": source.get("calibration")}
            for r in range(image.height // 256):
                for c in range(image.width // 256):
                    window = Window(c * 256, r * 256, 256, 256)
                    affine = image.window_transform(window)
                    values, labels = image.read(window=window), label.read(1, window=window)
                    inside = geometry_mask([polygon], (256, 256), affine, invert=True)
                    valid = (quality.read(1, window=window) == 1) & inside & (labels != 0) & np.all(np.isfinite(values) & (values != 0), axis=0)
                    labels[~valid] = 0
                    path = output / "patches" / batch["key"] / f"r{r:02d}-c{c:02d}"
                    path.mkdir(parents=True, exist_ok=True)
                    profile = {**image.profile, "width": 256, "height": 256, "transform": affine}
                    for name, data in (("image", values), ("label", labels[None]), ("quality", valid.astype("uint8")[None])):
                        target = path / f"{name}.tif"
                        with rasterio.open(target, "w", **{**profile, "count": data.shape[0], "dtype": data.dtype, "nodata": 0}) as dst:
                            dst.write(data)
                    row = copy.deepcopy(source)
                    row.update(aoi=batch["province"], province=batch["province"], split=batch["split"],
                        source_group=f"{batch['province']}/{source['scene_id']}",
                        spatial_location_id=f"{batch['province']}/{batch.get('spatial_window_id', batch['key'].rsplit('-g', 1)[-1])}/r{r}-c{c}",
                        patch_id=f"{batch['key']}-r{r}-c{c}", image_path=str(path / "image.tif"),
                        label_path=str(path / "label.tif"), quality_mask_path=str(path / "quality.tif"),
                        valid_pixel_ratio=float(valid.mean()), province_inside_fraction=float(inside.mean()),
                        quality_status="quality_eligible" if valid.mean() >= .8 and inside.mean() >= .95 else "quality_insufficient",
                        source_window=source_record, window_in_source=[c * 256, r * 256, 256, 256],
                        patch_sha256={name: service._sha(path / f"{name}.tif") for name in ("image", "label", "quality")})
                    classes, counts = np.unique(labels[valid], return_counts=True)
                    row["sample_class_coverage"] = {str(int(v)): int(n) for v, n in zip(classes, counts)}
                    patches.append(row)
    return patches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["smoke", "grid"], default="smoke")
    parser.add_argument("--output", type=Path, default=ROOT / "data/first-group-training-v1")
    parser.add_argument("--centers-per-province", type=int, default=16)
    parser.add_argument("--reference", choices=["worldcover", "esri_io"], default="worldcover")
    parser.add_argument("--years", nargs="+", type=int, default=[2020, 2021])
    parser.add_argument("--max-batches", type=int, default=0, help="0이면예산/목표까지. 새예산추가없이동일원장재개")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    service._integer(args.centers_per_province, "centers_per_province", 1, 32)
    service._integer(args.max_batches, "max_batches", 0, 10000)
    years = sorted(set(args.years))
    if not years or any(year not in range(2020, 2026) for year in years):
        raise ValueError("수집 연도는2020~2025입니다")
    if args.reference == "worldcover" and any(year not in (2020, 2021) for year in years):
        raise ValueError("WorldCover는2020/2021만허용하며후속연도로복제하지않습니다")
    output = args.output.resolve()
    # 동일 전역 원장/원본 근거 경로를 쓰도록 작업공간 data 안에만 출력한다.
    output.relative_to(ROOT / "data")
    output.mkdir(parents=True, exist_ok=True)
    ledger = CollectionLedger(ROOT / "data/first-group-training-budget/global-ledger.json", [
        ROOT / "data/first-group-annual/run-result.json", ROOT / "data/first-group-recovery32/run-result.json"],
        initial_metadata_charge=3675728)
    budget = ledger.snapshot()
    base = json.loads((ROOT / "configs/first-group.collection.json").read_text(encoding="utf-8"))
    batches = build_batches(base, args.stage, args.centers_per_province, args.reference, years)
    plan = {"created_at": now(), "stage": args.stage, "executed": False, "new_global_budget_bytes": ADDITIONAL,
        "historical_charged_upper_bound_bytes": budget["historical_charged_bytes"],
        "combined_maximum_charged_upper_bound_bytes": budget["combined_maximum_bytes"],
        "new_budget_already_charged_bytes": budget["new_charged_bytes"],
        "disk_free_bytes": shutil.disk_usage(ROOT).free, "minimum_disk_free_bytes": 8 * 1024 ** 3,
        "request_interval_seconds": 2, "concurrency": 1, "first_429_stops_all": True,
        "years": [2021] if args.stage == "smoke" else years, "reference": args.reference, "full_2020_2025_goal_met": False,
        "nominal_candidate_patches": sum(b["nominal_patches"] for b in batches), "eligible_patch_count": 0,
        "learning_ready": False, "label_note": "동년 연차 합성 약한 참조라벨. WC후속연도복제금지/서로다른taxonomy혼합금지",
        "batches": [{k: v for k, v in b.items() if k not in ("geometry", "config")} for b in batches]}
    write_json(output / f"{args.stage}-plan.json", plan)
    if not args.execute:
        print(json.dumps({k: v for k, v in plan.items() if k != "batches"}, ensure_ascii=False))
        return 0
    if plan["disk_free_bytes"] < plan["minimum_disk_free_bytes"]:
        raise RuntimeError("원본·정합본·패치복제용디스크8GiB이상필요")
    # 모든 stage가 같은 잠금을 공유한다. 429 후 다른 stage로 바꿔도 실행 불가.
    execution_lock = ledger.path.with_suffix(".execution.lock")
    descriptor = os.open(execution_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        service.configure_request_spacing(2)
        aggregate_path = output / "annual-window-report.json"
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8")) if aggregate_path.exists() else {
            "executed": True, "status": "collecting", "learning_ready": False, "scenes": [], "source_manifests": []}
        if any(s.get("label_source") != args.reference for s in aggregate["scenes"]):
            raise ValueError("WorldCover와Esri라벨은다른출력경로를사용해야합니다")
        executed = 0
        for batch in batches:
            if args.max_batches and executed >= args.max_batches:
                break
            key = batch["key"]
            directory = output / "sources" / key
            config_path = directory / "config.json"
            digest = hashlib.sha256(json.dumps(batch["config"], sort_keys=True).encode()).hexdigest()
            try:
                reserved = ledger.reserve(key, COG_BATCH + METADATA_BATCH, digest)
            except ValueError as exc:
                aggregate.update(status="stopped_budget", budget_stop_reason=str(exc))
                write_json(aggregate_path, aggregate)
                break
            if not reserved:
                continue
            executed += 1
            write_json(config_path, batch["config"])
            service.configure_metadata_budget(METADATA_BATCH)
            circuit = None
            try:
                print(json.dumps({"status": "batch_started", "key": key}), flush=True)
                preview = reference_preview(batch, directory) if args.stage == "grid" and args.reference == "worldcover" else None
                if preview and preview_is_redundant(preview, batch, aggregate["scenes"]):
                    aggregate.setdefault("label_first_deferred", []).append({"key": key,
                        "reason": "already_represented_dominant_class_not_helping_split_class_deficits", "preview": preview})
                else:
                    if preview:
                        # 사전 읽기 역시 같은 batch COG 상한에 포함한다.
                        config = copy.deepcopy(batch["config"])
                        config["prior_download_budget_bytes"] = preview["charged_bytes"]
                        write_json(config_path, config)
                    report = collect_windows(load_config(config_path), directory, execute=True)
                    circuit = report.get("batch_circuit_breaker")
                    patches = materialize_patches(report, batch, output)
                    aggregate["scenes"].extend(patches)
                    aggregate["source_manifests"].append(str(directory / "annual-window-report.json"))
            except Exception as exc:
                error = classify_error(exc)
                if error.get("http_status") == 429:
                    circuit = error
                aggregate.setdefault("batch_errors", []).append({"key": key, "error": error})
            finally:
                state_path = directory / "window-state.json"
                state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
                if state.get("last_rate_limit"):
                    circuit = state["last_rate_limit"]
                preview_path = directory / "reference-preview.json"
                preview_charge = json.loads(preview_path.read_text(encoding="utf-8")).get("charged_bytes", 0) if preview_path.exists() else 0
                charged = state.get("http_body_bytes", 0) + preview_charge + service.metadata_budget_status()["charged_bytes"]
                budget = ledger.settle(key, charged, str(directory / "annual-window-report.json"), circuit)
                aggregate.update(complete_window_count=len(aggregate["scenes"]), label_window_count=len(aggregate["scenes"]),
                    quality_eligible_window_count=sum(s.get("quality_status") == "quality_eligible" for s in aggregate["scenes"]),
                    batch_circuit_breaker=circuit, full_2020_2025_goal_met=False)
                write_json(aggregate_path, aggregate)
                result = {"status": "stopped_rate_limit" if circuit else "collecting", "manifests": [str(aggregate_path)],
                    "learning_ready": False, "maximum_total_bytes": budget["combined_maximum_bytes"],
                    "reserved_or_transferred_bytes_including_prior": budget["historical_charged_bytes"] + budget["new_charged_bytes"],
                    "historical_charged_upper_bound_bytes": budget["historical_charged_bytes"],
                    "new_charged_upper_bound_bytes": budget["new_charged_bytes"], "new_supplementary_budget_bytes": ADDITIONAL,
                    "complete_window_count": len(aggregate["scenes"]),
                    "quality_eligible_window_count": aggregate["quality_eligible_window_count"],
                    "circuit_breaker": circuit, "old_ledger_unchanged": True}
                write_json(output / "run-result.json", result)
                print(json.dumps({"status": "batch_finished", "key": key, "charged_bytes": charged,
                    "eligible_patch_count": aggregate["quality_eligible_window_count"], "rate_limited": bool(circuit)}), flush=True)
            if circuit:
                break
            metrics = candidate_coverage(aggregate["scenes"], args.reference, years)
            aggregate["coverage_metrics"] = metrics
            write_json(aggregate_path, aggregate)
            if args.stage == "grid" and metrics["candidate_target_met"]:
                # 충분성 최종 판정은 클래스·장면누출까지 보는 ML gate가 담당한다.
                aggregate.update(status="stopped_candidate_target_for_independent_audit", learning_ready=False)
                write_json(aggregate_path, aggregate)
                break
        result_path = output / "run-result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["status"] == "collecting":
                result["status"] = "finished_bounded_stage"
                write_json(result_path, result)
        return 0
    finally:
        os.close(descriptor)
        execution_lock.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
