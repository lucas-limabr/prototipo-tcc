import pytest

from index_optimizer.config import Settings
from index_optimizer.database.index_apply import (
    apply_indexes,
    dry_run,
    generate_index_ddl,
)
from index_optimizer.database.recommendations import (
    IndexRecommendation,
    RecommendationStatus,
)
from index_optimizer.errors import IndexApplicationError


def _recommendation(status=RecommendationStatus.RECOMMENDED):
    return IndexRecommendation(
        schema="cnpj",
        table="empresa",
        columns=("cnpj_basico",),
        access_method="btree",
        status=status,
        justification="teste",
        limitations=(),
        evidence_kind="Filter",
        evidence="(cnpj_basico = '1')",
    )


def _settings(environment="lab"):
    return Settings(
        db_name="index_lab",
        db_user="index_lab_user",
        db_password="secret",
        db_host="localhost",
        environment=environment,
        allowed_schemas=("cnpj",),
    )


def test_generates_predictable_safe_ddl_without_opening_connection():
    ddl = generate_index_ddl(_recommendation())

    assert ddl is not None
    assert ddl.name.startswith("ixo_empresa_cnpj_basico_idx_")
    assert ddl.statement is not None


def test_dry_run_ignores_non_recommendations():
    result = dry_run((_recommendation(), _recommendation(RecommendationStatus.INDETERMINATE)))

    assert len(result) == 1


def test_apply_requires_explicit_flag_and_lab_environment():
    with pytest.raises(IndexApplicationError, match="apply=True"):
        apply_indexes(_settings(), (_recommendation(),))
    with pytest.raises(IndexApplicationError, match="laboratório"):
        apply_indexes(_settings("production"), (_recommendation(),), apply=True)
