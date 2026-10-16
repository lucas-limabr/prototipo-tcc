from index_optimizer.database.opportunities import IndexOpportunity
from index_optimizer.database.recommendations import (
    RecommendationStatus,
    recommend_indexes,
)


def _opportunity(kind: str, existing: bool = False) -> IndexOpportunity:
    return IndexOpportunity(
        schema="cnpj",
        table="empresa",
        column="cnpj_basico",
        access_method="btree",
        evidence_kind=kind,
        evidence="(cnpj_basico = '1')",
        justification="evidência de teste",
        existing_equivalent=existing,
    )


def test_recommends_filter_with_explicit_rule_and_limitations():
    report = recommend_indexes((_opportunity("Filter"),))

    recommendation = report.recommendations[0]
    assert recommendation.status is RecommendationStatus.RECOMMENDED
    assert recommendation.columns == ("cnpj_basico",)
    assert "B-tree" in recommendation.justification
    assert recommendation.limitations
    assert report.has_recommendations is True


def test_existing_index_is_not_recommended_again():
    report = recommend_indexes((_opportunity("Hash Cond", existing=True),))

    recommendation = report.recommendations[0]
    assert recommendation.status is RecommendationStatus.EXISTING_EQUIVALENT
    assert report.has_recommendations is False


def test_sort_alone_is_indeterminate():
    report = recommend_indexes((_opportunity("Sort Key"),))

    assert report.recommendations[0].status is RecommendationStatus.INDETERMINATE
    assert "isoladamente" in report.recommendations[0].justification


def test_empty_opportunities_produce_valid_empty_report():
    report = recommend_indexes(())

    assert report.recommendations == ()
    assert report.has_recommendations is False
