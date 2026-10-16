from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg import sql

from index_optimizer.config import Settings
from index_optimizer.database.catalog import Catalog, inspect_catalog
from index_optimizer.database.connection import connect
from index_optimizer.database.recommendations import (
    IndexRecommendation,
    RecommendationStatus,
)
from index_optimizer.errors import IndexApplicationError, UnsupportedQueryError

MAX_IDENTIFIER_LENGTH = 63
_SAFE_NAME = re.compile(r"[^a-z0-9_]+")


@dataclass(frozen=True)
class IndexDDL:
    schema: str
    table: str
    column: str
    name: str
    statement: sql.Composable


@dataclass(frozen=True)
class IndexApplyResult:
    ddl: IndexDDL
    status: str
    created_at: datetime
    message: str


def generate_index_ddl(recommendation: IndexRecommendation) -> IndexDDL | None:
    if recommendation.status is not RecommendationStatus.RECOMMENDED:
        return None
    if recommendation.access_method != "btree" or len(recommendation.columns) != 1:
        raise UnsupportedQueryError("Somente índices B-tree simples são suportados.")
    schema, table, column = recommendation.schema, recommendation.table, recommendation.columns[0]
    name = _index_name(table, column)
    statement = sql.SQL("CREATE INDEX {name} ON {schema}.{table} USING btree ({column})").format(
        name=sql.Identifier(name),
        schema=sql.Identifier(schema),
        table=sql.Identifier(table),
        column=sql.Identifier(column),
    )
    return IndexDDL(schema=schema, table=table, column=column, name=name, statement=statement)


def render_ddl(ddl: IndexDDL, connection: psycopg.Connection[Any]) -> str:
    return ddl.statement.as_string(connection)


def dry_run(recommendations: tuple[IndexRecommendation, ...]) -> tuple[IndexDDL, ...]:
    return tuple(
        ddl
        for recommendation in recommendations
        if (ddl := generate_index_ddl(recommendation)) is not None
    )


def apply_indexes(
    settings: Settings,
    recommendations: tuple[IndexRecommendation, ...],
    *,
    apply: bool = False,
) -> tuple[IndexApplyResult, ...]:
    if not apply:
        raise IndexApplicationError("Aplicação bloqueada: use apply=True após revisar o dry run.")
    if not settings.is_lab:
        raise IndexApplicationError(
            "Aplicação de índices permitida somente no ambiente de laboratório."
        )

    results: list[IndexApplyResult] = []
    for recommendation in recommendations:
        ddl = generate_index_ddl(recommendation)
        if ddl is None:
            continue
        results.append(_apply_one(settings, ddl))
    return tuple(results)


def _apply_one(settings: Settings, ddl: IndexDDL) -> IndexApplyResult:
    created_at = datetime.now(UTC)
    try:
        with connect(settings) as conn, conn.transaction():
            conn.execute("SET TRANSACTION READ WRITE")
            catalog = inspect_catalog(conn, settings.allowed_schemas)
            if _equivalent_exists(catalog, ddl):
                return IndexApplyResult(
                    ddl,
                    "SKIPPED_EXISTING",
                    created_at,
                    "Índice equivalente já existe.",
                )
            conn.execute(
                sql.SQL("CREATE INDEX {name} ON {schema}.{table} USING btree ({column})").format(
                    name=sql.Identifier(ddl.name),
                    schema=sql.Identifier(ddl.schema),
                    table=sql.Identifier(ddl.table),
                    column=sql.Identifier(ddl.column),
                )
            )
            conn.execute(
                sql.SQL("ANALYZE {schema}.{table}").format(
                    schema=sql.Identifier(ddl.schema),
                    table=sql.Identifier(ddl.table),
                )
            )
    except psycopg.Error as exc:
        return IndexApplyResult(ddl, "FAILED", created_at, str(exc))
    return IndexApplyResult(ddl, "CREATED", created_at, "Índice criado e tabela analisada.")


def _equivalent_exists(catalog: Catalog, ddl: IndexDDL) -> bool:
    for index in catalog.indexes:
        if index.schema != ddl.schema or index.table != ddl.table:
            continue
        if re.search(rf"\(\s*\"?{re.escape(ddl.column)}\"?\s*\)", index.definition):
            return True
    return False


def _index_name(table: str, column: str) -> str:
    base = _SAFE_NAME.sub("_", f"ixo_{table}_{column}_idx".lower()).strip("_")
    digest = hashlib.sha256(base.encode()).hexdigest()[:8]
    return f"{base[: MAX_IDENTIFIER_LENGTH - 9]}_{digest}"
