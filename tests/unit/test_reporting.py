import json

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
