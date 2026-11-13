"""挖掘批次请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    min_support: float = Field(default=0.01, gt=0, le=0.5)
    min_confidence: float = Field(default=0.05, gt=0, le=1)
    max_itemset: int = Field(default=3, ge=2, le=4)
    filter_lift: float = Field(default=1.2, ge=0.5, le=10)
    filter_confidence: float = Field(default=0.25, gt=0, le=1)


class RunOut(BaseModel):
    id: str
    run_label: str
    status: str
    frequent_itemsets: int
    candidate_rules: int
    passed_rules: int
    stable_rules: int
    duration_ms: int
    created_at: str | None = None
