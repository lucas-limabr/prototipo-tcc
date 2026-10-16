from __future__ import annotations

import pytest

from index_optimizer.config import load_settings
from index_optimizer.database.benchmark import benchmark_query
from index_optimizer.database.catalog import inspect_database_catalog
from index_optimizer.database.connection import connect
from index_optimizer.database.explain import explain_query
from index_optimizer.database.index_apply import apply_indexes, dry_run
from index_optimizer.database.opportunities import extract_opportunities
from index_optimizer.database.plan_parser import parse_plan
from index_optimizer.database.recommendations import recommend_indexes

pytestmark = pytest.mark.integration

SCHEMA = "ixo_fase14"
TABLE = "items"
QUERY = f"SELECT id FROM {SCHEMA}.{TABLE} WHERE category = 'target'"


@pytest.fixture
def lab_settings(monkeypatch):
    monkeypatch.setenv("IXO_ALLOWED_SCHEMAS", SCHEMA)
    settings = load_settings()
    _prepare_fixture(settings)
    try:
        yield settings
    finally:
        _drop_fixture(settings)


def test_full_flow_validates_explains_recommends_measures_and_applies(lab_settings):
    estimated = explain_query(lab_settings, QUERY, allowed_schemas={SCHEMA})
    parsed = parse_plan(estimated.raw)
    catalog_before = inspect_database_catalog(lab_settings)
    opportunities = extract_opportunities(parsed, catalog_before)
    recommendations = recommend_indexes(opportunities)

    assert parsed.root.node_type
    assert any(item.column == "category" for item in opportunities)
    assert recommendations.has_recommendations

    ddls = dry_run(recommendations.recommendations)
    assert len(ddls) == 1
    assert ddls[0].schema == SCHEMA
    assert ddls[0].table == TABLE

    baseline = benchmark_query(
        lab_settings,
        QUERY,
        runs=2,
        warmups=1,
        allowed_schemas={SCHEMA},
    )
    applied = apply_indexes(lab_settings, recommendations.recommendations, apply=True)
    catalog_after = inspect_database_catalog(lab_settings)
    after = benchmark_query(
        lab_settings,
        QUERY,
        runs=2,
        warmups=1,
        allowed_schemas={SCHEMA},
    )

    assert applied[0].status == "CREATED"
    assert any(index.name == applied[0].ddl.name for index in catalog_after.indexes)
    assert baseline.valid_runs == after.valid_runs == 2


def test_query_without_useful_opportunity_does_not_change_structure(lab_settings):
    query = f"SELECT id FROM {SCHEMA}.{TABLE}"
    before = inspect_database_catalog(lab_settings)

    estimated = explain_query(lab_settings, query, allowed_schemas={SCHEMA})
    opportunities = extract_opportunities(parse_plan(estimated.raw), before)
    recommendations = recommend_indexes(opportunities)

    assert opportunities == ()
    assert recommendations.recommendations == ()
    assert dry_run(recommendations.recommendations) == ()
    assert inspect_database_catalog(lab_settings).indexes == before.indexes


def _prepare_fixture(settings) -> None:
    with connect(settings) as conn, conn.transaction():
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        conn.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{TABLE}")
        conn.execute(
            f"""
            CREATE TABLE {SCHEMA}.{TABLE} (
                id integer PRIMARY KEY,
                category text NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            INSERT INTO {SCHEMA}.{TABLE} (id, category)
            SELECT value, CASE WHEN value % 2 = 0 THEN 'target' ELSE 'other' END
            FROM generate_series(1, 200) AS value
            """
        )


def _drop_fixture(settings) -> None:
    with connect(settings) as conn, conn.transaction():
        conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
