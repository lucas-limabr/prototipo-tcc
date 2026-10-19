from contextlib import contextmanager
from unittest.mock import patch

import pytest

from index_optimizer.config import Settings
from index_optimizer.database.index_apply import _index_name
from index_optimizer.database.index_cleanup import (
    EXPERIMENTAL_INDEXES_QUERY,
    CleanupResult,
    _find_experimental_indexes,
    cleanup_experimental_indexes,
)
from index_optimizer.errors import IndexApplicationError


def _settings(environment="lab", host="localhost"):
    return Settings(
        db_name="index_lab",
        db_user="index_lab_user",
        db_password="secret",
        db_host=host,
        environment=environment,
        allowed_schemas=("cnpj",),
    )


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def transaction(self):
        return FakeTransaction()

    def execute(self, query, params=None):
        self.calls.append((query, params))
        if params is not None:
            return FakeResult(self.rows)
        return FakeResult([])


def _row(
    *,
    table="empresa",
    column="cnpj_basico",
    name=None,
    method="btree",
    primary=False,
    unique=False,
    exclusion=False,
    replica_identity=False,
    clustered=False,
    columns=1,
    key_columns=1,
    expressions=False,
    predicate=False,
):
    return (
        "cnpj",
        table,
        name or _index_name(table, column),
        column,
        method,
        primary,
        unique,
        exclusion,
        replica_identity,
        clustered,
        columns,
        key_columns,
        not expressions,
        not predicate,
    )


def test_selection_requires_prototype_name_and_simple_non_structural_btree():
    rows = [
        _row(),
        _row(name="ixo_manual_idx"),
        _row(unique=True),
        _row(primary=True),
        _row(method="hash"),
        _row(columns=2),
        _row(expressions=True),
        _row(clustered=True),
    ]
    connection = FakeConnection(rows)

    selected = _find_experimental_indexes(connection, ("cnpj",))

    assert [item.name for item in selected] == [_index_name("empresa", "cnpj_basico")]
    assert "ixo\\_%" in EXPERIMENTAL_INDEXES_QUERY
    assert "indisprimary = false" in EXPERIMENTAL_INDEXES_QUERY


def test_cleanup_requires_confirmation_and_local_lab():
    with pytest.raises(IndexApplicationError, match="experimental-indexes"):
        cleanup_experimental_indexes(_settings())
    with pytest.raises(IndexApplicationError, match="laboratório local"):
        cleanup_experimental_indexes(_settings(environment="production"), experimental_indexes=True)
    with pytest.raises(IndexApplicationError, match="laboratório local"):
        cleanup_experimental_indexes(_settings(host="db"), experimental_indexes=True)


def test_cleanup_is_transactional_and_uses_delimited_identifiers():
    row = _row()
    connection = FakeConnection([row])

    @contextmanager
    def fake_connect(_settings):
        yield connection

    with patch("index_optimizer.database.index_cleanup.connect", fake_connect):
        result = cleanup_experimental_indexes(_settings(), experimental_indexes=True)

    assert isinstance(result, CleanupResult)
    assert result.removed_count == 1
    assert connection.calls[0][0] == "SET TRANSACTION READ WRITE"
    drop_statement = connection.calls[2][0]
    rendered = drop_statement.as_string(None)
    assert rendered == 'DROP INDEX "cnpj"."ixo_empresa_cnpj_basico_idx_adc44be5"'


def test_cleanup_delimits_schema_identifier_without_sql_injection():
    unsafe_schema = 'cnpj"; DROP SCHEMA public; --'
    connection = FakeConnection(
        [
            (
                unsafe_schema,
                "empresa",
                _index_name("empresa", "cnpj_basico"),
                "cnpj_basico",
                "btree",
                False,
                False,
                False,
                False,
                False,
                1,
                1,
                True,
                True,
            )
        ]
    )

    @contextmanager
    def fake_connect(_settings):
        yield connection

    with patch("index_optimizer.database.index_cleanup.connect", fake_connect):
        cleanup_experimental_indexes(_settings(), experimental_indexes=True)

    rendered = connection.calls[2][0].as_string(None)
    assert rendered.startswith('DROP INDEX "cnpj""; DROP SCHEMA public; --".')
    assert rendered.count("DROP SCHEMA") == 1


def test_cleanup_succeeds_with_no_eligible_indexes():
    connection = FakeConnection([])

    @contextmanager
    def fake_connect(_settings):
        yield connection

    with patch("index_optimizer.database.index_cleanup.connect", fake_connect):
        result = cleanup_experimental_indexes(_settings(), experimental_indexes=True)

    assert result == CleanupResult(removed_indexes=())
    assert result.removed_count == 0
