"""数据集概览（小票样本 / SKU 支持度 / 门店分层）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import basket_service


def summary(db: Session) -> dict:
    return basket_service.dataset_summary(db)
