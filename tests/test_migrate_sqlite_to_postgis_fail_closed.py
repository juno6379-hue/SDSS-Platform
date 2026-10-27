import importlib.util
import sqlite3
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_sqlite_to_postgis.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("migrate_sqlite_to_postgis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_without_postgres_does_not_claim_migration_or_parity(tmp_path, monkeypatch):
    module = _load_module()
    sqlite_path = tmp_path / "catalog.sqlite3"
    conn = sqlite3.connect(sqlite_path)
    conn.execute("CREATE TABLE records (kind TEXT, id TEXT, body TEXT)")
    conn.execute(
        "INSERT INTO records(kind, id, body) VALUES (?, ?, ?)",
        ("dataset", "one", '{"value": 1}'),
    )
    conn.commit()
    conn.close()

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    ddl_path = output_dir / "01_postgis_schema_ddl.sql"
    ddl_path.write_text("CREATE TABLE records(id text);", encoding="utf-8")

    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setattr(module, "SQLITE_PATH", sqlite_path)
    monkeypatch.setattr(module, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(module, "DDL_PATH", ddl_path)

    assert module.migrate_and_verify() is True
    report = (output_dir / "01_sqlite_to_postgis_verification.md").read_text(
        encoding="utf-8"
    )

    assert "BLOCKED_NO_POSTGIS_PILOT_EXECUTION" in report
    assert "N/A (not executed)" in report
    assert "NOT_MEASURED" in report
    assert "DDL_ONLY_NOT_APPLIED" in report
    assert "100% MATCH" not in report
    assert "tables provisioned" not in report
    assert "Zero Downtime" not in report
    assert "CONNECTED_AND_MIGRATED" not in report
