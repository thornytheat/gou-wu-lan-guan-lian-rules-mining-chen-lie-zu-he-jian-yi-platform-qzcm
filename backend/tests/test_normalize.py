"""解析/归一/门禁：挖掘参数、规则过滤口径、规则键 → 货架分区归一。"""
from __future__ import annotations

import pytest

from src.constants import error_codes as codes
from src.services.fixtures_loader import zone_payload
from src.services.mining_core import filter_rules, normalize_params, validate_params
from src.utils.errors import AppError

# 与 mining_service.DEFAULT_PARAMS 同构（settings 默认值），但显式写出避免依赖运行环境
DEFAULTS = {
    "min_support": 0.01,
    "min_confidence": 0.05,
    "max_itemset": 3,
    "filter_lift": 1.2,
    "filter_confidence": 0.25,
    "shelf_slots": 6,
    "adoption_rate": 0.35,
    "sample_days": 7,
}


def test_normalize_params_overlays_non_none_values() -> None:
    """非 None 覆盖默认值；None 视为「未传」；其余默认值原样保留。"""
    params = normalize_params(DEFAULTS, {"min_support": 0.02, "max_itemset": None, "shelf_slots": 4})

    assert params["min_support"] == pytest.approx(0.02)
    assert params["max_itemset"] == 3  # None 不覆盖
    assert params["shelf_slots"] == 4
    assert params["filter_lift"] == pytest.approx(1.2)  # 未传 → 默认
    assert params["sample_days"] == 7
    assert set(params) == set(DEFAULTS)


def test_normalize_params_none_payload_returns_copy_of_defaults() -> None:
    """空 payload → 与默认值相等的新 dict（改返回值不能污染全局默认值）。"""
    params = normalize_params(DEFAULTS, None)
    assert params == DEFAULTS
    assert params is not DEFAULTS

    params["min_support"] = 0.4
    assert DEFAULTS["min_support"] == pytest.approx(0.01)


@pytest.mark.parametrize(
    "params",
    [
        {**DEFAULTS, "min_support": 0.5},  # 开区间上界，合法
        {**DEFAULTS, "min_support": 1e-06},
        {**DEFAULTS, "min_confidence": 1.0},
        {**DEFAULTS, "max_itemset": 2},
        {**DEFAULTS, "max_itemset": 4},
    ],
)
def test_validate_params_accepts_boundaries(params: dict) -> None:
    """边界合法值必须放行（否则前端只能猜口径）。"""
    assert validate_params(params) is None


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"min_support": 0.0}, "min_support=0.0"),
        ({"min_support": 0.500001}, "min_support=0.500001"),
        ({"min_support": -0.1}, "min_support=-0.1"),
        ({"min_confidence": 0.0}, "min_confidence=0.0"),
        ({"min_confidence": 1.0001}, "min_confidence=1.0001"),
        ({"max_itemset": 1}, "max_itemset=1"),
        ({"max_itemset": 5}, "max_itemset=5"),
    ],
)
def test_validate_params_rejects_out_of_range(override: dict, field: str) -> None:
    """越界参数 → 422 VALIDATION_ERROR（禁止静默降级成默认值）。"""
    with pytest.raises(AppError) as exc:
        validate_params({**DEFAULTS, **override})

    error = exc.value
    assert error.code == codes.VALIDATION_ERROR
    assert error.http_status == 422
    assert error.detail == field


def test_filter_rules_is_strictly_greater() -> None:
    """可执行口径：lift 与 confidence 都必须严格大于阈值，恰好等于要被剔除。"""
    rules = [
        {"rule_key": "eq_lift", "lift": 1.2, "confidence": 0.9},
        {"rule_key": "eq_conf", "lift": 1.9, "confidence": 0.25},
        {"rule_key": "just_lift", "lift": 1.200001, "confidence": 0.9},
        {"rule_key": "just_conf", "lift": 1.9, "confidence": 0.250001},
        {"rule_key": "low_both", "lift": 1.0, "confidence": 0.1},
    ]

    passed = filter_rules(rules, filter_lift=1.2, filter_confidence=0.25)

    assert [rule["rule_key"] for rule in passed] == ["just_lift", "just_conf"]
    assert len(passed) == 2


def test_zone_payload_normalizes_run_prefixed_and_reversed_rule_key() -> None:
    """rule_key 归一：去 run 前缀、前后项顺序无关，都映射到同一货架分区。"""
    base = zone_payload("N01>N02")

    assert base == {
        "zone": "端架A · 冰饮堆头",
        "zone_code": "A1",
        "shelf_label": "端架A 上层 · 价签位 01",
        "note": "啤酒与花生同层陈列，端架第一视线高度；三层门店均稳定。",
    }
    assert zone_payload("RUN-2026-W41-DEMO@N01>N02") == base
    assert zone_payload("N02>N01") == base  # 反向前后项同样命中


def test_zone_payload_unknown_rule_is_explicitly_unassigned() -> None:
    """未知规则必须给出「未分配」的显式值，而不是空对象/抛错。"""
    payload = zone_payload("ZZZ>QQQ")

    assert payload["zone"] == "未分配货架区"
    assert payload["zone_code"] == ""
    assert payload["shelf_label"] == "待定货架位"
    assert payload["note"] == ""


def test_zone_payload_conflict_groups_are_stable_for_shared_zone() -> None:
    """同一端架的两条规则必须共享冲突组 A1（冲突消解的前提）。"""
    first = zone_payload("N01>N02")
    second = zone_payload("N04>N05")

    assert first["zone_code"] == second["zone_code"] == "A1"
    assert first["zone"] == second["zone"] == "端架A · 冰饮堆头"
    assert first["shelf_label"] != second["shelf_label"]  # 位号不同（价签位 01 / 02）
