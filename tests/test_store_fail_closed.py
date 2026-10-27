import traceback
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import pytest

from app.postgis_registry import SchemaHealth
from app.store import Store, StorageBackendError, StorageConfigurationError, _connect_postgres


HEALTH = SchemaHealth(
    status="IMPLEMENTED_UNVERIFIED", contract_matches=True, schema_version="0355",
    migration_code_status="IMPLEMENTED_UNVERIFIED", postgis_version="3.4.2",
    missing_tables=(), column_issues=(), constraint_issues=(), geometry_issues=(),
    index_issues=(), issues=(),
)


class _Connection:
    def __init__(self): self.closed = False
    def close(self): self.closed = True


def test_psycopg_v3_connection_forces_read_only_session():
    captured = {}
    expected = object()
    fake = SimpleNamespace(connect=lambda dsn, **kwargs: captured.update(dsn=dsn, **kwargs) or expected)
    with patch.dict(sys.modules, {"psycopg": fake}):
        assert _connect_postgres("redacted") is expected
    assert captured == {
        "dsn": "redacted", "connect_timeout": 10,
        "options": "-c default_transaction_read_only=on",
    }


def test_local_default_is_explicit_sqlite_development_backend(tmp_path):
    with patch.dict("os.environ", {}, clear=True):
        store = Store(tmp_path)
    assert store.storage_status()["status"] == "READY"
    assert store.storage_status()["writable"] is True
    assert store.put("jobs", {"id": "a", "status": "queued"})["id"] == "a"


@pytest.mark.parametrize("mode", ["postgres", "postgres-inspect"])
def test_postgres_modes_require_dsn_and_never_create_sqlite(tmp_path, mode):
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(StorageConfigurationError, match="POSTGRES_DSN_REQUIRED"):
            Store(tmp_path, storage_mode=mode)
    assert not (tmp_path / "catalog.sqlite3").exists()


def test_postgres_startup_error_suppresses_secret_context(tmp_path):
    env = {"POSTGRES_DSN": "postgresql://user:secret@invalid/db"}
    with patch.dict("os.environ", env, clear=True), patch(
        "app.store._connect_postgres", side_effect=RuntimeError("secret connection detail")
    ):
        with pytest.raises(StorageBackendError, match="POSTGRES_STARTUP_FAILED") as captured:
            Store(tmp_path)
    rendered = "".join(traceback.format_exception(captured.value))
    assert "secret connection detail" not in rendered
    assert "user:secret" not in rendered


def test_development_fallback_is_explicit_and_reported(tmp_path):
    env = {"POSTGRES_DSN": "x", "GEOAI_ENVIRONMENT": "development", "GEOAI_ALLOW_DEV_SQLITE_FALLBACK": "1"}
    with patch.dict("os.environ", env, clear=True), patch(
        "app.store._connect_postgres", side_effect=RuntimeError("offline")
    ):
        store = Store(tmp_path)
    status = store.storage_status()
    assert status["status"] == "DEGRADED_DEV_FALLBACK"
    assert status["fallback_reason"] == "POSTGRES_STARTUP_FAILED"
    assert status["writable"] is True


def test_healthy_schema_still_blocks_writable_postgres_cutover_and_closes(tmp_path):
    connection = _Connection()
    with patch.dict("os.environ", {"POSTGRES_DSN": "redacted"}, clear=True), patch(
        "app.store._connect_postgres", return_value=connection
    ), patch("app.store.require_healthy_schema", return_value=HEALTH):
        with pytest.raises(StorageBackendError, match="POSTGRES_CUTOVER_BLOCKED"):
            Store(tmp_path, storage_mode="postgres")
    assert connection.closed is True
    assert not (tmp_path / "catalog.sqlite3").exists()


def test_inspection_mode_is_read_only_and_closes_connection(tmp_path):
    connection = _Connection()
    with patch.dict("os.environ", {"POSTGRES_DSN": "redacted"}, clear=True), patch(
        "app.store._connect_postgres", return_value=connection
    ), patch("app.store.require_healthy_schema", return_value=HEALTH):
        store = Store(tmp_path, storage_mode="postgres-inspect")
    assert connection.closed is True
    status = store.storage_status()
    assert status["status"] == "BLOCKED_POSTGRES_INSPECTION_ONLY"
    assert status["writable"] is False
    for operation in (
        lambda: store.put("datasets", {"id": "x"}),
        lambda: store.get("datasets", "x"),
        lambda: store.list("datasets"),
    ):
        with pytest.raises(StorageBackendError, match="POSTGRES_INSPECTION_READ_ONLY"):
            operation()


def test_fallback_and_sqlite_are_forbidden_in_production(tmp_path):
    with patch.dict("os.environ", {"POSTGRES_DSN": "x"}, clear=True):
        with pytest.raises(StorageConfigurationError, match="SQLITE_FALLBACK_FORBIDDEN"):
            Store(tmp_path, storage_mode="postgres", environment="production", allow_dev_fallback=True)
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(StorageConfigurationError, match="SQLITE_DEV_BACKEND_FORBIDDEN"):
            Store(Path(tmp_path), storage_mode="sqlite-dev", environment="production")
