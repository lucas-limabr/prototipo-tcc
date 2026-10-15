import pytest

from index_optimizer.database.plan_parser import parse_plan
from index_optimizer.errors import UnsupportedQueryError


def test_parses_nested_scan_join_and_sort_nodes():
    raw = [
        {
            "Plan": {
                "Node Type": "Sort",
                "Startup Cost": 10.0,
                "Total Cost": 20.0,
                "Plan Rows": 4,
                "Plan Width": 32,
                "Sort Key": ["e.razao_social"],
                "Plans": [
                    {
                        "Node Type": "Nested Loop",
                        "Join Filter": "(e.id = f.id)",
                        "Plans": [
                            {
                                "Node Type": "Index Scan",
                                "Relation Name": "empresa",
                                "Alias": "e",
                                "Index Cond": "(cnpj_basico = '1')",
                                "Plan Rows": 1,
                            },
                            {
                                "Node Type": "Seq Scan",
                                "Relation Name": "estabelecimento",
                                "Filter": "(uf = 'SP')",
                            },
                        ],
                    }
                ],
            }
        }
    ]

    result = parse_plan(raw)
    assert result.raw is raw
    assert result.root.node_type == "Sort"
    assert result.root.sort_keys == ("e.razao_social",)
    join = result.root.children[0]
    assert join.conditions[0].kind == "Join Filter"
    assert join.children[0].relation == type(join.children[0].relation)("empresa", "e")
    assert join.children[1].conditions[0].expression == "(uf = 'SP')"


def test_optional_fields_can_be_absent():
    result = parse_plan({"Plan": {"Node Type": "Result"}})

    assert result.root.relation is None
    assert result.root.conditions == ()
    assert result.root.children == ()
    assert result.root.plan_rows is None


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"Plan": {"Node Type": "Seq Scan", "Plans": {}}},
        {"Plan": {"Node Type": "Seq Scan", "Plan Rows": "many"}},
        [{"Plan": {"Relation Name": "empresa"}}],
    ],
)
def test_rejects_malformed_plans(value):
    with pytest.raises(UnsupportedQueryError):
        parse_plan(value)
