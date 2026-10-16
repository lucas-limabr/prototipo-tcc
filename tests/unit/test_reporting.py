import json
from datetime import UTC, datetime

from index_optimizer.database.index_apply import IndexApplyResult, generate_index_ddl
from index_optimizer.database.recommendations import (
    IndexRecommendation,
    RecommendationStatus,
)
from index_optimizer.database.reporting import build_report, report_to_json, report_to_markdown


def test_report_has_stable_id_and_structured_json():
    report = build_report(
        "SELECT 1",
        condition={"database": "index_lab", "phase": 13},
        limitations=("Amostra pequena.",),
    )

    payload = json.loads(report_to_json(report))

    assert (
        report.experiment_id
        == build_report(
            "SELECT 1",
            condition={"phase": 13, "database": "index_lab"},
        ).experiment_id
    )
    assert payload["query"] == "SELECT 1"
    assert payload["limitations"] == ["Amostra pequena."]


def test_markdown_explicitly_reports_empty_recommendations():
    report = build_report("SELECT 1", condition={"phase": 13})

    markdown = report_to_markdown(report)

    assert "Nenhuma recomendação registrada." in markdown
    assert report.experiment_id in markdown


def test_json_serializes_applied_index_ddl():
    recommendation = IndexRecommendation(
        schema="public",
        table="items",
        columns=("category",),
        access_method="btree",
        status=RecommendationStatus.RECOMMENDED,
        justification="Filtro observado.",
        limitations=(),
        evidence_kind="Filter",
        evidence="category = 'target'",
    )
    ddl = generate_index_ddl(recommendation)
    assert ddl is not None
    result = IndexApplyResult(ddl, "CREATED", datetime.now(UTC), "ok")

    payload = json.loads(
        report_to_json(build_report("SELECT 1", condition={}, applied_indexes=(result,)))
    )

    assert payload["applied_indexes"][0]["ddl"]["name"] == ddl.name
