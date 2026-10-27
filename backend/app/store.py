"""Fail-closed storage selection for SQLite development and PostGIS inspection.

The PostgreSQL pilot is deliberately read-only. A successful schema
inspection proves DDL compatibility only; it does not enable application
CRUD until typed mappings and backend-neutral transactions exist.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .postgis_registry import PostGISContractError, require_healthy_schema


class StorageConfigurationError(RuntimeError):
    """Storage settings are incomplete or unsafe for the selected environment."""


class StorageBackendError(RuntimeError):
    """The selected storage backend failed; callers must not change backends."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _connect_postgres(dsn: str):
    """Open a psycopg v3 connection without propagating secret-bearing causes."""
    try:
        import psycopg
    except ImportError:  # pragma: no cover - deployment-image dependent
        raise StorageBackendError("POSTGRES_DRIVER_UNAVAILABLE") from None
    try:
        return psycopg.connect(
            dsn,
            connect_timeout=10,
            options="-c default_transaction_read_only=on",
        )
    except Exception:
        raise StorageBackendError("POSTGRES_CONNECTION_FAILED") from None


class Store:
    def __init__(
        self,
        root: Path,
        recover_jobs: bool = False,
        *,
        storage_mode: str | None = None,
        allow_dev_fallback: bool | None = None,
        environment: str | None = None,
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "catalog.sqlite3"
        self.postgres_dsn = os.getenv("POSTGRES_DSN")
        self.environment = (environment or os.getenv("GEOAI_ENVIRONMENT") or "development").lower()
        configured_mode = storage_mode or os.getenv("GEOAI_STORAGE_MODE")
        self.configured_mode = configured_mode or ("postgres" if self.postgres_dsn else "sqlite-dev")
        self.allow_dev_fallback = (
            _env_truthy(os.getenv("GEOAI_ALLOW_DEV_SQLITE_FALLBACK"))
            if allow_dev_fallback is None else bool(allow_dev_fallback)
        )
        self._backend = self.configured_mode
        self._fallback_used = False
        self._fallback_reason: str | None = None
        self._schema_health: dict[str, Any] | None = None
        self._validate_configuration()
        self._init_db()

        for job in self.list("jobs") if recover_jobs and self._backend == "sqlite-dev" else []:
            if job["status"] in ("queued", "running"):
                job.update(
                    status="failed",
                    error="서버 재시작으로 중단되었습니다. 입력을 확인하고 다시 실행하십시오.",
                    finished_at=now(),
                )
                self.put("jobs", job)

    @property
    def backend(self) -> str:
        return self._backend

    def _validate_configuration(self) -> None:
        if self.configured_mode not in {"sqlite-dev", "postgres-inspect", "postgres"}:
            raise StorageConfigurationError("STORAGE_MODE_UNSUPPORTED")
        if self.configured_mode == "sqlite-dev" and self.environment not in {"development", "test"}:
            raise StorageConfigurationError("SQLITE_DEV_BACKEND_FORBIDDEN")
        if self.allow_dev_fallback and self.environment != "development":
            raise StorageConfigurationError("SQLITE_FALLBACK_FORBIDDEN_OUTSIDE_DEVELOPMENT")
        if self.configured_mode in {"postgres-inspect", "postgres"} and not self.postgres_dsn:
            raise StorageConfigurationError("POSTGRES_DSN_REQUIRED")

    def _init_db(self) -> None:
        if self.configured_mode == "sqlite-dev":
            self._init_sqlite()
            return
        try:
            with closing(_connect_postgres(str(self.postgres_dsn))) as connection:
                health = require_healthy_schema(connection)
            self._schema_health = health.as_dict()
            if self.configured_mode == "postgres":
                raise StorageBackendError("POSTGRES_CUTOVER_BLOCKED")
            self._backend = "postgres-inspect"
        except Exception as exc:
            if self.allow_dev_fallback and self.environment == "development":
                self._backend = "sqlite-dev"
                self._fallback_used = True
                self._fallback_reason = self._safe_failure_code(exc)
                self._init_sqlite()
                return
            if isinstance(exc, PostGISContractError):
                raise StorageBackendError(str(exc)) from None
            if isinstance(exc, StorageBackendError):
                raise exc from None
            raise StorageBackendError("POSTGRES_STARTUP_FAILED") from None

    @staticmethod
    def _safe_failure_code(exc: Exception) -> str:
        if isinstance(exc, (PostGISContractError, StorageBackendError)):
            return str(exc)
        return "POSTGRES_STARTUP_FAILED"

    def _init_sqlite(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS records "
                "(kind TEXT, id TEXT, body TEXT, PRIMARY KEY(kind,id))"
            )

    def storage_status(self) -> dict[str, Any]:
        if self._fallback_used:
            status = "DEGRADED_DEV_FALLBACK"
        elif self._backend == "postgres-inspect":
            status = "BLOCKED_POSTGRES_INSPECTION_ONLY"
        else:
            status = "READY"
        return {
            "status": status,
            "configured_mode": self.configured_mode,
            "active_backend": self._backend,
            "environment": self.environment,
            "writable": self._backend == "sqlite-dev",
            "fallback_used": self._fallback_used,
            "fallback_reason": self._fallback_reason,
            "schema_health": self._schema_health,
        }

    @contextmanager
    def connect(self):
        if self._backend != "sqlite-dev":
            raise StorageBackendError("DIRECT_SQLITE_ACCESS_UNAVAILABLE_IN_POSTGRES_MODE")
        connection = sqlite3.connect(self.db, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _require_sqlite_crud(self) -> None:
        if self._backend != "sqlite-dev":
            raise StorageBackendError("POSTGRES_INSPECTION_READ_ONLY") from None

    def put(self, kind: str, record: dict[str, Any]) -> dict[str, Any]:
        self._require_sqlite_crud()
        record = dict(record)
        record.setdefault("id", uuid.uuid4().hex)
        record.setdefault("created_at", now())
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO records VALUES(?,?,?)",
                (kind, record["id"], json.dumps(record, ensure_ascii=False, allow_nan=False)),
            )
        return record

    def get(self, kind: str, identifier: str) -> dict[str, Any]:
        self._require_sqlite_crud()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT body FROM records WHERE kind=? AND id=?", (kind, identifier)
            ).fetchone()
        if not row:
            raise KeyError(identifier)
        return json.loads(row[0])

    def list(self, kind: str) -> list[dict[str, Any]]:
        self._require_sqlite_crud()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT body FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
