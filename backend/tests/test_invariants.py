"""性质/不变量：比率区间、CI 有序且包住点估计、计数守恒、确定性、阈值单调。

这些不是「再算一遍」，而是换个角度卡住算法口径：任何一处实现漂移都会破坏其中一条。
"""
from __future__ import annotations

import random

import pytest

from src.services.apriori_service import apriori, build_rules
from src.services.planogram_core import assign_positions, select_slots
from src.services.stability_service import analyze_rule

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
TIERS = ["high", "mid", "low"]


def with_tiers(baskets: list[frozenset[str]]) -> list[tuple[frozenset[str], str]]:
    return [(basket, TIERS[index % len(TIERS)]) for index, basket in enumerate(baskets)]


def test_supports_and_confidences_stay_in_unit_interval() -> None:
    """support/confidence ∈ [0,1]；lift > 0；conviction ≥ 0（无穷大已封顶）。"""
    result = apriori(BASKETS, min_support=0.2, max_itemset=3)
    rules = build_rules(result["counts"], result["basket_count"], min_confidence=0.5)

    assert result["frequent_itemsets"] == 7
    for row in result["itemsets"]:
        assert 0.0 < row["support"] <= 1.0
        assert row["count"] >= result["min_count"]
        assert row["size"] == len(row["items"])
    assert len(rules) == 9
    for rule in rules:
        assert 0.0 < rule["support"] <= 1.0
        assert 0.0 < rule["confidence"] <= 1.0
        assert rule["lift"] > 0.0
        assert 0.0 <= rule["conviction"] <= 9999.0


def test_ci_bounds_bracket_lift_and_are_ordered() -> None:
    """CI 下界 < 上界，且点估计 lift 落在区间内（总体与每一层都要成立）。"""
    transactions = with_tiers(BASKETS)
    result = analyze_rule(
        transactions,
        {"antecedent": ["A"], "consequent": ["B"]},
        mean_amount=40.0,
        params={"adoption_rate": 0.35, "sample_days": 7},
    )

    assert result["ci_low"] < result["ci_high"]
    assert result["ci_low"] <= result["lift"] <= result["ci_high"]
    for tier in result["tiers"]:
        assert tier["ci_low"] <= tier["ci_high"]
        if tier["baskets"]:
            assert tier["ci_low"] <= tier["lift"] <= tier["ci_high"]
        else:
            assert (tier["ci_low"], tier["ci_high"]) == (0.0, 0.0)


def test_itemset_counts_conserved_and_match_direct_recount() -> None:
    """计数守恒：by_size 求和 = 项集数 = 明细行数；每条计数与直接重数一致。"""
    result = apriori(BASKETS, min_support=0.2, max_itemset=3)

    assert sum(result["by_size"].values()) == result["frequent_itemsets"] == len(result["itemsets"])
    assert sum(result["by_size"].values()) == len(result["counts"])
    for row in result["itemsets"]:
        items = frozenset(row["items"])
        direct = sum(1 for basket in BASKETS if items <= basket)
        assert row["count"] == direct
        assert row["support"] == pytest.approx(direct / len(BASKETS), abs=1e-6)
    # 单品层计数之和 = 全部小票的商品出现次数（每张 3+2+2+3+1+2+2+2+1+1 = 19）
    single_counts = sum(row["count"] for row in result["itemsets"] if row["size"] == 1)
    assert single_counts == sum(len(basket) for basket in BASKETS) == 19


def test_deterministic_for_identical_inputs() -> None:
    """同输入两次结果完全一致（含 dict 顺序）；乱序输入不改变规则集合。"""
    first = apriori(BASKETS, min_support=0.2, max_itemset=3)
    first_rules = build_rules(first["counts"], first["basket_count"], 0.5)
    assert apriori(BASKETS, min_support=0.2, max_itemset=3) == first
    assert build_rules(first["counts"], first["basket_count"], 0.5) == first_rules

    shuffled = list(BASKETS)
    random.Random(7).shuffle(shuffled)
    second = apriori(shuffled, min_support=0.2, max_itemset=3)
    assert second["itemsets"] == first["itemsets"]
    assert build_rules(second["counts"], second["basket_count"], 0.5) == first_rules

    candidates = [
        {"rule_key": "A>B", "uplift_month": 100.0, "lift": 1.5, "conflict_group": "G1"},
        {"rule_key": "C>D", "uplift_month": 90.0, "lift": 1.2, "conflict_group": "G2"},
    ]
    assert select_slots(candidates, k=6) == select_slots(candidates, k=6)
    assert [slot["rule_key"] for slot in assign_positions(select_slots(candidates, k=6)["slots"])] == [
        "A>B",
        "C>D",
    ]


def test_threshold_monotonicity_shrinks_candidates() -> None:
    """阈值单调：提高 min_support / min_confidence 只会更严格，结果必为子集。"""
    loose = apriori(BASKETS, min_support=0.1, max_itemset=3)
    tight = apriori(BASKETS, min_support=0.35, max_itemset=3)

    assert set(tight["counts"]) < set(loose["counts"])
    assert tight["frequent_itemsets"] < loose["frequent_itemsets"]
    for itemset in tight["counts"]:
        assert tight["counts"][itemset] == loose["counts"][itemset]  # 同一项集计数不变

    loose_rules = build_rules(loose["counts"], loose["basket_count"], 0.4)
    tight_rules = build_rules(loose["counts"], loose["basket_count"], 0.7)
    loose_keys = {rule["rule_key"] for rule in loose_rules}
    tight_keys = {rule["rule_key"] for rule in tight_rules}
    assert tight_keys < loose_keys
    assert all(rule["confidence"] > 0.7 for rule in tight_rules)


def test_planogram_selection_conserves_uplift_and_groups() -> None:
    """陈列选择守恒：合计 = 选中位求和、位数 = 唯一冲突组数、每条候选只出现一次。"""
    candidates = [
        {"rule_key": "N01>N02", "uplift_month": 3060.0, "lift": 1.861, "conflict_group": "A1"},
        {"rule_key": "N04>N05", "uplift_month": 2640.0, "lift": 1.92, "conflict_group": "A1"},
        {"rule_key": "N08>N03", "uplift_month": 2640.0, "lift": 1.98, "conflict_group": "H3"},
        {"rule_key": "N07>N06", "uplift_month": 2460.0, "lift": 1.96, "conflict_group": "H4"},
        {"rule_key": "B03>B02", "uplift_month": 2220.0, "lift": 2.01, "conflict_group": "B2"},
        {"rule_key": "B05>B04", "uplift_month": 2100.0, "lift": 1.96, "conflict_group": "H1"},
    ]
    selection = select_slots(candidates, k=6)

    slots = selection["slots"]
    assert selection["total_uplift"] == pytest.approx(
        sum(float(slot["uplift_month"]) for slot in slots), abs=1e-6
    )
    assert selection["slot_count"] == selection["unique_pairs"] == len(slots) == 5
    groups = [slot["conflict_group"] for slot in slots]
    assert len(groups) == len(set(groups))  # 冲突组互斥
    keys = [slot["rule_key"] for slot in slots] + [row["rule_key"] for row in selection["skipped"]]
    assert sorted(keys) == sorted(candidate["rule_key"] for candidate in candidates)  # 无丢无重
