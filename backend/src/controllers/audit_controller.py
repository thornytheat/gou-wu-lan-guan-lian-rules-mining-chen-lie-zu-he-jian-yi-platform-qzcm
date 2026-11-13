"""审计日志（仅 admin）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.services import audit_service


def list_logs(db: Session, limit: int = 60) -> dict:
    rows = list(
        db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).scalars()
    )
    return {"logs": [audit_service.serialize(row) for row in rows], "count": len(rows)}
