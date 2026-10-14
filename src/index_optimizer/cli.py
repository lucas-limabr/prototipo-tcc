from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from index_optimizer import __version__
from index_optimizer.errors import ExitCode, IndexOptimizerError, NotImplementedYetError


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
    return parser


def _check_connection() -> int:
    from index_optimizer.config import load_settings
    from index_optimizer.database.connection import server_version

    settings = load_settings()
    version = server_version(settings)
    print(f"Conectado a {settings.db_host}:{settings.db_port}/{settings.db_name}")
    print(version)
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
        raise NotImplementedYetError(
            f"O comando '{args.command}' ainda não está implementado nesta versão."
        )
    except IndexOptimizerError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
