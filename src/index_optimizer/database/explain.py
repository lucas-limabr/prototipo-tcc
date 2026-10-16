from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg

from index_optimizer.config import Settings
from index_optimizer.database.connection import connect
from index_optimizer.database.query_validation import validate_read_query
from index_optimizer.errors import QueryTimeoutError


@dataclass(frozen=True)
class EstimatedPlan:
    sql: str
    plan: Any
    raw: Any


def explain_query(
    settings: Settings,
    sql: str,
    *,
    allowed_schemas: set[str] | None = None,
) -> EstimatedPlan:
    validated = validate_read_query(sql, allowed_schemas=allowed_schemas)
    explain_sql = f"EXPLAIN (FORMAT JSON) {validated.sql}"
    try:
        with connect(settings) as conn, conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            row = conn.execute(explain_sql).fetchone()
    except psycopg.errors.QueryCanceled as exc:
        raise QueryTimeoutError("O PostgreSQL cancelou o EXPLAIN por timeout.") from exc
    if row is None or not row[0]:
        raise RuntimeError("O PostgreSQL não retornou um plano para o EXPLAIN.")
    raw = row[0]
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise RuntimeError("Resposta inesperada de EXPLAIN (FORMAT JSON).")
    plan = raw[0].get("Plan")
    if not isinstance(plan, dict):
        raise RuntimeError("O plano JSON não contém o objeto Plan.")
    return EstimatedPlan(sql=validated.sql, plan=plan, raw=raw)
