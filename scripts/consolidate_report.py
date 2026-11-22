#!/usr/bin/env python3
"""Consolida os resultados de dois benchmarks em um relatório pré/pós."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from index_optimizer.database.benchmark import BenchmarkSummary
from index_optimizer.database.charts import _benchmark_from_payload
from index_optimizer.database.comparison import compare_benchmarks
from index_optimizer.database.reporting import build_report, report_to_json


def _read_benchmark(path: Path) -> tuple[BenchmarkSummary, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("o conteúdo JSON deve ser um objeto")
        benchmark = payload.get("baseline")
        query = payload.get("query")
        if not isinstance(benchmark, dict) or not isinstance(query, str):
            raise ValueError("o arquivo precisa conter 'baseline' e 'query'")
        return _benchmark_from_payload(benchmark, query), payload
    except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
        raise ValueError(f"Não foi possível ler o benchmark {path}: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera um relatório consolidado a partir dos benchmarks antes e depois."
    )
    parser.add_argument("--baseline", type=Path, required=True, help="JSON do benchmark antes.")
    parser.add_argument("--after", type=Path, required=True, help="JSON do benchmark depois.")
    parser.add_argument("--output", type=Path, required=True, help="Caminho do relatório JSON.")
    parser.add_argument(
        "--created-index",
        action="append",
        default=[],
        help="Nome de índice aplicado; pode ser informado mais de uma vez.",
    )
    parser.add_argument("--environment", help="Ambiente da execução, por exemplo 'lab'.")
    parser.add_argument("--dataset", help="Identificação da carga de dados usada.")
    parser.add_argument("--empresa-rows", type=int, help="Quantidade de linhas de empresas.")
    parser.add_argument(
        "--estabelecimento-rows", type=int, help="Quantidade de linhas de estabelecimentos."
    )
    parser.add_argument(
        "--limitation",
        action="append",
        default=[],
        help="Limitação a registrar; pode ser informada mais de uma vez.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        baseline, baseline_payload = _read_benchmark(args.baseline)
        after, _ = _read_benchmark(args.after)
        comparison = compare_benchmarks(baseline, after)
        if args.created_index:
            comparison = replace(comparison, created_indexes=tuple(args.created_index))

        baseline_condition = baseline_payload.get("condition", {})
        condition: dict[str, Any] = {
            "command": "benchmark-comparison",
            "environment": args.environment
            or (
                baseline_condition.get("environment")
                if isinstance(baseline_condition, dict)
                else None
            ),
            "runs": baseline.requested_runs,
            "warmups": baseline.warmups,
        }
        optional_metadata = {
            "dataset": args.dataset,
            "empresa_rows": args.empresa_rows,
            "estabelecimento_rows": args.estabelecimento_rows,
        }
        condition.update(
            {key: value for key, value in optional_metadata.items() if value is not None}
        )
        limitations = tuple(args.limitation)
        comparison = replace(
            comparison,
            limitations=(*comparison.limitations, *limitations),
        )
        report = build_report(
            baseline.sql,
            condition=condition,
            baseline=baseline,
            after=after,
            comparison=comparison,
            limitations=comparison.limitations,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report_to_json(report), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(comparison.explanation)
    print(f"status= {comparison.status.value}")
    print(f"relatório= {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
