"""Strict, read-only PostGIS pilot schema inspection.

The pilot is deliberately not a writable application backend. This module
only proves that an already-provisioned database matches the complete 0355
DDL contract; Store keeps cutover blocked until typed mapping and a
backend-neutral transaction API exist.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

SCHEMA_NAME = "geoai_registry"
SCHEMA_VERSION = "0355"
MIGRATION_CODE_STATUS = "IMPLEMENTED_UNVERIFIED"
MIN_POSTGIS_MAJOR = 3

ENTITY_TABLES = (
    "datasets", "assets", "scenes", "aois", "coverage", "experiments",
    "models", "predictions", "approvals",
)
SUPPORT_TABLES = ("schema_migrations", "operational_records")
OPERATIONAL_KINDS = frozenset({
    "jobs", "analyses", "gmais_idempotency", "gmais_jobs", "gmais_results",
    "lcluc-workflows", "mlops_retrain_jobs",
})
KIND_TO_ENTITY = {
    "datasets": "datasets", "dataset_versions": "datasets",
    "assets": "assets", "raster_assets": "assets",
    "scenes": "scenes", "stac_items": "scenes",
    "aois": "aois", "aoi_boundaries": "aois",
    "coverage": "coverage", "monthly_coverage": "coverage", "annual_coverage": "coverage",
    "experiments": "experiments", "training_runs": "experiments",
    "models": "models", "model_versions": "models",
    "predictions": "predictions", "prediction_results": "predictions",
    "approvals": "approvals", "approval_records": "approvals", "mlops_approvals": "approvals",
}

_COMMON = {
    "record_id": "text", "source_kind": "text", "source_record_id": "text",
    "created_at": "timestamptz", "raw_payload": "jsonb", "source_payload_sha256": "bpchar",
}
EXPECTED_COLUMNS: Mapping[str, Mapping[str, str]] = {
    "schema_migrations": {
        "version": "text", "applied_at": "timestamptz", "description": "text", "code_status": "text",
    },
    "operational_records": dict(_COMMON),
    "aois": {**_COMMON, "province_code": "text", "boundary_version": "text", "geometry": "geometry",
             "area_ha": "float8", "area_method_version": "text", "legal_boundary_certified": "bool"},
    "scenes": {**_COMMON, "provider": "text", "collection_id": "text", "acquisition_timestamp": "timestamptz",
               "processing_baseline": "text", "footprint": "geometry", "scene_cloud_pct": "float8", "status": "text"},
    "datasets": {**_COMMON, "dataset_id": "text", "dataset_version": "text", "class_schema_id": "text",
                 "boundary_version": "text", "mask_policy_version": "text", "status": "text", "learning_ready": "bool"},
    "assets": {**_COMMON, "dataset_record_id": "text", "scene_record_id": "text", "asset_role": "text",
               "immutable_uri": "text", "sha256": "bpchar", "size_bytes": "int8", "content_type": "text",
               "crs": "text", "affine": "_float8", "width": "int4", "height": "int4",
               "nodata_value": "float8", "status": "text"},
    "coverage": {**_COMMON, "dataset_record_id": "text", "aoi_record_id": "text", "year": "int2",
                 "month": "int2", "target_grid_version": "text", "mask_policy_version": "text",
                 "measurement_status": "text", "aoi_land_area_ha": "float8", "valid_area_ha": "float8",
                 "invalid_area_ha": "float8", "newly_recovered_area_ha": "float8", "coverage_pct": "float8",
                 "valid_footprint": "geometry"},
    "experiments": {**_COMMON, "dataset_record_id": "text", "experiment_id": "text", "git_sha": "bpchar",
                    "random_seed": "int8", "training_executed": "bool", "status": "text",
                    "started_at": "timestamptz", "finished_at": "timestamptz"},
    "models": {**_COMMON, "experiment_record_id": "text", "model_id": "text", "model_version": "text",
               "checkpoint_asset_record_id": "text", "class_schema_id": "text",
               "independent_evaluation": "bool", "status": "text"},
    "predictions": {**_COMMON, "model_record_id": "text", "dataset_record_id": "text", "aoi_record_id": "text",
                    "result_id": "text", "year": "int2", "prediction_asset_record_id": "text",
                    "measured_predictions": "bool", "status": "text"},
    "approvals": {**_COMMON, "subject_type": "text", "subject_record_id": "text", "decision": "text",
                  "approved_by": "text", "reason": "text", "approved_at": "timestamptz"},
}

REQUIRED_CONSTRAINTS = frozenset({
    "pk_schema_migrations", "ck_schema_migrations_code_status",
    "pk_operational_records", "uq_operational_source", "ck_operational_source_kind", "ck_operational_payload_sha",
    *{f"pk_{table}" for table in ENTITY_TABLES},
    *{f"uq_{table}_source" for table in ENTITY_TABLES},
    *{f"ck_{table}_payload_sha" for table in ENTITY_TABLES},
    "ck_aois_area", "ck_aois_geometry_valid", "ck_scenes_cloud", "ck_scenes_footprint_valid",
    "fk_assets_dataset", "fk_assets_scene", "ck_assets_sha", "ck_assets_size", "ck_assets_width", "ck_assets_height",
    "fk_coverage_dataset", "fk_coverage_aoi", "ck_coverage_year", "ck_coverage_month", "ck_coverage_aoi_area",
    "ck_coverage_valid_area", "ck_coverage_invalid_area", "ck_coverage_recovered_area", "ck_coverage_pct",
    "ck_coverage_footprint_valid", "fk_experiments_dataset", "fk_models_experiment", "fk_models_checkpoint_asset",
    "fk_predictions_model", "fk_predictions_dataset", "fk_predictions_aoi", "fk_predictions_asset",
    "ck_predictions_year", "ck_approvals_decision",
})
REQUIRED_INDEXES = frozenset({
    "idx_0355_aoi_geometry", "idx_0355_scene_footprint", "idx_0355_scene_time", "idx_0355_asset_sha",
    "idx_0355_dataset_identity", "idx_0355_coverage_aoi_year_month", "idx_0355_coverage_footprint",
    "idx_0355_model_status", "idx_0355_model_identity", "idx_0355_prediction_aoi_year",
    "idx_0355_approval_subject",
})


def _constraint_contract() -> dict[str, tuple[str, tuple[str, ...]]]:
    contract: dict[str, tuple[str, tuple[str, ...]]] = {
        "pk_schema_migrations": ("p", ("version",)),
        "ck_schema_migrations_code_status": ("c", ("code_status",)),
        "pk_operational_records": ("p", ("record_id",)),
        "uq_operational_source": ("u", ("source_kind", "source_record_id")),
        "ck_operational_source_kind": ("c", ("source_kind",)),
        "ck_operational_payload_sha": ("c", ("source_payload_sha256",)),
    }
    for table in ENTITY_TABLES:
        contract[f"pk_{table}"] = ("p", ("record_id",))
        contract[f"uq_{table}_source"] = ("u", ("source_kind", "source_record_id"))
        contract[f"ck_{table}_payload_sha"] = ("c", ("source_payload_sha256",))
    contract.update({
        "ck_aois_area": ("c", ("area_ha",)), "ck_aois_geometry_valid": ("c", ("geometry",)),
        "ck_scenes_cloud": ("c", ("scene_cloud_pct",)), "ck_scenes_footprint_valid": ("c", ("footprint",)),
        "fk_assets_dataset": ("f", ("dataset_record_id", "datasets")),
        "fk_assets_scene": ("f", ("scene_record_id", "scenes")), "ck_assets_sha": ("c", ("sha256",)),
        "ck_assets_size": ("c", ("size_bytes",)), "ck_assets_width": ("c", ("width",)),
        "ck_assets_height": ("c", ("height",)),
        "fk_coverage_dataset": ("f", ("dataset_record_id", "datasets")),
        "fk_coverage_aoi": ("f", ("aoi_record_id", "aois")), "ck_coverage_year": ("c", ("year",)),
        "ck_coverage_month": ("c", ("month",)), "ck_coverage_aoi_area": ("c", ("aoi_land_area_ha",)),
        "ck_coverage_valid_area": ("c", ("valid_area_ha",)),
        "ck_coverage_invalid_area": ("c", ("invalid_area_ha",)),
        "ck_coverage_recovered_area": ("c", ("newly_recovered_area_ha",)),
        "ck_coverage_pct": ("c", ("coverage_pct",)),
        "ck_coverage_footprint_valid": ("c", ("valid_footprint",)),
        "fk_experiments_dataset": ("f", ("dataset_record_id", "datasets")),
        "fk_models_experiment": ("f", ("experiment_record_id", "experiments")),
        "fk_models_checkpoint_asset": ("f", ("checkpoint_asset_record_id", "assets")),
        "fk_predictions_model": ("f", ("model_record_id", "models")),
        "fk_predictions_dataset": ("f", ("dataset_record_id", "datasets")),
        "fk_predictions_aoi": ("f", ("aoi_record_id", "aois")),
        "fk_predictions_asset": ("f", ("prediction_asset_record_id", "assets")),
        "ck_predictions_year": ("c", ("year",)), "ck_approvals_decision": ("c", ("decision",)),
    })
    return contract


EXPECTED_CONSTRAINT_CONTRACT = _constraint_contract()
EXPECTED_INDEX_MARKERS: Mapping[str, tuple[str, ...]] = {
    "idx_0355_aoi_geometry": ("aois", "using gist", "geometry"),
    "idx_0355_scene_footprint": ("scenes", "using gist", "footprint"),
    "idx_0355_scene_time": ("scenes", "acquisition_timestamp"),
    "idx_0355_asset_sha": ("assets", "sha256"),
    "idx_0355_dataset_identity": ("unique", "datasets", "dataset_id", "dataset_version"),
    "idx_0355_coverage_aoi_year_month": ("coverage", "aoi_record_id", "year", "month"),
    "idx_0355_coverage_footprint": ("coverage", "using gist", "valid_footprint"),
    "idx_0355_model_status": ("models", "status"),
    "idx_0355_model_identity": ("unique", "models", "model_id", "model_version"),
    "idx_0355_prediction_aoi_year": ("predictions", "aoi_record_id", "year"),
    "idx_0355_approval_subject": ("approvals", "subject_type", "subject_record_id"),
}
EXPECTED_GEOMETRIES = frozenset({
    ("aois", "geometry", "MULTIPOLYGON", 4326),
    ("scenes", "footprint", "MULTIPOLYGON", 4326),
    ("coverage", "valid_footprint", "MULTIPOLYGON", 4326),
})


class PostGISContractError(RuntimeError):
    """The connected database does not satisfy the pinned pilot contract."""


@dataclass(frozen=True)
class SchemaHealth:
    status: str
    contract_matches: bool
    schema_version: str | None
    migration_code_status: str | None
    postgis_version: str | None
    missing_tables: tuple[str, ...]
    column_issues: tuple[str, ...]
    constraint_issues: tuple[str, ...]
    geometry_issues: tuple[str, ...]
    index_issues: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """Compatibility only; writable application cutover remains blocked."""
        return self.contract_matches

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _postgis_major(version: str | None) -> int | None:
    try:
        return int(str(version).split(".", 1)[0]) if version else None
    except (TypeError, ValueError):
        return None


def evaluate_schema_inventory(
    *, schema_version: str | None, postgis_version: str | None, tables: Iterable[str],
    migration_code_status: str | None = None,
    columns: Mapping[str, Mapping[str, str]] | None = None,
    constraints: Mapping[str, tuple[str, str]] | None = None,
    indexes: Mapping[str, str] | None = None,
    geometries: Iterable[tuple[str, str, str, int]] | None = None,
) -> SchemaHealth:
    present = frozenset(str(item) for item in tables)
    missing = tuple(sorted(set(EXPECTED_COLUMNS) - present))
    issues: list[str] = []
    if schema_version != SCHEMA_VERSION:
        issues.append("SCHEMA_VERSION_MISMATCH")
    if migration_code_status != MIGRATION_CODE_STATUS:
        issues.append("MIGRATION_STATUS_MISMATCH")
    major = _postgis_major(postgis_version)
    if major is None:
        issues.append("POSTGIS_EXTENSION_UNVERIFIED")
    elif major < MIN_POSTGIS_MAJOR:
        issues.append("POSTGIS_VERSION_UNSUPPORTED")
    if missing:
        issues.append("REQUIRED_TABLES_MISSING")

    actual_columns = columns or {}
    column_issues = []
    for table, expected in EXPECTED_COLUMNS.items():
        actual = dict(actual_columns.get(table, {}))
        if actual != dict(expected):
            missing_columns = sorted(set(expected) - set(actual))
            extra_columns = sorted(set(actual) - set(expected))
            wrong_types = sorted(name for name in set(expected) & set(actual) if expected[name] != actual[name])
            column_issues.append(f"{table}:missing={missing_columns};extra={extra_columns};types={wrong_types}")
    if column_issues:
        issues.append("COLUMN_CONTRACT_MISMATCH")

    actual_constraints = constraints or {}
    constraint_problem_list: list[str] = []
    for name, (expected_type, markers) in EXPECTED_CONSTRAINT_CONTRACT.items():
        actual = actual_constraints.get(name)
        if actual is None:
            constraint_problem_list.append(name + ":missing")
            continue
        actual_type, definition = actual
        normalized = " ".join(str(definition).lower().replace('"', "").split())
        if str(actual_type) != expected_type or any(marker not in normalized for marker in markers):
            constraint_problem_list.append(name + ":definition")
    constraint_issues = tuple(sorted(constraint_problem_list))
    if constraint_issues:
        issues.append("CONSTRAINT_CONTRACT_MISMATCH")
    actual_indexes = indexes or {}
    index_problem_list: list[str] = []
    for name, markers in EXPECTED_INDEX_MARKERS.items():
        definition = actual_indexes.get(name)
        if definition is None:
            index_problem_list.append(name + ":missing")
            continue
        normalized = " ".join(str(definition).lower().replace('"', "").split())
        if any(marker not in normalized for marker in markers):
            index_problem_list.append(name + ":definition")
    index_issues = tuple(sorted(index_problem_list))
    if index_issues:
        issues.append("INDEX_CONTRACT_MISMATCH")
    actual_geometries = frozenset((str(a), str(b), str(c).upper(), int(d)) for a, b, c, d in (geometries or ()))
    geometry_issues = tuple(sorted(
        f"{table}.{column}:{geometry_type}:{srid}"
        for table, column, geometry_type, srid in EXPECTED_GEOMETRIES - actual_geometries
    ))
    if geometry_issues:
        issues.append("GEOMETRY_CONTRACT_MISMATCH")

    matches = not issues
    return SchemaHealth(
        status="IMPLEMENTED_UNVERIFIED" if matches else "BLOCKED", contract_matches=matches,
        schema_version=schema_version, migration_code_status=migration_code_status,
        postgis_version=postgis_version, missing_tables=missing,
        column_issues=tuple(column_issues), constraint_issues=constraint_issues,
        geometry_issues=geometry_issues, index_issues=index_issues, issues=tuple(issues),
    )


def inspect_connection(connection: Any) -> SchemaHealth:
    """Read complete schema metadata. No DDL/DML is issued."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
        postgis_row = cursor.fetchone()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s", (SCHEMA_NAME,))
        table_names = tuple(str(row[0]) for row in cursor.fetchall())
        version_row = None
        if "schema_migrations" in table_names:
            cursor.execute(
                "SELECT version, code_status FROM geoai_registry.schema_migrations WHERE version = %s",
                (SCHEMA_VERSION,),
            )
            version_row = cursor.fetchone()
        cursor.execute(
            "SELECT table_name, column_name, udt_name FROM information_schema.columns "
            "WHERE table_schema = %s ORDER BY table_name, ordinal_position", (SCHEMA_NAME,),
        )
        columns: dict[str, dict[str, str]] = {}
        for table, column, udt_name in cursor.fetchall():
            columns.setdefault(str(table), {})[str(column)] = str(udt_name)
        cursor.execute(
            "SELECT con.conname, con.contype, pg_get_constraintdef(con.oid) FROM pg_constraint con "
            "JOIN pg_class c ON c.oid = con.conrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s", (SCHEMA_NAME,),
        )
        constraints = {str(name): (str(kind), str(definition)) for name, kind, definition in cursor.fetchall()}
        cursor.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s", (SCHEMA_NAME,))
        indexes = {str(name): str(definition) for name, definition in cursor.fetchall()}
        cursor.execute(
            "SELECT f_table_name, f_geometry_column, type, srid FROM public.geometry_columns "
            "WHERE f_table_schema = %s", (SCHEMA_NAME,),
        )
        geometries = tuple((str(a), str(b), str(c), int(d)) for a, b, c, d in cursor.fetchall())
    return evaluate_schema_inventory(
        schema_version=str(version_row[0]) if version_row else None,
        migration_code_status=str(version_row[1]) if version_row else None,
        postgis_version=str(postgis_row[0]) if postgis_row else None,
        tables=table_names, columns=columns, constraints=constraints, indexes=indexes, geometries=geometries,
    )


def require_healthy_schema(connection: Any) -> SchemaHealth:
    health = inspect_connection(connection)
    if not health.contract_matches:
        raise PostGISContractError("POSTGIS_SCHEMA_NOT_READY:" + (",".join(health.issues) or "UNKNOWN"))
    return health


def entity_for_kind(kind: str) -> str:
    try:
        return KIND_TO_ENTITY[kind]
    except KeyError:
        raise PostGISContractError(f"POSTGIS_KIND_NOT_MAPPED:{kind}") from None


def record_key(kind: str, identifier: str) -> str:
    return hashlib.sha256(f"{kind}\0{identifier}".encode("utf-8")).hexdigest()


def schema_contract() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA_NAME, "version": SCHEMA_VERSION,
        "minimum_postgis_major": MIN_POSTGIS_MAJOR,
        "entity_tables": list(ENTITY_TABLES), "support_tables": list(SUPPORT_TABLES),
        "status": "IMPLEMENTED_UNVERIFIED",
        "writable_cutover": "BLOCKED_TYPED_MAPPING_AND_TRANSACTION_API_MISSING",
        "real_database_migration": "BLOCKED",
    }
