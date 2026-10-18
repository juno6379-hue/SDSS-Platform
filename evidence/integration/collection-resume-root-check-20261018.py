"""Capture/compare existing files before an explicitly bounded collection continuation.

This audit never writes DATA. The pending batches remain charged and are not resumed.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/integration"
BASELINE = EVIDENCE / "collection-resume-root-baseline-20261018.json"


def record(path):
    if not path.exists():
        return {"exists": False}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"exists": True, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def catalog():
    uri = (ROOT / "data/catalog.sqlite3").as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute("SELECT kind,id,body FROM records ORDER BY kind,id").fetchall()
    return {"rows": len(rows), "canonical_sha256": hashlib.sha256(json.dumps(
        rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def snapshot():
    historical = json.loads((EVIDENCE / "recovery-commit-contract-preflight-20261017.json").read_text("utf-8"))
    paths = {Path(name) for name in historical["protected_references"]}
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    paths.update(ROOT / name for name in tracked if name.startswith(("backend/", "frontend/", "scripts/", "tests/")))
    paths.update((ROOT / "data/first-group-training-budget").glob("*"))
    for name in ("annual-window-report.json", "run-result.json", "parallel-v2-plan.json"):
        paths.add(ROOT / "data/first-group-training-esri-v1" / name)
    ledger = json.loads((ROOT / "data/first-group-training-budget/global-ledger.json").read_text("utf-8"))
    pending = {key: value for key, value in ledger["batches"].items() if value["status"] == "pending"}
    for key in pending:
        paths.update((ROOT / "data/first-group-training-esri-v1/sources" / key).rglob("*"))
    files = {str(path): record(path) for path in sorted(paths) if not path.is_dir()}
    return {"observed_at": datetime.now().astimezone().isoformat(), "files": files,
            "pending_batches": pending, "catalog": catalog()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("before", "after"))
    args = parser.parse_args()
    if args.mode == "before":
        result = snapshot()
        with BASELINE.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"baseline": str(BASELINE), "files": len(result["files"]), "catalog": result["catalog"]}))
        return
    before = json.loads(BASELINE.read_text("utf-8"))
    changes = [{"path": name, "before": old, "after": record(Path(name))}
               for name, old in before["files"].items() if record(Path(name)) != old]
    ledger = json.loads((ROOT / "data/first-group-training-budget/global-ledger.json").read_text("utf-8"))
    result = {"observed_at": datetime.now().astimezone().isoformat(), "changes": changes,
              "pending_batches_unchanged": all(ledger["batches"].get(k) == v for k, v in before["pending_batches"].items()),
              "old_pending_reserved_bytes": sum(v["reserved_bytes"] for v in before["pending_batches"].values()),
              "catalog_before": before["catalog"], "catalog_after": catalog(),
              "new_charged_bytes": ledger["new_charged_bytes"],
              "additional_maximum_bytes": ledger["additional_maximum_bytes"]}
    target = EVIDENCE / ("collection-resume-root-after-" + datetime.now().strftime("%Y%m%dT%H%M%S") + ".json")
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(target), "changes": [x["path"] for x in changes],
                      "pending_batches_unchanged": result["pending_batches_unchanged"],
                      "catalog_unchanged": result["catalog_before"] == result["catalog_after"]}))


if __name__ == "__main__":
    main()
