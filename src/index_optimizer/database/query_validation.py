from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from index_optimizer.errors import UnsupportedQueryError

MAX_QUERY_LENGTH = 100_000
_FORBIDDEN_FUNCTIONS = {
    "dblink_connect",
    "dblink_exec",
    "lo_export",
    "pg_advisory_lock",
    "pg_notify",
    "pg_sleep",
    "set_config",
    "setval",
    "nextval",
}


@dataclass(frozen=True)
class ValidatedQuery:
    sql: str
    expression: exp.Expression


def validate_read_query(
    sql: str,
    *,
    allowed_schemas: frozenset[str] | set[str] | None = None,
) -> ValidatedQuery:
    """Parse and validate a single, read-only PostgreSQL statement."""
    if not sql or not sql.strip():
        raise UnsupportedQueryError("A consulta SQL não pode ser vazia.")
    if len(sql) > MAX_QUERY_LENGTH:
        raise UnsupportedQueryError(f"A consulta excede o limite de {MAX_QUERY_LENGTH} caracteres.")
    try:
        statements = parse(sql, read="postgres")
    except ParseError as exc:
        raise UnsupportedQueryError(f"SQL inválido: {exc}") from exc
    if len(statements) != 1:
        raise UnsupportedQueryError("Apenas uma instrução SQL é permitida.")

    expression = statements[0]
    if not isinstance(expression, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsupportedQueryError("Somente consultas SELECT de leitura são permitidas.")
    if expression.find(exp.Into) is not None:
        raise UnsupportedQueryError("SELECT INTO não é permitido.")
    if expression.find(exp.Lock) is not None:
        raise UnsupportedQueryError("FOR UPDATE/FOR SHARE não é permitido.")
    for node in expression.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter)):
            raise UnsupportedQueryError("A consulta contém uma operação de escrita ou DDL.")
        if isinstance(node, exp.Anonymous) and node.name.lower() in _FORBIDDEN_FUNCTIONS:
            raise UnsupportedQueryError(f"A função {node.name} não é permitida.")
        if (
            isinstance(node, exp.Table)
            and allowed_schemas
            and node.db
            and node.db not in allowed_schemas
        ):
            raise UnsupportedQueryError(f"Schema não permitido: {node.db}.")
    return ValidatedQuery(sql=sql.strip().rstrip(";"), expression=expression)
