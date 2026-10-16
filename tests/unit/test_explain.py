from unittest.mock import MagicMock, patch

from index_optimizer.database.explain import explain_query


def test_explain_preserves_raw_json_and_does_not_analyze():
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = [
        [{"Plan": {"Node Type": "Result", "Plan Rows": 1}}]
    ]
    settings = MagicMock()
    with patch("index_optimizer.database.explain.connect") as connect:
        connect.return_value.__enter__.return_value = connection
        result = explain_query(settings, "SELECT 1")

    connection.execute.assert_any_call("SET TRANSACTION READ ONLY")
    sql = connection.execute.call_args_list[-1].args[0]
    assert sql == "EXPLAIN (FORMAT JSON) SELECT 1"
    assert "ANALYZE" not in sql
    assert result.raw[0]["Plan"]["Node Type"] == "Result"
