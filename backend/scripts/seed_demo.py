"""幂等演示数据入口：`python -m scripts.seed_demo`（SEED_DEMO=true 启动自动跑一次）。

自然键：
  User.email / Sku.code / OrderBasket.basket_no / MiningRun.run_label
  / RuleCandidate.rule_key（= run_label + 规则键）/ PlanogramSlot.slot_key

每次结束打印一行（键名与顺序为批次契约，逐字一致）：
  SEED_SUMMARY brand=basketrule skus=40 baskets=3000 rules=6 slots=1 users=3
重复执行只打印 SEED_SKIPPED，末尾 SEED_SUMMARY 行不变。
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from src.config.database import session_scope
from src.constants.enums import SlotStatus
from src.models.mining_run import MiningRun
from src.models.order_basket import OrderBasket
from src.models.planogram_slot import PlanogramSlot
from src.models.rule_candidate import RuleCandidate
from src.models.sku import Sku
from src.models.user import User
from src.services import fixtures_loader, ingest_core, mining_service
from src.utils.password import hash_password
from scripts import fixtures, fixtures_baskets

CREATED = 0
SKIPPED = 0


def _log(kind: str, entity: str, key: str) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def _created(entity: str, key: str) -> None:
    _log("SEED_CREATED", entity, key)


def _skipped(entity: str, key: str) -> None:
    _log("SEED_SKIPPED", entity, key)


def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role in fixtures.DEMO_USERS:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(fixtures.DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                is_active=True,
            )
            db.add(user)
            db.flush()
            _created("User", email)
        else:
            _skipped("User", email)
        users[role] = user
    return users


def seed_skus(db) -> None:
    for spec in fixtures.DEMO_SKUS:
        row = db.execute(select(Sku).where(Sku.code == spec["code"])).scalar_one_or_none()
        if row is None:
            db.add(
                Sku(
                    code=spec["code"],
                    name=spec["name"],
                    category=spec["category"],
                    price=Decimal(spec["price"]),
                    unit=spec["unit"],
                    shelf_hint=spec["shelf_hint"],
                )
            )
            _created("Sku", spec["code"])
        else:
            _skipped("Sku", spec["code"])
    db.flush()


def seed_baskets(db) -> int:
    existing = db.execute(select(func.count(OrderBasket.basket_no.distinct()))).scalar_one()
    if existing:
        _skipped("OrderBasket", f"all:{existing}")
        return existing
    baskets = fixtures_baskets.build_baskets()
    for item in baskets:
        db.add(
            OrderBasket(
                basket_no=item["basket_no"],
                store_code=item["store_code"],
                store_name=item["store_name"],
                store_tier=item["store_tier"],
                channel=item["channel"],
                basket_ts=item["basket_ts"],
                net_amount=Decimal(item["net_amount"]),
                item_count=item["item_count"],
                lines=item["lines"],
                version=1,
                status="active",
                content_hash=ingest_core.content_hash(item["basket_no"], item["lines"]),
                source_batch="SEED-BASELINE",
                imported_at=datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc),
            )
        )
    db.flush()
    _created("OrderBasket", f"all:{len(baskets)}")
    return len(baskets)


def seed_run(db, analyst: User) -> tuple[MiningRun, bool]:
    run, created = mining_service.create_seed_run(db, analyst, fixtures.SEED_RUN_LABEL)
    if created:
        _created("MiningRun", run.run_label)
    else:
        _skipped("MiningRun", run.run_label)
    rules = db.execute(select(RuleCandidate).where(RuleCandidate.run_id == run.id)).scalars().all()
    if rules:
        _skipped("RuleCandidate", f"{len(rules)} rules in {run.run_label}")
    return run, created


def seed_plan(db, admin: User, run: MiningRun) -> None:
    slot_key = f"{fixtures.PLAN_CODE_SEED}-N01>N02"
    existing = db.execute(select(PlanogramSlot).where(PlanogramSlot.slot_key == slot_key)).scalar_one_or_none()
    if existing is not None:
        _skipped("PlanogramSlot", slot_key)
        return
    rule = db.execute(
        select(RuleCandidate).where(
            RuleCandidate.run_id == run.id, RuleCandidate.rule_key.like("%N01>N02")
        )
    ).scalars().first()
    if rule is None:
        _skipped("PlanogramSlot", slot_key)
        return
    meta = fixtures_loader.zone_payload("N01>N02")
    db.add(
        PlanogramSlot(
            slot_key=slot_key,
            plan_code=fixtures.PLAN_CODE_SEED,
            rule_id=rule.id,
            shelf_label=meta.get("shelf_label", "端架A 上层 · 价签位 01"),
            zone=meta.get("zone", "端架A · 冰饮堆头"),
            conflict_group=meta.get("zone_code", "A1"),
            position_index=1,
            est_uplift=rule.uplift_month,
            status=SlotStatus.PUBLISHED.value,
            note="上周（W44）店长已执行的样板位，保留作对照。",
            published_at=datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc),
        )
    )
    db.flush()
    _created("PlanogramSlot", slot_key)


def seed_all() -> dict:
    global CREATED, SKIPPED
    CREATED = 0
    SKIPPED = 0
    with session_scope() as db:
        users = seed_users(db)
        seed_skus(db)
        seed_baskets(db)
        run, _ = seed_run(db, users["analyst"])
        seed_plan(db, users["admin"], run)

        skus = db.execute(select(func.count()).select_from(Sku)).scalar_one()
        baskets = db.execute(select(func.count(OrderBasket.basket_no.distinct()))).scalar_one()
        users_count = db.execute(select(func.count()).select_from(User)).scalar_one()
        rules = db.execute(
            select(func.count()).select_from(RuleCandidate).where(RuleCandidate.run_id == run.id)
        ).scalar_one()
        slots = db.execute(
            select(func.count())
            .select_from(PlanogramSlot)
            .where(PlanogramSlot.plan_code == fixtures.PLAN_CODE_SEED)
        ).scalar_one()
        db.commit()

    print(
        f"SEED_SUMMARY brand=basketrule skus={skus} baskets={baskets} rules={rules} "
        f"slots={slots} users={users_count}",
        flush=True,
    )
    return {"created": CREATED, "skipped": SKIPPED, "skus": skus, "baskets": baskets, "rules": rules}


if __name__ == "__main__":
    seed_all()
