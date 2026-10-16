from __future__ import annotations

import re
from dataclasses import dataclass

from index_optimizer.database.catalog import Catalog
from index_optimizer.database.plan_parser import PlanNode, QueryPlan

_REFERENCE = re.compile(r"\b(?:(?P<qualifier>[A-Za-z_][\w]*)\.)?(?P<column>[A-Za-z_][\w]*)\b")
_SQL_WORDS = frozenset({"and", "or", "not", "null", "true", "false", "is", "unknown"})
_EVIDENCE_KINDS = frozenset({"Filter", "Index Cond", "Join Filter", "Hash Cond", "Merge Cond"})


@dataclass(frozen=True)
class IndexOpportunity:
    schema: str
    table: str
    column: str
    access_method: str
    evidence_kind: str
    evidence: str
    justification: str
    existing_equivalent: bool


def extract_opportunities(plan: QueryPlan, catalog: Catalog) -> tuple[IndexOpportunity, ...]:
    """Extract verifiable single-column B-tree opportunities without recommending them."""
    relations = _relations(plan.root)
    columns = {(item.schema, item.table, item.name) for item in catalog.columns}
    table_schemas = _table_schemas(catalog)
    existing = _existing_first_columns(catalog)
    found: dict[tuple[str, str, str, str], IndexOpportunity] = {}

    for node, inherited_table, inherited_alias in _walk_with_context(plan.root):
        relation_ref = node.relation
        table = (
            relations.get(relation_ref.alias or relation_ref.name)
            if relation_ref
            else inherited_table
        )
        relation = (table_schemas[table], table) if table in table_schemas else None
        if relation is None:
            for condition in node.conditions:
                if condition.kind not in {"Join Filter", "Hash Cond", "Merge Cond"}:
                    continue
                for schema, joined_table, column in _join_columns(
                    condition.expression, relations, table_schemas, columns
                ):
                    key = (schema, joined_table, column, condition.kind)
                    found.setdefault(
                        key,
                        _candidate(
                            schema,
                            joined_table,
                            column,
                            condition.kind,
                            condition.expression,
                            (schema, joined_table, column) in existing,
                        ),
                    )
            continue
        schema, table = relation
        for condition in node.conditions:
            if condition.kind not in _EVIDENCE_KINDS:
                continue
            alias = relation_ref.alias if relation_ref else inherited_alias
            for column in _columns_in(condition.expression, alias, table, columns):
                key = (schema, table, column, condition.kind)
                found.setdefault(
                    key,
                    _candidate(
                        schema,
                        table,
                        column,
                        condition.kind,
                        condition.expression,
                        (schema, table, column) in existing,
                    ),
                )
        for expression in node.sort_keys:
            alias = relation_ref.alias if relation_ref else inherited_alias
            for column in _columns_in(expression, alias, table, columns):
                key = (schema, table, column, "Sort Key")
                found.setdefault(
                    key,
                    _candidate(
                        schema,
                        table,
                        column,
                        "Sort Key",
                        expression,
                        (schema, table, column) in existing,
                    ),
                )
    return tuple(found.values())


def _candidate(
    schema: str,
    table: str,
    column: str,
    kind: str,
    evidence: str,
    existing: bool,
) -> IndexOpportunity:
    status = "já possui índice equivalente" if existing else "não há índice equivalente no catálogo"
    return IndexOpportunity(
        schema=schema,
        table=table,
        column=column,
        access_method="btree",
        evidence_kind=kind,
        evidence=evidence,
        justification=f"Coluna identificada em {kind}: {evidence}; {status}.",
        existing_equivalent=existing,
    )


def _columns_in(
    expression: str,
    alias: str | None,
    table: str,
    catalog_columns: set[tuple[str, str, str]],
) -> tuple[str, ...]:
    matches: list[str] = []
    for match in _REFERENCE.finditer(expression):
        qualifier = match.group("qualifier")
        column = match.group("column")
        if column.lower() in _SQL_WORDS:
            continue
        if qualifier and qualifier not in {alias, table}:
            continue
        if (
            any(
                item_table == table and item_column == column
                for _, item_table, item_column in catalog_columns
            )
            and column not in matches
        ):
            matches.append(column)
    return tuple(matches)


def _join_columns(
    expression: str,
    relations: dict[str, str],
    table_schemas: dict[str, str],
    catalog_columns: set[tuple[str, str, str]],
) -> tuple[tuple[str, str, str], ...]:
    result: list[tuple[str, str, str]] = []
    for match in _REFERENCE.finditer(expression):
        qualifier = match.group("qualifier")
        column = match.group("column")
        table = relations.get(qualifier or "")
        if not qualifier or table is None or table not in table_schemas:
            continue
        schema = table_schemas[table]
        if (schema, table, column) in catalog_columns and (schema, table, column) not in result:
            result.append((schema, table, column))
    return tuple(result)


def _relations(root: PlanNode) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in _walk(root):
        if node.relation:
            result[node.relation.name] = node.relation.name
            if node.relation.alias:
                result[node.relation.alias] = node.relation.name
    return result


def _table_schemas(catalog: Catalog) -> dict[str, str]:
    grouped: dict[str, set[str]] = {}
    for table in catalog.tables:
        grouped.setdefault(table.name, set()).add(table.schema)
    return {table: next(iter(schemas)) for table, schemas in grouped.items() if len(schemas) == 1}


def _existing_first_columns(catalog: Catalog) -> set[tuple[str, str, str]]:
    result: set[tuple[str, str, str]] = set()
    for index in catalog.indexes:
        match = re.search(r"\(\s*\"?([A-Za-z_][\w]*)\"?", index.definition)
        if match:
            result.add((index.schema, index.table, match.group(1)))
    return result


def _walk(node: PlanNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _walk_with_context(
    node: PlanNode,
    table: str | None = None,
    alias: str | None = None,
):
    current_table = node.relation.name if node.relation else table
    current_alias = node.relation.alias if node.relation else alias
    if current_table is None:
        descendants = {
            descendant.relation.name
            for descendant in _walk(node)
            if descendant.relation is not None
        }
        if len(descendants) == 1:
            current_table = next(iter(descendants))
            current_alias = next(
                descendant.relation.alias
                for descendant in _walk(node)
                if descendant.relation is not None and descendant.relation.name == current_table
            )
    yield node, current_table, current_alias
    for child in node.children:
        yield from _walk_with_context(child, current_table, current_alias)
