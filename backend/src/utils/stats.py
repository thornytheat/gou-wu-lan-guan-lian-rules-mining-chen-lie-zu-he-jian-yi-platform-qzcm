"""统计工具：Wilson 置信区间 + 数值收敛（手写，不引入 scipy）。"""
from __future__ import annotations

import math

from src.config.settings import settings


def wilson_interval(successes: int, n: int, z: float | None = None) -> tuple[float, float]:
    """二项比例的 Wilson 置信区间（闭式解，含小样本修正）。"""
    if n <= 0:
        return 0.0, 0.0
    z = settings.wilson_z if z is None else z
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def wilson_lift_interval(successes: int, n: int, consequent_support: float) -> tuple[float, float]:
    """把置信度区间折算成提升度区间（lift = conf / sup(B)）。"""
    low, high = wilson_interval(successes, n)
    if consequent_support <= 0:
        return 0.0, 0.0
    return low / consequent_support, high / consequent_support


def round2(value: float) -> float:
    return round(value + 1e-9, 2)
