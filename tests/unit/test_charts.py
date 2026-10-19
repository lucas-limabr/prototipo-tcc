import json
from pathlib import Path

import pytest

from index_optimizer.database.benchmark import BenchmarkSummary, Measurement
from index_optimizer.database.charts import (
    ChartDataError,
    extract_performance_chart_data,
    report_from_json,
    save_performance_chart,
)
from index_optimizer.database.comparison import (
    ComparisonStatus,
    PerformanceComparison,
)
from index_optimizer.database.reporting import build_report, report_to_json


def _benchmark(median: float) -> BenchmarkSummary:
    measurements = tuple(
        Measurement(
            run=index,
            server_time_ms=value,
            planning_time_ms=None,
            execution_time_ms=value,
            rows=1,
            buffers={},
        )
        for index, value in enumerate((median - 1, median + 1), start=1)
    )
    return BenchmarkSummary(
        sql="SELECT 1",
        warmups=1,
        requested_runs=2,
        measurements=measurements,
        errors=(),
        mean_server_time_ms=median,
        median_server_time_ms=median,
        min_server_time_ms=median - 1,
        max_server_time_ms=median + 1,
        stdev_server_time_ms=1,
    )


def _report():
    baseline = _benchmark(10)
    after = _benchmark(5)
    comparison = PerformanceComparison(
        sql="SELECT 1",
        status=ComparisonStatus.IMPROVED,
        baseline_median_ms=10,
        after_median_ms=5,
        reduction_percent=50,
        speedup=2,
        result_rows_equal=True,
        plan_changed=None,
        created_indexes=(),
        explanation="ok",
        limitations=(),
    )
    return build_report(
        "SELECT 1",
        condition={},
        baseline=baseline,
        after=after,
        comparison=comparison,
    )


def test_chart_creates_stable_path_and_directory(tmp_path: Path):
    report = _report()

    output = save_performance_chart(report, tmp_path / "charts")

    assert output == tmp_path / "charts" / f"{report.experiment_id}-performance.png"
    assert output.is_file()


def test_chart_rejects_incomplete_report():
    with pytest.raises(ChartDataError, match="baseline, after e comparison"):
        extract_performance_chart_data(build_report("SELECT 1", condition={}))


def test_report_json_round_trip_for_chart(tmp_path: Path):
    report_path = tmp_path / "report.json"
    report_path.write_text(report_to_json(_report()), encoding="utf-8")

    loaded = report_from_json(report_path)

    assert extract_performance_chart_data(loaded).after_median_ms == 5


def test_historical_aggregate_report_creates_chart(tmp_path: Path):
    from index_optimizer.database.charts import report_from_json

    report_path = Path(__file__).parents[2] / "docs" / "experimentos" / "fase15-filtro-uf.json"
    report = report_from_json(report_path)

    output = save_performance_chart(report, tmp_path)

    assert output.is_file()
    assert extract_performance_chart_data(report).baseline_median_ms == 854.946


def test_cli_plot_reads_report_and_prints_path(tmp_path: Path, capsys):
    from index_optimizer.cli import main

    report_path = tmp_path / "report.json"
    report_path.write_text(report_to_json(_report()), encoding="utf-8")

    assert main(["plot", "--report", str(report_path), "--output-dir", str(tmp_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert Path(payload["path"]).is_file()
