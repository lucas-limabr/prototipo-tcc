from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from index_optimizer.errors import UnsupportedQueryError


@dataclass(frozen=True)
class RelationRef:
    name: str
    alias: str | None = None


@dataclass(frozen=True)
class PlanCondition:
    kind: str
    expression: str


@dataclass(frozen=True)
class PlanNode:
    node_type: str
    relation: RelationRef | None
    startup_cost: float | None
    total_cost: float | None
    plan_rows: float | None
    plan_width: int | None
    conditions: tuple[PlanCondition, ...]
    sort_keys: tuple[str, ...]
    children: tuple[PlanNode, ...]
    raw: dict[str, Any]


@dataclass(frozen=True)
class QueryPlan:
    root: PlanNode
    raw: Any


def parse_plan(value: Any) -> QueryPlan:
    """Parse PostgreSQL EXPLAIN JSON while retaining the original response."""
    root = _extract_root(value)
    return QueryPlan(root=_parse_node(root), raw=value)


def _extract_root(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        if "Plan" in value:
            value = value["Plan"]
        if isinstance(value, dict):
            return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return _extract_root(value[0])
    raise UnsupportedQueryError("Plano JSON malformado: objeto Plan ausente.")


def _parse_node(value: dict[str, Any]) -> PlanNode:
    node_type = value.get("Node Type")
    if not isinstance(node_type, str) or not node_type.strip():
        raise UnsupportedQueryError("Plano JSON malformado: Node Type ausente.")

    relation_name = value.get("Relation Name")
    alias = value.get("Alias")
    if relation_name is not None and not isinstance(relation_name, str):
        raise UnsupportedQueryError("Plano JSON malformado: Relation Name inválido.")
    if alias is not None and not isinstance(alias, str):
        raise UnsupportedQueryError("Plano JSON malformado: Alias inválido.")
    relation = RelationRef(relation_name, alias) if relation_name else None

    children_value = value.get("Plans", [])
    if not isinstance(children_value, list) or not all(
        isinstance(child, dict) for child in children_value
    ):
        raise UnsupportedQueryError("Plano JSON malformado: Plans inválido.")

    conditions = tuple(
        PlanCondition(kind=key, expression=value[key])
        for key in ("Filter", "Index Cond", "Join Filter", "Hash Cond", "Merge Cond")
        if key in value and _is_text(value[key], f"Plano JSON malformado: {key} inválido.")
    )
    sort_keys = _text_list(value.get("Sort Key", []), "Sort Key")

    return PlanNode(
        node_type=node_type,
        relation=relation,
        startup_cost=_number(value, "Startup Cost"),
        total_cost=_number(value, "Total Cost"),
        plan_rows=_number(value, "Plan Rows"),
        plan_width=_integer(value, "Plan Width"),
        conditions=conditions,
        sort_keys=sort_keys,
        children=tuple(_parse_node(child) for child in children_value),
        raw=value,
    )


def _number(value: dict[str, Any], key: str) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise UnsupportedQueryError(f"Plano JSON malformado: {key} inválido.")
    return float(item)


def _integer(value: dict[str, Any], key: str) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, int):
        raise UnsupportedQueryError(f"Plano JSON malformado: {key} inválido.")
    return item


def _is_text(value: Any, message: str) -> bool:
    if not isinstance(value, str):
        raise UnsupportedQueryError(message)
    return True


def _text_list(value: Any, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise UnsupportedQueryError(f"Plano JSON malformado: {key} inválido.")
    return tuple(value)
