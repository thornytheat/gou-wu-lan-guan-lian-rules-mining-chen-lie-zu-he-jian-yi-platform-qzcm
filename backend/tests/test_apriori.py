"""算法 1：Apriori 频繁项集 + 关联规则指标（support/confidence/lift/conviction）。

全部为纯函数测试：不连 DB、不 mock 算法，输入是 frozenset 小票，期望值手算。
"""
from __future__ import annotations

import random

import pytest

from src.services.apriori_service import (
    CONVICTION_CAP,
    apriori,
    build_rules,
    rule_counterexamples,
)

# 10 张小票（A=8 / B=6 / C=5，AB=4 / AC=4 / BC=3，ABC=2），手算基数便于逐项核对。
BASKETS: list[frozenset[str]] = [
    frozenset({"A", "B", "C"}),
    frozenset({"A", "B"}),
    frozenset({"A", "C"}),
    frozenset({"A", "B", "C"}),
    frozenset({"A"}),
    frozenset({"B", "C"}),
    frozenset({"A", "B"}),
    frozenset({"A", "C"}),
    frozenset({"B"}),
    frozenset({"A"}),
]
N = len(BASKETS)


def counts_of(min_support: float, max_itemset: int = 3) -> dict:
    return apriori(BASKETS, min_support=min_support, max_itemset=max_itemset)["counts"]


# ------------------------------------------------------------------ 正常路径


def test_frequent_itemsets_and_supports_hand_computed() -> None:
    """min_support=0.2（min_count=2）→ 3 单品 + 3 对 + 1 三元组 = 7 个频繁项集。"""
    result = apriori(BASKETS, min_support=0.2, max_itemset=3)

    assert result["basket_count"] == N == 10
    assert result["min_count"] == 2  # max(1, ceil(0.2 * 10))
    assert result["frequent_itemsets"] == 7
    assert result["by_size"] == {1: 3, 2: 3, 3: 1}

    # 排序口径：size 升序 → count 降序 → items 字典序
    assert [row["items"] for row in result["itemsets"]] == [
        ["A"],
        ["B"],
        ["C"],
        ["A", "B"],
        ["A", "C"],
        ["B", "C"],
        ["A", "B", "C"],
    ]
    assert [row["count"] for row in result["itemsets"]] == [8, 6, 5, 4, 4, 3, 2]
    assert [row["support"] for row in result["itemsets"]] == pytest.approx(
        [0.8, 0.6, 0.5, 0.4, 0.4, 0.3, 0.2], abs=1e-6
    )
    assert result["counts"][frozenset({"A", "B", "C"})] == 2


def test_build_rules_metrics_hand_computed() -> None:
    """min_confidence=0.5 → 9 条方向规则；A→B 与 {B,C}→{A} 逐字段手算。"""
    counts = counts_of(0.2)
    rules = build_rules(counts, N, min_confidence=0.5)
    by_key = {rule["rule_key"]: rule for rule in rules}

    assert len(rules) == 9
    assert set(by_key) == {
        "A>B",
        "B>A",
        "A>C",
        "C>A",
        "B>C",
        "C>B",
        "A+B>C",
        "A+C>B",
        "B+C>A",
    }

    # A→B：support=4/10=0.4；conf=4/8=0.5；lift=0.5/sup(B=0.6)=0.833333；conv=(1-0.6)/(1-0.5)=0.8
    ab = by_key["A>B"]
    assert ab["antecedent"] == ["A"]
    assert ab["consequent"] == ["B"]
    assert ab["support"] == pytest.approx(0.4, abs=1e-6)
    assert ab["confidence"] == pytest.approx(0.5, abs=1e-6)
    assert ab["lift"] == pytest.approx(0.833333, abs=1e-6)
    assert ab["conviction"] == pytest.approx(0.8, abs=1e-6)
    assert ab["cooccur_count"] == 4

    # {B,C}→{A}：support=2/10；conf=2/3=0.666667；lift=(2/3)/0.8=0.833333；conv=(1-0.8)/(1-2/3)=0.6
    bc_a = by_key["B+C>A"]
    assert bc_a["support"] == pytest.approx(0.2, abs=1e-6)
    assert bc_a["confidence"] == pytest.approx(0.666667, abs=1e-6)
    assert bc_a["lift"] == pytest.approx(0.833333, abs=1e-6)
    assert bc_a["conviction"] == pytest.approx(0.6, abs=1e-6)

    # 全量排序：lift 降序，同 lift 时 confidence 降序
    lifts = [rule["lift"] for rule in rules]
    assert all(lifts[i] >= lifts[i + 1] for i in range(len(lifts) - 1))
    for prev, nxt in zip(rules, rules[1:]):
        if prev["lift"] == nxt["lift"]:
            assert prev["confidence"] >= nxt["confidence"]
    # 每条规则的 support 必须等于共现计数 / 总小票数
    for rule in rules:
        assert rule["support"] == pytest.approx(rule["cooccur_count"] / N, abs=1e-6)


def test_max_itemset_caps_itemset_size() -> None:
    """max_itemset=2 → 三元组不产出（6 个项集，by_size 只有 1/2）。"""
    result = apriori(BASKETS, min_support=0.2, max_itemset=2)

    assert result["by_size"] == {1: 3, 2: 3}
    assert result["frequent_itemsets"] == 6
    assert all(row["size"] <= 2 for row in result["itemsets"])
    assert frozenset({"A", "B", "C"}) not in result["counts"]


def test_conviction_capped_when_confidence_is_one() -> None:
    """后项全含 → confidence=1.0，conviction 记上限 9999（除零保护，文档化口径）。"""
    baskets = [frozenset({"A", "B"}) for _ in range(4)]
    result = apriori(baskets, min_support=0.5, max_itemset=2)
    rules = build_rules(result["counts"], result["basket_count"], min_confidence=0.5)
    by_key = {rule["rule_key"]: rule for rule in rules}

    assert CONVICTION_CAP == 9999.0
    assert by_key["A>B"]["confidence"] == pytest.approx(1.0, abs=1e-6)
    assert by_key["A>B"]["lift"] == pytest.approx(1.0, abs=1e-6)
    assert by_key["A>B"]["conviction"] == pytest.approx(9999.0, abs=1e-6)


def test_rule_counterexamples_counts_antecedent_without_consequent() -> None:
    """反例 = 含前项但不含后项的小票数：{A}→{B} 为 8-4=4；{A}→{B,C} 为 8-2=6。"""
    assert rule_counterexamples(BASKETS, ["A"], ["B"]) == 4
    assert rule_counterexamples(BASKETS, ["A"], ["B", "C"]) == 6
    assert rule_counterexamples(BASKETS, ["A", "B"], ["C"]) == 2  # AB 里 4 张，含 C 的 2 张


# ------------------------------------------------------------------ 边界/异常


def test_apriori_empty_transactions_raises_value_error() -> None:
    """空样本必须显式报错，不许返回空结果冒充「无关联」。"""
    with pytest.raises(ValueError) as exc:
        apriori([], min_support=0.01)
    assert "小票样本为空" in str(exc.value)


def test_apriori_single_basket_boundary() -> None:
    """单张小票：min_count=1，所有子集（3 个）都频繁，support 全为 1.0。"""
    result = apriori([frozenset({"A", "B"})], min_support=0.5, max_itemset=3)

    assert result["basket_count"] == 1
    assert result["min_count"] == 1
    assert result["by_size"] == {1: 2, 2: 1}
    assert [row["support"] for row in result["itemsets"]] == pytest.approx([1.0, 1.0, 1.0])
    rules = build_rules(result["counts"], result["basket_count"], min_confidence=0.5)
    assert [rule["rule_key"] for rule in rules] == ["A>B", "B>A"]
    assert all(rule["conviction"] == pytest.approx(CONVICTION_CAP) for rule in rules)


def test_apriori_all_identical_baskets_zero_variance() -> None:
    """全相同小票（零方差）：7 个项集全 support=1.0，不出现 0 除。"""
    baskets = [frozenset({"A", "B", "C"}) for _ in range(5)]
    result = apriori(baskets, min_support=0.2, max_itemset=3)

    assert result["frequent_itemsets"] == 7
    assert result["by_size"] == {1: 3, 2: 3, 3: 1}
    assert {row["support"] for row in result["itemsets"]} == {1.0}


def test_apriori_min_support_one_keeps_only_universal_items() -> None:
    """min_support=1.0 → min_count=n，只有每张都出现的单品保留。"""
    baskets = [frozenset({"A", "B"}), frozenset({"A", "B"}), frozenset({"A"})]
    result = apriori(baskets, min_support=1.0, max_itemset=3)

    assert result["min_count"] == 3
    assert [row["items"] for row in result["itemsets"]] == [["A"]]
    assert result["by_size"] == {1: 1}
    assert frozenset({"B"}) not in result["counts"]


def test_apriori_itemset_below_threshold_is_absent() -> None:
    """min_support=0.35 → min_count=4：BC(3)/ABC(2) 必须被剪掉。"""
    result = apriori(BASKETS, min_support=0.35, max_itemset=3)

    assert result["min_count"] == 4  # ceil(0.35 * 10) = 4
    assert result["by_size"] == {1: 3, 2: 2}
    assert frozenset({"B", "C"}) not in result["counts"]
    assert frozenset({"A", "B", "C"}) not in result["counts"]


def test_apriori_is_deterministic_and_order_independent() -> None:
    """乱序输入 → 同一批频繁项集与规则（顺序无关 + 确定性）。"""
    first = apriori(BASKETS, min_support=0.2, max_itemset=3)
    shifted = list(BASKETS)
    random.Random(20261112).shuffle(shifted)
    second = apriori(shifted, min_support=0.2, max_itemset=3)

    assert second == first
    assert build_rules(second["counts"], second["basket_count"], 0.5) == build_rules(
        first["counts"], first["basket_count"], 0.5
    )
