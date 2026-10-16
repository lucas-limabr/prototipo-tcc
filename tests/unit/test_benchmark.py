from unittest.mock import MagicMock, call, patch

import pytest

from index_optimizer.database.benchmark import benchmark_query
from index_optimizer.errors import UnsupportedQueryError


def _settings():
    return MagicMock()


def _connection(payload):
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = [payload]
    return connection


def test_benchmark_separates_warmup_and_returns_statistics():
    payload = [
        {
            "Plan": {"Node Type": "Result", "Actual Rows": 1},
            "Planning Time": 0.2,
            "Execution Time": 4.0,
        }
    ]
    connection = _connection(payload)
    with patch("index_optimizer.database.benchmark.connect") as connect:
        connect.return_value.__enter__.return_value = connection
        result = benchmark_query(_settings(), "SELECT 1", runs=2, warmups=1)

    assert result.valid_runs == 2
    assert result.mean_server_time_ms == 4.0
    assert result.median_server_time_ms == 4.0
    assert result.measurements[0].rows == 1.0
    assert connection.execute.call_args_list.count(call("SET TRANSACTION READ ONLY")) == 3


def test_benchmark_discards_failed_measurement_and_records_error():
    connection = MagicMock()
    connection.execute.return_value.fetchone.side_effect = [
        [[{"Plan": {"Node Type": "Result"}}]],
        [[{"Plan": {"Node Type": "Result"}, "Execution Time": 3.0}]],
    ]
    with patch("index_optimizer.database.benchmark.connect") as connect:
        connect.return_value.__enter__.return_value = connection
        with pytest.raises(UnsupportedQueryError, match="1"):
            benchmark_query(_settings(), "SELECT 1", runs=2, warmups=0)


def test_benchmark_requires_two_valid_measurements():
    connection = _connection([{"Plan": {"Node Type": "Result"}}])
    with patch("index_optimizer.database.benchmark.connect") as connect:
        connect.return_value.__enter__.return_value = connection
        with pytest.raises(UnsupportedQueryError, match="suficientes"):
            benchmark_query(_settings(), "SELECT 1", runs=1, warmups=0)
