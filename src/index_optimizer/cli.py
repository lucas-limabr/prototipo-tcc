from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from index_optimizer import __version__
from index_optimizer.errors import ExitCode, IndexOptimizerError


def _add_query_source(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="Consulta SQL de leitura (SELECT).")
    group.add_argument("--query-file", metavar="PATH", help="Arquivo contendo a consulta SQL.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="index-optimizer",
        description="Analisa consultas SELECT no PostgreSQL e recomenda índices (laboratório).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMANDO")

    sub.add_parser("check-connection", help="Verifica a conexão com o banco de laboratório.")

    analyze = sub.add_parser("analyze", help="Valida, captura o plano e recomenda (sem alterar).")
    _add_query_source(analyze)

    benchmark = sub.add_parser("benchmark", help="Mede a consulta sob protocolo repetível.")
    _add_query_source(benchmark)
    benchmark.add_argument("--runs", type=int, default=5, help="Medições válidas (padrão: 5).")
    benchmark.add_argument("--warmup", type=int, default=1, help="Aquecimentos (padrão: 1).")

    optimize = sub.add_parser("optimize", help="Recomenda e, opcionalmente, aplica índices.")
    _add_query_source(optimize)
    mode = optimize.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Apenas mostra o DDL (padrão).")
    mode.add_argument(
        "--apply-indexes",
        action="store_true",
        help="Aplica os índices recomendados (somente no laboratório).",
    )
    optimize.add_argument("--runs", type=int, default=5, help="Medições válidas (padrão: 5).")

    cleanup = sub.add_parser(
        "cleanup",
        help="Remove índices experimentais criados pelo protótipo (somente laboratório local).",
    )
    cleanup.add_argument(
        "--experimental-indexes",
        action="store_true",
        required=True,
        help="Confirma explicitamente a remoção dos índices experimentais elegíveis.",
    )
    plot = sub.add_parser("plot", help="Gera um gráfico PNG a partir de um relatório JSON.")
    plot.add_argument("--report", required=True, type=Path, metavar="PATH")
    plot.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/charts"),
        metavar="PATH",
        help="Diretório de saída (padrão: reports/charts).",
    )
    return parser


def _check_connection() -> int:
    from index_optimizer.config import load_settings
    from index_optimizer.database.connection import server_version

    settings = load_settings()
    version = server_version(settings)
    print(f"Conectado a {settings.db_host}:{settings.db_port}/{settings.db_name}")
    print(version)
    return ExitCode.OK


def _read_query(args: argparse.Namespace) -> str:
    if args.query is not None:
        return args.query
    return Path(args.query_file).read_text(encoding="utf-8")


def _analysis(query: str, settings):
    from index_optimizer.database.catalog import inspect_database_catalog
    from index_optimizer.database.explain import explain_query
    from index_optimizer.database.opportunities import extract_opportunities
    from index_optimizer.database.plan_parser import parse_plan
    from index_optimizer.database.recommendations import recommend_indexes

    estimated = explain_query(settings, query, allowed_schemas=set(settings.allowed_schemas))
    catalog = inspect_database_catalog(settings)
    opportunities = extract_opportunities(parse_plan(estimated.raw), catalog)
    recommendations = recommend_indexes(opportunities)
    return estimated, recommendations


def _report_for_analysis(query: str, settings):
    from index_optimizer.database.reporting import build_report

    estimated, recommendations = _analysis(query, settings)
    return build_report(
        query,
        condition={"command": "analyze", "environment": settings.environment},
        estimated_plan=estimated.raw,
        recommendations=recommendations.recommendations,
        limitations=("A análise não altera a estrutura do banco.",),
    )


def _run_analyze(args: argparse.Namespace) -> int:
    from index_optimizer.config import load_settings
    from index_optimizer.database.reporting import report_to_json

    report = _report_for_analysis(_read_query(args), load_settings())
    print(report_to_json(report))
    return ExitCode.OK


def _run_benchmark(args: argparse.Namespace) -> int:
    from index_optimizer.config import load_settings
    from index_optimizer.database.benchmark import benchmark_query
    from index_optimizer.database.reporting import build_report, report_to_json

    settings = load_settings()
    query = _read_query(args)
    benchmark = benchmark_query(
        settings,
        query,
        runs=args.runs,
        warmups=args.warmup,
        allowed_schemas=set(settings.allowed_schemas),
    )
    report = build_report(
        query,
        condition={
            "command": "benchmark",
            "environment": settings.environment,
            "runs": args.runs,
            "warmups": args.warmup,
        },
        baseline=benchmark,
    )
    print(report_to_json(report))
    return ExitCode.OK


def _run_optimize(args: argparse.Namespace) -> int:
    from index_optimizer.config import load_settings
    from index_optimizer.database.connection import connect
    from index_optimizer.database.index_apply import apply_indexes, dry_run, render_ddl
    from index_optimizer.database.reporting import build_report, report_to_json

    settings = load_settings()
    query = _read_query(args)
    estimated, recommendations = _analysis(query, settings)
    ddls = dry_run(recommendations.recommendations)
    with connect(settings) as connection:
        rendered_ddls = [render_ddl(ddl, connection) for ddl in ddls]
    applied = (
        apply_indexes(settings, recommendations.recommendations, apply=True)
        if args.apply_indexes
        else ()
    )
    report = build_report(
        query,
        condition={
            "command": "optimize",
            "environment": settings.environment,
            "mode": "apply" if args.apply_indexes else "dry-run",
        },
        estimated_plan=estimated.raw,
        recommendations=recommendations.recommendations,
        applied_indexes=applied,
        limitations=(
            "O modo dry-run não modifica o banco."
            if not args.apply_indexes
            else "A aplicação foi autorizada explicitamente no laboratório.",
        ),
    )
    payload = json.loads(report_to_json(report))
    payload["dry_run"] = rendered_ddls
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return ExitCode.OK


def _run_cleanup(args: argparse.Namespace) -> int:
    from index_optimizer.config import load_settings
    from index_optimizer.database.index_cleanup import cleanup_experimental_indexes

    settings = load_settings()
    result = cleanup_experimental_indexes(
        settings,
        experimental_indexes=args.experimental_indexes,
    )
    if result.removed_count:
        message = f"{result.removed_count} índice(s) experimental(is) removido(s)."
    else:
        message = "Nenhum índice experimental elegível encontrado."
    payload = {
        "command": "cleanup",
        "environment": settings.environment,
        "experimental_indexes": args.experimental_indexes,
        "message": message,
        "removed_count": result.removed_count,
        "removed_indexes": [item.name for item in result.removed_indexes],
        "status": "SUCCESS",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return ExitCode.OK


def _run_plot(args: argparse.Namespace) -> int:
    from index_optimizer.database.charts import (
        extract_performance_chart_data,
        extract_variability_chart_data,
        report_from_json,
        save_performance_chart,
        save_variability_chart,
    )

    report = report_from_json(args.report)
    extract_performance_chart_data(report)
    extract_variability_chart_data(report)
    performance_path = save_performance_chart(report, args.output_dir)
    variability_path = save_variability_chart(report, args.output_dir)
    print(
        json.dumps(
            {
                "command": "plot",
                "paths": {
                    "performance": str(performance_path),
                    "variability": str(variability_path),
                },
            },
            ensure_ascii=False,
        )
    )
    return ExitCode.OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return ExitCode.OK

    try:
        if args.command == "check-connection":
            return _check_connection()
        if args.command == "analyze":
            return _run_analyze(args)
        if args.command == "benchmark":
            return _run_benchmark(args)
        if args.command == "optimize":
            return _run_optimize(args)
        if args.command == "cleanup":
            return _run_cleanup(args)
        if args.command == "plot":
            return _run_plot(args)
    except IndexOptimizerError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
