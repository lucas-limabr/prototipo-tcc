from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

import psycopg

from index_optimizer.config import Settings
from index_optimizer.database.connection import connect
from index_optimizer.database.query_validation import validate_read_query
from index_optimizer.errors import QueryTimeoutError, UnsupportedQueryError


@dataclass(frozen=True)
class Measurement:
    run: int
    server_time_ms: float
    planning_time_ms: float | None
    execution_time_ms: float | None
    rows: float | None
    buffers: dict[str, Any]


@dataclass(frozen=True)
class BenchmarkSummary:
    sql: str
    warmups: int
    requested_runs: int
    measurements: tuple[Measurement, ...]
    errors: tuple[str, ...]
    mean_server_time_ms: float
    median_server_time_ms: float
    min_server_time_ms: float
    max_server_time_ms: float
    stdev_server_time_ms: float | None

    @property
    def valid_runs(self) -> int:
        return len(self.measurements)


def benchmark_query(
    settings: Settings,
    sql: str,
    *,
    runs: int = 5,
    warmups: int = 1,
    allowed_schemas: set[str] | None = None,
) -> BenchmarkSummary:
    if runs < 1 or warmups < 0:
        raise UnsupportedQueryError("runs deve ser maior que zero e warmups não pode ser negativo.")
    validated = validate_read_query(sql, allowed_schemas=allowed_schemas)
    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {validated.sql}"
    errors: list[str] = []
    measurements: list[Measurement] = []

    for run in range(warmups):
        _execute_once(settings, explain_sql, run=run, errors=None)
    for run in range(1, runs + 1):
        result = _execute_once(settings, explain_sql, run=run, errors=errors)
        if result is not None:
            measurements.append(result)

    if len(measurements) < 2:
        raise UnsupportedQueryError(
            f"Não há medições válidas suficientes: {len(measurements)}; mínimo esperado: 2."
        )
    values = [item.server_time_ms for item in measurements]
    return BenchmarkSummary(
        sql=validated.sql,
        warmups=warmups,
        requested_runs=runs,
        measurements=tuple(measurements),
        errors=tuple(errors),
        mean_server_time_ms=statistics.fmean(values),
        median_server_time_ms=statistics.median(values),
        min_server_time_ms=min(values),
        max_server_time_ms=max(values),
        stdev_server_time_ms=statistics.stdev(values) if len(values) > 1 else None,
    )


def _execute_once(
    settings: Settings,
    explain_sql: str,
    *,
    run: int,
    errors: list[str] | None,
) -> Measurement | None:
    try:
        with connect(settings) as conn, conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            row = conn.execute(explain_sql).fetchone()
    except psycopg.errors.QueryCanceled as exc:
        if errors is None:
            raise QueryTimeoutError("O aquecimento foi cancelado por timeout.") from exc
        errors.append(f"execução {run}: timeout")
        return None
    except psycopg.Error as exc:
        if errors is None:
            raise
        errors.append(f"execução {run}: {type(exc).__name__}: {exc}")
        return None
    try:
        return _measurement_from_row(row, run)
    except UnsupportedQueryError as exc:
        if errors is None:
            raise
        errors.append(f"execução {run}: {exc}")
        return None


def _measurement_from_row(row: Any, run: int) -> Measurement:
    if row is None or not row[0]:
        raise UnsupportedQueryError("EXPLAIN não retornou dados.")
    raw = row[0]
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise UnsupportedQueryError("Resposta inesperada de EXPLAIN ANALYZE.")
    payload = raw[0]
    plan = payload.get("Plan")
    if not isinstance(plan, dict):
        raise UnsupportedQueryError("EXPLAIN ANALYZE não contém Plan.")
    execution = _optional_number(payload, "Execution Time")
    planning = _optional_number(payload, "Planning Time")
    if execution is None:
        raise UnsupportedQueryError("EXPLAIN ANALYZE não contém Execution Time.")
    rows = _optional_number(plan, "Actual Rows")
    buffer_keys = (
        "Shared Hit Blocks",
        "Shared Read Blocks",
        "Shared Dirtied Blocks",
        "Shared Written Blocks",
        "Local Hit Blocks",
        "Local Read Blocks",
        "Temp Read Blocks",
        "Temp Written Blocks",
    )
    buffers = {key: plan[key] for key in buffer_keys if key in plan}
    return Measurement(
        run=run,
        server_time_ms=execution,
        planning_time_ms=planning,
        execution_time_ms=execution,
        rows=rows,
        buffers=buffers,
    )


def _optional_number(value: dict[str, Any], key: str) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise UnsupportedQueryError(f"Campo {key} inválido no plano.")
    return float(item)
