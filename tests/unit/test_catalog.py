from index_optimizer.database.catalog import (
    COLUMNS_QUERY,
    CONSTRAINTS_QUERY,
    INDEXES_QUERY,
    SCHEMAS_QUERY,
    TABLES_QUERY,
    inspect_catalog,
)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))
        return FakeResult(next(self.results))


def test_inspect_catalog_transforms_metadata_and_filters_by_allowed_schemas():
    conn = FakeConnection(
        [
            [("cnpj",)],
            [("cnpj", "empresa", "BASE TABLE")],
            [("cnpj", "empresa", 1, "cnpj_basico", "character", "bpchar", "NO", None)],
            [("cnpj", "empresa", "empresa_pkey", "PRIMARY KEY", "PRIMARY KEY (cnpj_basico)")],
            [
                (
                    "cnpj",
                    "empresa",
                    "empresa_pkey",
                    "CREATE UNIQUE INDEX empresa_pkey ON cnpj.empresa USING btree (cnpj_basico)",
                )
            ],
        ]
    )

    catalog = inspect_catalog(conn, ("cnpj",))

    assert catalog.schemas[0].name == "cnpj"
    assert catalog.tables[0].name == "empresa"
    assert catalog.columns[0].nullable is False
    assert catalog.constraints[0].constraint_type == "PRIMARY KEY"
    assert catalog.indexes[0].name == "empresa_pkey"
    assert all(params == (["cnpj"],) for _, params in conn.calls)


def test_inspect_catalog_rejects_empty_schema_scope():
    conn = FakeConnection([])

    try:
        inspect_catalog(conn, ())
    except ValueError as exc:
        assert "não pode ser vazio" in str(exc)
    else:
        raise AssertionError("empty schema scope should fail")


def test_catalog_queries_are_read_only_metadata_queries():
    queries = (SCHEMAS_QUERY, TABLES_QUERY, COLUMNS_QUERY, CONSTRAINTS_QUERY, INDEXES_QUERY)

    assert all(
        not query.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "DROP", "ALTER"))
        for query in queries
    )
