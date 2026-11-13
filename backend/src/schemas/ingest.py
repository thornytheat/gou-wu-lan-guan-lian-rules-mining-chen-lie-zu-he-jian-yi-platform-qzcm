"""补传导入请求 / 响应模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IngestRecordIn(BaseModel):
    record_id: str = Field(min_length=1, max_length=48)
    record_type: Literal["supplement", "void", "correction"]
    basket_no: str = Field(min_length=1, max_length=40)
    occurred_at: str = Field(min_length=10, max_length=40)
    source_seq: int = Field(default=0, ge=0)
    same_as_no: str | None = Field(default=None, max_length=40)
    reason: str = Field(default="", max_length=200)
    store_code: str | None = Field(default=None, max_length=16)
    store_name: str | None = Field(default=None, max_length=80)
    store_tier: Literal["high", "mid", "low"] | None = None
    channel: str | None = Field(default=None, max_length=20)
    lines: list[dict] | None = None


class ImportRequest(BaseModel):
    batch_no: str = Field(min_length=1, max_length=48)
    file_name: str = Field(default="", max_length=200)
    source: str = Field(default="daily-upload", max_length=40)
    note: str = Field(default="", max_length=400)
    records: list[IngestRecordIn] = Field(min_length=1, max_length=4000)


class DemoImportRequest(BaseModel):
    note: str = Field(default="", max_length=400)


class IngestDetailRow(BaseModel):
    record_id: str
    basket_no: str
    record_type: str
    result: str
    result_label: str
    occurred_at: str
    source_seq: int
    note: str
    target: str


class IngestBatchOut(BaseModel):
    batch_no: str
    source: str
    file_name: str
    status: str
    counts: dict[str, int]
    count_labels: dict[str, str]
    records: list[IngestDetailRow]
    note: str
    imported_at: str | None = None
    trace_id: str = ""


class IngestFinalBasket(BaseModel):
    basket_no: str
    version: int
    store_code: str
    store_name: str
    store_tier: str
    basket_ts: str | None = None
    net_amount: float
    item_count: int
    lines: list[dict]
    source_batch: str
    imported_at: str | None = None
    content_hash: str


class IngestSummaryOut(BaseModel):
    latest: IngestBatchOut | None = None
    last_counts: dict[str, int]
    totals: dict[str, int]
    batches: list[dict]
    final_baskets: list[IngestFinalBasket] = []
