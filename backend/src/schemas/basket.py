"""小票与数据集模型。"""
from __future__ import annotations

from pydantic import BaseModel


class BasketLine(BaseModel):
    sku: str
    name: str
    qty: int
    amount: float


class BasketSample(BaseModel):
    id: str
    basket_no: str
    store_code: str
    store_name: str
    store_tier: str
    channel: str
    basket_ts: str | None
    net_amount: float
    item_count: int
    lines: list[BasketLine]


class DatasetSummary(BaseModel):
    baskets: int
    skus: int
    lines: int
    avg_lines: float
    revenue: float
    mean_amount: float
    stores: int
    sample_days: int
    adoption_rate: float
    tiers: list[dict]
    store_rows: list[dict]
    sku_support: list[dict]
    sample_baskets: list[BasketSample]
