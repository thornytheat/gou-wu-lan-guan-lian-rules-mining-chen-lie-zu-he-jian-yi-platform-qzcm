"""挖掘批次：创建 / 列表 / 轮询 / 频繁项集分页。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.mining import RunCreateRequest
from src.services import mining_service


def create_run(db: Session, user: User, payload: RunCreateRequest, trace_id: str = "") -> dict:
    run = mining_service.create_run(db, user, payload.model_dump(), trace_id=trace_id)
    return mining_service.serialize_run(run, with_itemsets=False)


def list_runs(db: Session, limit: int = 10) -> dict:
    runs = [mining_service.serialize_run(run) for run in mining_service.list_runs(db, limit=limit)]
    return {"runs": runs, "count": len(runs)}


def get_run(db: Session, run_id: str, with_itemsets: bool = False) -> dict:
    run = mining_service.get_run(db, run_id)
    return mining_service.serialize_run(run, with_itemsets=with_itemsets)


def itemsets(db: Session, run_id: str, offset: int = 0, limit: int = 50, size: int | None = None) -> dict:
    run = mining_service.get_run(db, run_id)
    return mining_service.itemsets_page(db, run, offset=offset, limit=limit, size=size)
