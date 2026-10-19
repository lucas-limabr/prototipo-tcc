from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import sql

from index_optimizer.config import Settings
from index_optimizer.database.connection import connect
from index_optimizer.database.index_apply import _index_name
from index_optimizer.errors import IndexApplicationError

EXPERIMENTAL_INDEXES_QUERY = r"""
SELECT
    namespace.nspname AS schema_name,
    table_class.relname AS table_name,
    index_class.relname AS index_name,
    attribute.attname AS column_name,
    access_method.amname AS access_method,
    index_info.indisprimary,
    index_info.indisunique,
    index_info.indisexclusion,
    index_info.indisreplident,
    index_info.indisclustered,
    index_info.indnatts,
    index_info.indnkeyatts,
    index_info.indexprs IS NULL AS has_no_expressions,
    index_info.indpred IS NULL AS has_no_predicate
FROM pg_index AS index_info
JOIN pg_class AS index_class ON index_class.oid = index_info.indexrelid
JOIN pg_class AS table_class ON table_class.oid = index_info.indrelid
JOIN pg_namespace AS namespace ON namespace.oid = table_class.relnamespace
JOIN pg_am AS access_method ON access_method.oid = index_class.relam
JOIN pg_attribute AS attribute
  ON attribute.attrelid = table_class.oid
 AND attribute.attnum = index_info.indkey[0]
WHERE namespace.nspname = ANY(%s)
  AND index_class.relkind = 'i'
  AND table_class.relkind IN ('r', 'p')
  AND index_class.relname LIKE 'ixo\_%' ESCAPE '\'
  AND access_method.amname = 'btree'
  AND index_info.indisprimary = false
  AND index_info.indisunique = false
  AND index_info.indisexclusion = false
  AND index_info.indisreplident = false
  AND index_info.indisclustered = false
  AND index_info.indnatts = 1
  AND index_info.indnkeyatts = 1
  AND index_info.indkey[0] > 0
  AND index_info.indexprs IS NULL
  AND index_info.indpred IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM pg_constraint AS constraint_info
      WHERE constraint_info.conindid = index_class.oid
  )
ORDER BY namespace.nspname, table_class.relname, index_class.relname
"""


@dataclass(frozen=True)
class ExperimentalIndex:
    """An index that is safe to consider for prototype cleanup."""

    schema: str
    table: str
    name: str
    column: str
    access_method: str


@dataclass(frozen=True)
class CleanupResult:
    """Result of one transactional experimental-index cleanup."""

    removed_indexes: tuple[ExperimentalIndex, ...]

    @property
    def removed_count(self) -> int:
        return len(self.removed_indexes)


def cleanup_experimental_indexes(
    settings: Settings,
    *,
    experimental_indexes: bool = False,
) -> CleanupResult:
    """Remove only prototype indexes after explicit lab authorization."""
    if not experimental_indexes:
        raise IndexApplicationError(
            "Limpeza bloqueada: use --experimental-indexes para confirmar a ação."
        )
    if not settings.is_lab:
        raise IndexApplicationError(
            "Limpeza de índices experimentais permitida somente no ambiente de laboratório local."
        )

    try:
        with connect(settings) as connection, connection.transaction():
            connection.execute("SET TRANSACTION READ WRITE")
            candidates = _find_experimental_indexes(connection, settings.allowed_schemas)
            for index in candidates:
                connection.execute(
                    sql.SQL("DROP INDEX {index}").format(
                        index=sql.Identifier(index.schema, index.name),
                    )
                )
    except psycopg.Error as exc:
        raise IndexApplicationError(f"Falha ao remover índices experimentais: {exc}") from exc
    return CleanupResult(removed_indexes=candidates)


def _find_experimental_indexes(
    connection: psycopg.Connection[Any],
    allowed_schemas: tuple[str, ...],
) -> tuple[ExperimentalIndex, ...]:
    rows = connection.execute(EXPERIMENTAL_INDEXES_QUERY, (list(allowed_schemas),)).fetchall()
    return tuple(candidate for row in rows if (candidate := _candidate_from_row(row)) is not None)


def _candidate_from_row(row: tuple[Any, ...]) -> ExperimentalIndex | None:
    (
        schema,
        table,
        name,
        column,
        access_method,
        is_primary,
        is_unique,
        is_exclusion,
        is_replica_identity,
        is_clustered,
        number_of_columns,
        number_of_key_columns,
        has_no_expressions,
        has_no_predicate,
    ) = row
    if (
        not isinstance(schema, str)
        or not isinstance(table, str)
        or not isinstance(name, str)
        or not isinstance(column, str)
        or not name.startswith("ixo_")
        or access_method != "btree"
        or is_primary
        or is_unique
        or is_exclusion
        or is_replica_identity
        or is_clustered
        or number_of_columns != 1
        or number_of_key_columns != 1
        or not has_no_expressions
        or not has_no_predicate
        or name != _index_name(table, column)
    ):
        return None
    return ExperimentalIndex(
        schema=schema,
        table=table,
        name=name,
        column=column,
        access_method=access_method,
    )


# Short alias for callers that do not need to repeat the safety qualifier.
cleanup_indexes = cleanup_experimental_indexes
