import pytest

from index_optimizer.database.query_validation import validate_read_query
from index_optimizer.errors import UnsupportedQueryError


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "WITH rows AS (SELECT 1 AS value) SELECT value FROM rows",
        "SELECT * FROM cnpj.empresa WHERE cnpj_basico = '1'",
    ],
)
def test_accepts_read_queries(sql):
    assert validate_read_query(sql).sql


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "SELECT 1; SELECT 2",
        "INSERT INTO empresa VALUES (1)",
        "SELECT * INTO outra FROM empresa",
        "SELECT * FROM empresa FOR UPDATE",
        "SELECT pg_sleep(1)",
        "SELECT * FROM other_schema.empresa",
    ],
)
def test_rejects_unsafe_queries(sql):
    schemas = {"cnpj"} if "other_schema" in sql else None
    with pytest.raises(UnsupportedQueryError):
        validate_read_query(sql, allowed_schemas=schemas)


def test_rejects_invalid_sql():
    with pytest.raises(UnsupportedQueryError, match="SQL inválido"):
        validate_read_query("SELECT FROM")
