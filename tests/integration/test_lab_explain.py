import pytest

from index_optimizer.config import load_settings
from index_optimizer.database.explain import explain_query

pytestmark = pytest.mark.integration


def test_lab_explain_returns_estimated_plan(monkeypatch):
    monkeypatch.setenv("IXO_ALLOWED_SCHEMAS", "cnpj")

    result = explain_query(
        load_settings(),
        "SELECT cnpj_basico FROM cnpj.empresa LIMIT 1",
        allowed_schemas={"cnpj"},
    )

    assert result.plan["Node Type"]
    assert result.raw[0]["Plan"] == result.plan
