from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import rule_controller
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.rule import BatchReviewRequest, ReviewRequest

router = APIRouter(tags=["rules"])


@router.get("/rules/export.csv")
def export_rules(
    run_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_permission("rules:export")),
):
    return rule_controller.export_rules(db, run_id)


@router.get("/rules")
def list_rules(
    run_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    stable: bool | None = Query(default=None),
    min_lift: float | None = Query(default=None),
    q: str = Query(default=""),
    sort: str = Query(default="uplift"),
    direction: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_permission("rules:read")),
) -> dict:
    return rule_controller.list_rules(
        db,
        run_id=run_id,
        status=status,
        stable=stable,
        min_lift=min_lift,
        keyword=q,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )


@router.post("/rules/batch-review")
def batch_review(
    payload: BatchReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("rules:review")),
) -> dict:
    return rule_controller.batch_review(
        db, user, payload, trace_id=getattr(request.state, "trace_id", "")
    )


@router.get("/rules/{rule_id}")
def detail(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("rules:read")),
) -> dict:
    return rule_controller.detail(db, rule_id)


@router.post("/rules/{rule_id}/review")
def review(
    rule_id: str,
    payload: ReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("rules:review")),
) -> dict:
    return rule_controller.review(
        db, user, rule_id, payload, trace_id=getattr(request.state, "trace_id", "")
    )
