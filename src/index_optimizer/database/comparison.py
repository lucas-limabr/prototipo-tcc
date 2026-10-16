from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from index_optimizer.database.benchmark import BenchmarkSummary
from index_optimizer.database.index_apply import IndexApplyResult
from index_optimizer.database.plan_parser import QueryPlan, parse_plan


class ComparisonStatus(StrEnum):
    IMPROVED = "MELHORIA"
    REGRESSED = "REGRESSAO"
    UNCHANGED = "SEM_MUDANCA_RELEVANTE"
    INCONCLUSIVE = "INCONCLUSIVO"


@dataclass(frozen=True)
class PerformanceComparison:
    sql: str
    status: ComparisonStatus
    baseline_median_ms: float | None
    after_median_ms: float | None
    reduction_percent: float | None
    speedup: float | None
    result_rows_equal: bool | None
    plan_changed: bool | None
    created_indexes: tuple[str, ...]
    explanation: str
    limitations: tuple[str, ...]


def compare_benchmarks(
    baseline: BenchmarkSummary,
    after: BenchmarkSummary,
    *,
    baseline_plan: QueryPlan | None = None,
    after_plan: QueryPlan | None = None,
    applied_indexes: tuple[IndexApplyResult, ...] = (),
    relevance_threshold_percent: float = 5.0,
) -> PerformanceComparison:
    if relevance_threshold_percent < 0:
        raise ValueError("relevance_threshold_percent não pode ser negativo.")
    if baseline.sql != after.sql or (
        baseline.warmups,
        baseline.requested_runs,
    ) != (after.warmups, after.requested_runs):
        return _inconclusive(
            baseline,
            after,
            applied_indexes,
            "A consulta ou o protocolo de medição não é idêntico.",
        )
    if baseline.valid_runs < 2 or after.valid_runs < 2:
        return _inconclusive(
            baseline,
            after,
            applied_indexes,
            "Amostra insuficiente: são necessárias pelo menos duas medições válidas em cada etapa.",
        )
    before = baseline.median_server_time_ms
    after_value = after.median_server_time_ms
    if before <= 0 or after_value <= 0:
        return _inconclusive(
            baseline,
            after,
            applied_indexes,
            "Tempos medianos inválidos ou não positivos.",
        )
    reduction = ((before - after_value) / before) * 100
    speedup = before / after_value
    if reduction > relevance_threshold_percent:
        status = ComparisonStatus.IMPROVED
    elif reduction < -relevance_threshold_percent:
        status = ComparisonStatus.REGRESSED
    else:
        status = ComparisonStatus.UNCHANGED

    before_rows = _rows(baseline)
    after_rows = _rows(after)
    rows_equal = (
        before_rows == after_rows if before_rows is not None and after_rows is not None else None
    )
    if rows_equal is False:
        status = ComparisonStatus.INCONCLUSIVE
    plan_changed = _plan_changed(baseline_plan, after_plan)
    indexes = tuple(result.ddl.name for result in applied_indexes if result.status == "CREATED")
    limitations = [
        "A comparação não demonstra causalidade nem significância estatística.",
        "A métrica comparada é o tempo mediano do servidor em milissegundos.",
    ]
    if rows_equal is False:
        limitations.append("A quantidade de linhas observadas mudou entre as etapas.")
    explanation = (
        f"Mediana antes: {before:.3f} ms; depois: {after_value:.3f} ms; "
        f"variação: {reduction:.2f}%; speedup: {speedup:.3f}x."
    )
    return PerformanceComparison(
        sql=baseline.sql,
        status=status,
        baseline_median_ms=before,
        after_median_ms=after_value,
        reduction_percent=reduction,
        speedup=speedup,
        result_rows_equal=rows_equal,
        plan_changed=plan_changed,
        created_indexes=indexes,
        explanation=explanation,
        limitations=tuple(limitations),
    )


def compare_raw_plans(
    baseline: BenchmarkSummary,
    after: BenchmarkSummary,
    baseline_raw: object,
    after_raw: object,
    *,
    applied_indexes: tuple[IndexApplyResult, ...] = (),
) -> PerformanceComparison:
    return compare_benchmarks(
        baseline,
        after,
        baseline_plan=parse_plan(baseline_raw),
        after_plan=parse_plan(after_raw),
        applied_indexes=applied_indexes,
    )


def _inconclusive(
    baseline: BenchmarkSummary,
    after: BenchmarkSummary,
    applied_indexes: tuple[IndexApplyResult, ...],
    reason: str,
) -> PerformanceComparison:
    return PerformanceComparison(
        sql=baseline.sql,
        status=ComparisonStatus.INCONCLUSIVE,
        baseline_median_ms=None,
        after_median_ms=None,
        reduction_percent=None,
        speedup=None,
        result_rows_equal=None,
        plan_changed=None,
        created_indexes=tuple(
            result.ddl.name for result in applied_indexes if result.status == "CREATED"
        ),
        explanation=reason,
        limitations=("Nenhuma conclusão de desempenho deve ser extraída.",),
    )


def _rows(summary: BenchmarkSummary) -> float | None:
    values = {measurement.rows for measurement in summary.measurements}
    return next(iter(values)) if len(values) == 1 else None


def _plan_changed(before: QueryPlan | None, after: QueryPlan | None) -> bool | None:
    if before is None or after is None:
        return None
    return before.root.node_type != after.root.node_type or before.root.raw != after.root.raw
