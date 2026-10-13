import pytest

from index_optimizer import __version__
from index_optimizer.cli import main
from index_optimizer.errors import ExitCode


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("analyze", "benchmark", "optimize"):
        assert cmd in out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    assert main([]) == ExitCode.OK
    assert "usage" in capsys.readouterr().out


def test_subcommand_not_implemented(capsys):
    assert main(["analyze", "--query", "SELECT 1"]) == ExitCode.UNEXPECTED
    assert "não está implementado" in capsys.readouterr().err


def test_query_source_required():
    with pytest.raises(SystemExit) as exc:
        main(["analyze"])
    assert exc.value.code == 2


def test_dry_run_and_apply_are_exclusive():
    with pytest.raises(SystemExit) as exc:
        main(["optimize", "--query", "SELECT 1", "--dry-run", "--apply-indexes"])
    assert exc.value.code == 2
