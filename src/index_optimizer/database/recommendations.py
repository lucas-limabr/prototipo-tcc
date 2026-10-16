from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from index_optimizer.database.opportunities import IndexOpportunity


class RecommendationStatus(StrEnum):
    RECOMMENDED = "RECOMENDADO"
    NOT_RECOMMENDED = "NAO_RECOMENDADO"
    INDETERMINATE = "INDETERMINADO"
    EXISTING_EQUIVALENT = "JA_EXISTE_EQUIVALENTE"


@dataclass(frozen=True)
class IndexRecommendation:
    schema: str
    table: str
    columns: tuple[str, ...]
    access_method: str
    status: RecommendationStatus
    justification: str
    limitations: tuple[str, ...]
    evidence_kind: str | None
    evidence: str | None


@dataclass(frozen=True)
class RecommendationReport:
    recommendations: tuple[IndexRecommendation, ...]

    @property
    def has_recommendations(self) -> bool:
        return any(item.status is RecommendationStatus.RECOMMENDED for item in self.recommendations)


def recommend_indexes(
    opportunities: tuple[IndexOpportunity, ...],
) -> RecommendationReport:
    """Apply conservative, deterministic rules without changing the database."""
    recommendations = tuple(_recommend(opportunity) for opportunity in opportunities)
    return RecommendationReport(recommendations=recommendations)


def _recommend(opportunity: IndexOpportunity) -> IndexRecommendation:
    base = dict(
        schema=opportunity.schema,
        table=opportunity.table,
        columns=(opportunity.column,),
        access_method=opportunity.access_method,
        evidence_kind=opportunity.evidence_kind,
        evidence=opportunity.evidence,
    )
    if opportunity.existing_equivalent:
        return IndexRecommendation(
            **base,
            status=RecommendationStatus.EXISTING_EQUIVALENT,
            justification=(
                f"Não recomendar: já existe índice equivalente para "
                f"{opportunity.schema}.{opportunity.table} ({opportunity.column})."
            ),
            limitations=(
                "A equivalência foi verificada pela primeira coluna da definição do índice.",
            ),
        )
    if opportunity.evidence_kind == "Sort Key":
        return IndexRecommendation(
            **base,
            status=RecommendationStatus.INDETERMINATE,
            justification=(
                f"Ordenação por {opportunity.column} foi observada, mas isso "
                "isoladamente não prova benefício de um índice."
            ),
            limitations=(
                "Não há seletividade, frequência da consulta ou custo comparativo "
                "pré/pós-indexação.",
            ),
        )
    if opportunity.evidence_kind in {
        "Filter",
        "Index Cond",
        "Join Filter",
        "Hash Cond",
        "Merge Cond",
    }:
        return IndexRecommendation(
            **base,
            status=RecommendationStatus.RECOMMENDED,
            justification=(
                f"Recomendar índice B-tree simples em {opportunity.schema}."
                f"{opportunity.table} ({opportunity.column}) por evidência "
                f"de {opportunity.evidence_kind}."
            ),
            limitations=(
                "A recomendação é preliminar e deve ser confirmada por medições.",
                "Não são gerados índices compostos automaticamente.",
            ),
        )
    return IndexRecommendation(
        **base,
        status=RecommendationStatus.NOT_RECOMMENDED,
        justification="A evidência não pertence às regras conservadoras suportadas.",
        limitations=("A regra não foi classificada para recomendação automática.",),
    )
