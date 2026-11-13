"""算法 1：频繁项集（Apriori）与关联规则指标。

输入：小票集合（每张是 SKU code 的集合）
输出：频繁项集（含支持度计数）+ 候选规则（support / confidence / lift / conviction）

口径：
  support(A)      = 含 A 的小票数 / 总小票数
  confidence(A→B) = support(A∪B) / support(A)
  lift(A→B)       = confidence(A→B) / support(B)
  conviction      = (1 - support(B)) / (1 - confidence)，confidence=1 时记 9999
候选规则保留 confidence ≥ min_confidence；业务过滤在 mining_service 里做（lift/conf 阈值）。
"""
from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from typing import Iterable, Sequence

CONVICTION_CAP = 9999.0


def _join(level: dict[frozenset[str], int], k: int) -> list[frozenset[str]]:
    """由 k-1 项频繁集生成 k 项候选（k=2 两两拼接；k>2 共享前 k-2 个元素后拼接）。"""
    keys = sorted((tuple(sorted(key)) for key in level.keys()))
    out: set[frozenset[str]] = set()
    if k == 2:
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                out.add(frozenset(keys[i]) | frozenset(keys[j]))
        return list(out)
    for i in range(len(keys)):
        a = keys[i]
        for j in range(i + 1, len(keys)):
            b = keys[j]
            if a[: k - 2] != b[: k - 2]:
                break
            out.add(frozenset(a[: k - 1]) | frozenset(b[: k - 1]))
    return list(out)


def apriori(
    transactions: Sequence[frozenset[str]],
    min_support: float,
    max_itemset: int = 3,
) -> dict:
    """标准 Apriori：逐层候选生成 + 支持度计数 + 剪枝。"""
    n = len(transactions)
    if n == 0:
        raise ValueError("小票样本为空，无法挖掘")
    min_count = max(1, math.ceil(min_support * n))

    counter: Counter[str] = Counter()
    for basket in transactions:
        counter.update(basket)
    level: dict[frozenset[str], int] = {
        frozenset([code]): count for code, count in counter.items() if count >= min_count
    }
    frequent: dict[frozenset[str], int] = dict(level)

    k = 2
    while level and k <= max_itemset:
        candidates = _join(level, k)
        new_level: dict[frozenset[str], int] = {}
        for cand in candidates:
            count = sum(1 for basket in transactions if cand <= basket)
            if count >= min_count:
                new_level[cand] = count
        frequent.update(new_level)
        level = new_level
        k += 1

    itemsets = [
        {
            "items": sorted(items),
            "count": count,
            "support": round(count / n, 6),
            "size": len(items),
        }
        for items, count in frequent.items()
    ]
    itemsets.sort(key=lambda row: (row["size"], -row["count"], row["items"]))

    by_size: dict[int, int] = {}
    for row in itemsets:
        by_size[row["size"]] = by_size.get(row["size"], 0) + 1

    return {
        "basket_count": n,
        "min_count": min_count,
        "itemsets": itemsets,
        "counts": frequent,
        "by_size": by_size,
        "frequent_itemsets": len(itemsets),
    }


def build_rules(
    counts: dict[frozenset[str], int],
    n: int,
    min_confidence: float,
) -> list[dict]:
    """从频繁项集导出方向规则（前项非空、后项非空），按置信度下限截断。"""
    rules: list[dict] = []
    for itemset, count in counts.items():
        if len(itemset) < 2:
            continue
        items = sorted(itemset)
        for size in range(1, len(items)):
            for antecedent in combinations(items, size):
                ante = frozenset(antecedent)
                cons = frozenset(itemset) - ante
                support = count / n
                support_a = counts.get(ante, 0) / n
                support_b = counts.get(cons, 0) / n
                if support_a <= 0 or support_b <= 0:
                    continue
                confidence = support / support_a
                if confidence < min_confidence:
                    continue
                lift = confidence / support_b
                if confidence >= 1.0:
                    conviction = CONVICTION_CAP
                else:
                    conviction = (1.0 - support_b) / (1.0 - confidence)
                rules.append(
                    {
                        "antecedent": sorted(ante),
                        "consequent": sorted(cons),
                        "support": round(support, 6),
                        "confidence": round(confidence, 6),
                        "lift": round(lift, 6),
                        "conviction": round(min(conviction, CONVICTION_CAP), 4),
                        "cooccur_count": count,
                        "rule_key": f"{'+'.join(sorted(ante))}>{'+'.join(sorted(cons))}",
                    }
                )
    rules.sort(key=lambda row: (-row["lift"], -row["confidence"], row["rule_key"]))
    return rules


def rule_counterexamples(
    transactions: Sequence[frozenset[str]],
    antecedent: Iterable[str],
    consequent: Iterable[str],
) -> int:
    """反例样本数：含前项但不含后项的小票数（衡量“不成立”的规模）。"""
    ante = frozenset(antecedent)
    cons = frozenset(consequent)
    return sum(1 for basket in transactions if ante <= basket and not cons <= basket)
