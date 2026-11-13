"""陈列建议：生成 / 查询 / 发布 / 导出工单。"""
from __future__ import annotations

from fastapi import Response
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.planogram import GeneratePlanRequest, SlotUpdateRequest
from src.services import export_service, planogram_service


def list_plans(db: Session, role: str) -> dict:
    return planogram_service.list_plans(db, role)


def generate(db: Session, user: User, payload: GeneratePlanRequest, trace_id: str = "") -> dict:
    return planogram_service.generate_plan(db, user, run_id=payload.run_id, trace_id=trace_id)


def get_plan(db: Session, plan_code: str, role: str) -> dict:
    plan = planogram_service.get_plan(db, plan_code, role)
    if plan is None:
        from src.constants import error_codes as codes
        from src.utils.errors import AppError

        raise AppError(codes.NOT_FOUND, "建议单不存在或尚未发布", f"plan_code={plan_code}")
    return plan


def publish(db: Session, user: User, plan_code: str, trace_id: str = "") -> dict:
    return planogram_service.publish_plan(db, user, plan_code, trace_id=trace_id)


def update_slot(db: Session, user: User, slot_id: str, payload: SlotUpdateRequest, trace_id: str = "") -> dict:
    return planogram_service.update_slot(db, user, slot_id, payload.status, payload.note, trace_id=trace_id)


def export_plan(db: Session, plan_code: str) -> Response:
    filename, body = export_service.planogram_csv(db, plan_code)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
