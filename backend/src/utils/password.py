"""密码哈希（bcrypt via passlib）。"""
from __future__ import annotations

from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return _ctx.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _ctx.verify(raw, hashed)
    except Exception:
        return False
