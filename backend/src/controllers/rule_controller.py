"""规则列表 / 详情 / 复核 / 导出。"""
from __future__ import annotations

from fastapi import Response
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.rule import BatchReviewRequest, ReviewRequest
from src.services import export_service, rule_service


def list_rules(
    db: Session,
    run_id: str | None = None,
    status: str | None = None,
    stable: bool | None = None,
    min_lift: float | None = None,
    keyword: str = "",
    sort: str = "uplift",
    direction: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    return rule_service.list_rules(
        db,
        run_id=run_id,
        status=status,
        stable=stable,
        min_lift=min_lift,
        keyword=keyword,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )


def detail(db: Session, rule_id: str) -> dict:
    return rule_service.detail(db, rule_id)


def review(db: Session, user: User, rule_id: str, payload: ReviewRequest, trace_id: str = "") -> dict:
    return rule_service.review(db, user, rule_id, payload.decision, payload.reason, trace_id=trace_id)


def batch_review(db: Session, user: User, payload: BatchReviewRequest, trace_id: str = "") -> dict:
    return rule_service.batch_review(
        db, user, payload.rule_ids, payload.decision, payload.reason, trace_id=trace_id
    )


def export_rules(db: Session, run_id: str | None = None) -> Response:
    filename, body = export_service.rules_csv(db, run_id)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
