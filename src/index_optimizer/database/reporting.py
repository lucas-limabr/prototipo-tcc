from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from index_optimizer.database.benchmark import BenchmarkSummary
from index_optimizer.database.comparison import PerformanceComparison
from index_optimizer.database.index_apply import IndexApplyResult
from index_optimizer.database.recommendations import IndexRecommendation


@dataclass(frozen=True)
class ExperimentReport:
    experiment_id: str
    generated_at: str
    query: str
    condition: dict[str, Any]
    estimated_plan: Any
    recommendations: tuple[IndexRecommendation, ...]
    baseline: BenchmarkSummary | None
    after: BenchmarkSummary | None
    comparison: PerformanceComparison | None
    applied_indexes: tuple[IndexApplyResult, ...]
    limitations: tuple[str, ...]


def build_report(
    query: str,
    *,
    condition: dict[str, Any],
    estimated_plan: Any = None,
    recommendations: tuple[IndexRecommendation, ...] = (),
    baseline: BenchmarkSummary | None = None,
    after: BenchmarkSummary | None = None,
    comparison: PerformanceComparison | None = None,
    applied_indexes: tuple[IndexApplyResult, ...] = (),
    limitations: tuple[str, ...] = (),
) -> ExperimentReport:
    generated_at = datetime.now(UTC).isoformat()
    experiment_id = hashlib.sha256(
        json.dumps(
            {"query": query, "condition": condition},
            sort_keys=True,
            ensure_ascii=True,
        ).encode()
    ).hexdigest()[:16]
    return ExperimentReport(
        experiment_id=experiment_id,
        generated_at=generated_at,
        query=query,
        condition=dict(condition),
        estimated_plan=estimated_plan,
        recommendations=recommendations,
        baseline=baseline,
        after=after,
        comparison=comparison,
        applied_indexes=applied_indexes,
        limitations=limitations,
    )


def report_to_dict(report: ExperimentReport) -> dict[str, Any]:
    return _json_safe(asdict(report))


def report_to_json(report: ExperimentReport) -> str:
    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2, sort_keys=True)


def report_to_markdown(report: ExperimentReport) -> str:
    comparison = report.comparison
    lines = [
        f"# Relatório do experimento `{report.experiment_id}`",
        "",
        f"- Gerado em: `{report.generated_at}`",
        f"- Consulta: `{report.query}`",
        f"- Condição: `{json.dumps(report.condition, ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Recomendações",
        "",
    ]
    if report.recommendations:
        lines.extend(
            f"- `{item.status.value}` — `{item.schema}.{item.table}({', '.join(item.columns)})`: "
            f"{item.justification}"
            for item in report.recommendations
        )
    else:
        lines.append("- Nenhuma recomendação registrada.")
    lines.extend(["", "## Medições", ""])
    if report.baseline:
        lines.append(f"- Linha de base: mediana `{report.baseline.median_server_time_ms:.3f} ms`.")
    if report.after:
        lines.append(f"- Pós-indexação: mediana `{report.after.median_server_time_ms:.3f} ms`.")
    if comparison:
        lines.append(f"- Resultado: **{comparison.status.value}** — {comparison.explanation}")
    if report.applied_indexes:
        lines.extend(["", "## Índices aplicados", ""])
        lines.extend(
            f"- `{item.ddl.name}`: `{item.status}` — {item.message}"
            for item in report.applied_indexes
        )
    lines.extend(["", "## Limitações", ""])
    if report.limitations:
        lines.extend(f"- {item}" for item in report.limitations)
    else:
        lines.append("- Nenhuma registrada.")
    return "\n".join(lines) + "\n"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            safe_item = _json_safe(item)
            if safe_item is None or safe_item == [] or safe_item == {}:
                continue
            result[key] = safe_item
        return result
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if value.__class__.__module__.startswith("psycopg.sql"):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return _json_safe(asdict(value))
    return value
