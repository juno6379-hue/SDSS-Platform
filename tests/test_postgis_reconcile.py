import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from app.postgis_reconcile import SnapshotAuditError, build_snapshot_dry_run


def _snapshot(path: Path, rows: list[tuple[str, str, dict]]) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE records (kind TEXT, id TEXT, body TEXT, PRIMARY KEY(kind,id))"
        )
        connection.executemany(
            "INSERT INTO records VALUES (?, ?, ?)",
            [
                (kind, identifier, json.dumps(body, ensure_ascii=False, allow_nan=False))
                for kind, identifier, body in rows
            ],
        )


def test_read_only_snapshot_dry_run_checks_every_domain_entity(tmp_path):
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [[[[127.0, 37.0], [127.1, 37.0], [127.1, 37.1], [127.0, 37.0]]]],
    }
    rows = [
        ("datasets", "dataset-1", {"id": "dataset-1", "created_at": "2026-10-21T00:00:00+09:00", "note": None}),
        ("assets", "asset-1", {"id": "asset-1", "created_at": "2026-10-21T00:01:00+09:00"}),
        ("scenes", "scene-1", {"id": "scene-1", "created_at": "2026-10-21T00:02:00+09:00", "footprint": geometry}),
        ("aois", "aoi-1", {"id": "aoi-1", "created_at": "2026-10-21T00:03:00+09:00", "geometry": geometry}),
        ("coverage", "coverage-1", {"id": "coverage-1", "created_at": "2026-10-21T00:04:00Z"}),
        ("experiments", "experiment-1", {"id": "experiment-1", "created_at": "2026-10-21T00:05:00Z"}),
        ("models", "model-1", {"id": "model-1", "created_at": "2026-10-21T00:06:00Z"}),
        ("predictions", "prediction-1", {"id": "prediction-1", "created_at": "2026-10-21T00:07:00Z"}),
        ("approvals", "approval-1", {"id": "approval-1", "created_at": "2026-10-21T00:08:00Z"}),
        ("jobs", "job-1", {"id": "job-1", "created_at": "2026-10-21T00:09:00Z", "status": "failed"}),
    ]
    source = tmp_path / "snapshot.sqlite3"
    _snapshot(source, rows)
    before = source.read_bytes()

    first = build_snapshot_dry_run(source)
    second = build_snapshot_dry_run(source)

    assert first["status"] == "TESTED_SYNTHETIC"
    assert first["execution"] == "DRY_RUN_NO_WRITES"
    assert first["real_database_migration"] == "BLOCKED"
    assert first["checks"] == {
        "source_row_count": 10,
        "projected_row_count": 10,
        "unmapped_row_count": 0,
        "issue_count": 0,
        "ids_unique_within_entity": True,
        "json_roundtrip_all": True,
        "timestamps_valid_and_aware": True,
        "geometries_structurally_valid_when_present": True,
        "nulls_preserved": True,
        "sidecars_absent": True,
        "snapshot_unchanged_during_audit": True,
    }
    assert set(first["entity_counts"]) == {
        "datasets", "assets", "scenes", "aois", "coverage",
        "experiments", "models", "predictions", "approvals",
        "operational_records",
    }
    assert first["plan_sha256"] == second["plan_sha256"]
    assert source.read_bytes() == before


def test_snapshot_dry_run_blocks_unmapped_naive_timestamp_and_bad_geometry(tmp_path):
    source = tmp_path / "bad.sqlite3"
    _snapshot(
        source,
        [
            ("unknown", "x", {"id": "x"}),
            (
                "aois",
                "bad-aoi",
                {
                    "id": "bad-aoi",
                    "created_at": "2026-10-21T00:00:00",
                    "geometry": {"type": "Point", "coordinates": [200, 95]},
                },
            ),
        ],
    )

    report = build_snapshot_dry_run(source)

    assert report["status"] == "BLOCKED"
    assert report["checks"]["unmapped_row_count"] == 1
    assert report["checks"]["timestamps_valid_and_aware"] is False
    assert report["checks"]["geometries_structurally_valid_when_present"] is False
    assert {issue["code"] for issue in report["issues"]} == {
        "TIMESTAMP_NAIVE", "GEOMETRY_INVALID"
    }


def test_snapshot_blocks_wrong_geojson_type_even_when_coordinates_are_in_range(tmp_path):
    source = tmp_path / "point.sqlite3"
    _snapshot(source, [("aois", "a", {"id": "a", "geometry": {"type": "Point", "coordinates": [127, 37]}})])
    report = build_snapshot_dry_run(source)
    assert report["status"] == "BLOCKED"
    assert report["projected_records"][0]["geometry"]["reason"] == "MultiPolygon required"


def test_snapshot_blocks_open_multipolygon_ring(tmp_path):
    source = tmp_path / "ring.sqlite3"
    geometry = {"type": "MultiPolygon", "coordinates": [[[[127, 37], [128, 37], [128, 38], [127, 38]]]]}
    _snapshot(source, [("scenes", "s", {"id": "s", "footprint": geometry})])
    report = build_snapshot_dry_run(source)
    assert report["status"] == "BLOCKED"
    assert report["projected_records"][0]["geometry"]["reason"] == "ring must be closed"


@pytest.mark.parametrize("suffix", ["-wal", "-shm"])
def test_snapshot_rejects_wal_and_shm_sidecars(tmp_path, suffix):
    source = tmp_path / "live.sqlite3"
    _snapshot(source, [])
    sidecar = Path(str(source) + suffix)
    sidecar.write_bytes(b"present")
    with pytest.raises(SnapshotAuditError, match="SQLITE_SNAPSHOT_SIDECAR_PRESENT"):
        build_snapshot_dry_run(source)


def test_snapshot_rejects_concurrent_file_change(tmp_path):
    source = tmp_path / "changing.sqlite3"
    _snapshot(source, [])
    with patch("app.postgis_reconcile._sha256_file", side_effect=["a" * 64, "b" * 64]):
        with pytest.raises(SnapshotAuditError, match="SQLITE_SNAPSHOT_CHANGED_DURING_AUDIT"):
            build_snapshot_dry_run(source)
