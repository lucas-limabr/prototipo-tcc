import pytest

from index_optimizer.config import load_settings
from index_optimizer.database.connection import server_version

pytestmark = pytest.mark.integration


def test_server_version_is_postgres_17():
    version = server_version(load_settings())
    assert version.startswith("PostgreSQL 17")
