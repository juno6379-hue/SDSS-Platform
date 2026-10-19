"""G0/G1 데이터 증거를 읽기만 하고 별도 snapshot으로 보존한다. HTTP 없음."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


def snapshot(path):
    """실행중 원자교체되는 JSON의 한 버전을 캡처한다. 원본 수정 없음."""
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), {"path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()}


def gmais_evidence(sample):
    package = ROOT / "contracts/upstream/GMAIS-v0.2"
    manifest_path = package / "package_manifest.json"
    if not manifest_path.exists():
        return {"state":"SOURCE_MISSING","scope":"shared workspace only","canonical_package_verified":False}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = []
    for relative,expected in manifest["files"].items():
        path = package / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        checks.append({"path":relative,"expected_sha256":expected,"actual_sha256":actual,"match":actual == expected})
    schema_path = package / "schemas/dataset-manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return {"state":"SOURCE_PRESENT_LOCAL_COPY","package_path":str(package),"version":manifest["version"],
        "status":manifest["status"],"consortium_approved":False,
        "canonical_package_verified":all(item["match"] for item in checks),"package_file_count":len(checks),"file_sha_checks":checks,
        "dataset_schema_sha256":hashlib.sha256(schema_path.read_bytes()).hexdigest(),
        "dataset_required_fields":schema["required"],"top_additional_properties":schema["additionalProperties"],
        "quality_status_values":schema["properties"]["quality_status"]["enum"],
        "cross_reference_profile_sha256":hashlib.sha256((package / "templates/cross-reference-profile.md").read_bytes()).hexdigest(),
        "legacy_patch_static_field_comparison":{"missing_required_fields":[key for key in schema["required"] if key not in sample],
            "undeclared_top_level_fields":[key for key in sample if key not in schema["properties"]],
            "is_full_schema_validation":False},
        "jsonschema_validator_available":importlib.util.find_spec("jsonschema") is not None,
        "note":"unmodified upstream internal proposal; static comparison does not establish contract/scientific approval"}


def main():
    started = datetime.now(timezone.utc).isoformat()
    report_path = ROOT / "data/first-group-training-esri-v1/annual-window-report.json"
    report, report_reference = snapshot(report_path)
    ledger_path = ROOT / "data/first-group-training-budget/global-ledger.json"
    ledger, ledger_reference = snapshot(ledger_path)
    rows = report.get("scenes",[])
    eligible = [row for row in rows if row.get("quality_status") == "quality_eligible"]
    provinces = ("south_sulawesi","gorontalo","southeast_sulawesi","east_java","banten","west_java")
    matrix = {p:{str(y):sum(row.get("province",row.get("aoi")) == p and str(row.get("year")) == str(y) for row in eligible)
        for y in range(2020,2026)} for p in provinces}
    hashes = []
    for item in ledger.get("historical_ledgers",[]):
        path = Path(item["path"])
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        hashes.append({"path":str(path),"expected_sha256":item["sha256"],"actual_sha256":actual,"match":actual == item["sha256"]})
    examples = []
    attempts, errors = Counter(), []
    for source_path in report.get("source_manifests",[]):
        path = Path(source_path)
        if not path.is_file():
            continue
        for row in json.loads(path.read_text(encoding="utf-8")).get("scenes",[]):
            attempts[row.get("status","unknown")] += 1
            error = row.get("error") or row.get("label_error")
            if error:
                errors.append({"path":source_path,"aoi":row.get("aoi"),"year":row.get("year"),
                    "category":error.get("category"),"http_status":error.get("http_status"),
                    "sanitized_message":error.get("sanitized_message")})
    # 보고서상적격과파일무결성은다른검증이다. 첫2개만실제해시재계산한다.
    for row in eligible[:2]:
        files = {}
        for key,tag in (("image_path","image"),("label_path","label"),("quality_mask_path","quality")):
            path = Path(row[key])
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            expected = row.get("patch_sha256",{}).get(tag)
            files[tag] = {"path":str(path),"exists":path.is_file(),"sha256":actual,"expected_sha256":expected,"match":actual == expected}
        examples.append({"patch_id":row.get("patch_id"),"province":row.get("province"),"year":row.get("year"),
            "scene_id":row.get("scene_id"),"label_source":row.get("label_source"),"label_year":row.get("label_year"),
            "normalization_evidence":row.get("normalization"),"files":files})
    gmais_files = []
    for directory in (ROOT / "api",ROOT / "schemas",ROOT / "reference_adapter",ROOT / "GMAIS",ROOT / "gmais",ROOT / "contracts"):
        if directory.exists():
            gmais_files.extend(str(path.relative_to(ROOT)) for path in directory.rglob("*") if path.is_file())
    catalogue = ROOT / "data/catalog.sqlite3"
    catalogue_counts = {}
    if catalogue.exists():
        # mode=ro이며마이그레이션/등록/UPDATE를실행하지않는다.
        with sqlite3.connect(catalogue.as_uri() + "?mode=ro",uri=True) as connection:
            tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "records" in tables:
                catalogue_counts = dict(connection.execute("SELECT kind,COUNT(*) FROM records GROUP BY kind"))
    result = {"snapshot_started_at":started,"snapshot_finished_at":datetime.now(timezone.utc).isoformat(),
        "scope":"§3/G0/G1 existing data implementation inventory; no collector mutation/no HTTP/no scientific approval",
        "requested_protected_session":89858,"network_requests":0,"source_manifest":report_reference,"ledger":ledger_reference,
        "running_evidence":{"execution_lock_present":ledger_path.with_suffix(".execution.lock").exists(),
            "pending_batches":[key for key,value in ledger.get("batches",{}).items() if value.get("status") == "pending"],
            "process_health_verified":False,"note":"lock/last manifest alone are not process completion/health proof"},
        "collection":{"physical_patches":len(rows),"manifest_quality_eligible_patches":len(eligible),
            "quality_ineligible_patches":len(rows)-len(eligible),"eligible_by_province_year":matrix,
            "label_sources":dict(Counter(row.get("label_source","unknown") for row in rows)),
            "wrong_label_year_count":sum(str(row.get("label_year")) != str(row.get("year")) for row in rows),
            "source_attempt_statuses":dict(attempts),"source_attempt_errors":errors,
            "covered_province_year_cells":sum(n > 0 for years in matrix.values() for n in years.values()),
            "expected_province_year_cells":36,"split_counts":{s:sum(r.get("split") == s for r in eligible) for s in ("train","val","test")},
            "training_ready":False,"readiness_reason":"manifest eligibility count is not class balance/leakage/independent validation approval"},
        "budget":{"historical_charged_upper_bound_bytes":ledger["historical_charged_bytes"],
            "new_reserved_or_measured_bytes":ledger["new_charged_bytes"],"new_budget_maximum_bytes":ledger["additional_maximum_bytes"],
            "combined_maximum_bytes":ledger["combined_maximum_bytes"],"external_research_metadata_bytes":ledger.get("external_research_metadata_body_bytes"),
            "pending_reserved_bytes":sum(b["charged_bytes"] for b in ledger["batches"].values() if b["status"] == "pending"),
            "ledger_internal_sum_matches":ledger["new_charged_bytes"] == ledger.get("external_research_metadata_body_bytes",0)+sum(b["charged_bytes"] for b in ledger["batches"].values()),
            "rate_limit_active":ledger["rate_limit_active"],"historical_sha_checks":hashes,
            "is_total_network_received_bytes":False},"sample_patch_integrity":examples,
        "gmais_v02":gmais_evidence(eligible[0] if eligible else {}),
        "runtime":{"python":sys.version.split()[0],"optional_modules_present":{m:importlib.util.find_spec(m) is not None for m in ("numpy","rasterio","pyproj","shapely","ee")}},
        "catalogue_record_counts":catalogue_counts,
        "protected_artifacts_modified":False,"existing_source_and_ledger_files_written":0}
    output = ROOT / "evidence/integration/data-g0-g1-20261016.json"
    if output.exists():
        # 이전증거를최신값으로덮지않고새snapshot파일을만든다.
        output = output.with_name(f"data-g0-g1-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"evidence":str(output),"eligible":len(eligible),"physical":len(rows),"coverage":result["collection"]["covered_province_year_cells"],
        "pending":len(result["running_evidence"]["pending_batches"]),"rate_limit":ledger["rate_limit_active"],"gmais":result["gmais_v02"]["state"]}))
    return output


if __name__ == "__main__":
    main()
