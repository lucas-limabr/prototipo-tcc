import json
from unittest.mock import patch

import pytest

from index_optimizer import __version__
from index_optimizer.cli import main
from index_optimizer.database.index_cleanup import CleanupResult
from index_optimizer.errors import ExitCode


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("analyze", "benchmark", "optimize", "cleanup"):
        assert cmd in out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    assert main([]) == ExitCode.OK
    assert "usage" in capsys.readouterr().out


@patch("index_optimizer.cli._run_analyze", return_value=ExitCode.OK)
def test_analyze_dispatches_to_implementation(run_analyze):
    assert main(["analyze", "--query", "SELECT 1"]) == ExitCode.OK
    run_analyze.assert_called_once()


@patch("index_optimizer.cli._run_benchmark", return_value=ExitCode.OK)
def test_benchmark_dispatches_to_implementation(run_benchmark):
    assert main(["benchmark", "--query", "SELECT 1"]) == ExitCode.OK
    run_benchmark.assert_called_once()


@patch("index_optimizer.cli._run_optimize", return_value=ExitCode.OK)
def test_optimize_dispatches_to_implementation(run_optimize):
    assert main(["optimize", "--query", "SELECT 1", "--dry-run"]) == ExitCode.OK
    run_optimize.assert_called_once()


def test_query_source_required():
    with pytest.raises(SystemExit) as exc:
        main(["analyze"])
    assert exc.value.code == 2


def test_dry_run_and_apply_are_exclusive():
    with pytest.raises(SystemExit) as exc:
        main(["optimize", "--query", "SELECT 1", "--dry-run", "--apply-indexes"])
    assert exc.value.code == 2


def test_cleanup_requires_explicit_experimental_indexes_flag():
    with pytest.raises(SystemExit) as exc:
        main(["cleanup"])
    assert exc.value.code == 2


@patch("index_optimizer.cli._run_cleanup", return_value=ExitCode.OK)
def test_cleanup_dispatches_with_explicit_flag(run_cleanup):
    assert main(["cleanup", "--experimental-indexes"]) == ExitCode.OK
    run_cleanup.assert_called_once()


@patch("index_optimizer.database.index_cleanup.cleanup_experimental_indexes")
@patch("index_optimizer.config.load_settings")
def test_cleanup_reports_success_when_no_indexes(load_settings, cleanup, capsys):
    load_settings.return_value.environment = "lab"
    cleanup.return_value = CleanupResult(removed_indexes=())

    assert main(["cleanup", "--experimental-indexes"]) == ExitCode.OK

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SUCCESS"
    assert payload["removed_count"] == 0
    assert payload["removed_indexes"] == []
    assert "Nenhum índice" in payload["message"]
