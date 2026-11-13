"""陈列建议位（货架位 + 组合 + 预估增量 + 冲突组）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class PlanogramSlot(Base, TimestampMixin):
    __tablename__ = "planogram_slots"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    slot_key: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.rule_candidates.id"), nullable=False
    )
    shelf_label: Mapped[str] = mapped_column(String(80), nullable=False)
    zone: Mapped[str] = mapped_column(String(40), nullable=False)
    conflict_group: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    position_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    est_uplift: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
