from index_optimizer.database.benchmark import BenchmarkSummary, Measurement
from index_optimizer.database.comparison import ComparisonStatus, compare_benchmarks


def _summary(sql="SELECT 1", median=10.0, rows=1.0, runs=2):
    measurements = tuple(Measurement(i, median, 0.1, median, rows, {}) for i in range(1, runs + 1))
    return BenchmarkSummary(
        sql,
        1,
        runs,
        measurements,
        (),
        median,
        median,
        median,
        median,
        0.0,
    )


def test_reports_improvement_reduction_speedup_and_equal_results():
    result = compare_benchmarks(_summary(), _summary(median=5.0))

    assert result.status is ComparisonStatus.IMPROVED
    assert result.reduction_percent == 50.0
    assert result.speedup == 2.0
    assert result.result_rows_equal is True


def test_distinguishes_regression_and_no_relevant_change():
    assert (
        compare_benchmarks(_summary(), _summary(median=20.0)).status is ComparisonStatus.REGRESSED
    )
    assert (
        compare_benchmarks(_summary(), _summary(median=10.2)).status is ComparisonStatus.UNCHANGED
    )


def test_rejects_incomparable_protocol_or_changed_result_count():
    result = compare_benchmarks(_summary(), _summary(sql="SELECT 2"))
    assert result.status is ComparisonStatus.INCONCLUSIVE

    result = compare_benchmarks(_summary(), _summary(rows=2.0))
    assert result.status is ComparisonStatus.INCONCLUSIVE
    assert result.result_rows_equal is False
