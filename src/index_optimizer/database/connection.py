from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from index_optimizer.config import Settings
from index_optimizer.errors import ConnectionFailedError


def _conninfo(settings: Settings) -> dict[str, object]:
    return {
        "host": settings.db_host,
        "port": settings.db_port,
        "dbname": settings.db_name,
        "user": settings.db_user,
        "password": settings.db_password,
        "connect_timeout": settings.connect_timeout_s,
        "application_name": "index-optimizer",
        "options": (
            f"-c statement_timeout={settings.statement_timeout_ms} "
            f"-c lock_timeout={settings.lock_timeout_ms}"
        ),
    }


@contextmanager
def connect(settings: Settings) -> Iterator[psycopg.Connection]:
    target = f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
    try:
        conn = psycopg.connect(**_conninfo(settings))
    except psycopg.OperationalError as exc:
        reason = str(exc).replace(settings.db_password, "***").strip()
        raise ConnectionFailedError(
            f"Não foi possível conectar ao PostgreSQL em {target}. "
            f"Verifique se o laboratório está ativo (docker compose ps) e as variáveis IXO_DB_*. "
            f"Detalhe: {reason}"
        ) from exc
    try:
        yield conn
    finally:
        conn.close()


def server_version(settings: Settings) -> str:
    with connect(settings) as conn:
        row = conn.execute("SELECT version()").fetchone()
    if row is None:
        raise ConnectionFailedError("O servidor não retornou a versão.")
    return str(row[0])
