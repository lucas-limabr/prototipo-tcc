import socket

import pytest

from index_optimizer.cli import main
from index_optimizer.config import load_settings
from index_optimizer.database.connection import connect
from index_optimizer.errors import ConnectionFailedError, ExitCode


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _env(port: int) -> dict[str, str]:
    return {
        "IXO_DB_HOST": "127.0.0.1",
        "IXO_DB_PORT": str(port),
        "IXO_DB_NAME": "lab",
        "IXO_DB_USER": "u",
        "IXO_DB_PASSWORD": "super-secret-pw",
        "IXO_CONNECT_TIMEOUT_S": "2",
    }


def test_unreachable_server_raises_clear_error():
    settings = load_settings(_env(_free_port()))
    with pytest.raises(ConnectionFailedError) as exc, connect(settings):
        pass
    message = str(exc.value)
    assert "Não foi possível conectar" in message
    assert "super-secret-pw" not in message
    assert exc.value.exit_code == ExitCode.CONNECTION_FAILURE


def test_cli_check_connection_failure(monkeypatch, capsys):
    for key, value in _env(_free_port()).items():
        monkeypatch.setenv(key, value)
    assert main(["check-connection"]) == ExitCode.CONNECTION_FAILURE
    assert "Não foi possível conectar" in capsys.readouterr().err


def test_cli_check_connection_missing_config(monkeypatch):
    for key in ("IXO_DB_NAME", "IXO_DB_USER", "IXO_DB_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    assert main(["check-connection"]) == ExitCode.INVALID_INPUT
