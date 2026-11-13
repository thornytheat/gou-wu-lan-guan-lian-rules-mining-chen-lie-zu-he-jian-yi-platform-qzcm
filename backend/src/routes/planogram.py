from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import planogram_controller
from src.middlewares.rbac import require_permission
from src.middlewares.rate_limit import rate_limit
from src.models.user import User
from src.schemas.planogram import GeneratePlanRequest, SlotUpdateRequest

router = APIRouter(tags=["planogram"])


@router.get("/planogram")
def list_plans(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("planogram:read")),
) -> dict:
    return planogram_controller.list_plans(db, user.role)


@router.post("/planogram/generate")
def generate(
    payload: GeneratePlanRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("planogram:write")),
    _=rate_limit("mining"),
) -> dict:
    return planogram_controller.generate(
        db, user, payload, trace_id=getattr(request.state, "trace_id", "")
    )


@router.get("/planogram/{plan_code}")
def get_plan(
    plan_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("planogram:read")),
) -> dict:
    return planogram_controller.get_plan(db, plan_code, user.role)


@router.post("/planogram/{plan_code}/publish")
def publish(
    plan_code: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("planogram:publish")),
) -> dict:
    return planogram_controller.publish(
        db, user, plan_code, trace_id=getattr(request.state, "trace_id", "")
    )


@router.get("/planogram/{plan_code}/export")
def export_plan(
    plan_code: str,
    db: Session = Depends(get_db),
    _=Depends(require_permission("rules:export")),
):
    return planogram_controller.export_plan(db, plan_code)


@router.patch("/planogram/slots/{slot_id}")
def update_slot(
    slot_id: str,
    payload: SlotUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("planogram:write")),
) -> dict:
    return planogram_controller.update_slot(
        db, user, slot_id, payload, trace_id=getattr(request.state, "trace_id", "")
    )
