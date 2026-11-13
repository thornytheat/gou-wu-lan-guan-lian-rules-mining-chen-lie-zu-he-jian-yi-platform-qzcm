"""规则复核请求模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    decision: Literal["adopt", "reject", "park"]
    reason: str = Field(default="", max_length=400)


class BatchReviewRequest(BaseModel):
    rule_ids: list[str] = Field(min_length=1, max_length=50)
    decision: Literal["adopt", "reject", "park"]
    reason: str = Field(default="", max_length=400)
