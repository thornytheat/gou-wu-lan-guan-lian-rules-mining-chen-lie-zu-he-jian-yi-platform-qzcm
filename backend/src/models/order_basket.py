"""小票与明细行（一行一版本；lines 里是明细行 JSON 数组）。

补传是「版本化入库」：同一 basket_no 可以有多个版本行，
  version      该小票的内容版本号（1 起，更正 +1）
  status       active（最终有效）/ superseded（被同票的更新版本取代）/ voided（作废）
  superseded_by 指向取代它的版本；voided_by 指向让此版本失效的作废记录
挖掘、概览、反例一律只读 active 行，因此重复补传不新增、作废不参与、晚到更正只影响新分析。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class OrderBasket(Base, TimestampMixin):
    __tablename__ = "order_baskets"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    # 业务键：同一张小票的全部版本共用（不再唯一）
    basket_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    store_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    store_name: Mapped[str] = mapped_column(String(80), nullable=False)
    store_tier: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    basket_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    lines: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 版本化字段
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    source_batch: Mapped[str] = mapped_column(String(48), nullable=False, default="", index=True)
    # 指向取代 / 作废它的补传记录（台账 record_id），不是 UUID 外键：版本可回放核对
    superseded_by: Mapped[str] = mapped_column(String(48), nullable=False, default="")
    voided_by: Mapped[str] = mapped_column(String(48), nullable=False, default="")
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
