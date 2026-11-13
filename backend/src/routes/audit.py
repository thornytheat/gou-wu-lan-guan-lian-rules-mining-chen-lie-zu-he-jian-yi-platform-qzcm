from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.rbac import require_permission

router = APIRouter(tags=["audit"])


@router.get("/audit/logs")
def list_logs(
    limit: int = Query(default=60, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_permission("audit:read")),
) -> dict:
    return audit_controller.list_logs(db, limit=limit)
