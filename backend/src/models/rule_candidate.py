"""关联规则候选（含稳定性与增量结论）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class RuleCandidate(Base, TimestampMixin):
    __tablename__ = "rule_candidates"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rule_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.mining_runs.id"), nullable=False, index=True
    )
    antecedent: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    consequent: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    support: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    lift: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    conviction: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    cooccur_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counterexample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate", index=True)
    stable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tier_high_lift: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    tier_mid_lift: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    tier_low_lift: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    ci_low: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    ci_high: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    tier_detail: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    uplift_month: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    conflict_group: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
