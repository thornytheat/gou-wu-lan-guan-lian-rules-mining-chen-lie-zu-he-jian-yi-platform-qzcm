"""审计日志：业务动作显式记录（登录 / 跑挖掘 / 复核 / 发布 / 导出）。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.models.user import User


def record(
    db: Session,
    action: str,
    actor: User | None = None,
    entity_type: str = "",
    entity_id: Any = "",
    detail: dict[str, Any] | None = None,
    client_ip: str = "",
    trace_id: str = "",
) -> AuditLog:
    row = AuditLog(
        action=action,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "",
        actor_role=actor.role if actor else "",
        entity_type=entity_type,
        entity_id=str(entity_id),
        detail=detail or {},
        client_ip=client_ip,
        trace_id=trace_id,
    )
    db.add(row)
    return row


def serialize(row: AuditLog) -> dict:
    return {
        "id": str(row.id),
        "action": row.action,
        "actor_email": row.actor_email,
        "actor_role": row.actor_role,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "detail": row.detail,
        "client_ip": row.client_ip,
        "trace_id": row.trace_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
