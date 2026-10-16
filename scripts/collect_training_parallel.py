"""공유 예산/전역2초간격/첫429중단을 유지하는 실제수집 2worker v2."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.data import service
from app.data.budget import CollectionLedger
from app.data.parallel import run_two_workers
from collect_samples import collect_windows, load_config, now
from collect_training_grid import build_batches, materialize_patches, candidate_coverage, write_json, ADDITIONAL, COG_BATCH, METADATA_BATCH
from diagnose_stac import classify_error


def balanced_coverage(scenes):
    metrics = candidate_coverage(scenes, "esri_io", range(2020, 2026))
    eligible = [s for s in scenes if s.get("quality_status") == "quality_eligible"]
    ratios, contributing, dominance = {}, {}, {}
    for split in ("train", "val", "test"):
        selected = [s for s in eligible if s.get("split") == split]
        counts = metrics["required_class_pixel_counts"][split]
        total = sum(sum(s.get("sample_class_coverage", {}).values()) for s in selected)
        ratios[split] = {code: n / total if total else 0 for code, n in counts.items()}
        all_codes = {code for row in selected for code in row.get("sample_class_coverage", {})}
        dominance[split] = max((sum(row.get("sample_class_coverage", {}).get(code, 0) for row in selected) / total
            for code in all_codes), default=0) if total else 0
        contributing[split] = {code: sum(s.get("sample_class_coverage", {}).get(code, 0) >= 256 for s in selected) for code in counts}
    metrics.update(required_class_pixel_fractions=ratios, required_class_contributing_patches=contributing, dominant_class_fraction=dominance,
        policy_note="개발정책:필수클래스비율0.5%/기여패치5개/지배클래스90%이하;독립정확도인수기준아님")
    metrics["candidate_target_met"] = bool(metrics["candidate_target_met"] and all(
        min(ratios[s].values()) >= .005 and min(contributing[s].values()) >= 5 and dominance[s] <= .9 for s in ratios))
    return metrics


def v2_jobs(base, centers=4):
    jobs = build_batches(base, "grid", centers, "esri_io", range(2020, 2026))
    for job in jobs:
        old_key = job["key"]
        job.update(key=f"parallel-v2-{old_key}", spatial_window_id=old_key.rsplit("-g", 1)[-1])
        job["config"].update(collection_policy_version="parallel-v2", candidate_valid_fraction=.65,
            min_valid_fraction=.8, cloud_cover=60, label_first=True)
    return jobs


def extra_jobs(base, plans, centers=4):
    """로컬제안의SHA/기하를검증한뒤기존ID를바꾸지않고새공간작업을만든다."""
    from app.data.candidates import validate_candidate_plan
    templates = build_batches(base,"grid",centers,"esri_io",[2020])
    by_province = {job["province"]: job for job in templates}
    existing = [{"province": job["province"], **job["center"]} for job in templates]
    result = []
    province_rank = {province:0 for province in by_province}
    for path in plans:
        path = path.resolve()
        path.relative_to(ROOT / "data")
        validated = validate_candidate_plan(path,ROOT / "data/first-group-boundaries/selected-six.geojson",existing)
        for index, candidate in enumerate(validated["candidates"]):
            province = candidate["province"]
            rank = province_rank[province]
            province_rank[province] += 1
            existing.append({"province":province,"lon":candidate["lon"],"lat":candidate["lat"],"grid_crs":candidate["grid_crs"]})
            for year in candidate["years"]:
                job = copy.deepcopy(by_province[province])
                config = job["config"]
                aoi = config["aois"][0]
                aoi.update(id=f"{province}-extra-{index:02d}",bbox=candidate["bbox"])
                config.update(years=[year],collection_policy_version="parallel-v2-extra",candidate_valid_fraction=.65,
                    min_valid_fraction=.8,cloud_cover=60,label_first=True,
                    spatial_candidate_evidence={"path":validated["source_path"],"sha256":validated["source_sha256"],
                        "class_presence_verified":False,"spatial_window_id":candidate["spatial_window_id"]})
                job.update(key=f"parallel-v2-extra-{province}-{year}-{candidate['spatial_window_id']}",year=year,
                    spatial_window_id=candidate["spatial_window_id"],candidate_rank=rank,
                    center={k:candidate[k] for k in ("lon","lat","grid_crs")})
                result.append(job)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/first-group-training-esri-v1")
    parser.add_argument("--centers-per-province", type=int, default=4)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--candidate-plan",type=Path,action="append",default=[],help="로컬검증후추가공간후보를공통원장으로소비")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    service._integer(args.centers_per_province, "centers_per_province", 1, 16)
    service._integer(args.max_batches, "max_batches", 0, 1000)
    output = args.output.resolve()
    output.relative_to(ROOT / "data")
    output.mkdir(parents=True, exist_ok=True)
    ledger = CollectionLedger(ROOT / "data/first-group-training-budget/global-ledger.json", [
        ROOT / "data/first-group-annual/run-result.json", ROOT / "data/first-group-recovery32/run-result.json"], initial_metadata_charge=3675728)
    snapshot = ledger.snapshot()
    base = json.loads((ROOT / "configs/first-group.collection.json").read_text(encoding="utf-8"))
    jobs = v2_jobs(base, args.centers_per_province)
    additions = extra_jobs(base,args.candidate_plan,args.centers_per_province)
    jobs = additions + jobs
    plan = {"created_at": now(), "executed": False, "policy_version": "parallel-v2", "workers": 2,
        "global_request_spacing_seconds": 2, "first_429_stops_all_workers": True,
        "source_scl_minimum": .65, "final_patch_valid_minimum": .8, "scene_cloud_maximum": 60,
        "same_global_ledger": str(ledger.path), "new_budget_added": False,
        "additional_maximum_bytes": ADDITIONAL, "combined_maximum_bytes": snapshot["combined_maximum_bytes"],
        "new_charged_bytes_before": snapshot["new_charged_bytes"], "nominal_candidate_patches": len(jobs) * 16,
        "v1_successful_spatial_windows_reused_without_redownload": True,
        "extra_candidate_plan_paths": [str(path) for path in args.candidate_plan],
        "jobs": [{k: v for k, v in job.items() if k not in ("config", "geometry")} for job in jobs], "learning_ready": False}
    plan_path = output / "parallel-v2-plan.json"
    if plan_path.exists():
        old_bytes = plan_path.read_bytes()
        archived = output / "plans" / f"{hashlib.sha256(old_bytes).hexdigest()}.json"
        archived.parent.mkdir(parents=True,exist_ok=True)
        if not archived.exists():
            archived.write_bytes(old_bytes)
    write_json(plan_path, plan)
    if not args.execute:
        print(json.dumps({k: v for k, v in plan.items() if k != "jobs"}, ensure_ascii=True))
        return 0
    lock = ledger.path.with_suffix(".execution.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    event = threading.Event()
    service.configure_request_spacing(2)
    service.configure_request_circuit(event)
    aggregate_path = output / "annual-window-report.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8")) if aggregate_path.exists() else {
        "executed": True, "scenes": [], "source_manifests": [], "learning_ready": False}
    if any(s.get("label_source") != "esri_io" for s in aggregate["scenes"]):
        raise ValueError("다른참조taxonomy와혼합하지않습니다")
    # 기존성공창을먼저제외한뒤주별대기열을교대로배치한다. 최초두worker가
    # 같은주의서로다른연도에만몰리지않도록남은주를균등하게진행한다.
    provinces = [a["id"] for a in base["aois"]]
    pending_by_province = {p: [] for p in provinces}
    for job in jobs:
        prefix = f"{job['province']}/{job['spatial_window_id']}/"
        if not any(s.get("province") == job["province"] and int(s["year"]) == job["year"] and s.get("spatial_location_id", "").startswith(prefix) and s.get("quality_status") == "quality_eligible" for s in aggregate["scenes"]):
            pending_by_province[job["province"]].append(job)
    for province,queue in pending_by_province.items():
        queue.sort(key=lambda job:(job.get("candidate_rank",int(job["spatial_window_id"]) if job["spatial_window_id"].isdigit() else 0),job["year"],job["key"]))
    jobs = [pending_by_province[p][index] for index in range(max(map(len,pending_by_province.values()),default=0))
            for p in provinces if index < len(pending_by_province[p])]
    observed_threads = set()
    active_count, maximum_active = 0, 0
    reserved_inflight = 0
    active_lock = threading.Lock()

    def reserve(job):
        nonlocal reserved_inflight
        prefix = f"{job['province']}/{job['spatial_window_id']}/"
        # 같은물리창에 v1 적격패치가 하나라도 있으면 재수집으로 개수를 늘리지 않는다.
        if any(s.get("province") == job["province"] and int(s["year"]) == job["year"] and
            s.get("spatial_location_id", "").startswith(prefix) and s.get("quality_status") == "quality_eligible" for s in aggregate["scenes"]):
            return False
        if len(aggregate["scenes"]) + 16 * (reserved_inflight + 1) > 3000:
            raise ValueError("최대3000개패치후보를초과하지않습니다")
        digest = hashlib.sha256(json.dumps(job["config"], sort_keys=True).encode()).hexdigest()
        accepted = ledger.reserve(job["key"], COG_BATCH + METADATA_BATCH, digest)
        if accepted:
            reserved_inflight += 1
            metrics = balanced_coverage(aggregate["scenes"])
            split = job["split"]
            fractions = metrics["required_class_pixel_fractions"][split]
            patch_counts = metrics["required_class_contributing_patches"][split]
            province_rows = [s for s in aggregate["scenes"] if s.get("province") == job["province"] and s.get("quality_status") == "quality_eligible"]
            job["selection_context"] = {"priority_source_classes": [int(code) for code in fractions if fractions[code] < .005 or patch_counts[code] < 5],
                "allow_dominant_class_deferral": len(province_rows) >= 50 and len({s.get("spatial_location_id") for s in province_rows}) >= 32
                    and any(int(s["year"]) == job["year"] for s in province_rows),
                "snapshot_eligible_patches": len(province_rows)}
        return accepted

    def work(job):
        nonlocal active_count, maximum_active
        with active_lock:
            active_count += 1
            maximum_active = max(maximum_active, active_count)
            observed_threads.add(threading.get_ident())
        directory = output / "sources" / job["key"]
        config_path = directory / "config.json"
        write_json(config_path, job["config"])
        service.configure_metadata_budget(METADATA_BATCH)
        result = {"key": job["key"], "worker_thread": threading.get_ident(), "patches": []}
        print(json.dumps({"status": "worker_started", "key": job["key"], "thread": threading.get_ident()}), flush=True)
        try:
            write_json(directory / "selection-context.json", job.get("selection_context", {}))
            report = collect_windows(load_config(config_path), directory, execute=True, selection_context=job.get("selection_context"))
            result.update(report_path=str(directory / "annual-window-report.json"), circuit=report.get("batch_circuit_breaker"))
            result["patches"] = materialize_patches(report, job, output)
        except Exception as exc:
            result["error"] = classify_error(exc)
        finally:
            state_path = directory / "window-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            metadata = service.metadata_budget_status()
            result.update(cog_charged_bytes=state.get("http_body_bytes", 0), metadata_budget=metadata,
                charged_bytes=state.get("http_body_bytes", 0) + metadata["charged_bytes"])
            write_json(directory / "worker-result.json", {k: v for k, v in result.items() if k != "patches"})
            with active_lock:
                active_count -= 1
        return result

    def finalize(job, result):
        nonlocal reserved_inflight
        # 원장 변경/합산 보고서는 항상 coordinator 스레드에서만 수행한다.
        if "unmeasured_worker_failure" in result:
            result = {"charged_bytes": COG_BATCH + METADATA_BATCH, "patches": [],
                "error": classify_error(result["unmeasured_worker_failure"]), "measurement_known": False}
        circuit = result.get("circuit") or service.request_circuit_status()
        current = ledger.settle(job["key"], result["charged_bytes"], result.get("report_path"), circuit)
        reserved_inflight -= 1
        if circuit:
            event.set()
        new_rows = result.get("patches", [])
        if new_rows:
            prefix = f"{job['province']}/{job['spatial_window_id']}/"
            replaced = [s for s in aggregate["scenes"] if s.get("province") == job["province"] and int(s["year"]) == job["year"] and s.get("spatial_location_id", "").startswith(prefix)]
            if replaced:
                aggregate.setdefault("historical_noneligible_patches", []).extend(replaced)
                aggregate["scenes"] = [s for s in aggregate["scenes"] if s not in replaced]
            aggregate["scenes"].extend(new_rows)
        if result.get("report_path"):
            aggregate["source_manifests"].append(result["report_path"])
        if result.get("error"):
            aggregate.setdefault("batch_errors", []).append({"key": job["key"], "error": result["error"]})
        metrics = balanced_coverage(aggregate["scenes"])
        aggregate.update(status="stopped_rate_limit" if circuit else "parallel_collecting", policy_version="parallel-v2",
            complete_window_count=len(aggregate["scenes"]), label_window_count=len(aggregate["scenes"]),
            quality_eligible_window_count=metrics["eligible_patch_count"], coverage_metrics=metrics,
            batch_circuit_breaker=circuit, learning_ready=False, full_2020_2025_goal_met=False)
        write_json(aggregate_path, aggregate)
        write_json(output / "run-result.json", {"status": aggregate["status"], "manifests": [str(aggregate_path)],
            "workers": 2, "observed_worker_threads": len(observed_threads), "observed_maximum_active_workers": maximum_active,
            "maximum_total_bytes": current["combined_maximum_bytes"],
            "reserved_or_transferred_bytes_including_prior": current["historical_charged_bytes"] + current["new_charged_bytes"],
            "new_charged_upper_bound_bytes": current["new_charged_bytes"], "new_supplementary_budget_bytes": ADDITIONAL,
            "complete_window_count": len(aggregate["scenes"]), "quality_eligible_window_count": metrics["eligible_patch_count"],
            "circuit_breaker": circuit, "old_ledger_unchanged": True, "learning_ready": False})
        print(json.dumps({"status": "worker_finished", "key": job["key"], "charged_bytes": result["charged_bytes"],
            "new_patches": len(new_rows), "eligible_total": metrics["eligible_patch_count"], "rate_limited": bool(circuit)}), flush=True)
        if metrics["candidate_target_met"]:
            event.set()

    try:
        summary = run_two_workers(jobs, reserve, work, finalize, event, args.max_batches)
        final_path = output / "run-result.json"
        if final_path.exists():
            result = json.loads(final_path.read_text(encoding="utf-8"))
            result.update(parallel_execution=summary)
            if not result.get("circuit_breaker"):
                result["status"] = "finished_bounded_parallel_stage"
            write_json(final_path, result)
        return 0
    finally:
        service.configure_request_circuit(None)
        os.close(descriptor)
        lock.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
