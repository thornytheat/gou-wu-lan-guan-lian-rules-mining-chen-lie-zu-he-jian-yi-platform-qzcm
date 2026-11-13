"""小票与 SKU 数据访问（算法输入 + 样本展示）。"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.limits import MAX_COUNTEREXAMPLES
from src.models.order_basket import OrderBasket
from src.models.sku import Sku


def sku_maps(db: Session) -> tuple[dict[str, str], dict[str, str]]:
    rows = db.execute(select(Sku)).scalars().all()
    return {row.code: row.name for row in rows}, {row.code: row.category for row in rows}


ACTIVE_BASKET = OrderBasket.status == "active"


def load_transactions(db: Session) -> list[tuple[frozenset[str], str]]:
    """只读最终有效版本：重复补传 / 已作废 / 被更正取代的版本不进入挖掘。"""
    rows = db.execute(
        select(OrderBasket.store_tier, OrderBasket.lines).where(ACTIVE_BASKET)
    ).all()
    out: list[tuple[frozenset[str], str]] = []
    for tier, lines in rows:
        out.append((frozenset(line["sku"] for line in lines), tier))
    return out


def dataset_summary(db: Session) -> dict:
    basket_count = db.execute(select(func.count()).select_from(OrderBasket).where(ACTIVE_BASKET)).scalar_one()
    amount_sum = db.execute(select(func.coalesce(func.sum(OrderBasket.net_amount), 0)).where(ACTIVE_BASKET)).scalar_one()
    item_sum = db.execute(select(func.coalesce(func.sum(OrderBasket.item_count), 0)).where(ACTIVE_BASKET)).scalar_one()
    sku_count = db.execute(select(func.count()).select_from(Sku)).scalar_one()
    tier_rows = db.execute(
        select(OrderBasket.store_tier, func.count())
        .where(ACTIVE_BASKET)
        .group_by(OrderBasket.store_tier)
    ).all()
    store_rows = db.execute(
        select(OrderBasket.store_code, OrderBasket.store_name, OrderBasket.store_tier, func.count())
        .where(ACTIVE_BASKET)
        .group_by(OrderBasket.store_code, OrderBasket.store_name, OrderBasket.store_tier)
        .order_by(OrderBasket.store_code)
    ).all()
    sample_rows = (
        db.execute(
            select(OrderBasket)
            .where(ACTIVE_BASKET)
            .order_by(OrderBasket.basket_ts.desc(), OrderBasket.basket_no)
            .limit(6)
        )
        .scalars()
        .all()
    )
    names, _ = sku_maps(db)
    support_rows = db.execute(select(OrderBasket.lines).where(ACTIVE_BASKET)).scalars().all()
    support: Counter[str] = Counter()
    for lines in support_rows:
        support.update({line["sku"] for line in lines})

    return {
        "baskets": basket_count,
        "skus": sku_count,
        "lines": int(item_sum),
        "avg_lines": round(item_sum / basket_count, 2) if basket_count else 0,
        "revenue": float(amount_sum),
        "mean_amount": round(float(amount_sum) / basket_count, 2) if basket_count else 0,
        "stores": len(store_rows),
        "sample_days": settings.sample_days,
        "adoption_rate": settings.adoption_rate,
        "tiers": [{"tier": tier, "baskets": count} for tier, count in tier_rows],
        "store_rows": [
            {"code": code, "name": name, "tier": tier, "baskets": count}
            for code, name, tier, count in store_rows
        ],
        "sku_support": [
            {"sku": code, "name": names.get(code, code), "baskets": count, "support": round(count / basket_count, 4)}
            for code, count in sorted(support.items(), key=lambda kv: -kv[1])
        ],
        "sample_baskets": [serialize_basket(row, names) for row in sample_rows],
    }


def serialize_basket(row: OrderBasket, names: dict[str, str]) -> dict:
    return {
        "id": str(row.id),
        "basket_no": row.basket_no,
        "store_code": row.store_code,
        "store_name": row.store_name,
        "store_tier": row.store_tier,
        "channel": row.channel,
        "basket_ts": row.basket_ts.isoformat() if row.basket_ts else None,
        "net_amount": float(row.net_amount),
        "item_count": row.item_count,
        "version": row.version,
        "status": row.status,
        "source_batch": row.source_batch,
        "lines": [
            {
                "sku": line["sku"],
                "name": names.get(line["sku"], line["sku"]),
                "qty": line["qty"],
                "amount": float(line["amount"]),
            }
            for line in row.lines
        ],
    }


def counterexample_baskets(
    db: Session, antecedent: list[str], consequent: list[str], limit: int = MAX_COUNTEREXAMPLES
) -> list[dict]:
    names, _ = sku_maps(db)
    ante = set(antecedent)
    cons = set(consequent)
    rows = (
        db.execute(
            select(OrderBasket).where(ACTIVE_BASKET).order_by(OrderBasket.basket_ts.desc()).limit(1200)
        )
        .scalars()
        .all()
    )
    out: list[dict] = []
    for row in rows:
        codes = {line["sku"] for line in row.lines}
        if ante <= codes and not cons <= codes:
            out.append(serialize_basket(row, names))
            if len(out) >= limit:
                break
    return out


def cooccurrence_matrix(db: Session, sku_limit: int = 8) -> dict:
    """Top SKU 的共现矩阵（供规则详情热力图；后端真算，前端只画）。"""
    rows = db.execute(select(OrderBasket.lines).where(ACTIVE_BASKET)).scalars().all()
    support: Counter[str] = Counter()
    for lines in rows:
        support.update({line["sku"] for line in lines})
    top = [code for code, _ in support.most_common(sku_limit)]
    index = {code: i for i, code in enumerate(top)}
    matrix = [[0] * len(top) for _ in top]
    totals = [support[code] for code in top]
    for lines in rows:
        codes = [line["sku"] for line in lines if line["sku"] in index]
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                a, b = index[codes[i]], index[codes[j]]
                matrix[a][b] += 1
                matrix[b][a] += 1
    for i, code in enumerate(top):
        matrix[i][i] = support[code]
    names, categories = sku_maps(db)
    return {
        "skus": [{"sku": code, "name": names.get(code, code), "category": categories.get(code, ""), "baskets": totals[i]} for i, code in enumerate(top)],
        "matrix": matrix,
        "baskets": len(rows),
    }
