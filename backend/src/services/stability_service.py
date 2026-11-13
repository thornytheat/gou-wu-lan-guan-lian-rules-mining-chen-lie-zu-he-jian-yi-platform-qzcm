"""算法 2（上半）：门店分层稳定性（Wilson 区间）+ 预估月增量。

口径：
  分层（高/中/低客流）内分别算 lift 与 Wilson 区间（对共现小票比例做二项区间估计，
  n = 该层小票数），lift_ci = support_ci / (support(A) * support(B))。
  稳定 = 三层 lift 均 > 1.15 且三层 CI 下界均 > 1。
  预估月增量 = 共现小票数 × 客单均值 × 采纳率(0.35) × (30 / 样本天数)。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from src.config.settings import settings
from src.constants.enums import StoreTier
from src.utils.stats import round2, wilson_interval

TIER_ORDER = (StoreTier.HIGH.value, StoreTier.MID.value, StoreTier.LOW.value)


def _pct(count: int, total: int) -> float:
    return count / total if total else 0.0


def analyze_rule(
    transactions: Sequence[tuple[frozenset[str], str]],
    rule: dict,
    mean_amount: float,
    params: dict,
) -> dict:
    ante = frozenset(rule["antecedent"])
    cons = frozenset(rule["consequent"])
    n_total = len(transactions)
    total_count = sum(1 for basket, _ in transactions if ante <= basket and cons <= basket)
    ante_total = sum(1 for basket, _ in transactions if ante <= basket)
    cons_total = sum(1 for basket, _ in transactions if cons <= basket)

    support = _pct(total_count, n_total)
    support_a = _pct(ante_total, n_total)
    support_b = _pct(cons_total, n_total)
    confidence = _pct(total_count, ante_total)
    lift = confidence / support_b if support_b else 0.0
    ci_low, ci_high = wilson_interval(total_count, n_total)
    lift_low = ci_low / (support_a * support_b) if support_a and support_b else 0.0
    lift_high = ci_high / (support_a * support_b) if support_a and support_b else 0.0

    by_tier: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "ab": 0, "a": 0, "b": 0})
    for basket, tier in transactions:
        bucket = by_tier[tier]
        bucket["n"] += 1
        if ante <= basket:
            bucket["a"] += 1
            if cons <= basket:
                bucket["ab"] += 1
        if cons <= basket:
            bucket["b"] += 1

    tiers: list[dict] = []
    stable = True
    for tier in TIER_ORDER:
        bucket = by_tier[tier]
        n_t = bucket["n"]
        sup_ab = _pct(bucket["ab"], n_t)
        sup_a = _pct(bucket["a"], n_t)
        sup_b = _pct(bucket["b"], n_t)
        tier_lift = sup_ab / (sup_a * sup_b) if sup_a and sup_b else 0.0
        t_low, t_high = wilson_interval(bucket["ab"], n_t)
        tier_lift_low = t_low / (sup_a * sup_b) if sup_a and sup_b else 0.0
        tier_lift_high = t_high / (sup_a * sup_b) if sup_a and sup_b else 0.0
        tier_stable = tier_lift > settings.stable_tier_lift and tier_lift_low > 1.0
        stable = stable and tier_stable
        tiers.append(
            {
                "tier": tier,
                "baskets": n_t,
                "cooccur": bucket["ab"],
                "antecedent": bucket["a"],
                "consequent": bucket["b"],
                "support": round(sup_ab, 6),
                "lift": round(tier_lift, 4),
                "ci_low": round(tier_lift_low, 4),
                "ci_high": round(tier_lift_high, 4),
                "stable": tier_stable,
            }
        )

    adoption = params.get("adoption_rate", settings.adoption_rate)
    sample_days = params.get("sample_days", settings.sample_days)
    monthly_factor = 30.0 / max(1, sample_days)
    uplift_raw = total_count * mean_amount * adoption * monthly_factor

    return {
        "support": round(support, 6),
        "confidence": round(confidence, 6),
        "lift": round(lift, 4),
        "ci_low": round(lift_low, 4),
        "ci_high": round(lift_high, 4),
        "cooccur_count": total_count,
        "counterexample_count": max(0, ante_total - total_count),
        "mean_amount": round2(mean_amount),
        "adoption_rate": adoption,
        "monthly_factor": round(monthly_factor, 4),
        "uplift_month": round2(uplift_raw),
        "stable": stable,
        "tiers": tiers,
        "tier_lifts": {tier["tier"]: tier["lift"] for tier in tiers},
    }
