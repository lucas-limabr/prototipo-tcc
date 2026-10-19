"""Geração de gráficos para relatórios de experimentos."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from index_optimizer.database.benchmark import BenchmarkSummary
from index_optimizer.database.reporting import ExperimentReport
from index_optimizer.errors import IndexOptimizerError


class ChartDataError(IndexOptimizerError):
    """Indica que o relatório não contém dados suficientes para um gráfico."""


@dataclass(frozen=True)
class PerformanceChartData:
    """Valores usados no gráfico de comparação de desempenho."""

    experiment_id: str
    baseline_median_ms: float
    after_median_ms: float
    status: str


@dataclass(frozen=True)
class VariabilityChartData:
    """Médias e desvios padrão usados no gráfico de variabilidade."""

    experiment_id: str
    baseline_mean_ms: float
    after_mean_ms: float
    baseline_stdev_ms: float
    after_stdev_ms: float
    status: str


def extract_performance_chart_data(report: ExperimentReport) -> PerformanceChartData:
    """Extrai as medianas antes/depois e o resultado de um relatório."""
    if report.baseline is None or report.after is None or report.comparison is None:
        raise ChartDataError(
            "O relatório precisa conter baseline, after e comparison para gerar o gráfico."
        )
    if report.baseline.median_server_time_ms <= 0 or report.after.median_server_time_ms <= 0:
        raise ChartDataError("O relatório não contém medianas positivas; o gráfico não foi gerado.")
    return PerformanceChartData(
        experiment_id=report.experiment_id,
        baseline_median_ms=report.baseline.median_server_time_ms,
        after_median_ms=report.after.median_server_time_ms,
        status=report.comparison.status.value,
    )


def extract_variability_chart_data(report: ExperimentReport) -> VariabilityChartData:
    """Extrai médias e desvios padrão antes/depois de um relatório."""
    if report.baseline is None or report.after is None or report.comparison is None:
        raise ChartDataError(
            "O relatório precisa conter baseline, after e comparison para gerar o gráfico."
        )
    values = (
        report.baseline.mean_server_time_ms,
        report.after.mean_server_time_ms,
        report.baseline.stdev_server_time_ms,
        report.after.stdev_server_time_ms,
    )
    if any(value <= 0 for value in values[:2]):
        raise ChartDataError("O relatório não contém médias positivas; o gráfico não foi gerado.")
    if any(value is None or value < 0 for value in values[2:]):
        raise ChartDataError(
            "O relatório precisa conter desvios padrão não negativos para gerar o gráfico."
        )
    return VariabilityChartData(
        experiment_id=report.experiment_id,
        baseline_mean_ms=values[0],
        after_mean_ms=values[1],
        baseline_stdev_ms=values[2],
        after_stdev_ms=values[3],
        status=report.comparison.status.value,
    )


def save_performance_chart(
    report: ExperimentReport,
    output_dir: Path = Path("reports/charts"),
) -> Path:
    """Salva um gráfico PNG de medianas antes/depois e retorna seu caminho."""
    data = extract_performance_chart_data(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{data.experiment_id}-performance.png"

    color = {
        "MELHORIA": "#2e7d32",
        "REGRESSAO": "#c62828",
        "SEM_MUDANCA_RELEVANTE": "#ef6c00",
        "INCONCLUSIVO": "#616161",
    }.get(data.status, "#616161")
    values = [data.baseline_median_ms, data.after_median_ms]
    figure, axis = plt.subplots(figsize=(7, 4.5))
    bars = axis.bar(["Antes", "Depois"], values, color=["#607d8b", color])
    axis.set_ylabel("Tempo mediano do servidor (ms)")
    axis.set_title(f"Desempenho antes/depois — {data.status}")
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    for bar, value in zip(bars, values, strict=True):
        axis.annotate(
            f"{value:.3f} ms",
            xy=(bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    figure.tight_layout()
    figure.savefig(output_path, format="png", dpi=150)
    plt.close(figure)
    return output_path


def save_variability_chart(
    report: ExperimentReport,
    output_dir: Path = Path("reports/charts"),
) -> Path:
    """Salva um gráfico PNG de médias com desvio padrão antes/depois."""
    data = extract_variability_chart_data(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{data.experiment_id}-variability.png"
    color = {
        "MELHORIA": "#2e7d32",
        "REGRESSAO": "#c62828",
        "SEM_MUDANCA_RELEVANTE": "#ef6c00",
        "INCONCLUSIVO": "#616161",
    }.get(data.status, "#616161")
    means = [data.baseline_mean_ms, data.after_mean_ms]
    deviations = [data.baseline_stdev_ms, data.after_stdev_ms]
    figure, axis = plt.subplots(figsize=(7, 4.5))
    bars = axis.bar(
        ["Antes", "Depois"],
        means,
        yerr=deviations,
        capsize=6,
        color=["#607d8b", color],
        error_kw={"ecolor": "#263238", "elinewidth": 1.2},
    )
    axis.set_ylabel("Tempo médio do servidor (ms)")
    axis.set_title(f"Variabilidade antes/depois — {data.status}")
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    for bar, mean, deviation in zip(bars, means, deviations, strict=True):
        axis.annotate(
            f"{mean:.3f} ± {deviation:.3f} ms",
            xy=(bar.get_x() + bar.get_width() / 2, mean + deviation),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    figure.tight_layout()
    figure.savefig(output_path, format="png", dpi=150)
    plt.close(figure)
    return output_path


def report_from_json(path: Path) -> ExperimentReport:
    """Lê um relatório JSON e reconstrói somente os dados necessários ao gráfico."""
    from index_optimizer.database.comparison import ComparisonStatus, PerformanceComparison

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("o relatório deve ser um objeto JSON")
        baseline = _benchmark_from_payload(payload["baseline"], payload.get("query", ""))
        after = _benchmark_from_payload(payload["after"], payload.get("query", ""))
        comparison_payload = payload["comparison"]
        if not isinstance(comparison_payload, dict):
            raise TypeError("comparison ausente")
        comparison = PerformanceComparison(
            sql=str(comparison_payload.get("sql", baseline.sql)),
            status=ComparisonStatus(comparison_payload["status"]),
            baseline_median_ms=_optional_float(comparison_payload.get("baseline_median_ms")),
            after_median_ms=_optional_float(comparison_payload.get("after_median_ms")),
            reduction_percent=_optional_float(comparison_payload.get("reduction_percent")),
            speedup=_optional_float(comparison_payload.get("speedup")),
            result_rows_equal=comparison_payload.get("result_rows_equal"),
            plan_changed=comparison_payload.get("plan_changed"),
            created_indexes=tuple(comparison_payload.get("created_indexes", ())),
            explanation=str(comparison_payload.get("explanation", "")),
            limitations=tuple(comparison_payload.get("limitations", ())),
        )
    except (AttributeError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ChartDataError(f"Relatório inválido para geração do gráfico: {path}") from exc
    return ExperimentReport(
        experiment_id=str(payload.get("experiment_id", "")),
        generated_at=str(payload.get("generated_at", "")),
        query=str(payload.get("query", "")),
        condition=dict(payload.get("condition", payload.get("environment", {}))),
        estimated_plan=payload.get("estimated_plan"),
        recommendations=(),
        baseline=baseline,
        after=after,
        comparison=comparison,
        applied_indexes=(),
        limitations=tuple(payload.get("limitations", ())),
    )


def _benchmark_from_payload(payload: Any, query: str) -> BenchmarkSummary:
    from index_optimizer.database.benchmark import Measurement

    if not isinstance(payload, dict):
        raise TypeError("benchmark ausente")
    if "measurements" not in payload:
        median = _optional_float(payload.get("median_server_time_ms"))
        valid_runs = int(payload.get("valid_runs", 0))
        if median is None or valid_runs < 1:
            raise TypeError("benchmark agregado sem mediana ou medições válidas")
        return BenchmarkSummary(
            sql=query,
            warmups=0,
            requested_runs=valid_runs,
            measurements=(
                Measurement(
                    run=1,
                    server_time_ms=median,
                    planning_time_ms=None,
                    execution_time_ms=median,
                    rows=None,
                    buffers={},
                ),
            ),
            errors=(),
            mean_server_time_ms=float(payload.get("mean_server_time_ms", median)),
            median_server_time_ms=median,
            min_server_time_ms=float(payload.get("min_server_time_ms", median)),
            max_server_time_ms=float(payload.get("max_server_time_ms", median)),
            stdev_server_time_ms=None,
        )
    measurements = tuple(
        Measurement(
            run=int(item["run"]),
            server_time_ms=float(item["server_time_ms"]),
            planning_time_ms=_optional_float(item.get("planning_time_ms")),
            execution_time_ms=_optional_float(item.get("execution_time_ms")),
            rows=_optional_float(item.get("rows")),
            buffers=dict(item.get("buffers", {})),
        )
        for item in payload["measurements"]
    )
    return BenchmarkSummary(
        sql=str(payload["sql"]),
        warmups=int(payload["warmups"]),
        requested_runs=int(payload["requested_runs"]),
        measurements=measurements,
        errors=tuple(payload.get("errors", ())),
        mean_server_time_ms=float(payload["mean_server_time_ms"]),
        median_server_time_ms=float(payload["median_server_time_ms"]),
        min_server_time_ms=float(payload["min_server_time_ms"]),
        max_server_time_ms=float(payload["max_server_time_ms"]),
        stdev_server_time_ms=_optional_float(payload.get("stdev_server_time_ms")),
    )


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
