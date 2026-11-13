"""挖掘参数归一 / 门禁校验 / 规则过滤（纯函数，不 import Session、不碰数据库）。

抽出来是为了让「参数口径 + 过滤口径」能被单元测试直接覆盖；
mining_service 只是调用这里的函数，行为与抽取前逐字一致：

  归一：默认参数打底，payload 里非 None 的键覆盖（None 视为“未传”）
  校验：min_support ∈ (0, 0.5]；min_confidence ∈ (0, 1]；max_itemset ∈ {2,3,4}
  过滤：业务口径是严格大于（lift > filter_lift 且 confidence > filter_confidence），
        恰好等于阈值的规则会被剔除。
"""
from __future__ import annotations

from src.constants import error_codes as codes
from src.utils.errors import AppError


def normalize_params(defaults: dict, payload: dict | None) -> dict:
    """默认值 + 非空覆盖；返回新 dict，不改默认值。"""
    params = dict(defaults)
    for key, value in (payload or {}).items():
        if value is not None:
            params[key] = value
    return params


def validate_params(params: dict) -> None:
    """参数门禁：越界一律 422 VALIDATION_ERROR，不静默降级。"""
    if not (0 < params["min_support"] <= 0.5):
        raise AppError(
            codes.VALIDATION_ERROR,
            "最小支持度需在 (0, 0.5] 之间",
            f"min_support={params['min_support']}",
        )
    if not (0 < params["min_confidence"] <= 1):
        raise AppError(
            codes.VALIDATION_ERROR,
            "置信度下限需在 (0, 1] 之间",
            f"min_confidence={params['min_confidence']}",
        )
    if params["max_itemset"] not in (2, 3, 4):
        raise AppError(
            codes.VALIDATION_ERROR,
            "最大项集长度只支持 2/3/4",
            f"max_itemset={params['max_itemset']}",
        )


def filter_rules(
    rules: list[dict], filter_lift: float, filter_confidence: float
) -> list[dict]:
    """可执行规则口径：lift 与 confidence 都必须**严格大于**阈值（保持原实现）。"""
    return [
        rule
        for rule in rules
        if rule["lift"] > filter_lift and rule["confidence"] > filter_confidence
    ]
