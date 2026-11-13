"""挖掘批次编排：参数 → Apriori → 规则过滤 → 分层稳定性 → 陈列选择预览。

算法全部在 Python 侧真算（numpy/pandas 不参与，纯标准库足够 3,000 张小票）；
前端只消费后端回传的数值，不做任何硬编码。
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.config.database import session_scope
from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.log_templates import ACTION_MINING_RUN
from src.constants.enums import RuleStatus, RunStatus
from src.constants.limits import MAX_BASKETS_PER_RUN
from src.models.mining_run import MiningRun
from src.models.order_basket import OrderBasket
from src.models.rule_candidate import RuleCandidate
from src.models.user import User
from src.services import (
    apriori_service,
    audit_service,
    basket_service,
    fixtures_loader,
    mining_core,
    planogram_service,
    stability_service,
)
from src.utils.errors import AppError
from src.utils.logger import get_logger

logger = get_logger("basketrule.mining")

DEFAULT_PARAMS = {
    "min_support": settings.default_min_support,
    "min_confidence": settings.default_min_confidence,
    "max_itemset": settings.default_max_itemset,
    "filter_lift": settings.default_filter_lift,
    "filter_confidence": settings.default_filter_confidence,
    "shelf_slots": settings.shelf_slots,
    "adoption_rate": settings.adoption_rate,
    "sample_days": settings.sample_days,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_params(payload: dict | None) -> dict:
    """默认参数 + payload 覆盖（口径见 mining_core.normalize_params）。"""
    return mining_core.normalize_params(DEFAULT_PARAMS, payload)


def create_run(db: Session, user: User, payload: dict | None, trace_id: str = "") -> MiningRun:
    params = normalize_params(payload)
    mining_core.validate_params(params)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    label = f"RUN-{stamp}"
    seq = 1
    while db.execute(select(MiningRun.id).where(MiningRun.run_label == label)).first():
        seq += 1
        label = f"RUN-{stamp}-{seq}"

    run = MiningRun(
        run_label=label,
        params=params,
        status=RunStatus.QUEUED.value,
        itemsets=[],
        summary={},
        created_by=user.id,
        created_at=_now(),
    )
    db.add(run)
    db.flush()
    audit_service.record(
        db,
        action=ACTION_MINING_RUN,
        actor=user,
        entity_type="mining_run",
        entity_id=run.id,
        detail={"run_label": label, "params": params},
        trace_id=trace_id,
    )
    db.commit()

    dispatch_run(str(run.id))
    return run


def dispatch_run(run_id: str) -> None:
    """投递 Celery 任务；broker 不可用时同步兜底执行（保证演示链路不中断）。"""
    try:
        from src.config.celery_app import TASK_RUN_MINING, celery_app

        celery_app.send_task(TASK_RUN_MINING, args=[run_id], queue="celery")
        logger.info("mining run %s dispatched to worker", run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("dispatch failed (%s), run %s inline", exc, run_id)
        execute_run(run_id)


def execute_run(run_id: str) -> None:
    """worker / 兜底路径共用入口：独立 session，异常落 run.error。"""
    try:
        with session_scope() as db:
            run = db.get(MiningRun, run_id)
            if run is None or run.status == RunStatus.SUCCEEDED.value:
                return
            run.status = RunStatus.RUNNING.value
            db.flush()
            _execute(db, run)
    except Exception as exc:  # noqa: BLE001
        logger.error("run %s failed: %s", run_id, exc, exc_info=True)
        with session_scope() as db:
            run = db.get(MiningRun, run_id)
            if run is not None:
                run.status = RunStatus.FAILED.value
                run.error = str(exc)[:800]
                run.finished_at = _now()


def _execute(db: Session, run: MiningRun) -> None:
    started = time.perf_counter()
    params = normalize_params(run.params)
    transactions = basket_service.load_transactions(db)
    if not transactions:
        raise RuntimeError("小票样本为空，无法挖掘")
    if len(transactions) > MAX_BASKETS_PER_RUN:
        raise RuntimeError(f"小票样本超过单次上限 {MAX_BASKETS_PER_RUN}")

    basket_count = db.execute(select(func.count()).select_from(OrderBasket)).scalar_one()
    revenue = db.execute(select(func.coalesce(func.sum(OrderBasket.net_amount), 0))).scalar_one()
    mean_amount = round(float(revenue) / basket_count, 2)

    result = apriori_service.apriori(
        [basket for basket, _ in transactions],
        min_support=params["min_support"],
        max_itemset=params["max_itemset"],
    )
    candidate_rules = apriori_service.build_rules(
        result["counts"], result["basket_count"], params["min_confidence"]
    )
    passed = mining_core.filter_rules(
        candidate_rules, params["filter_lift"], params["filter_confidence"]
    )

    # 同一批次重跑：先清掉旧规则（含关联建议位由 planogram 负责重算）
    existing = db.execute(select(RuleCandidate.id).where(RuleCandidate.run_id == run.id)).scalars().all()
    if existing:
        db.execute(delete(RuleCandidate).where(RuleCandidate.run_id == run.id))
        db.flush()

    names, _ = basket_service.sku_maps(db)
    rows: list[RuleCandidate] = []
    preview: list[dict] = []
    for rule in passed:
        metrics = stability_service.analyze_rule(
            transactions, rule, mean_amount=mean_amount, params=params
        )
        meta = fixtures_loader.zone_payload(rule["rule_key"])
        row = RuleCandidate(
            rule_key=f"{run.run_label}@{rule['rule_key']}",
            run_id=run.id,
            antecedent=rule["antecedent"],
            consequent=rule["consequent"],
            support=round(rule["support"], 6),
            confidence=round(rule["confidence"], 6),
            lift=round(rule["lift"], 4),
            conviction=round(rule["conviction"], 4),
            cooccur_count=rule["cooccur_count"],
            counterexample_count=metrics["counterexample_count"],
            status=RuleStatus.CANDIDATE.value,
            stable=metrics["stable"],
            tier_high_lift=metrics["tier_lifts"].get("high"),
            tier_mid_lift=metrics["tier_lifts"].get("mid"),
            tier_low_lift=metrics["tier_lifts"].get("low"),
            ci_low=metrics["ci_low"],
            ci_high=metrics["ci_high"],
            tier_detail=metrics["tiers"],
            uplift_month=metrics["uplift_month"],
            conflict_group=meta["zone_code"] or "未分组",
        )
        db.add(row)
        rows.append(row)
        preview.append(
            {
                "rule_key": rule["rule_key"],
                "label": f"{' + '.join(names.get(code, code) for code in rule['antecedent'])} → "
                f"{' + '.join(names.get(code, code) for code in rule['consequent'])}",
                "uplift_month": metrics["uplift_month"],
                "lift": metrics["lift"],
                "stable": metrics["stable"],
                "conflict_group": meta["zone_code"] or "未分组",
                "zone": meta["zone"],
                "shelf_label": meta["shelf_label"],
            }
        )
    db.flush()

    selection = planogram_service.select_slots(preview, k=params["shelf_slots"])
    duration_ms = int((time.perf_counter() - started) * 1000)

    run.status = RunStatus.SUCCEEDED.value
    run.params = params
    run.frequent_itemsets = result["frequent_itemsets"]
    run.candidate_rules = len(candidate_rules)
    run.passed_rules = len(passed)
    run.stable_rules = sum(1 for row in rows if row.stable)
    run.basket_count = result["basket_count"]
    run.duration_ms = duration_ms
    run.itemsets = result["itemsets"]
    run.summary = {
        "basket_count": result["basket_count"],
        "min_count": result["min_count"],
        "mean_amount": mean_amount,
        "by_size": result["by_size"],
        "frequent_itemsets": result["frequent_itemsets"],
        "candidate_rules": len(candidate_rules),
        "passed_rules": len(passed),
        "filtered_out": len(candidate_rules) - len(passed),
        "stable_rules": sum(1 for row in rows if row.stable),
        "params": params,
        "selection": {
            "slot_count": selection["slot_count"],
            "total_uplift": selection["total_uplift"],
            "slots": [
                {
                    "label": slot["label"],
                    "rule_key": slot["rule_key"],
                    "uplift_month": slot["uplift_month"],
                    "shelf_label": slot["shelf_label"],
                    "zone": slot["zone"],
                }
                for slot in selection["slots"]
            ],
            "skipped": [
                {"rule_key": item["rule_key"], "label": item["label"], "reason": item["skip_reason"]}
                for item in selection["skipped"]
            ],
        },
        "algorithm": "apriori@1.0.0 + wilson-tier@1.0.0 + greedy-knapsack@1.0.0",
    }
    run.finished_at = _now()
    db.flush()
    logger.info(
        "run %s done: itemsets=%s candidates=%s passed=%s stable=%s slots=%s uplift=%s",
        run.run_label,
        run.frequent_itemsets,
        run.candidate_rules,
        run.passed_rules,
        run.stable_rules,
        selection["slot_count"],
        selection["total_uplift"],
    )


def latest_run(db: Session) -> MiningRun | None:
    return db.execute(
        select(MiningRun).where(MiningRun.status == RunStatus.SUCCEEDED.value).order_by(MiningRun.created_at.desc())
    ).scalars().first()


def list_runs(db: Session, limit: int = 10) -> list[MiningRun]:
    return list(
        db.execute(select(MiningRun).order_by(MiningRun.created_at.desc()).limit(limit)).scalars().all()
    )


def serialize_run(run: MiningRun, with_itemsets: bool = False) -> dict:
    payload = {
        "id": str(run.id),
        "run_label": run.run_label,
        "status": run.status,
        "params": run.params,
        "frequent_itemsets": run.frequent_itemsets,
        "candidate_rules": run.candidate_rules,
        "passed_rules": run.passed_rules,
        "stable_rules": run.stable_rules,
        "basket_count": run.basket_count,
        "duration_ms": run.duration_ms,
        "summary": run.summary,
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
    if with_itemsets:
        payload["itemsets"] = run.itemsets
    return payload


def get_run(db: Session, run_id: str) -> MiningRun:
    run = db.get(MiningRun, run_id)
    if run is None:
        raise AppError(codes.NOT_FOUND, "挖掘批次不存在", f"run_id={run_id}")
    return run


def itemsets_page(db: Session, run: MiningRun, offset: int, limit: int, size: int | None) -> dict:
    itemsets = run.itemsets or []
    if size:
        itemsets = [row for row in itemsets if row["size"] == size]
    total = len(itemsets)
    names, categories = basket_service.sku_maps(db)
    page = itemsets[offset : offset + limit]
    rows = [
        {
            "items": row["items"],
            "labels": [names.get(code, code) for code in row["items"]],
            "categories": [categories.get(code, "") for code in row["items"]],
            "count": row["count"],
            "support": row["support"],
            "size": row["size"],
        }
        for row in page
    ]
    return {"total": total, "offset": offset, "limit": limit, "rows": rows}


def create_seed_run(db: Session, user: User, run_label: str, params: dict | None = None) -> tuple[MiningRun, bool]:
    """seed 专用：固定 run_label，同事务内同步跑完算法（幂等）。"""
    existing = db.execute(select(MiningRun).where(MiningRun.run_label == run_label)).scalar_one_or_none()
    if existing is not None:
        return existing, False
    run = MiningRun(
        run_label=run_label,
        params=normalize_params(params),
        status=RunStatus.RUNNING.value,
        itemsets=[],
        summary={},
        created_by=user.id,
        created_at=_now(),
    )
    db.add(run)
    db.flush()
    _execute(db, run)
    db.flush()
    return run, True
