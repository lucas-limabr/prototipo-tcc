from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg

from index_optimizer.config import Settings
from index_optimizer.database.connection import connect

SCHEMAS_QUERY = """
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = ANY(%s)
ORDER BY schema_name
"""

TABLES_QUERY = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema = ANY(%s)
ORDER BY table_schema, table_name
"""

COLUMNS_QUERY = """
SELECT table_schema, table_name, ordinal_position, column_name,
       data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = ANY(%s)
ORDER BY table_schema, table_name, ordinal_position
"""

CONSTRAINTS_QUERY = """
SELECT
    n.nspname AS schema_name,
    cls.relname AS table_name,
    con.conname AS constraint_name,
    CASE con.contype
        WHEN 'p' THEN 'PRIMARY KEY'
        WHEN 'f' THEN 'FOREIGN KEY'
        WHEN 'u' THEN 'UNIQUE'
        WHEN 'c' THEN 'CHECK'
        WHEN 'x' THEN 'EXCLUSION'
        ELSE con.contype::text
    END AS constraint_type,
    pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class cls ON cls.oid = con.conrelid
JOIN pg_namespace n ON n.oid = cls.relnamespace
WHERE n.nspname = ANY(%s)
ORDER BY n.nspname, cls.relname, con.conname
"""

INDEXES_QUERY = """
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = ANY(%s)
ORDER BY schemaname, tablename, indexname
"""


@dataclass(frozen=True)
class SchemaInfo:
    name: str


@dataclass(frozen=True)
class TableInfo:
    schema: str
    name: str
    table_type: str


@dataclass(frozen=True)
class ColumnInfo:
    schema: str
    table: str
    ordinal_position: int
    name: str
    data_type: str
    udt_name: str
    nullable: bool
    default: str | None


@dataclass(frozen=True)
class ConstraintInfo:
    schema: str
    table: str
    name: str
    constraint_type: str
    definition: str


@dataclass(frozen=True)
class IndexInfo:
    schema: str
    table: str
    name: str
    definition: str


@dataclass(frozen=True)
class Catalog:
    schemas: tuple[SchemaInfo, ...]
    tables: tuple[TableInfo, ...]
    columns: tuple[ColumnInfo, ...]
    constraints: tuple[ConstraintInfo, ...]
    indexes: tuple[IndexInfo, ...]


def _rows(conn: psycopg.Connection[Any], query: str, schemas: tuple[str, ...]) -> list[Any]:
    return conn.execute(query, (list(schemas),)).fetchall()


def inspect_catalog(conn: psycopg.Connection[Any], allowed_schemas: tuple[str, ...]) -> Catalog:
    """Read catalog metadata without changing database state."""
    if not allowed_schemas:
        raise ValueError("allowed_schemas não pode ser vazio.")

    schema_rows = _rows(conn, SCHEMAS_QUERY, allowed_schemas)
    table_rows = _rows(conn, TABLES_QUERY, allowed_schemas)
    column_rows = _rows(conn, COLUMNS_QUERY, allowed_schemas)
    constraint_rows = _rows(conn, CONSTRAINTS_QUERY, allowed_schemas)
    index_rows = _rows(conn, INDEXES_QUERY, allowed_schemas)

    return Catalog(
        schemas=tuple(SchemaInfo(name=row[0]) for row in schema_rows),
        tables=tuple(
            TableInfo(schema=row[0], name=row[1], table_type=row[2]) for row in table_rows
        ),
        columns=tuple(
            ColumnInfo(
                schema=row[0],
                table=row[1],
                ordinal_position=row[2],
                name=row[3],
                data_type=row[4],
                udt_name=row[5],
                nullable=row[6] == "YES",
                default=row[7],
            )
            for row in column_rows
        ),
        constraints=tuple(
            ConstraintInfo(
                schema=row[0],
                table=row[1],
                name=row[2],
                constraint_type=row[3],
                definition=row[4],
            )
            for row in constraint_rows
        ),
        indexes=tuple(
            IndexInfo(schema=row[0], table=row[1], name=row[2], definition=row[3])
            for row in index_rows
        ),
    )


def inspect_database_catalog(settings: Settings) -> Catalog:
    with connect(settings) as conn, conn.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        return inspect_catalog(conn, settings.allowed_schemas)
