"""算法 2（上半）：门店分层 Wilson 区间稳定性 + 预估月增量。

手算样本：
  S1 12 张（高/中/低各 4）：A=9 B=9 AB=6 → lift=0.889、CI 下界 0.4512 → 不稳定
  S2 60 张（每层 20，AB=9 A=10 B=10）→ lift=1.8、层内 CI 下界 1.0328 → 三层稳定
  S3 只有 high 层（20 张）→ 缺层降级为不稳定
  S4 30 张全相同 {A,B} → 零方差，lift=1.0 且 CI 下界 0.8865 < 1 → 不稳定
"""
from __future__ import annotations

import pytest

from src.services.stability_service import TIER_ORDER, analyze_rule
from src.utils.stats import round2, wilson_interval, wilson_lift_interval

RULE = {"antecedent": ["A"], "consequent": ["B"]}
PARAMS = {"adoption_rate": 0.35, "sample_days": 7}
MEAN_AMOUNT = 40.0


def tier_block(tier: str, repeat: int = 1) -> list[tuple[frozenset[str], str]]:
    """一层 20 张的标准块：9×{A,B} / 1×{A} / 1×{B} / 9×{X}（A=10 B=10 AB=9）。"""
    block = [(frozenset({"A", "B"}), tier) for _ in range(9)]
    block.append((frozenset({"A"}), tier))
    block.append((frozenset({"B"}), tier))
    block.extend((frozenset({"X"}), tier) for _ in range(9))
    return block * repeat


S1 = [
    (frozenset({"A", "B"}), "high"),
    (frozenset({"A", "B"}), "high"),
    (frozenset({"A"}), "high"),
    (frozenset({"B"}), "high"),
    (frozenset({"A", "B"}), "mid"),
    (frozenset({"A", "B"}), "mid"),
    (frozenset({"A"}), "mid"),
    (frozenset({"B"}), "mid"),
    (frozenset({"A", "B"}), "low"),
    (frozenset({"A", "B"}), "low"),
    (frozenset({"A"}), "low"),
    (frozenset({"B"}), "low"),
]
S2 = tier_block("high") + tier_block("mid") + tier_block("low")
S3 = tier_block("high")
S4 = [(frozenset({"A", "B"}), tier) for tier in ("high", "mid", "low") for _ in range(10)]


# ------------------------------------------------------------------ 正常路径


def test_analyze_rule_hand_computed_three_tiers() -> None:
    """S1：support=0.5、conf=2/3、lift=0.889、CI[0.4512, 1.3266]、不稳定。"""
    result = analyze_rule(S1, RULE, mean_amount=MEAN_AMOUNT, params=PARAMS)

    assert result["support"] == pytest.approx(0.5, abs=1e-6)
    assert result["confidence"] == pytest.approx(0.666667, abs=1e-6)
    assert result["lift"] == pytest.approx(0.8889, abs=1e-4)
    assert result["ci_low"] == pytest.approx(0.4512, abs=1e-4)
    assert result["ci_high"] == pytest.approx(1.3266, abs=1e-4)
    assert result["cooccur_count"] == 6
    assert result["counterexample_count"] == 3  # 含 A 的 9 张 - 共现 6 张
    assert result["stable"] is False
    assert [tier["tier"] for tier in result["tiers"]] == list(TIER_ORDER)
    assert [tier["tier"] for tier in result["tiers"]] == ["high", "mid", "low"]
    assert result["tier_lifts"] == pytest.approx({"high": 0.8889, "mid": 0.8889, "low": 0.8889}, abs=1e-4)
    high = result["tiers"][0]
    assert high["baskets"] == 4
    assert high["cooccur"] == 2
    assert high["antecedent"] == 3
    assert high["consequent"] == 3
    assert high["support"] == pytest.approx(0.5, abs=1e-6)
    assert high["ci_low"] == pytest.approx(0.2667, abs=1e-4)  # 0.1500357 / 0.5625
    assert high["ci_high"] == pytest.approx(1.511, abs=1e-4)
    assert high["stable"] is False


def test_analyze_rule_stable_when_all_tiers_strong() -> None:
    """S2：三层 lift=1.8、层内 CI 下界 1.0328 → 三层均已稳定。"""
    result = analyze_rule(S2, RULE, mean_amount=MEAN_AMOUNT, params=PARAMS)

    assert result["support"] == pytest.approx(0.45, abs=1e-6)
    assert result["confidence"] == pytest.approx(0.9, abs=1e-6)
    assert result["lift"] == pytest.approx(1.8, abs=1e-4)
    assert result["ci_low"] == pytest.approx(1.3237, abs=1e-4)
    assert result["ci_high"] == pytest.approx(2.3003, abs=1e-4)
    assert result["stable"] is True
    for tier in result["tiers"]:
        assert tier["baskets"] == 20
        assert tier["cooccur"] == 9
        assert tier["lift"] == pytest.approx(1.8, abs=1e-4)
        assert tier["ci_low"] == pytest.approx(1.0328, abs=1e-4)
        assert tier["ci_high"] == pytest.approx(2.6317, abs=1e-4)
        assert tier["stable"] is True


def test_analyze_rule_uplift_month_formula_respects_params() -> None:
    """增量公式：共现 × 客单均值 × 采纳率 × (30 / 样本天数)。

    S2 共现 27、客单 ¥40：默认 0.35×30/7 → ¥1620.00；30 天样本、采纳率 0.5 → ¥540.00。
    """
    default = analyze_rule(S2, RULE, mean_amount=MEAN_AMOUNT, params=PARAMS)
    assert default["mean_amount"] == pytest.approx(40.0, abs=1e-6)
    assert default["adoption_rate"] == pytest.approx(0.35, abs=1e-9)
    assert default["monthly_factor"] == pytest.approx(4.2857, abs=1e-4)
    assert default["uplift_month"] == pytest.approx(1620.0, abs=1e-6)

    tuned = analyze_rule(
        S2, RULE, mean_amount=MEAN_AMOUNT, params={"adoption_rate": 0.5, "sample_days": 30}
    )
    assert tuned["monthly_factor"] == pytest.approx(1.0, abs=1e-9)
    assert tuned["uplift_month"] == pytest.approx(540.0, abs=1e-6)  # 27 × 40 × 0.5 × 1

    # 样本天数只影响月度折算，不影响 lift / 稳定性
    assert tuned["lift"] == pytest.approx(default["lift"], abs=1e-9)
    assert tuned["stable"] is default["stable"] is True


# ------------------------------------------------------------------ 边界


def test_analyze_rule_missing_tier_degrades_to_unstable() -> None:
    """S3：只有 high 层有样本 → mid/low 的 lift/CI 记 0 且整体不稳定（不静默当成稳定）。"""
    result = analyze_rule(S3, RULE, mean_amount=MEAN_AMOUNT, params=PARAMS)

    assert result["lift"] == pytest.approx(1.8, abs=1e-4)  # 全量口径仍然强
    assert result["ci_low"] == pytest.approx(1.0328, abs=1e-4)
    assert result["stable"] is False  # 缺两层 → 明确降级
    tiers = {tier["tier"]: tier for tier in result["tiers"]}
    assert tiers["high"]["stable"] is True
    for missing in ("mid", "low"):
        assert tiers[missing]["baskets"] == 0
        assert tiers[missing]["cooccur"] == 0
        assert tiers[missing]["lift"] == 0.0
        assert tiers[missing]["ci_low"] == 0.0
        assert tiers[missing]["ci_high"] == 0.0
        assert tiers[missing]["stable"] is False
    assert result["tier_lifts"] == pytest.approx({"high": 1.8, "mid": 0.0, "low": 0.0}, abs=1e-4)


def test_analyze_rule_all_identical_zero_variance() -> None:
    """S4：30 张全 {A,B}（零方差）→ lift=1.0、CI 下界 0.8865 < 1 → 判不稳定。"""
    result = analyze_rule(S4, RULE, mean_amount=MEAN_AMOUNT, params=PARAMS)

    assert result["support"] == pytest.approx(1.0, abs=1e-9)
    assert result["confidence"] == pytest.approx(1.0, abs=1e-9)
    assert result["lift"] == pytest.approx(1.0, abs=1e-9)
    assert result["ci_low"] == pytest.approx(0.8865, abs=1e-4)
    assert result["ci_high"] == pytest.approx(1.0, abs=1e-9)
    assert result["stable"] is False
    assert result["counterexample_count"] == 0
    assert result["uplift_month"] == pytest.approx(1800.0, abs=1e-6)  # 30 × 40 × 0.35 × 30/7


def test_analyze_rule_empty_transactions_returns_zeros() -> None:
    """空样本：全部指标降级为 0，不抛 ZeroDivisionError。"""
    result = analyze_rule([], RULE, mean_amount=0.0, params=PARAMS)

    assert result["support"] == 0.0
    assert result["confidence"] == 0.0
    assert result["lift"] == 0.0
    assert result["ci_low"] == 0.0
    assert result["ci_high"] == 0.0
    assert result["cooccur_count"] == 0
    assert result["counterexample_count"] == 0
    assert result["uplift_month"] == 0.0
    assert result["stable"] is False
    assert len(result["tiers"]) == 3
    assert {tier["baskets"] for tier in result["tiers"]} == {0}


def test_analyze_rule_single_basket_sample_too_small() -> None:
    """单张小票：support=1、CI 下界 0.2065 < 1 → 样本不足，不稳定。"""
    result = analyze_rule([(frozenset({"A", "B"}), "high")], RULE, MEAN_AMOUNT, PARAMS)

    assert result["support"] == pytest.approx(1.0, abs=1e-9)
    assert result["confidence"] == pytest.approx(1.0, abs=1e-9)
    assert result["ci_low"] == pytest.approx(0.2065, abs=1e-4)
    assert result["ci_high"] == pytest.approx(1.0, abs=1e-9)
    assert result["stable"] is False
    assert result["uplift_month"] == pytest.approx(60.0, abs=1e-6)  # 1 × 40 × 0.35 × 30/7


# ------------------------------------------------------------------ 统计工具


def test_wilson_interval_hand_computed() -> None:
    """啤酒→花生实测：51/3000，z=1.96 → (0.012954, 0.022282)。"""
    low, high = wilson_interval(51, 3000, z=1.96)

    assert low == pytest.approx(0.012953675, abs=1e-9)
    assert high == pytest.approx(0.022281738, abs=1e-9)
    # 区间必须包住样本比例（Wilson 中心略有偏置，不能拿中点当点估计）
    assert low < 51 / 3000 < high


def test_wilson_interval_edges() -> None:
    """边界：n=0 → (0,0)；0 次成功 → 上界 0.2425；全部成功 → 上界封顶 1.0。"""
    assert wilson_interval(0, 0) == (0.0, 0.0)
    assert wilson_interval(0, 12) == pytest.approx((0.0, 0.242500757), abs=1e-9)
    low, high = wilson_interval(10, 10)
    assert low == pytest.approx(0.722459831, abs=1e-9)
    assert high == 1.0


def test_wilson_lift_interval_scales_by_consequent_support() -> None:
    """lift 区间 = 置信度区间 / sup(B)。

    啤酒→花生：conf=51/202、sup(B)=407/3000 → (1.4563, 2.3338)；
    analyze_rule 实际走「support 区间 / (supA·supB)」，同一数据的口径值见下方 (1.4180, 2.4391)。
    """
    low, high = wilson_lift_interval(51, 202, 407 / 3000)

    assert low == pytest.approx(1.456264, abs=1e-5)
    assert high == pytest.approx(2.333831, abs=1e-5)
    # sup(B)=0 时明确降级为 (0,0)，不产生 inf
    assert wilson_lift_interval(51, 202, 0.0) == (0.0, 0.0)

    # analyze_rule 的口径：support 区间 / (supA · supB) —— 与 TESTING 的 [1.418, 2.439] 对齐
    support_low, support_high = wilson_interval(51, 3000)
    sup_a, sup_b = 202 / 3000, 407 / 3000
    assert support_low / (sup_a * sup_b) == pytest.approx(1.4180, abs=1e-4)
    assert support_high / (sup_a * sup_b) == pytest.approx(2.4391, abs=1e-4)


def test_round2_half_up_for_decimal_cent() -> None:
    """金额收敛：+1e-9 偏置实现「见分进位」，避免 1.005 → 1.00。"""
    assert round2(1.005) == pytest.approx(1.01)
    assert round2(2.675) == pytest.approx(2.68)
    assert round2(12480.004) == pytest.approx(12480.0)
    assert round2(-1.234) == pytest.approx(-1.23)
