"""健康检查（Docker healthcheck 目标）。"""
from __future__ import annotations

from src.config.database import ping_db
from src.config.settings import settings


def health() -> dict:
    db_ok = ping_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "basketrule-backend",
        "brand": settings.brand,
        "db": db_ok,
        "version": "1.0.0",
    }
