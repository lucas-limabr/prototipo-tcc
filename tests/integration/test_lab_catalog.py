import pytest

from index_optimizer.config import load_settings
from index_optimizer.database.catalog import inspect_database_catalog

pytestmark = pytest.mark.integration


def test_lab_catalog_lists_loaded_cnpj_objects(monkeypatch):
    monkeypatch.setenv("IXO_ALLOWED_SCHEMAS", "cnpj")

    catalog = inspect_database_catalog(load_settings())

    assert "cnpj" in {schema.name for schema in catalog.schemas}
    assert {"empresa", "estabelecimento", "socio"} <= {table.name for table in catalog.tables}
    assert any(index.table == "estabelecimento" for index in catalog.indexes)
    assert any(constraint.constraint_type == "FOREIGN KEY" for constraint in catalog.constraints)
