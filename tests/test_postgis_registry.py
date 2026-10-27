from app.postgis_registry import (
    ENTITY_TABLES, EXPECTED_COLUMNS, EXPECTED_CONSTRAINT_CONTRACT, EXPECTED_GEOMETRIES,
    EXPECTED_INDEX_MARKERS, MIGRATION_CODE_STATUS, SUPPORT_TABLES, PostGISContractError,
    entity_for_kind, evaluate_schema_inventory, inspect_connection, record_key,
)


def _healthy_inventory(**overrides):
    values = {
        "schema_version": "0355", "migration_code_status": MIGRATION_CODE_STATUS,
        "postgis_version": "3.4.2", "tables": set(ENTITY_TABLES) | set(SUPPORT_TABLES),
        "columns": EXPECTED_COLUMNS,
        "constraints": {name: (kind, " ".join(markers)) for name, (kind, markers) in EXPECTED_CONSTRAINT_CONTRACT.items()},
        "indexes": {name: " ".join(markers) for name, markers in EXPECTED_INDEX_MARKERS.items()},
        "geometries": EXPECTED_GEOMETRIES,
    }
    values.update(overrides)
    return evaluate_schema_inventory(**values)


def test_schema_inventory_requires_the_complete_contract():
    health = _healthy_inventory()
    assert health.contract_matches is True
    assert health.status == "IMPLEMENTED_UNVERIFIED"
    assert health.issues == ()


def test_schema_inventory_fails_closed_on_each_structural_surface():
    columns = {table: dict(items) for table, items in EXPECTED_COLUMNS.items()}
    columns["assets"]["size_bytes"] = "text"
    constraints = {name: (kind, " ".join(markers)) for name, (kind, markers) in EXPECTED_CONSTRAINT_CONTRACT.items()}
    constraints.pop("fk_assets_dataset")
    constraints["ck_assets_size"] = ("c", "width")
    indexes = {name: " ".join(markers) for name, markers in EXPECTED_INDEX_MARKERS.items()}
    indexes.pop("idx_0355_asset_sha")
    indexes["idx_0355_model_status"] = "models model_version"
    health = _healthy_inventory(
        schema_version="0354", migration_code_status="VERIFIED_REAL", postgis_version="2.5",
        tables={"datasets"}, columns=columns,
        constraints=constraints, indexes=indexes,
        geometries=set(),
    )
    assert health.status == "BLOCKED"
    assert set(health.issues) == {
        "SCHEMA_VERSION_MISMATCH", "MIGRATION_STATUS_MISMATCH", "POSTGIS_VERSION_UNSUPPORTED",
        "REQUIRED_TABLES_MISSING", "COLUMN_CONTRACT_MISMATCH", "CONSTRAINT_CONTRACT_MISMATCH",
        "INDEX_CONTRACT_MISMATCH", "GEOMETRY_CONTRACT_MISMATCH",
    }


class _Cursor:
    def __init__(self): self.rows = []
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def execute(self, sql, _parameters=None):
        if "pg_extension" in sql: self.rows = [("3.4.2",)]
        elif "information_schema.tables" in sql: self.rows = [(x,) for x in EXPECTED_COLUMNS]
        elif "schema_migrations WHERE" in sql: self.rows = [("0355", MIGRATION_CODE_STATUS)]
        elif "information_schema.columns" in sql:
            self.rows = [(t, c, typ) for t, cols in EXPECTED_COLUMNS.items() for c, typ in cols.items()]
        elif "pg_constraint" in sql:
            self.rows = [(name, kind, " ".join(markers)) for name, (kind, markers) in EXPECTED_CONSTRAINT_CONTRACT.items()]
        elif "pg_indexes" in sql: self.rows = [(name, " ".join(markers)) for name, markers in EXPECTED_INDEX_MARKERS.items()]
        elif "geometry_columns" in sql: self.rows = list(EXPECTED_GEOMETRIES)
        else: self.rows = []
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return list(self.rows)


class _Connection:
    def cursor(self): return _Cursor()


def test_connection_inspection_is_select_only_and_checks_full_inventory():
    health = inspect_connection(_Connection())
    assert health.contract_matches is True
    assert health.status == "IMPLEMENTED_UNVERIFIED"


def test_kind_mapping_and_record_key_are_explicit():
    assert entity_for_kind("dataset_versions") == "datasets"
    try:
        entity_for_kind("arbitrary-json-kind")
    except PostGISContractError as exc:
        assert str(exc) == "POSTGIS_KIND_NOT_MAPPED:arbitrary-json-kind"
        assert exc.__suppress_context__ is True
    else:
        raise AssertionError("unknown kind was accepted")
    assert record_key("datasets", "same") != record_key("dataset_versions", "same")
