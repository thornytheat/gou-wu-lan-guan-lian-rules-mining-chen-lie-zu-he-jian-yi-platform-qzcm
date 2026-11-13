"""通用响应模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: str = ""
    trace_id: str | None = None


class MessageResponse(BaseModel):
    ok: bool = True
    message: str = ""
    data: dict[str, Any] | None = None
