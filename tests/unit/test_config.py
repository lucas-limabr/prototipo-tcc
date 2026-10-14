import pytest

from index_optimizer.config import load_settings
from index_optimizer.errors import ConfigError

BASE = {"IXO_DB_NAME": "lab", "IXO_DB_USER": "u", "IXO_DB_PASSWORD": "secret"}


def test_defaults_are_local_lab():
    s = load_settings(BASE)
    assert s.db_host == "localhost"
    assert s.db_port == 55432
    assert s.allowed_schemas == ("public",)
    assert s.is_lab


def test_password_not_in_repr():
    assert "secret" not in repr(load_settings(BASE))


def test_missing_required_lists_all():
    with pytest.raises(ConfigError) as exc:
        load_settings({})
    for name in ("IXO_DB_NAME", "IXO_DB_USER", "IXO_DB_PASSWORD"):
        assert name in str(exc.value)


@pytest.mark.parametrize("port", ["abc", "0", "-1", "70000"])
def test_invalid_port(port):
    with pytest.raises(ConfigError):
        load_settings({**BASE, "IXO_DB_PORT": port})


def test_schemas_parsed():
    s = load_settings({**BASE, "IXO_ALLOWED_SCHEMAS": " public , dados ,"})
    assert s.allowed_schemas == ("public", "dados")


def test_empty_schemas_rejected():
    with pytest.raises(ConfigError):
        load_settings({**BASE, "IXO_ALLOWED_SCHEMAS": " , "})


@pytest.mark.parametrize(
    "extra",
    [{"IXO_ENVIRONMENT": "production"}, {"IXO_DB_HOST": "db.example.com"}],
)
def test_not_lab(extra):
    assert not load_settings({**BASE, **extra}).is_lab
