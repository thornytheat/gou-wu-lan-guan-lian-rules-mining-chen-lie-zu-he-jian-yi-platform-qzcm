"""算法 2（下半）纯函数：K=6 冲突组贪心背包 + 货架位编号。

只吃 list[dict] / int，不 import Session / 模型 / 数据库配置，便于单元测试。
口径（与 planogram_service 完全一致，后者只是重新导出）：

  排序：-预估月增量 → -lift → rule_key 升序（同分并列时稳定可复现）
  贪心：冲突组（默认取 rule_key）只取一条；货架位满 K 后剩余全部记 skipped
  合计：selected 的 uplift_month 求和（round 2）
"""
from __future__ import annotations

from src.constants.enums import SlotStatus

ZONE_ORDER = ["A1", "H3", "H4", "B2", "H1", "H2", "H5", "H6"]


def select_slots(candidates: list[dict], k: int) -> dict:
    """按 预估增量 / 冲突组占用 贪心选择：同冲突组只取一条，直到货架位用满。

    candidates: [{rule_id, rule_key, uplift_month, conflict_group, zone, shelf_label, stable, ...}]
    返回 {slots, skipped, total_uplift, unique_pairs}
    """
    ranked = sorted(
        candidates,
        key=lambda row: (-float(row["uplift_month"]), -float(row.get("lift") or 0), row["rule_key"]),
    )
    slots: list[dict] = []
    skipped: list[dict] = []
    used_groups: dict[str, str] = {}
    for row in ranked:
        group = row.get("conflict_group") or row["rule_key"]
        if len(slots) >= k:
            skipped.append({**row, "skip_reason": f"货架位已满（K={k}）"})
            continue
        if group in used_groups:
            skipped.append(
                {
                    **row,
                    "skip_reason": f"冲突组「{group}」已由 {used_groups[group]} 占用（同组只取增量更高的一条）",
                }
            )
            continue
        used_groups[group] = row["rule_key"]
        slots.append({**row, "conflict_group": group})

    total = sum(float(slot["uplift_month"]) for slot in slots)
    return {
        "slots": slots,
        "skipped": skipped,
        "total_uplift": round(total, 2),
        "unique_pairs": len(slots),
        "slot_count": len(slots),
        "status": SlotStatus.DRAFT.value,
    }


def assign_positions(slots: list[dict]) -> list[dict]:
    """按货架分区顺序编号，保证同一分区连续。"""

    def zone_rank(slot: dict) -> tuple[int, float]:
        zone = slot.get("zone", "")
        try:
            idx = ZONE_ORDER.index(zone)
        except ValueError:
            idx = len(ZONE_ORDER)
        return idx, -float(slot["uplift_month"])

    ordered = sorted(slots, key=zone_rank)
    for index, slot in enumerate(ordered, start=1):
        slot["position_index"] = index
    return ordered
