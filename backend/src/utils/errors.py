"""业务异常：带错误码 / 人话消息 / 调试细节 / HTTP 状态。"""
from __future__ import annotations

from typing import Any

from src.constants import error_codes as codes


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        detail: str = "",
        http_status: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or codes.ERROR_MESSAGES.get(code, "请求失败")
        self.detail = detail
        self.http_status = http_status or codes.HTTP_STATUS.get(code, 400)
        self.extra = extra or {}
        super().__init__(self.message)

    def to_payload(self, trace_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "trace_id": trace_id,
        }
        if self.extra:
            payload["extra"] = self.extra
        return payload
