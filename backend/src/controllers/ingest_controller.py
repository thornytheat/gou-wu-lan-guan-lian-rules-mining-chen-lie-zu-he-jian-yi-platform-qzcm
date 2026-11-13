"""补传导入：概览 / 提交批次 / 回放批次 / 演示批次。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.ingest import DemoImportRequest, ImportRequest
from src.services import ingest_service


def summary(db: Session) -> dict:
    return ingest_service.import_summary(db)


def import_batch(db: Session, user: User, payload: ImportRequest, trace_id: str = "") -> dict:
    record = ingest_service.apply_import(
        db,
        user,
        batch_no=payload.batch_no,
        records=[item.model_dump() for item in payload.records],
        file_name=payload.file_name,
        source=payload.source,
        note=payload.note,
        trace_id=trace_id,
    )
    return ingest_service.import_summary(db, record)


def import_demo(db: Session, user: User, payload: DemoImportRequest, trace_id: str = "") -> dict:
    record = ingest_service.import_demo(db, user, trace_id=trace_id)
    return ingest_service.import_summary(db, record)


def replay(db: Session, batch_no: str) -> dict:
    record = ingest_service.replay_batch(db, batch_no)
    return record
