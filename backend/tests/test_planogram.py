"""算法 2（下半）：陈列位贪心背包选择（同冲突组只取一条，K=6）+ 货架位编号。

候选值取自 seed 主流程（共现 51/44/41/44/37/35 × 客单 ¥40 × 0.35 × 30/7 = 3060/2640/2460/2640/2220/2100），
期望值与 README/TESTING 里的「6 条候选 → 剔除 1 条 → 5 个货架位 / ¥12,480」一致。
"""
from __future__ import annotations

import pytest

from src.services.planogram_core import ZONE_ORDER, assign_positions, select_slots

SEED_CANDIDATES: list[dict] = [
    {
        "rule_id": "r1",
        "rule_key": "N01>N02",
        "uplift_month": 3060.0,
        "lift": 1.861,
        "conflict_group": "A1",
        "zone": "A1",
        "shelf_label": "端架A 上层 · 价签位 01",
    },
    {
        "rule_id": "r2",
        "rule_key": "N04>N05",
        "uplift_month": 2640.0,
        "lift": 1.92,
        "conflict_group": "A1",
        "zone": "A1",
        "shelf_label": "端架A 上层 · 价签位 02",
    },
    {
        "rule_id": "r3",
        "rule_key": "N07>N06",
        "uplift_month": 2460.0,
        "lift": 1.96,
        "conflict_group": "H4",
        "zone": "H4",
        "shelf_label": "H4 速食层 · 眼高位",
    },
    {
        "rule_id": "r4",
        "rule_key": "N08>N03",
        "uplift_month": 2640.0,
        "lift": 1.98,
        "conflict_group": "H3",
        "zone": "H3",
        "shelf_label": "H3 膨化层 · 端头位",
    },
    {
        "rule_id": "r5",
        "rule_key": "B03>B02",
        "uplift_month": 2220.0,
        "lift": 2.01,
        "conflict_group": "B2",
        "zone": "B2",
        "shelf_label": "冷柜B 第二层 · 早餐角",
    },
    {
        "rule_id": "r6",
        "rule_key": "B05>B04",
        "uplift_month": 2100.0,
        "lift": 1.96,
        "conflict_group": "H1",
        "zone": "H1",
        "shelf_label": "H1 热柜旁 · 咖啡加购位",
    },
]


# ------------------------------------------------------------------ 正常路径


def test_select_slots_greedy_conflict_group_matches_seed_flow() -> None:
    """K=6：6 条候选里 N04>N05 与 N01>N02 同属 A1 → 剔除增量更低者，剩 5 位 / ¥12,480。"""
    selection = select_slots(SEED_CANDIDATES, k=6)

    assert selection["slot_count"] == 5
    assert selection["unique_pairs"] == 5
    assert selection["total_uplift"] == pytest.approx(12480.0, abs=1e-6)
    assert selection["status"] == "draft"
    assert [slot["rule_key"] for slot in selection["slots"]] == [
        "N01>N02",
        "N08>N03",
        "N07>N06",
        "B03>B02",
        "B05>B04",
    ]
    assert [float(slot["uplift_month"]) for slot in selection["slots"]] == pytest.approx(
        [3060.0, 2640.0, 2460.0, 2220.0, 2100.0]
    )
    # 每个货架位的冲突组就是它自己占用的组
    assert [slot["conflict_group"] for slot in selection["slots"]] == ["A1", "H3", "H4", "B2", "H1"]

    assert len(selection["skipped"]) == 1
    skipped = selection["skipped"][0]
    assert skipped["rule_key"] == "N04>N05"
    assert skipped["conflict_group"] == "A1"
    assert "冲突组「A1」已由 N01>N02 占用" in skipped["skip_reason"]


def test_select_slots_respects_k_and_marks_slot_full() -> None:
    """K=3：位满后剩余候选一律 skipped 并标注「货架位已满（K=3）」。"""
    selection = select_slots(SEED_CANDIDATES, k=3)

    assert selection["slot_count"] == 3
    assert [slot["rule_key"] for slot in selection["slots"]] == ["N01>N02", "N08>N03", "N07>N06"]
    assert selection["total_uplift"] == pytest.approx(8160.0, abs=1e-6)  # 3060+2640+2460
    full = [row for row in selection["skipped"] if "货架位已满" in row["skip_reason"]]
    conflict = [row for row in selection["skipped"] if "冲突组" in row["skip_reason"]]
    assert {row["rule_key"] for row in full} == {"B03>B02", "B05>B04"}
    assert {row["rule_key"] for row in conflict} == {"N04>N05"}
    assert len(selection["skipped"]) == 3
    assert all("货架位已满（K=3）" in row["skip_reason"] for row in full)


def test_select_slots_tie_break_is_deterministic() -> None:
    """并列增量 100：先按 lift 降序、再按 rule_key 升序（结果可复现）。"""
    candidates = [
        {"rule_key": "X>Y", "uplift_month": 100.0, "lift": 1.5, "conflict_group": "G1"},
        {"rule_key": "Y>Z", "uplift_month": 100.0, "lift": 2.0, "conflict_group": "G2"},
        {"rule_key": "A>B", "uplift_month": 100.0, "lift": 2.0, "conflict_group": "G3"},
    ]
    selection = select_slots(candidates, k=6)

    assert [slot["rule_key"] for slot in selection["slots"]] == ["A>B", "Y>Z", "X>Y"]
    assert selection["total_uplift"] == pytest.approx(300.0, abs=1e-6)
    assert selection["skipped"] == []
    # 同输入两次结果完全一致
    assert select_slots(candidates, k=6) == selection


# ------------------------------------------------------------------ 边界


def test_select_slots_empty_candidates() -> None:
    """空候选：返回空建议单，合计 0，不抛错。"""
    selection = select_slots([], k=6)

    assert selection["slots"] == []
    assert selection["skipped"] == []
    assert selection["slot_count"] == 0
    assert selection["unique_pairs"] == 0
    assert selection["total_uplift"] == 0.0
    assert selection["status"] == "draft"


def test_select_slots_zero_slots_still_reports_skips() -> None:
    """K=0：一个都放不下，但每条候选都要落 skipped 说明（不静默丢弃）。"""
    selection = select_slots(SEED_CANDIDATES, k=0)

    assert selection["slots"] == []
    assert selection["slot_count"] == 0
    assert selection["total_uplift"] == 0.0
    assert len(selection["skipped"]) == len(SEED_CANDIDATES)
    assert all("货架位已满（K=0）" in row["skip_reason"] for row in selection["skipped"])


def test_select_slots_missing_conflict_group_falls_back_to_rule_key() -> None:
    """缺失/空 conflict_group → 用 rule_key 当冲突组（各自独立，不会互相挤掉）。"""
    candidates = [
        {"rule_key": "A>B", "uplift_month": 300.0},
        {"rule_key": "C>D", "uplift_month": 200.0, "conflict_group": ""},
        {"rule_key": "E>F", "uplift_month": 100.0, "conflict_group": None},
    ]
    selection = select_slots(candidates, k=6)

    assert selection["slot_count"] == 3
    assert [slot["conflict_group"] for slot in selection["slots"]] == ["A>B", "C>D", "E>F"]
    assert selection["total_uplift"] == pytest.approx(600.0, abs=1e-6)


def test_assign_positions_orders_zone_then_uplift() -> None:
    """货架位编号：分区序 A1→H4→B2→未知；同区按增量降序，编号从 1 连续。"""
    slots = [
        {"rule_key": "z", "zone": "H4", "uplift_month": 100.0},
        {"rule_key": "a2", "zone": "A1", "uplift_month": 200.0},
        {"rule_key": "a1", "zone": "A1", "uplift_month": 300.0},
        {"rule_key": "b", "zone": "B2", "uplift_month": 400.0},
        {"rule_key": "u", "zone": "未分配货架区", "uplift_month": 900.0},
    ]

    ordered = assign_positions(slots)

    assert [slot["rule_key"] for slot in ordered] == ["a1", "a2", "z", "b", "u"]
    assert [slot["position_index"] for slot in ordered] == [1, 2, 3, 4, 5]
    assert ZONE_ORDER[:4] == ["A1", "H3", "H4", "B2"]
    # 未知分区固定排最后（zone_rank 取 len(ZONE_ORDER)）
    assert ordered[-1]["zone"] == "未分配货架区"
