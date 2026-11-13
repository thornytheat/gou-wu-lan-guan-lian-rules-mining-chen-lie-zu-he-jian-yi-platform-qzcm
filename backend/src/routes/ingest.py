from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import ingest_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.ingest import DemoImportRequest, ImportRequest

router = APIRouter(tags=["ingest"])


@router.get("/ingest/summary")
def summary(
    db: Session = Depends(get_db),
    _=Depends(require_permission("baskets:read")),
) -> dict:
    """导入页概览：最近批次五类计数、最终有效小票、每日台账。"""
    return ingest_controller.summary(db)


@router.get("/ingest/batches/{batch_no}")
def replay(
    batch_no: str,
    db: Session = Depends(get_db),
    _=Depends(require_permission("baskets:read")),
) -> dict:
    return ingest_controller.replay(db, batch_no)


@router.post("/ingest/import")
def import_batch(
    payload: ImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("baskets:import")),
    _=rate_limit("ingest"),
) -> dict:
    return ingest_controller.import_batch(
        db, user, payload, trace_id=getattr(request.state, "trace_id", "")
    )


@router.post("/ingest/demo")
def import_demo(
    payload: DemoImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("baskets:import")),
    _=rate_limit("ingest"),
) -> dict:
    return ingest_controller.import_demo(
        db, user, payload, trace_id=getattr(request.state, "trace_id", "")
    )
