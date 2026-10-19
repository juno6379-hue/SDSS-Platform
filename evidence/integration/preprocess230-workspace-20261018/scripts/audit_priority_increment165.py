"""명시한 수집 launch의 완료 증분만 읽기 전용으로 감사한다. 수집/대기/복구 없음."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    # 기존 launch의 canonical 규칙과 바이트 호환. JSON 정규화 표준 인증 아님.
    return sha(json.dumps(value, sort_keys=True).encode())


class AuditBlocked(Exception):
    pass


def require(condition, code):
    if not condition:
        raise AuditBlocked(code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_json(path, limit):
    raw = snapshot(path, limit)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(AuditBlocked("NONFINITE_JSON")))
    except (UnicodeError, ValueError, RecursionError):
        raise AuditBlocked("INVALID_JSON") from None
    return raw, value


def snapshot(path, limit):
    path = Path(path)
    require(path.is_file(), "FILE_UNAVAILABLE")
    before = path.stat()
    require(before.st_size <= limit, "FILE_LIMIT")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    after = path.stat()
    require(len(raw) <= limit, "FILE_LIMIT")
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "FILE_CHANGED_DURING_READ")
    return raw


def local(root, value):
    require(type(value) is str and bool(value) and "://" not in value, "PATH_INVALID")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    require(".." not in path.parts, "PATH_INVALID")
    require(path.is_relative_to(root), "PATH_OUTSIDE_ROOT")
    for current in (path, *path.parents):
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(), "PATH_LINK")
        if current == root:
            break
    require(path.resolve() == path.absolute(), "PATH_ALIAS")
    return path


def effective_config(config):
    # collect_samples.load_config의 유일한 JSON 변환: years가 있으면 periods를 덮어쓴다.
    # 서비스 import/endpoint검사/HTTP 없이 원 config와 실행 config의 SHA 범위를 분리한다.
    result = json.loads(json.dumps(config))
    if result.get("years"):
        result["periods"] = {str(year): {"start_date": f"{year}-{result.get('season_start', '06-01')}",
                                       "end_date": f"{year}-{result.get('season_end', '09-30')}"}
                             for year in result["years"]}
    return result


def native_patch(root, row, geometry, checked):
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    from contextlib import ExitStack
    raw = {}
    for role, field, limit in (("image", "image_path", 64 << 20), ("label", "label_path", 2 << 20),
                               ("quality", "quality_mask_path", 2 << 20)):
        path = local(root, row[field])
        raw[role] = snapshot(path, limit)
        digest = sha(raw[role])
        require(digest == row["patch_sha256"][role], "PATCH_SHA_MISMATCH")
        checked[str(path)] = digest
    with rasterio.Env(GDAL_PAM_ENABLED="NO", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", PROJ_NETWORK="OFF"):
        with ExitStack() as stack:
            datasets = {}
            for role in raw:
                require(raw[role][:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"), "NOT_TIFF")
                memory = stack.enter_context(MemoryFile(raw[role]))
                datasets[role] = stack.enter_context(memory.open(driver="GTiff"))
            image, label, quality = (datasets[r] for r in ("image", "label", "quality"))
            signature = lambda ds: (ds.crs, ds.transform, ds.width, ds.height)
            require(image.crs is not None and signature(image) == signature(label) == signature(quality), "PATCH_GRID_MISMATCH")
            require((image.width, image.height, image.count) == (256, 256, 6), "PATCH_SHAPE")
            require(label.count == quality.count == 1 and label.dtypes == quality.dtypes == ("uint8",), "PATCH_TYPES")
            values, labels, mask = image.read(), label.read(1), quality.read(1)
            require(np.isin(mask, [0, 1]).all(), "MASK_NONBINARY")
            inside = geometry_mask([transform_geom("EPSG:4326", image.crs, geometry)],
                                   (256, 256), image.transform, invert=True)
            valid = (mask == 1) & inside & (labels != 0) & np.all(np.isfinite(values) & (values != 0), axis=0)
            require(np.array_equal(mask, valid.astype("uint8")), "MASK_SUPPORT_MISMATCH")
            require(np.all(labels[~valid] == 0), "LABEL_OUTSIDE_SUPPORT")
            ratio, province = float(valid.mean()), float(inside.mean())
            for field, actual in (("valid_pixel_ratio", ratio), ("province_inside_fraction", province)):
                declared = row[field]
                require(type(declared) in (int, float) and math.isfinite(declared) and declared == actual, "PATCH_RATIO_MISMATCH")
            status = "quality_eligible" if ratio >= .8 and province >= .95 else "quality_insufficient"
            require(row["quality_status"] == status, "PATCH_STATUS_MISMATCH")
            codes, counts = np.unique(labels[valid], return_counts=True)
            histogram = {str(int(code)): int(n) for code, n in zip(codes, counts)}
            declared = row["sample_class_coverage"]
            require(type(declared) is dict and all(type(v) is int and v >= 0 for v in declared.values()) and declared == histogram, "CLASS_HISTOGRAM_MISMATCH")
            return {"patch_id": row["patch_id"], "quality_status": status, "valid_pixels": int(valid.sum()),
                    "province_inside_pixels": int(inside.sum()), "class_histogram": histogram,
                    "eligible_bare_pixels": histogram.get("8", 0) if status == "quality_eligible" else 0,
                    "image_band_descriptions": list(image.descriptions),
                    "maximum_class_fraction": max(histogram.values(), default=0) / int(valid.sum()) if valid.any() else None,
                    "maximum_class_fraction_over_90_percent": bool(valid.any() and max(histogram.values(), default=0) * 10 > int(valid.sum()) * 9)}


def audit_increment(data_root, launch_path, boundary_path):
    started = time.perf_counter()
    result = {"schema_version": 1, "scope": "READONLY_FIXED_LAUNCH_INCREMENT_NATIVE_AUDIT",
              "recorded_at": datetime.now(timezone.utc).isoformat(), "status": "INCOMPLETE",
              "issue": None, "native_validation_complete": False, "batches": [], "native_patches_checked": 0, "native_eligible_patches": 0,
              "eligible_bare_pixels": 0, "source_or_ledger_writes": 0, "collection_executed": False,
              "learning_ready": False, "scientific_accuracy_validated": False,
              "limitations": ["Sequential observations, not an atomic filesystem/DB snapshot.",
                  "Only selected launch batches get native patch checks; prior rows are canonical metadata checks.",
                  "Esri weak labels and training support masks are not independent truth or QA/model approval.",
                  "Stored whole-pool counts/leakage are metadata only, not whole-pool raster revalidation.",
                  "No HTTP, collection, retries, refunds, reservation edits or source reconstruction."]}
    try:
        root = Path(data_root).absolute()
        require(root.is_dir() and root.resolve() == root and not root.is_symlink() and not getattr(root, "is_junction", lambda: False)(), "ROOT_INVALID")
        launch_raw, launch = read_json(launch_path, 1 << 20)
        aggregate_path = local(root, "first-group-training-esri-v1/annual-window-report.json")
        ledger_path = local(root, "first-group-training-budget/global-ledger.json")
        aggregate_raw, aggregate = read_json(aggregate_path, 128 << 20)
        ledger_raw, ledger = read_json(ledger_path, 16 << 20)
        boundary_raw, boundary = read_json(local(root, str(boundary_path)), 16 << 20)
        geometries = {f["properties"]["province_id"]: f["geometry"] for f in boundary["features"]}
        jobs, old_count = launch["selected_jobs"], launch["manifest_before_rows"]
        require(type(jobs) is list and 1 <= len(jobs) <= 16 and type(old_count) is int and old_count >= 0, "LAUNCH_INVALID")
        keys = [j["key"] for j in jobs]
        require(all(type(k) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,180}", k) for k in keys) and len(set(keys)) == len(keys), "LAUNCH_KEYS_INVALID")
        rows = aggregate["scenes"]
        require(type(rows) is list and len(rows) <= 3000 and len(rows) >= old_count and canonical(rows[:old_count]) == launch["old_rows_canonical_sha256"], "OLD_ROWS_CHANGED")
        pending = launch["pending_before"]
        require(type(pending) is dict and all(ledger["batches"].get(k) == v for k, v in pending.items()), "PENDING_CHANGED")
        result.update(launch_sha256=sha(launch_raw), aggregate_sha256_at_read=sha(aggregate_raw), ledger_sha256_at_read=sha(ledger_raw),
                      boundary_sha256=sha(boundary_raw), old_rows_verified=old_count, pending_rows_verified=len(pending),
                      pending_reserved_bytes=sum(v["reserved_bytes"] for v in pending.values()),
                      physical_total_at_read=len(rows), eligible_total_at_read=sum(r.get("quality_status") == "quality_eligible" for r in rows),
                      execution_lock_present_at_read=(root / "first-group-training-budget/global-ledger.execution.lock").exists())
        cells = {(p, y): sum(r.get("province") == p and str(r.get("year")) == str(y) and r.get("quality_status") == "quality_eligible" for r in rows) for p in geometries for y in range(2020, 2026)}
        result["cell_gap_total_at_read"] = sum(max(0, 28 - n) for n in cells.values())
        result["eligible_target_gap_at_read"] = max(0, 1200 - result["eligible_total_at_read"])
        selected = {k: ledger["batches"].get(k) for k in keys}
        result["selected_ledger_observations"] = selected
        if any(type(v) is not dict or v.get("status") != "settled" for v in selected.values()):
            result["issue"] = "SELECTED_BATCH_NOT_SETTLED"
            return result
        checked, all_patch_ids = {}, set()
        for job in jobs:
            key = job["key"]
            folder = local(root, "first-group-training-esri-v1/sources/" + key)
            files = {name: folder / name for name in ("config.json", "worker-result.json", "window-state.json", "annual-window-report.json")}
            if any(not path.is_file() for path in files.values()):
                result["issue"] = "TERMINAL_OR_REPORT_MISSING"
                return result
            documents = {}
            for name, path in files.items():
                raw, documents[name] = read_json(local(root, str(path)), 16 << 20)
                checked[str(path)] = sha(raw)
            config, worker, state, report = (documents[n] for n in files)
            entry = selected[key]
            require(canonical(config) == job["config_sha256"] == entry["config_sha256"], "CONFIG_PIN_MISMATCH")
            require(canonical(effective_config(config)) == state["config_sha256"], "EFFECTIVE_CONFIG_PIN_MISMATCH")
            require(worker["key"] == key and local(root, entry["report_path"]) == files["annual-window-report.json"] == local(root, worker["report_path"]), "REPORT_BINDING_MISMATCH")
            require("error" not in worker or type(worker["error"]) is dict, "WORKER_ERROR_SHAPE")
            charge = worker["charged_bytes"]
            require(all(type(v) is int and v >= 0 for v in (charge, entry["charged_bytes"], state["http_body_bytes"], worker["metadata_budget"]["charged_bytes"], worker["cog_charged_bytes"])), "WORKER_CHARGE_TYPE")
            require(type(charge) is int and charge >= 0 and charge == entry["charged_bytes"] == state["http_body_bytes"] + worker["metadata_budget"]["charged_bytes"] == worker["cog_charged_bytes"] + worker["metadata_budget"]["charged_bytes"], "WORKER_CHARGE_MISMATCH")
            patch_rows = [r for r in rows if r.get("patch_id", "").startswith(key + "-")]
            observed = {"key": key, "settled": True, "stored_config_sha256": canonical(config),
                        "effective_config_sha256": state["config_sha256"], "charged_bytes": charge, "worker_error": "error" in worker,
                        "worker_error_category": worker.get("error", {}).get("category"),
                        "rate_limited": bool(worker.get("circuit")), "scene_status_counts": {}, "scene_failure_count": 0,
                        "patches": [], "native_patches_checked": 0, "native_eligible_patches": 0, "eligible_bare_pixels": 0}
            for scene in report.get("scenes", []):
                status = scene.get("status", "unknown")
                observed["scene_status_counts"][status] = observed["scene_status_counts"].get(status, 0) + 1
                if status != "rgb_window_downloaded" or scene.get("label_status") not in ("esri_io_aligned_weak_labels", "worldcover_aligned_weak_labels"):
                    observed["scene_failure_count"] += 1
            for row in patch_rows:
                require(row["patch_id"] not in all_patch_ids, "DUPLICATE_PATCH_ID")
                all_patch_ids.add(row["patch_id"])
                require(row["source_window"]["boundary_sha256"] == sha(boundary_raw) and local(root, row["source_window"]["boundary_path"]) == local(root, str(boundary_path)), "BOUNDARY_PIN_MISMATCH")
                require(row["province"] == job["province"] and str(row["year"]) == str(job["year"]) and row["split"] == job["split"], "PATCH_JOB_MISMATCH")
                observation = native_patch(root, row, geometries[job["province"]], checked)
                observed["patches"].append(observation)
                observed["native_patches_checked"] += 1
                observed["native_eligible_patches"] += observation["quality_status"] == "quality_eligible"
                observed["eligible_bare_pixels"] += observation["eligible_bare_pixels"]
            observed["data_outcome"] = "ZERO_PATCHES" if not patch_rows else "PATCHES_WITH_SOURCE_FAILURES" if observed["worker_error"] or observed["scene_failure_count"] or observed["rate_limited"] else "PATCHES_NATIVE_CHECKED"
            result["batches"].append(observed)
        for path, digest in checked.items():
            require(sha(snapshot(Path(path), 64 << 20)) == digest, "SELECTED_FILE_CHANGED_DURING_AUDIT")
        _, after_ledger = read_json(ledger_path, 16 << 20)
        require(all(after_ledger["batches"].get(k) == v for k, v in selected.items()), "SELECTED_LEDGER_CHANGED")
        require(all(after_ledger["batches"].get(k) == v for k, v in pending.items()), "PENDING_CHANGED_DURING_AUDIT")
        result["native_patches_checked"] = sum(b["native_patches_checked"] for b in result["batches"])
        result["native_eligible_patches"] = sum(b["native_eligible_patches"] for b in result["batches"])
        result["eligible_bare_pixels"] = sum(b["eligible_bare_pixels"] for b in result["batches"])
        result["native_validation_complete"] = True
        result["file_sha_rechecks"] = len(checked)
        result["external_metadata_changed_during_audit"] = {"aggregate": sha(snapshot(aggregate_path, 128 << 20)) != sha(aggregate_raw), "ledger": sha(snapshot(ledger_path, 16 << 20)) != sha(ledger_raw)}
        result["status"] = "COMPLETED_ZERO_PATCHES" if not result["native_patches_checked"] else "COMPLETED_WITH_SOURCE_FAILURES" if any(b["data_outcome"] != "PATCHES_NATIVE_CHECKED" for b in result["batches"]) else "COMPLETED_NATIVE_CHECKED"
        scene_splits = {}
        for row in rows:
            if row.get("quality_status") == "quality_eligible" and row.get("scene_id"):
                scene_splits.setdefault(row["scene_id"], set()).add(row.get("split"))
        result["declared_cross_split_scene_ids"] = sorted(k for k, splits in scene_splits.items() if len(splits) > 1)
        return result
    except (AuditBlocked, OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
        result.update(status="INTEGRITY_BLOCKED", issue=str(exc) if type(exc) is AuditBlocked else "INPUT_OR_FILE_INVALID")
        return result
    finally:
        for field in ("native_patches_checked", "native_eligible_patches", "eligible_bare_pixels"):
            result[field] = sum(batch[field] for batch in result["batches"])
        result["seconds"] = time.perf_counter() - started


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--launch", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_increment(args.data_root, args.launch, args.boundary)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 2 if result["status"] in ("INTEGRITY_BLOCKED", "INCOMPLETE") else 3 if result["status"] != "COMPLETED_NATIVE_CHECKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
