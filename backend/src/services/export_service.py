"""CSV 导出：陈列工单（店长执行）与规则清单。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import SLOT_STATUS_LABELS, RULE_STATUS_LABELS
from src.models.planogram_slot import PlanogramSlot
from src.models.rule_candidate import RuleCandidate
from src.models.user import User
from src.services import basket_service, mining_service


def _write(rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue()


def planogram_csv(db: Session, plan_code: str) -> tuple[str, str]:
    slots = list(
        db.execute(
            select(PlanogramSlot)
            .where(PlanogramSlot.plan_code == plan_code)
            .order_by(PlanogramSlot.position_index)
        ).scalars()
    )
    names, _ = basket_service.sku_maps(db)
    rules = {
        row.id: row
        for row in db.execute(
            select(RuleCandidate).where(RuleCandidate.id.in_({slot.rule_id for slot in slots}))
        ).scalars()
    }
    run = None
    if rules:
        run = mining_service.get_run(db, str(next(iter(rules.values())).run_id))
    snapshot_label = f"{run.run_label} · active 有效版本" if run is not None else ""
    adopted = [slot for slot in slots if rules.get(slot.rule_id) and rules[slot.rule_id].status == "adopted"]
    exported = adopted or slots
    rows: list[list[str]] = [
        [
            "序号",
            "建议单号",
            "货架位",
            "货架分区",
            "组合规则",
            "前项商品",
            "后项商品",
            "提升度",
            "置信度",
            "共现小票数",
            "预估月增量(元)",
            "状态",
            "小票版本口径",
            "生成时间",
        ]
    ]
    for slot in exported:
        rule = rules.get(slot.rule_id)
        ante = " + ".join(names.get(code, code) for code in (rule.antecedent if rule else []))
        cons = " + ".join(names.get(code, code) for code in (rule.consequent if rule else []))
        rows.append(
            [
                str(slot.position_index),
                slot.plan_code,
                slot.shelf_label,
                slot.zone,
                f"{ante} → {cons}" if rule else "",
                ante,
                cons,
                f"{float(rule.lift):.2f}" if rule else "",
                f"{float(rule.confidence):.3f}" if rule else "",
                str(rule.cooccur_count) if rule else "",
                f"{float(slot.est_uplift):.2f}",
                SLOT_STATUS_LABELS.get(slot.status, slot.status),
                snapshot_label,
                (slot.created_at or datetime.now()).strftime("%Y-%m-%d %H:%M"),
            ]
        )
    return f"basketrule-workorder-{plan_code}.csv", _write(rows)


def rules_csv(db: Session, run_id: str | None) -> tuple[str, str]:
    run = mining_service.get_run(db, run_id) if run_id else mining_service.latest_run(db)
    names, _ = basket_service.sku_maps(db)
    rows: list[list[str]] = [
        [
            "规则键",
            "前项",
            "后项",
            "支持度",
            "置信度",
            "提升度",
            "conviction",
            "共现小票数",
            "CI下界",
            "CI上界",
            "三层lift",
            "稳定性",
            "状态",
            "预估月增量(元)",
            "冲突组",
        ]
    ]
    if run is not None:
        rules = list(
            db.execute(
                select(RuleCandidate)
                .where(RuleCandidate.run_id == run.id)
                .order_by(RuleCandidate.uplift_month.desc())
            ).scalars()
        )
        for rule in rules:
            rows.append(
                [
                    rule.rule_key,
                    " + ".join(names.get(code, code) for code in rule.antecedent),
                    " + ".join(names.get(code, code) for code in rule.consequent),
                    f"{float(rule.support):.4f}",
                    f"{float(rule.confidence):.4f}",
                    f"{float(rule.lift):.3f}",
                    f"{float(rule.conviction):.2f}",
                    str(rule.cooccur_count),
                    f"{float(rule.ci_low):.3f}" if rule.ci_low is not None else "",
                    f"{float(rule.ci_high):.3f}" if rule.ci_high is not None else "",
                    f"{float(rule.tier_high_lift or 0):.2f} / {float(rule.tier_mid_lift or 0):.2f} / "
                    f"{float(rule.tier_low_lift or 0):.2f}",
                    "稳定" if rule.stable else "观察",
                    RULE_STATUS_LABELS.get(rule.status, rule.status),
                    f"{float(rule.uplift_month):.2f}",
                    rule.conflict_group,
                ]
            )
    label = run.run_label if run else "no-run"
    return f"basketrule-rules-{label}.csv", _write(rows)
