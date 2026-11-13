from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import mining_controller
from src.middlewares.rbac import require_permission
from src.middlewares.rate_limit import rate_limit
from src.models.user import User
from src.schemas.mining import RunCreateRequest

router = APIRouter(tags=["mining"])


@router.get("/mining/runs")
def list_runs(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _=Depends(require_permission("mining:read")),
) -> dict:
    return mining_controller.list_runs(db, limit=limit)


@router.post("/mining/runs")
def create_run(
    payload: RunCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mining:run")),
    _=rate_limit("mining"),
) -> dict:
    return mining_controller.create_run(db, user, payload, trace_id=getattr(request.state, "trace_id", ""))


@router.get("/mining/runs/{run_id}")
def get_run(
    run_id: str,
    with_itemsets: bool = Query(default=False),
    db: Session = Depends(get_db),
    _=Depends(require_permission("mining:read")),
) -> dict:
    return mining_controller.get_run(db, run_id, with_itemsets=with_itemsets)


@router.get("/mining/runs/{run_id}/itemsets")
def itemsets(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    size: int | None = Query(default=None, ge=1, le=4),
    db: Session = Depends(get_db),
    _=Depends(require_permission("mining:read")),
) -> dict:
    return mining_controller.itemsets(db, run_id, offset=offset, limit=limit, size=size)
