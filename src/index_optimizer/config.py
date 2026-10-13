from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from index_optimizer.errors import ConfigError

LAB_ENVIRONMENT = "lab"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_REQUIRED = ("IXO_DB_NAME", "IXO_DB_USER", "IXO_DB_PASSWORD")


@dataclass(frozen=True)
class Settings:
    db_name: str
    db_user: str
    db_password: str = field(repr=False)
    db_host: str = "localhost"
    db_port: int = 5432
    environment: str = LAB_ENVIRONMENT
    allowed_schemas: tuple[str, ...] = ("public",)
    statement_timeout_ms: int = 30_000
    lock_timeout_ms: int = 5_000

    @property
    def is_lab(self) -> bool:
        return self.environment == LAB_ENVIRONMENT and self.db_host in LOCAL_HOSTS


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser um inteiro; recebido {raw!r}.") from exc
    if value <= 0:
        raise ConfigError(f"{name} deve ser maior que zero; recebido {value}.")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env

    missing = [name for name in _REQUIRED if not env.get(name)]
    if missing:
        raise ConfigError(
            "Variáveis obrigatórias ausentes: "
            + ", ".join(missing)
            + ". Copie .env.example para .env e carregue-o (ex.: set -a; source .env; set +a)."
        )

    port = _positive_int(env, "IXO_DB_PORT", 5432)
    if port > 65535:
        raise ConfigError(f"IXO_DB_PORT fora do intervalo válido: {port}.")

    schemas = tuple(
        s.strip() for s in env.get("IXO_ALLOWED_SCHEMAS", "public").split(",") if s.strip()
    )
    if not schemas:
        raise ConfigError("IXO_ALLOWED_SCHEMAS não pode ser vazio.")

    return Settings(
        db_name=env["IXO_DB_NAME"],
        db_user=env["IXO_DB_USER"],
        db_password=env["IXO_DB_PASSWORD"],
        db_host=env.get("IXO_DB_HOST", "localhost") or "localhost",
        db_port=port,
        environment=(env.get("IXO_ENVIRONMENT") or LAB_ENVIRONMENT).strip().lower(),
        allowed_schemas=schemas,
        statement_timeout_ms=_positive_int(env, "IXO_STATEMENT_TIMEOUT_MS", 30_000),
        lock_timeout_ms=_positive_int(env, "IXO_LOCK_TIMEOUT_MS", 5_000),
    )
