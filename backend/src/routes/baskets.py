from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import basket_controller
from src.middlewares.rbac import require_permission

router = APIRouter(tags=["baskets"])


@router.get("/baskets/summary")
def summary(db: Session = Depends(get_db), _=Depends(require_permission("baskets:read"))) -> dict:
    """小票样本与支持度概览；店长（viewer）无原始 POS 明细权限 → 403。"""
    return basket_controller.summary(db)
