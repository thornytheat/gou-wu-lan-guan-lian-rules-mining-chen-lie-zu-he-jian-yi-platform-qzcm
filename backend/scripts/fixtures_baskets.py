"""确定性小票生成器（纯标准库，不依赖 DB / numpy）。

结构（决定 46 / 12 / 6 这组算法输出）：
  1. 40 个 SKU 全部 ≥ min_support=1%（30 张）→ 40 个频繁 1-项集；
  2. 只有 6 组预埋商品对 ≥ 1%（51/44/41/37/35/44 张）→ 6 个频繁 2-项集；
  3. 任意非设计商品对 < 30 张（生成时按 29 封顶），任一组合块 ≤ 25 张
     → 没有任何 3-项集达到 1%，频繁项集合计 46；
  4. 3,000 张 / 9,600 行 → 平均 3.2 行；客单均值 ¥40.00（价格经一次性调参）。

结构分解：
  预埋对 252 张（2 行）= 504 行
  关联主商品小票 2,172 张（3 行，attach + 2 个长尾）= 6,516 行
  长尾小票 576 张（4/5 行，1~2 个 trigger + 长尾）= 2,580 行
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone

from scripts import fixtures

RNG_SEED = 20261112
PAIR_CAP = 29          # 非设计商品对的小票数上限（< 30）
BLOCK_WEIGHT = 25      # 单个组合块的小票数上限（< 30，保证三元组不达标）
TZ = timezone(timedelta(hours=8))
HOURS = [7, 8, 8, 9, 12, 12, 13, 17, 18, 18, 19, 19, 20, 20, 21, 22]


def _sku_codes() -> list[str]:
    return [item["code"] for item in fixtures.DEMO_SKUS]


def plan() -> dict:
    """固定结构计划（行数、张数、trigger / attach 配额）。"""
    pair_baskets = sum(spec["cooccur"] for spec in fixtures.PAIR_BUNDLES)
    pair_lines = pair_baskets * 2
    attach_plan = {
        spec["right"]: spec["attach_baskets"] - spec["cooccur"] for spec in fixtures.PAIR_BUNDLES
    }
    trigger_plan = {
        spec["left"]: spec["trigger_baskets"] - spec["cooccur"] for spec in fixtures.PAIR_BUNDLES
    }
    attach_baskets = sum(attach_plan.values())
    attach_lines = attach_baskets * 3
    rest_baskets = fixtures.BASKET_TOTAL - pair_baskets - attach_baskets
    rest_lines = fixtures.BASKET_TOTAL * 32 // 10 - pair_lines - attach_lines
    # 4 行 / 5 行拆分
    five = rest_lines - 4 * rest_baskets
    four = rest_baskets - five
    triggers_in_rest = sum(trigger_plan.values())
    return {
        "pair_baskets": pair_baskets,
        "pair_lines": pair_lines,
        "attach_plan": attach_plan,
        "trigger_plan": trigger_plan,
        "attach_baskets": attach_baskets,
        "attach_lines": attach_lines,
        "rest_baskets": rest_baskets,
        "rest_lines": rest_lines,
        "rest_four": four,
        "rest_five": five,
        "triggers_in_rest": triggers_in_rest,
        "filler_in_rest": rest_lines - triggers_in_rest,
        "total_lines": fixtures.BASKET_TOTAL * 32 // 10,
    }


def _build_raw() -> list[dict]:
    plan_data = plan()
    codes = _sku_codes()
    pair_members = {spec["left"] for spec in fixtures.PAIR_BUNDLES} | {
        spec["right"] for spec in fixtures.PAIR_BUNDLES
    }
    fillers = [code for code in codes if code not in pair_members]
    filler_weight = fixtures.FILLER_WEIGHTS
    rng = random.Random(RNG_SEED)

    counts: Counter[str] = Counter()
    pair_load: dict[frozenset[str], int] = defaultdict(int)
    attach_load: dict[tuple[str, str], int] = defaultdict(int)
    rows: list[dict] = []

    def pair_key(a: str, b: str) -> frozenset[str]:
        return frozenset((a, b))

    def can_add(base: list[str], candidate: str, weight: int) -> bool:
        for other in base:
            if pair_load[pair_key(other, candidate)] + weight > PAIR_CAP:
                return False
        return True

    def commit(items: list[str], weight: int, tag: str = "") -> None:
        for _ in range(weight):
            rows.append({"items": list(items), "tag": tag})
            for code in items:
                counts[code] += 1
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                pair_load[pair_key(items[i], items[j])] += weight

    # ---------------- 1) 预埋强关联对 ----------------
    for spec in fixtures.PAIR_BUNDLES:
        commit([spec["left"], spec["right"]], spec["cooccur"], tag=f"pair:{spec['key']}")

    # ---------------- 2) 关联主商品小票（attach + 2 长尾） ----------------
    def pick_fillers(
        base: list[str], need: int, weight: int, attach: str | None = None
    ) -> list[str]:
        """挑长尾商品：优先与当前 attach 负载低、其次全局出现次数少的组合。"""
        if attach:
            pool = sorted(
                fillers,
                key=lambda code: (
                    attach_load[(attach, code)],
                    counts[code] / max(filler_weight.get(code, 100), 1),
                ),
            )
        else:
            pool = sorted(
                fillers,
                key=lambda code: (
                    counts[code] / max(filler_weight.get(code, 100), 1),
                    rng.random(),
                ),
            )
        chosen: list[str] = []
        for candidate in pool:
            if candidate in base or candidate in chosen:
                continue
            if not can_add(base + chosen, candidate, weight):
                continue
            chosen.append(candidate)
            if len(chosen) == need:
                break
        return chosen

    for attach, needed in plan_data["attach_plan"].items():
        remaining = needed
        while remaining > 0:
            weight = min(BLOCK_WEIGHT, remaining)
            picked: list[str] = []
            while weight >= 1:
                picked = pick_fillers([attach], 2, weight, attach=attach)
                if len(picked) == 2:
                    break
                weight -= 1
            if len(picked) < 2:
                raise RuntimeError(f"attach 块生成失败 attach={attach} remaining={remaining}")
            commit([attach] + picked, weight, tag="attach")
            for code in picked:
                attach_load[(attach, code)] += weight
            remaining -= weight

    # ---------------- 3) 长尾小票（1~2 trigger + 长尾，4/5 行） ----------------
    triggers: list[str] = []
    for trigger, needed in plan_data["trigger_plan"].items():
        triggers.extend([trigger] * needed)
    rng.shuffle(triggers)

    # 711 个 trigger 配额分到 576 张长尾小票：135 张放第二个 trigger（换商品，避免同物重复）
    per_basket: list[list[str]] = [[code] for code in triggers[: plan_data["rest_baskets"]]]
    second_quota = triggers[plan_data["rest_baskets"] :]
    cursor = 0
    for code in second_quota:
        for offset in range(len(per_basket)):
            index = (cursor + offset) % len(per_basket)
            if code not in per_basket[index] and len(per_basket[index]) < 2:
                per_basket[index].append(code)
                cursor = index + 1
                break
        else:  # pragma: no cover - 兜底
            per_basket[0].append(code)

    sizes = [4] * plan_data["rest_four"] + [5] * plan_data["rest_five"]
    rng.shuffle(sizes)
    for index, size in enumerate(sizes):
        base = per_basket[index]
        need = size - len(base)
        picked = pick_fillers(base, need, 1)
        while len(picked) < need:
            extra = next(
                (
                    code
                    for code in fillers
                    if code not in base and code not in picked and can_add(base + picked, code, 1)
                ),
                None,
            )
            if extra is None:
                break
            picked.append(extra)
        if len(picked) < need:
            raise RuntimeError(f"长尾小票生成失败 index={index}")
        commit(base + picked, 1, tag="filler")

    if len(rows) != fixtures.BASKET_TOTAL:
        raise RuntimeError(f"小票数不符：{len(rows)} != {fixtures.BASKET_TOTAL}")
    return rows, plan_data


def _assign_meta(rows: list[dict], plan_data: dict) -> list[dict]:
    rng = random.Random(RNG_SEED + 7)
    stores = fixtures.DEMO_STORES
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for store in stores:
        by_tier[store["tier"]].append(store)

    # 预埋对小票按三等分门店分层（保证每层都有足够共现样本，Wilson 下界 > 1）
    pair_tiers = ["high", "mid", "low"] * 60
    pair_cursor = 0
    store_cursor = 0
    for row in rows:
        if row.get("tag", "").startswith("pair:"):
            tier = pair_tiers[pair_cursor % len(pair_tiers)]
            pair_cursor += 1
            row["store"] = by_tier[tier][pair_cursor % len(by_tier[tier])]
        else:
            row["store"] = stores[store_cursor % len(stores)]
            store_cursor += 1

    rng.shuffle(rows)
    prices = fixtures.sku_price_map()
    fresh_codes = {"I08", "N08", "I01"}
    start = date.fromisoformat(fixtures.SAMPLE_START)
    baskets: list[dict] = []
    for index, row in enumerate(rows):
        day = index % fixtures.SAMPLE_DAYS
        hour = HOURS[(index * 3) % len(HOURS)]
        minute = (index * 11) % 60
        ts = datetime.combine(start + timedelta(days=day), time(hour=hour, minute=minute), tzinfo=TZ)
        lines = []
        total = 0.0
        for code in row["items"]:
            qty = 2 if (code in fresh_codes and index % 9 == 0) else 1
            amount = round(prices[code] * qty, 2)
            total += amount
            lines.append({"sku": code, "qty": qty, "amount": f"{amount:.2f}"})
        baskets.append(
            {
                "basket_no": f"BR-{ts.strftime('%Y%m%d')}-{index + 1:05d}",
                "store_code": row["store"]["code"],
                "store_name": row["store"]["name"],
                "store_tier": row["store"]["tier"],
                "channel": fixtures.CHANNELS[index % len(fixtures.CHANNELS)],
                "basket_ts": ts,
                "net_amount": f"{round(total, 2):.2f}",
                "item_count": len(lines),
                "lines": lines,
            }
        )
    return baskets


def build_baskets() -> list[dict]:
    """生成 3,000 张小票（确定性：同进程多次调用结果一致）。"""
    rows, plan_data = _build_raw()
    return _assign_meta(rows, plan_data)


def transactions(baskets: list[dict]) -> list[tuple[frozenset[str], str]]:
    return [
        (frozenset(line["sku"] for line in basket["lines"]), basket["store_tier"])
        for basket in baskets
    ]


def dataset_stats(baskets: list[dict]) -> dict:
    total = sum(float(basket["net_amount"]) for basket in baskets)
    lines = sum(basket["item_count"] for basket in baskets)
    supports: Counter[str] = Counter()
    for basket in baskets:
        supports.update({line["sku"] for line in basket["lines"]})
    return {
        "baskets": len(baskets),
        "lines": lines,
        "avg_lines": round(lines / len(baskets), 2),
        "revenue": round(total, 2),
        "mean_amount": round(total / len(baskets), 2),
        "min_support_count": min(supports.values()),
        "max_support_count": max(supports.values()),
        "sku_count": len(supports),
        "supports": dict(supports),
    }
