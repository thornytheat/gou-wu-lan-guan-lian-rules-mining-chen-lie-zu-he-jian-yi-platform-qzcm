"""规则查询、复核（采纳/驳回/挂起）与详情聚合。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import ReviewDecision, RuleStatus
from src.constants.limits import MAX_PAGE_SIZE
from src.constants.log_templates import ACTION_RULE_BATCH_REVIEW, ACTION_RULE_REVIEW
from src.models.rule_candidate import RuleCandidate
from src.models.rule_review import RuleReview
from src.models.user import User
from src.services import audit_service, basket_service, fixtures_loader, mining_service
from src.utils.errors import AppError

DECISION_STATUS = {
    ReviewDecision.ADOPT.value: RuleStatus.ADOPTED.value,
    ReviewDecision.REJECT.value: RuleStatus.REJECTED.value,
    ReviewDecision.PARK.value: RuleStatus.PARKED.value,
}


def scope_run(db: Session, run_id: str | None) -> dict:
    if run_id:
        run = mining_service.get_run(db, run_id)
    else:
        run = mining_service.latest_run(db)
    if run is None:
        return {"run": None, "rules": []}
    rows = list(
        db.execute(
            select(RuleCandidate)
            .where(RuleCandidate.run_id == run.id)
            .order_by(RuleCandidate.uplift_month.desc(), RuleCandidate.lift.desc())
        ).scalars()
    )
    return {"run": run, "rules": rows}


def serialize_rule(row: RuleCandidate, names: dict[str, str]) -> dict:
    ante = [names.get(code, code) for code in row.antecedent]
    cons = [names.get(code, code) for code in row.consequent]
    meta = fixtures_loader.zone_payload(row.rule_key.split("@")[-1])
    return {
        "id": str(row.id),
        "rule_key": row.rule_key,
        "run_id": str(row.run_id),
        "antecedent": row.antecedent,
        "consequent": row.consequent,
        "antecedent_labels": ante,
        "consequent_labels": cons,
        "label": f"{' + '.join(ante)} → {' + '.join(cons)}",
        "support": float(row.support),
        "confidence": float(row.confidence),
        "lift": float(row.lift),
        "conviction": float(row.conviction),
        "cooccur_count": row.cooccur_count,
        "counterexample_count": row.counterexample_count,
        "status": row.status,
        "stable": row.stable,
        "tier_lifts": {
            "high": float(row.tier_high_lift) if row.tier_high_lift is not None else None,
            "mid": float(row.tier_mid_lift) if row.tier_mid_lift is not None else None,
            "low": float(row.tier_low_lift) if row.tier_low_lift is not None else None,
        },
        "tier_detail": row.tier_detail or [],
        "ci_low": float(row.ci_low) if row.ci_low is not None else None,
        "ci_high": float(row.ci_high) if row.ci_high is not None else None,
        "uplift_month": float(row.uplift_month),
        "conflict_group": row.conflict_group,
        "zone": meta.get("zone", ""),
        "shelf_label": meta.get("shelf_label", ""),
        "note": meta.get("note", ""),
        "reviews": [],
    }


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
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    scoped = scope_run(db, run_id)
    run = scoped["run"]
    rows = scoped["rules"]
    names, _ = basket_service.sku_maps(db)
    items = [serialize_rule(row, names) for row in rows]

    if status:
        items = [item for item in items if item["status"] == status]
    if stable is not None:
        items = [item for item in items if item["stable"] is stable]
    if min_lift is not None:
        items = [item for item in items if item["lift"] >= min_lift]
    if keyword:
        needle = keyword.strip().lower()
        items = [
            item
            for item in items
            if needle in item["label"].lower() or needle in item["rule_key"].lower()
        ]

    sort_key = {
        "uplift": lambda item: item["uplift_month"],
        "lift": lambda item: item["lift"],
        "confidence": lambda item: item["confidence"],
        "conviction": lambda item: item["conviction"],
        "cooccur": lambda item: item["cooccur_count"],
        "ci_low": lambda item: item["ci_low"] or 0,
    }.get(sort, lambda item: item["uplift_month"])
    items.sort(key=sort_key, reverse=(direction != "asc"))

    total = len(items)
    start = (page - 1) * page_size
    stats = {
        "total": len(rows),
        "adopted": sum(1 for row in rows if row.status == RuleStatus.ADOPTED.value),
        "stable": sum(1 for row in rows if row.stable),
        "candidate": sum(1 for row in rows if row.status == RuleStatus.CANDIDATE.value),
        "total_uplift": round(sum(float(row.uplift_month) for row in rows), 2),
    }
    return {
        "run": mining_service.serialize_run(run) if run else None,
        "rules": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "stats": stats,
    }


def get_rule(db: Session, rule_id: str) -> RuleCandidate:
    row = db.get(RuleCandidate, rule_id)
    if row is None:
        raise AppError(codes.NOT_FOUND, "规则不存在", f"rule_id={rule_id}")
    return row


def serialize_review(db: Session, review: RuleReview) -> dict:
    reviewer = db.get(User, review.reviewer_id)
    return {
        "id": str(review.id),
        "decision": review.decision,
        "reason": review.reason,
        "reviewer": reviewer.display_name if reviewer else "",
        "reviewer_email": reviewer.email if reviewer else "",
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
    }


def detail(db: Session, rule_id: str) -> dict:
    row = get_rule(db, rule_id)
    names, _ = basket_service.sku_maps(db)
    payload = serialize_rule(row, names)
    reviews = list(
        db.execute(
            select(RuleReview).where(RuleReview.rule_id == row.id).order_by(RuleReview.reviewed_at.desc())
        ).scalars()
    )
    payload["reviews"] = [serialize_review(db, review) for review in reviews]
    payload["matrix"] = basket_service.cooccurrence_matrix(db)
    payload["counterexamples"] = basket_service.counterexample_baskets(
        db, row.antecedent, row.consequent
    )
    payload["run"] = mining_service.serialize_run(mining_service.get_run(db, str(row.run_id)))
    payload["uplift_basis"] = {
        "cooccur_count": row.cooccur_count,
        "mean_amount": payload["run"]["summary"].get("mean_amount"),
        "adoption_rate": payload["run"]["summary"].get("params", {}).get("adoption_rate"),
        "monthly_factor": round(30 / max(1, payload["run"]["summary"].get("params", {}).get("sample_days", 7)), 4),
        "formula": "共现小票数 × 客单均值 × 采纳率 0.35 × (30 / 样本天数)",
    }
    return payload


def _apply_decision(db: Session, row: RuleCandidate, user: User, decision: str, reason: str) -> None:
    if decision not in DECISION_STATUS:
        raise AppError(codes.VALIDATION_ERROR, "复核动作不合法", f"decision={decision}")
    if not reason.strip() and decision in (ReviewDecision.REJECT.value, ReviewDecision.PARK.value):
        raise AppError(codes.VALIDATION_ERROR, "驳回或挂起必须填写理由", "reason required")
    row.status = DECISION_STATUS[decision]
    db.add(
        RuleReview(
            rule_id=row.id,
            reviewer_id=user.id,
            decision=decision,
            reason=reason.strip(),
        )
    )


def review(
    db: Session, user: User, rule_id: str, decision: str, reason: str, trace_id: str = ""
) -> dict:
    row = get_rule(db, rule_id)
    _apply_decision(db, row, user, decision, reason)
    audit_service.record(
        db,
        action=ACTION_RULE_REVIEW,
        actor=user,
        entity_type="rule_candidate",
        entity_id=row.id,
        detail={"decision": decision, "rule_key": row.rule_key, "reason": reason[:120]},
        trace_id=trace_id,
    )
    db.commit()
    return detail(db, rule_id)


def batch_review(
    db: Session, user: User, rule_ids: list[str], decision: str, reason: str, trace_id: str = ""
) -> dict:
    if not rule_ids:
        raise AppError(codes.VALIDATION_ERROR, "请选择至少一条规则", "rule_ids empty")
    rows = list(db.execute(select(RuleCandidate).where(RuleCandidate.id.in_(rule_ids))).scalars())
    if not rows:
        raise AppError(codes.NOT_FOUND, "未找到可复核的规则", "rule_ids not found")
    for row in rows:
        _apply_decision(db, row, user, decision, reason)
    audit_service.record(
        db,
        action=ACTION_RULE_BATCH_REVIEW,
        actor=user,
        entity_type="rule_candidate",
        entity_id=",".join(rule_ids)[:64],
        detail={"decision": decision, "count": len(rows), "reason": reason[:120]},
        trace_id=trace_id,
    )
    db.commit()
    names, _ = basket_service.sku_maps(db)
    return {"updated": len(rows), "rules": [serialize_rule(row, names) for row in rows]}
