"""陈列建议请求模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeneratePlanRequest(BaseModel):
    run_id: str | None = None


class SlotUpdateRequest(BaseModel):
    status: Literal["draft", "published", "archived"]
    note: str = Field(default="", max_length=400)
