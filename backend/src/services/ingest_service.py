"""补传入库编排：解析 → 按发生顺序折算版本 → 落库 → 台账 + 审计。

调用方：导入页（/ingest）与 worker/兜底路径共用 apply_import。
幂等：同一 batch_no 重复提交直接回放上次结果，不会二次改动小票版本。
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.ingest import INGEST_RESULT_LABELS, INGEST_RESULT_ORDER, IngestResult
from src.constants.log_templates import ACTION_BASKET_IMPORT
from src.models.basket_ingest_record import BasketIngestRecord
from src.models.order_basket import OrderBasket
from src.models.sku import Sku
from src.models.user import User
from src.services import audit_service, ingest_core
from src.utils.errors import AppError
from src.utils.logger import get_logger

logger = get_logger("basketrule.ingest")

MAX_RECORDS_PER_BATCH = 4000
MAX_BATCHES_PER_DAY_PER_USER = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_counts() -> dict[str, int]:
    return {result: 0 for result in INGEST_RESULT_ORDER}


def _record_counts(record: BasketIngestRecord) -> dict[str, int]:
    return {
        IngestResult.RECEIVED.value: record.received_count,
        IngestResult.DUPLICATE.value: record.duplicate_count,
        IngestResult.VOIDED.value: record.voided_count,
        IngestResult.CORRECTED.value: record.corrected_count,
        IngestResult.REJECTED.value: record.rejected_count,
    }


def _serialize_batch(record: BasketIngestRecord) -> dict:
    """批次字段（不含台账明细之外的内容）；供 latest / 回放 / 台账共用。"""
    return {
        "batch_no": record.batch_no,
        "source": record.source,
        "file_name": record.file_name,
        "status": record.status,
        "counts": _record_counts(record),
        "count_labels": INGEST_RESULT_LABELS,
        "records": record.detail or [],
        "note": record.note,
        "imported_at": record.imported_at.isoformat() if record.imported_at else None,
        "trace_id": record.trace_id,
    }


def _serialize_record(record: BasketIngestRecord | None, latest_versions: list[dict] | None = None) -> dict:
    if record is None:
        return {"latest": None, "final_baskets": latest_versions or []}
    payload = _serialize_batch(record)
    payload["latest"] = _serialize_batch(record)
    if latest_versions is not None:
        payload["final_baskets"] = latest_versions
    return payload


def _final_versions(db: Session, limit: int = 200) -> list[dict]:
    """供导入页核对的「最终有效小票」列表（只含 active 版本，按最近入库优先）。"""
    rows = list(
        db.execute(
            select(OrderBasket)
            .where(OrderBasket.status == "active")
            .order_by(OrderBasket.imported_at.desc().nullslast(), OrderBasket.basket_ts.desc())
            .limit(limit)
        ).scalars()
    )
    return [
        {
            "basket_no": row.basket_no,
            "version": row.version,
            "store_code": row.store_code,
            "store_name": row.store_name,
            "store_tier": row.store_tier,
            "basket_ts": row.basket_ts.isoformat() if row.basket_ts else None,
            "net_amount": float(row.net_amount),
            "item_count": row.item_count,
            "lines": row.lines,
            "source_batch": row.source_batch,
            "imported_at": row.imported_at.isoformat() if row.imported_at else None,
            "content_hash": row.content_hash,
        }
        for row in rows
    ]


def latest_record(db: Session) -> BasketIngestRecord | None:
    return db.execute(
        select(BasketIngestRecord).order_by(BasketIngestRecord.imported_at.desc()).limit(1)
    ).scalars().first()


def import_summary(db: Session, record: BasketIngestRecord | None = None) -> dict:
    """导入页概览：最近一次导入的五类计数 + 累计有效版本 + 每日台账。"""
    record = record if record is not None else latest_record(db)
    active_count = db.execute(
        select(OrderBasket.basket_no).where(OrderBasket.status == "active").distinct()
    ).scalars().all()

    def counted(status: str) -> int:
        return len(
            set(
                db.execute(
                    select(OrderBasket.basket_no).where(OrderBasket.status == status)
                ).scalars().all()
            )
        )

    final_versions = _final_versions(db)
    batches = list(
        db.execute(
            select(BasketIngestRecord).order_by(BasketIngestRecord.imported_at.desc()).limit(12)
        ).scalars()
    )
    payload = _serialize_record(record, latest_versions=final_versions)
    payload.update(
        {
            "last_counts": _record_counts(record) if record is not None else _empty_counts(),
            "active_baskets": len(active_count),
            "totals": {
                "final_baskets": counted("active"),
                "baskets_voided": counted("voided"),
                "baskets_with_corrections": counted("superseded"),
                "supplement_versions": len(
                    db.execute(
                        select(OrderBasket.id).where(
                            OrderBasket.source_batch.notin_(["", "SEED-BASELINE"])
                        )
                    ).all()
                ),
                "ledger_batches": len(batches),
            },
            "batches": [
                {
                    "batch_no": batch.batch_no,
                    "file_name": batch.file_name,
                    "source": batch.source,
                    "imported_at": batch.imported_at.isoformat() if batch.imported_at else None,
                    "counts": _record_counts(batch),
                    "counts_total": sum(_record_counts(batch).values()),
                }
                for batch in batches
            ],
        }
    )
    return payload


def replay_batch(db: Session, batch_no: str) -> dict:
    record = db.execute(
        select(BasketIngestRecord).where(BasketIngestRecord.batch_no == batch_no)
    ).scalar_one_or_none()
    if record is None:
        raise AppError(codes.NOT_FOUND, "导入批次不存在", f"batch_no={batch_no}")
    return _serialize_record(record)


def _load_initial_versions(db: Session, basket_nos: set[str]) -> list[ingest_core.Version]:
    """把涉及的小票现有版本读成纯数据，交给 ingest_core.resolve 演进。"""
    if not basket_nos:
        return []
    rows = list(
        db.execute(
            select(OrderBasket)
            .where(OrderBasket.basket_no.in_(basket_nos))
            .order_by(OrderBasket.version)
        ).scalars()
    )
    return [
        ingest_core.Version(
            record_id=f"{row.source_batch or 'SEED'}:{row.basket_no}:v{row.version}",
            basket_no=row.basket_no,
            version=row.version,
            status=row.status,
            store_code=row.store_code,
            store_name=row.store_name,
            store_tier=row.store_tier,
            channel=row.channel,
            basket_ts=row.basket_ts,
            net_amount=float(row.net_amount),
            item_count=row.item_count,
            lines=list(row.lines),
            content_hash=row.content_hash,
            source_batch=row.source_batch,
            superseded_by=row.superseded_by,
            voided_by=row.voided_by,
            db_row_id=str(row.id),
        )
        for row in rows
    ]


def apply_import(
    db: Session,
    user: User,
    batch_no: str,
    records: list[dict],
    file_name: str = "",
    source: str = "daily-upload",
    note: str = "",
    trace_id: str = "",
) -> BasketIngestRecord:
    """把一批补传记录折算成版本并落库；重复 batch_no 直接回放。"""
    batch_no = (batch_no or "").strip()
    if not batch_no:
        raise AppError(codes.VALIDATION_ERROR, "缺少导入批次号 batch_no", "batch_no empty")
    if len(batch_no) > 48:
        raise AppError(codes.VALIDATION_ERROR, "批次号过长（≤48 字符）", f"len={len(batch_no)}")
    if not records:
        raise AppError(codes.VALIDATION_ERROR, "导入记录为空", "records empty")
    if len(records) > MAX_RECORDS_PER_BATCH:
        raise AppError(
            codes.VALIDATION_ERROR,
            f"单次导入最多 {MAX_RECORDS_PER_BATCH} 条记录",
            f"records={len(records)}",
        )
    if any(not isinstance(item, dict) for item in records):
        raise AppError(codes.VALIDATION_ERROR, "records 必须是对象数组", "records 类型不合法")

    existing = db.execute(
        select(BasketIngestRecord).where(BasketIngestRecord.batch_no == batch_no)
    ).scalar_one_or_none()
    if existing is not None:
        logger.info("ingest batch %s replayed", batch_no)
        return existing

    today = _now().date().isoformat()
    todays = db.execute(
        select(BasketIngestRecord.batch_no).where(
            BasketIngestRecord.imported_by == user.id,
            BasketIngestRecord.batch_no.like(f"ING-{today}%"),
        )
    ).all()
    if len(todays) >= MAX_BATCHES_PER_DAY_PER_USER:
        raise AppError(
            codes.RATE_LIMITED,
            f"每天最多导入 {MAX_BATCHES_PER_DAY_PER_USER} 批，请合并后重试",
            f"batches_today={len(todays)}",
        )

    known = set(db.execute(select(Sku.code)).scalars().all())
    started = time.perf_counter()
    touched = set()
    for raw in records:
        if isinstance(raw, dict):
            for key in ("basket_no", "same_as_no"):
                if raw.get(key):
                    touched.add(str(raw[key]).strip())
    resolution = ingest_core.normalize_and_resolve(
        records, batch_no, known, initial_versions=_load_initial_versions(db, touched)
    )

    _persist_versions(db, resolution.versions, batch_no=batch_no)

    detail = BasketIngestRecord(
        batch_no=batch_no,
        source=(source or "daily-upload")[:40],
        file_name=(file_name or "")[:200],
        status="applied",
        received_count=resolution.counts[IngestResult.RECEIVED.value],
        duplicate_count=resolution.counts[IngestResult.DUPLICATE.value],
        voided_count=resolution.counts[IngestResult.VOIDED.value],
        corrected_count=resolution.counts[IngestResult.CORRECTED.value],
        rejected_count=resolution.counts[IngestResult.REJECTED.value],
        event_seq=resolution.event_seq,
        detail=resolution.summaries,
        note=(note or "")[:400],
        imported_by=user.id,
        imported_at=_now(),
        trace_id=trace_id,
    )
    db.add(detail)
    audit_service.record(
        db,
        action=ACTION_BASKET_IMPORT,
        actor=user,
        entity_type="basket_ingest",
        entity_id=batch_no,
        detail={
            "batch_no": batch_no,
            "file_name": detail.file_name,
            "received": detail.received_count,
            "duplicate": detail.duplicate_count,
            "voided": detail.voided_count,
            "corrected": detail.corrected_count,
            "rejected": detail.rejected_count,
            "final_baskets": resolution.final_basket_count,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        },
        trace_id=trace_id,
    )
    db.commit()
    logger.info(
        "ingest %s applied: received=%s dup=%s void=%s corrected=%s rejected=%s",
        batch_no,
        detail.received_count,
        detail.duplicate_count,
        detail.voided_count,
        detail.corrected_count,
        detail.rejected_count,
    )
    return detail


def _persist_versions(db: Session, versions: list[ingest_core.Version], batch_no: str) -> None:
    """把本批新增 / 状态变化的版本写回；库中已有行只更新状态，不覆盖内容。"""
    if not versions:
        return

    touched_nos = {version.basket_no for version in versions}
    db_rows = {
        str(row.id): row
        for row in db.execute(
            select(OrderBasket).where(OrderBasket.basket_no.in_(touched_nos))
        ).scalars()
    }

    for version in versions:
        row = db_rows.get(version.db_row_id) if version.db_row_id else None
        if row is not None:
            # 已有版本：只同步状态流转（被取代 / 被作废）
            row.status = version.status
            row.superseded_by = version.superseded_by[:48]
            row.voided_by = version.voided_by[:48]
            continue
        row = OrderBasket(
            basket_no=version.basket_no,
            store_code=version.store_code,
            store_name=version.store_name,
            store_tier=version.store_tier,
            channel=version.channel,
            basket_ts=version.basket_ts,
            net_amount=version.net_amount,
            item_count=version.item_count,
            lines=version.lines,
            version=version.version,
            status=version.status,
            content_hash=version.content_hash,
            source_batch=batch_no,
            superseded_by=version.superseded_by[:48],
            voided_by=version.voided_by[:48],
            imported_at=_now(),
        )
        db.add(row)
        db.flush()
        version.db_row_id = str(row.id)
    db.flush()


def load_demo_records(db: Session) -> list[dict]:
    """导入页「填入演示补传」：一批含重复 / 作废 / 更正 / 拒绝的真实样本。"""
    rows = list(
        db.execute(
            select(OrderBasket)
            .where(OrderBasket.status == "active")
            .order_by(OrderBasket.basket_ts.desc())
            .limit(8)
        ).scalars()
    )
    if not rows:
        return []
    newest = rows[0]
    void_target = next((row for row in rows[1:] if row.basket_no != newest.basket_no), None)
    corrected_lines = [
        {"sku": line["sku"], "qty": line["qty"], "amount": float(line["amount"])}
        for line in newest.lines
    ]
    if "I01" in {line["sku"] for line in corrected_lines}:
        corrected_lines[0]["qty"] = int(corrected_lines[0]["qty"]) + 1
    else:
        corrected_lines.append({"sku": "I01", "qty": 1, "amount": 7.94})
    records: list[dict] = [
        {
            "record_id": f"DEMO-DUP-{newest.basket_no}",
            "record_type": "supplement",
            "basket_no": newest.basket_no,
            "occurred_at": newest.basket_ts.isoformat(),
            "source_seq": 1,
            "store_code": newest.store_code,
            "store_name": newest.store_name,
            "store_tier": newest.store_tier,
            "channel": newest.channel,
            "lines": [
                {"sku": line["sku"], "qty": line["qty"], "amount": float(line["amount"])}
                for line in newest.lines
            ],
        }
    ]
    if void_target is not None:
        records.append(
            {
                "record_id": f"DEMO-VOID-{void_target.basket_no}",
                "record_type": "void",
                "basket_no": void_target.basket_no,
                "occurred_at": void_target.basket_ts.isoformat(),
                "source_seq": 2,
                "reason": "收银机重复结算，整单作废",
            }
        )
    records.append(
        {
            "record_id": f"DEMO-COR-{newest.basket_no}",
            "record_type": "correction",
            "basket_no": "COR-DEMO-0001",
            "same_as_no": newest.basket_no,
            "occurred_at": newest.basket_ts.isoformat(),
            "source_seq": 3,
            "store_code": newest.store_code,
            "store_name": newest.store_name,
            "store_tier": newest.store_tier,
            "channel": newest.channel,
            "reason": "顾客补加口香糖，补录明细",
            "lines": corrected_lines,
        }
    )
    records.append(
        {
            "record_id": "DEMO-NEW-0001",
            "record_type": "supplement",
            "basket_no": f"NEW-{newest.basket_no}-A",
            "occurred_at": newest.basket_ts.isoformat(),
            "source_seq": 4,
            "store_code": newest.store_code,
            "store_name": newest.store_name,
            "store_tier": newest.store_tier,
            "channel": newest.channel,
            "lines": [
                {"sku": "I08", "qty": 1, "amount": 3.18},
                {"sku": "I01", "qty": 1, "amount": 7.94},
                {"sku": "N02", "qty": 1, "amount": 7.14},
            ],
        }
    )
    records.append(
        {
            "record_id": "DEMO-REJECT-SKU",
            "record_type": "supplement",
            "basket_no": "REJ-DEMO-0001",
            "occurred_at": _now().isoformat(),
            "source_seq": 5,
            "store_code": newest.store_code,
            "store_name": newest.store_name,
            "store_tier": newest.store_tier,
            "channel": "pos",
            "lines": [{"sku": "ZZZ999", "qty": 1, "amount": 9.9}],
        }
    )
    records.append(
        {
            "record_id": "DEMO-REJECT-QTY",
            "record_type": "supplement",
            "basket_no": "REJ-DEMO-0002",
            "occurred_at": _now().isoformat(),
            "source_seq": 6,
            "store_code": newest.store_code,
            "store_name": newest.store_name,
            "store_tier": newest.store_tier,
            "channel": "pos",
            "lines": [{"sku": "I01", "qty": -2, "amount": 7.94}],
        }
    )
    records.append(
        {
            "record_id": "DEMO-VOID-EARLY",
            "record_type": "void",
            "basket_no": "VOID-EARLY-0001",
            "occurred_at": newest.basket_ts.isoformat(),
            "source_seq": 7,
            "reason": "作废先到，原票尚未补传",
        }
    )
    return records


def import_demo(db: Session, user: User, trace_id: str = "") -> BasketIngestRecord:
    """一个按钮跑完整个演示：生成批次号 + 演示记录，走与真实导入同一条链路。

    同一账号重复点同一个秒级批次号会触发 apply_import 的幂等回放（直接返回旧台账），
    不会产生第二条记录，也不会二次改动小票版本。
    """
    stamp = _now().strftime("%Y%m%d-%H%M%S")
    batch_no = f"ING-{_now().date().isoformat()}-{stamp}"
    records = load_demo_records(db)
    if not records:
        raise AppError(codes.CONFLICT, "没有可用的有效小票，无法生成演示补传", "active baskets empty")
    return apply_import(
        db,
        user,
        batch_no=batch_no,
        records=records,
        file_name="demo-supplement-2026-11-13.json",
        source="demo",
        note="演示批次：重复 / 作废 / 更正 / 拒绝各至少一条",
        trace_id=trace_id,
    )
