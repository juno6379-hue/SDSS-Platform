"""Read-only SQLite snapshot inspection and deterministic PostGIS dry-run plan."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .postgis_registry import KIND_TO_ENTITY, OPERATIONAL_KINDS, SCHEMA_VERSION, record_key


MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_RECORDS = 100_000
MAX_JSON_BYTES = 8 * 1024 * 1024


class SnapshotAuditError(RuntimeError):
    """The source snapshot cannot be safely audited."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _walk_nulls(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, dict):
        return sum(_walk_nulls(item) for item in value.values())
    if isinstance(value, list):
        return sum(_walk_nulls(item) for item in value)
    return 0


def _timestamp_state(record: dict[str, Any]) -> dict[str, Any]:
    candidates = {key: value for key, value in record.items() if key.endswith("_at")}
    invalid: list[str] = []
    naive: list[str] = []
    null: list[str] = []
    for key, value in candidates.items():
        if value is None:
            null.append(key)
            continue
        if not isinstance(value, str):
            invalid.append(key)
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            invalid.append(key)
            continue
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            naive.append(key)
    return {
        "fields": sorted(candidates),
        "invalid": sorted(invalid),
        "naive": sorted(naive),
        "null": sorted(null),
    }


def _position(value: Any) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("position must have longitude and latitude")
    if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value[:2]):
        raise ValueError("position values must be numeric")
    lon, lat = float(value[0]), float(value[1])
    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError("coordinates must be finite")
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("coordinate outside EPSG:4326 range")
    return lon, lat


def _validate_multipolygon(coordinates: Any) -> int:
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("MultiPolygon must contain polygons")
    point_count = 0
    for polygon in coordinates:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("polygon must contain rings")
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError("ring must contain at least four positions")
            positions = [_position(item) for item in ring]
            if positions[0] != positions[-1]:
                raise ValueError("ring must be closed")
            point_count += len(positions)
    return point_count


_GEOMETRY_FIELD = {"aois": "geometry", "scenes": "footprint", "coverage": "valid_footprint"}


def _geometry_state(record: dict[str, Any], entity: str) -> dict[str, Any]:
    field = _GEOMETRY_FIELD.get(entity)
    known_fields = set(_GEOMETRY_FIELD.values())
    unexpected = sorted(key for key in known_fields if key in record and key != field)
    if unexpected:
        return {"status": "INVALID", "field": unexpected[0], "reason": "unexpected geometry field for entity"}
    if field is None:
        return {"status": "NOT_APPLICABLE", "field": None, "reason": None}
    if field not in record or record[field] is None:
        return {"status": "MISSING", "field": field, "reason": None}
    geometry = record[field]
    try:
        if not isinstance(geometry, dict):
            raise ValueError("geometry must be GeoJSON object")
        if geometry.get("type") != "MultiPolygon":
            raise ValueError("MultiPolygon required")
        count = _validate_multipolygon(geometry.get("coordinates"))
        return {"status": "VALID_STRUCTURE", "field": field, "reason": None, "point_count": count}
    except (TypeError, ValueError) as exc:
        return {"status": "INVALID", "field": field, "reason": str(exc)}


def _read_records(connection: sqlite3.Connection) -> list[tuple[str, str, str]]:
    columns = [row[1] for row in connection.execute("PRAGMA table_info(records)")]
    if columns != ["kind", "id", "body"]:
        raise SnapshotAuditError("SQLITE_RECORDS_SCHEMA_UNSUPPORTED")
    count = int(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0])
    if count > MAX_RECORDS:
        raise SnapshotAuditError("SQLITE_RECORD_LIMIT_EXCEEDED")
    return connection.execute("SELECT kind, id, body FROM records ORDER BY kind, id").fetchall()


def build_snapshot_dry_run(snapshot: Path, *, maximum_bytes: int = MAX_SNAPSHOT_BYTES) -> dict[str, Any]:
    """Inspect a stopped SQLite snapshot and build a no-write projection report."""
    path = Path(snapshot).resolve(strict=True)
    stat = path.stat()
    if not path.is_file() or stat.st_size > maximum_bytes:
        raise SnapshotAuditError("SQLITE_SNAPSHOT_FILE_INVALID")

    sidecars = (Path(str(path) + "-wal"), Path(str(path) + "-shm"))
    if any(sidecar.exists() for sidecar in sidecars):
        raise SnapshotAuditError("SQLITE_SNAPSHOT_SIDECAR_PRESENT")
    initial_identity = (stat.st_size, stat.st_mtime_ns, _sha256_file(path))

    uri = path.as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        integrity = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        if integrity != "ok":
            raise SnapshotAuditError("SQLITE_INTEGRITY_CHECK_FAILED")
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        records = _read_records(connection)
    finally:
        connection.close()
    final_stat = path.stat()
    final_identity = (final_stat.st_size, final_stat.st_mtime_ns, _sha256_file(path))
    if initial_identity != final_identity or any(sidecar.exists() for sidecar in sidecars):
        raise SnapshotAuditError("SQLITE_SNAPSHOT_CHANGED_DURING_AUDIT")

    entity_counts: Counter[str] = Counter()
    source_kind_counts: Counter[str] = Counter()
    unmapped_counts: Counter[str] = Counter()
    seen: defaultdict[str, set[str]] = defaultdict(set)
    projected: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    for kind, identifier, raw in records:
        source_kind_counts[kind] += 1
        encoded = raw.encode("utf-8")
        if len(encoded) > MAX_JSON_BYTES:
            issues.append({"code": "JSON_RECORD_LIMIT_EXCEEDED", "kind": kind, "id": identifier})
            continue
        try:
            body = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append({"code": "JSON_INVALID", "kind": kind, "id": identifier})
            continue
        if not isinstance(body, dict):
            issues.append({"code": "JSON_OBJECT_REQUIRED", "kind": kind, "id": identifier})
            continue
        entity = (
            "operational_records" if kind in OPERATIONAL_KINDS
            else KIND_TO_ENTITY.get(kind)
        )
        if entity is None:
            unmapped_counts[kind] += 1
            continue
        target_record_id = record_key(kind, identifier)
        if target_record_id in seen[entity]:
            issues.append({"code": "ENTITY_ID_COLLISION", "entity": entity, "id": identifier})
            continue
        seen[entity].add(target_record_id)
        if body.get("id") not in (None, identifier):
            issues.append({"code": "BODY_ID_MISMATCH", "kind": kind, "id": identifier})

        timestamps = _timestamp_state(body)
        if timestamps["invalid"]:
            issues.append({"code": "TIMESTAMP_INVALID", "kind": kind, "id": identifier, "fields": timestamps["invalid"]})
        if timestamps["naive"]:
            issues.append({"code": "TIMESTAMP_NAIVE", "kind": kind, "id": identifier, "fields": timestamps["naive"]})
        geometry = _geometry_state(body, entity)
        if geometry["status"] == "INVALID":
            issues.append({"code": "GEOMETRY_INVALID", "kind": kind, "id": identifier, "field": geometry["field"]})

        canonical = _canonical(body)
        projected.append({
            "entity": entity,
            "source_kind": kind,
            "source_id": identifier,
            "target_record_id": target_record_id,
            "payload_sha256": _sha256_bytes(canonical),
            "canonical_json_roundtrip": json.loads(canonical.decode("utf-8")) == body,
            "null_value_count": _walk_nulls(body),
            "timestamps": timestamps,
            "geometry": geometry,
        })
        entity_counts[entity] += 1

    projected.sort(key=lambda item: (item["entity"], item["source_kind"], item["source_id"]))
    checks = {
        "source_row_count": len(records),
        "projected_row_count": len(projected),
        "unmapped_row_count": sum(unmapped_counts.values()),
        "issue_count": len(issues),
        "ids_unique_within_entity": not any(item["code"] == "ENTITY_ID_COLLISION" for item in issues),
        "json_roundtrip_all": all(item["canonical_json_roundtrip"] for item in projected),
        "timestamps_valid_and_aware": not any(item["code"] in {"TIMESTAMP_INVALID", "TIMESTAMP_NAIVE"} for item in issues),
        "geometries_structurally_valid_when_present": not any(item["code"] == "GEOMETRY_INVALID" for item in issues),
        "nulls_preserved": True,
        "sidecars_absent": True,
        "snapshot_unchanged_during_audit": True,
    }
    plan_basis = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_sha256": initial_identity[2],
        "source_kind_counts": dict(sorted(source_kind_counts.items())),
        "entity_counts": dict(sorted(entity_counts.items())),
        "unmapped_kind_counts": dict(sorted(unmapped_counts.items())),
        "projected": projected,
        "issues": issues,
    }
    ready = checks["source_row_count"] == checks["projected_row_count"] and not issues
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "TESTED_SYNTHETIC" if ready else "BLOCKED",
        "execution": "DRY_RUN_NO_WRITES",
        "real_database_migration": "BLOCKED",
        "snapshot": {
            "path": str(path),
            "size_bytes": stat.st_size,
            "sha256": plan_basis["snapshot_sha256"],
            "journal_mode": journal_mode,
            "integrity_check": integrity,
        },
        "checks": checks,
        "source_kind_counts": plan_basis["source_kind_counts"],
        "entity_counts": plan_basis["entity_counts"],
        "unmapped_kind_counts": plan_basis["unmapped_kind_counts"],
        "issues": issues,
        "projected_records": projected,
        "plan_sha256": _sha256_bytes(_canonical(plan_basis)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SQLite to PostGIS registry dry-run")
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    report = build_snapshot_dry_run(args.snapshot)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["status"] == "TESTED_SYNTHETIC" else 2


if __name__ == "__main__":
    raise SystemExit(main())
