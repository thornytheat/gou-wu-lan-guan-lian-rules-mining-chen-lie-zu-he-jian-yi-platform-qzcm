"""算法 2（下半）：K=6 冲突组贪心背包，输出陈列建议位。

纯函数（select_slots / assign_positions / ZONE_ORDER）已抽到 src/services/planogram_core.py，
本模块重新导出并保留原调用路径（mining_service 仍用 planogram_service.select_slots），
行为与抽取前逐字一致。
"""
from __future__ import annotations

from src.constants.enums import SlotStatus
from src.services.planogram_core import (  # noqa: F401  (re-export 保持老调用方不变)
    ZONE_ORDER,
    assign_positions,
    select_slots,
)


# ---------------------------------------------------------------- DB 层 ----


from datetime import datetime, timezone  # noqa: E402

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.constants import error_codes as codes  # noqa: E402
from src.constants.enums import RuleStatus, SlotStatus  # noqa: E402
from src.constants.log_templates import (  # noqa: E402
    ACTION_PLANOGRAM_GENERATE,
    ACTION_PLANOGRAM_PUBLISH,
)
from src.models.planogram_slot import PlanogramSlot  # noqa: E402
from src.models.rule_candidate import RuleCandidate  # noqa: E402
from src.models.user import User  # noqa: E402
from src.services import audit_service, basket_service, fixtures_loader, mining_service  # noqa: E402
from src.utils.errors import AppError  # noqa: E402


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _candidates(db: Session, run) -> list[dict]:
    names, _ = basket_service.sku_maps(db)
    rows = list(
        db.execute(
            select(RuleCandidate)
            .where(RuleCandidate.run_id == run.id)
            .order_by(RuleCandidate.uplift_month.desc())
        ).scalars()
    )
    out: list[dict] = []
    for row in rows:
        if row.status == RuleStatus.REJECTED.value:
            continue
        meta = fixtures_loader.zone_payload(row.rule_key.split("@")[-1])
        out.append(
            {
                "rule_id": str(row.id),
                "rule_key": row.rule_key,
                "label": f"{' + '.join(names.get(code, code) for code in row.antecedent)} → "
                f"{' + '.join(names.get(code, code) for code in row.consequent)}",
                "uplift_month": float(row.uplift_month),
                "lift": float(row.lift),
                "stable": row.stable,
                "conflict_group": meta.get("zone_code") or row.conflict_group or "未分组",
                "zone": meta.get("zone", ""),
                "shelf_label": meta.get("shelf_label", ""),
                "note": meta.get("note", ""),
                "status": row.status,
            }
        )
    return out


def generate_plan(db: Session, user: User, run_id: str | None = None, trace_id: str = "") -> dict:
    run = mining_service.get_run(db, run_id) if run_id else mining_service.latest_run(db)
    if run is None:
        raise AppError(codes.CONFLICT, "还没有成功的挖掘批次，请先运行挖掘", "no succeeded run")
    plan_code = f"PLAN-{run.run_label.replace('RUN-', '')}"
    existing = list(db.execute(select(PlanogramSlot).where(PlanogramSlot.plan_code == plan_code)).scalars())
    if existing and any(slot.status == SlotStatus.PUBLISHED.value for slot in existing):
        raise AppError(codes.CONFLICT, "该建议单已发布，不能重新生成", f"plan_code={plan_code}")
    if existing:
        db.execute(delete(PlanogramSlot).where(PlanogramSlot.plan_code == plan_code))
        db.flush()

    params = run.params or {}
    k = int(params.get("shelf_slots", 6))
    candidates = _candidates(db, run)
    if not candidates:
        raise AppError(codes.CONFLICT, "当前批次没有可陈列的规则", "no candidates")
    selection = select_slots(candidates, k=k)
    ordered = assign_positions(selection["slots"])
    for slot in ordered:
        db.add(
            PlanogramSlot(
                slot_key=f"{plan_code}@{slot['rule_key'].split('@')[-1]}",
                plan_code=plan_code,
                rule_id=slot["rule_id"],
                shelf_label=slot["shelf_label"] or f"{slot['zone']} · 建议位",
                zone=slot["zone"] or "未分配货架区",
                conflict_group=slot["conflict_group"],
                position_index=slot["position_index"],
                est_uplift=slot["uplift_month"],
                status=SlotStatus.DRAFT.value,
                note=slot.get("note", ""),
            )
        )
    audit_service.record(
        db,
        action=ACTION_PLANOGRAM_GENERATE,
        actor=user,
        entity_type="planogram_slot",
        entity_id=plan_code,
        detail={
            "plan_code": plan_code,
            "run_label": run.run_label,
            "slots": selection["slot_count"],
            "skipped": len(selection["skipped"]),
            "total_uplift": selection["total_uplift"],
        },
        trace_id=trace_id,
    )
    db.commit()
    return get_plan(db, plan_code, user.role)


def list_plans(db: Session, role: str = "admin") -> dict:
    plan_codes = list(
        db.execute(select(PlanogramSlot.plan_code).group_by(PlanogramSlot.plan_code)).scalars()
    )
    items = []
    for code in sorted(plan_codes, reverse=True):
        plan = get_plan(db, code, role)
        if plan is None:
            continue
        items.append(
            {
                "plan_code": plan["plan_code"],
                "status": plan["status"],
                "slot_count": plan["slot_count"],
                "total_uplift": plan["total_uplift"],
                "published_at": plan["published_at"],
                "run_label": plan["run_label"],
            }
        )
    return {"plans": items, "count": len(items)}


def get_plan(db: Session, plan_code: str, role: str) -> dict | None:
    slots = list(
        db.execute(
            select(PlanogramSlot)
            .where(PlanogramSlot.plan_code == plan_code)
            .order_by(PlanogramSlot.position_index)
        ).scalars()
    )
    if not slots:
        return None
    published = [slot for slot in slots if slot.status == SlotStatus.PUBLISHED.value]
    if role == "viewer" and not published:
        return None
    names, _ = basket_service.sku_maps(db)
    rule_ids = {slot.rule_id for slot in slots}
    rules = {
        row.id: row
        for row in db.execute(select(RuleCandidate).where(RuleCandidate.id.in_(rule_ids))).scalars()
    }
    run = None
    if rules:
        run = mining_service.get_run(db, str(next(iter(rules.values())).run_id))
    payload_slots = []
    for slot in slots:
        rule = rules.get(slot.rule_id)
        meta = fixtures_loader.zone_payload(slot.slot_key.split("@")[-1])
        payload_slots.append(
            {
                "id": str(slot.id),
                "slot_key": slot.slot_key,
                "position_index": slot.position_index,
                "shelf_label": slot.shelf_label,
                "zone": slot.zone,
                "conflict_group": slot.conflict_group,
                "est_uplift": float(slot.est_uplift),
                "status": slot.status,
                "note": slot.note,
                "published_at": slot.published_at.isoformat() if slot.published_at else None,
                "rule": None
                if rule is None
                else {
                    "id": str(rule.id),
                    "rule_key": rule.rule_key,
                    "antecedent": rule.antecedent,
                    "consequent": rule.consequent,
                    "antecedent_labels": [names.get(code, code) for code in rule.antecedent],
                    "consequent_labels": [names.get(code, code) for code in rule.consequent],
                    "label": f"{' + '.join(names.get(code, code) for code in rule.antecedent)} → "
                    f"{' + '.join(names.get(code, code) for code in rule.consequent)}",
                    "lift": float(rule.lift),
                    "confidence": float(rule.confidence),
                    "cooccur_count": rule.cooccur_count,
                    "stable": rule.stable,
                    "status": rule.status,
                    "uplift_month": float(rule.uplift_month),
                },
                "buyer_hint": meta.get("note", slot.note),
            }
        )
    skipped: list[dict] = []
    if run is not None:
        selection = select_slots(_candidates(db, run), k=int((run.params or {}).get("shelf_slots", 6)))
        skipped = [
            {"rule_key": item["rule_key"], "label": item["label"], "reason": item["skip_reason"]}
            for item in selection["skipped"]
        ]
    params = run.params if run else {}
    summary = (run.summary if run else {}) or {}
    return {
        "plan_code": plan_code,
        "run_label": run.run_label if run else "",
        "basis": {
            "mean_amount": summary.get("mean_amount"),
            "adoption_rate": params.get("adoption_rate"),
            "sample_days": params.get("sample_days"),
            "monthly_factor": round(30 / max(1, int(params.get("sample_days", 7))), 4),
            "formula": "共现小票数 × 客单均值 × 采纳率 0.35 × (30 / 样本天数)",
        },
        "status": SlotStatus.PUBLISHED.value if published and len(published) == len(slots) else SlotStatus.DRAFT.value,
        "slot_count": len(slots),
        "total_uplift": round(sum(float(slot.est_uplift) for slot in slots), 2),
        "published_at": max((slot.published_at for slot in slots if slot.published_at), default=None).isoformat()
        if published
        else None,
        "slots": payload_slots,
        "skipped": skipped,
        "params": run.params if run else {},
    }


def publish_plan(db: Session, user: User, plan_code: str, trace_id: str = "") -> dict:
    slots = list(db.execute(select(PlanogramSlot).where(PlanogramSlot.plan_code == plan_code)).scalars())
    if not slots:
        raise AppError(codes.NOT_FOUND, "建议单不存在", f"plan_code={plan_code}")
    if all(slot.status == SlotStatus.PUBLISHED.value for slot in slots):
        return get_plan(db, plan_code, user.role)
    for slot in slots:
        slot.status = SlotStatus.PUBLISHED.value
        slot.published_at = _now()
    audit_service.record(
        db,
        action=ACTION_PLANOGRAM_PUBLISH,
        actor=user,
        entity_type="planogram_slot",
        entity_id=plan_code,
        detail={"plan_code": plan_code, "slots": len(slots)},
        trace_id=trace_id,
    )
    db.commit()
    return get_plan(db, plan_code, user.role)


def update_slot(db: Session, user: User, slot_id: str, status: str, note: str = "", trace_id: str = "") -> dict:
    slot = db.get(PlanogramSlot, slot_id)
    if slot is None:
        raise AppError(codes.NOT_FOUND, "建议位不存在", f"slot_id={slot_id}")
    if status not in {item.value for item in SlotStatus}:
        raise AppError(codes.VALIDATION_ERROR, "建议位状态不合法", f"status={status}")
    slot.status = status
    if note:
        slot.note = note
    if status == SlotStatus.PUBLISHED.value:
        slot.published_at = _now()
    audit_service.record(
        db,
        action=ACTION_PLANOGRAM_PUBLISH,
        actor=user,
        entity_type="planogram_slot",
        entity_id=slot.id,
        detail={"plan_code": slot.plan_code, "status": status},
        trace_id=trace_id,
    )
    db.commit()
    return get_plan(db, slot.plan_code, user.role)
