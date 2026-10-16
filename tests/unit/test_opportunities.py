from index_optimizer.database.catalog import Catalog, ColumnInfo, IndexInfo, TableInfo
from index_optimizer.database.opportunities import extract_opportunities
from index_optimizer.database.plan_parser import parse_plan


def _catalog(indexes=()):
    return Catalog(
        schemas=(),
        tables=(TableInfo("cnpj", "empresa", "BASE TABLE"),),
        columns=(
            ColumnInfo("cnpj", "empresa", 1, "cnpj_basico", "text", "text", False, None),
            ColumnInfo("cnpj", "empresa", 2, "razao_social", "text", "text", True, None),
        ),
        constraints=(),
        indexes=tuple(indexes),
    )


def test_extracts_filter_and_sort_with_explanation():
    plan = parse_plan(
        {
            "Plan": {
                "Node Type": "Sort",
                "Sort Key": ["e.razao_social"],
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "empresa",
                        "Alias": "e",
                        "Filter": "(e.cnpj_basico = '1')",
                    }
                ],
            }
        }
    )

    candidates = extract_opportunities(plan, _catalog())

    assert {(item.column, item.evidence_kind) for item in candidates} == {
        ("cnpj_basico", "Filter"),
        ("razao_social", "Sort Key"),
    }
    assert all(item.existing_equivalent is False for item in candidates)
    assert any("Filter" in item.justification for item in candidates)


def test_marks_existing_equivalent_index_and_ignores_unknown_columns():
    index = IndexInfo(
        "cnpj",
        "empresa",
        "empresa_cnpj_idx",
        "CREATE INDEX ON cnpj.empresa USING btree (cnpj_basico)",
    )
    plan = parse_plan(
        {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "empresa",
                "Filter": "(unknown_col = 'x' AND cnpj_basico = '1')",
            }
        }
    )

    candidates = extract_opportunities(plan, _catalog((index,)))

    assert len(candidates) == 1
    assert candidates[0].column == "cnpj_basico"
    assert candidates[0].existing_equivalent is True


def test_does_not_guess_when_plan_has_no_relation():
    plan = parse_plan({"Plan": {"Node Type": "Result", "Filter": "(cnpj_basico = '1')"}})

    assert extract_opportunities(plan, _catalog()) == ()


def test_extracts_both_sides_of_qualified_join_condition():
    catalog = _catalog()
    catalog = Catalog(
        schemas=catalog.schemas,
        tables=(*catalog.tables, TableInfo("cnpj", "estabelecimento", "BASE TABLE")),
        columns=(
            *catalog.columns,
            ColumnInfo("cnpj", "estabelecimento", 1, "cnpj_basico", "text", "text", False, None),
        ),
        constraints=catalog.constraints,
        indexes=catalog.indexes,
    )
    plan = parse_plan(
        {
            "Plan": {
                "Node Type": "Hash Join",
                "Hash Cond": "(e.cnpj_basico = f.cnpj_basico)",
                "Plans": [
                    {"Node Type": "Seq Scan", "Relation Name": "empresa", "Alias": "e"},
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "estabelecimento",
                        "Alias": "f",
                    },
                ],
            }
        }
    )

    candidates = extract_opportunities(plan, catalog)

    assert {(item.table, item.column) for item in candidates} == {
        ("empresa", "cnpj_basico"),
        ("estabelecimento", "cnpj_basico"),
    }
