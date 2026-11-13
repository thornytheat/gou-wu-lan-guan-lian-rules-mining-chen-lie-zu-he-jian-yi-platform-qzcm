"""补传导入的可核对台账（每次导入一行，明细里逐票处置结果）。

明细存 JSONB 数组（每张小票一条），保证同一批次的处置结果可回放核对；
最终有效内容落在 order_baskets 的版本行上（见 OrderBasket）。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class BasketIngestRecord(Base, TimestampMixin):
    __tablename__ = "basket_ingest_records"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    batch_no: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="daily-upload")
    file_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="applied", index=True)
    received_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    voided_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    corrected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_seq: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    detail: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    imported_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.users.id"), nullable=True
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
