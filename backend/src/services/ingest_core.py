"""补传解析纯函数：按发生顺序把「补传 / 作废 / 更正」折成每张小票的唯一有效版本。

不 import Session / 模型 / 数据库，输入输出都是 dict / str，便于单元测试。

口径（与 ingest_service 完全一致）：

  1. 发生顺序 = (occurred_at, source_seq, 到达序号)。**不看文件上传先后**：
     同一批里后上传的旧发生时间记录会排在前面，因此「晚到」不会偷改历史。
  2. 同票同内容 → DUPLICATE，不新增版本（重复补传不新增）。
  3. 同票不同内容、且不是更正记录 → REJECTED：旧内容不能被直接覆盖，
     必须显式作废或更正才能改变一张已有效的小票。
  4. 更正记录以 same_as_no 指向目标小票的**原始票号**（可链式），取链尾；
     链上被取代的版本全部 superseded。晚到更正只在本批生效，已发布建议单不回溯。
  5. 作废优先于同票的补传版本：
       作废先到、原票后到 → 原票 VOIDED（不参与挖掘）；
       原票先到、作废后到 → 原票 VOIDED；
       作废后无人再补传 → 该票没有有效版本（不参与挖掘）。
  6. 缺字段 / 未知 SKU / 数量非正 / 金额为负 / 自相矛盾（作废带明细、更正无目标、
     更正与目标门店或时间不一致）→ REJECTED，且不改变任何已有状态。

结果返回每张票的版本链 + 终态，供导入页核对；`initial_versions` 是库中已生效的版本，
本批记录只在其上继续演进。
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.constants.ingest import INGEST_RESULT_LABELS, IngestRecordType, IngestResult


@dataclass
class Resolution:
    summaries: list[dict]
    versions: list[Version]
    counts: dict[str, int]
    event_seq: dict[str, int]

    @property
    def final_versions(self) -> list[Version]:
        return [version for version in self.versions if version.status == "active"]

    @property
    def final_basket_count(self) -> int:
        return len({version.basket_no for version in self.final_versions})


@dataclass
class NormalizedRecord:
    record_id: str
    record_type: str
    basket_no: str
    occurred_at: datetime
    source_seq: int
    arrive_seq: int
    store_code: str = ""
    store_name: str = ""
    store_tier: str = ""
    channel: str = ""
    net_amount: float = 0.0
    item_count: int = 0
    lines: list[dict] = field(default_factory=list)
    same_as_no: str = ""
    reason: str = ""

    @property
    def sort_key(self) -> tuple[datetime, int, int]:
        return (self.occurred_at, self.source_seq, self.arrive_seq)


@dataclass
class Version:
    """一张小票的一个内容版本（可能来自库中已生效行，也可能本批新增）。"""

    record_id: str
    basket_no: str
    version: int
    status: str  # active / superseded / voided
    store_code: str
    store_name: str
    store_tier: str
    channel: str
    basket_ts: datetime
    net_amount: float
    item_count: int
    lines: list[dict]
    content_hash: str
    source_batch: str = ""
    superseded_by: str = ""
    voided_by: str = ""
    db_row_id: str = ""


def _clean_str(value) -> str:
    return str(value).strip() if value is not None else ""


def _parse_ts(value) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _same_instant(first: datetime, second: datetime) -> bool:
    """比较两个时间点是否相同；无时区信息按 UTC（PG timestamptz 回来一般带时区）。"""
    def aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    return aware(first) == aware(second)


def content_hash(basket_no: str, lines: list[dict]) -> str:
    """内容指纹：小票号 + 按 SKU 升序的 (sku, qty)；金额与时间不计入内容。"""
    payload = "|".join(
        f"{line['sku']}:{int(line['qty'])}" for line in sorted(lines, key=lambda item: item["sku"])
    )
    return hashlib.sha256(f"{basket_no}#{payload}".encode("utf-8")).hexdigest()


def normalize_record(raw: dict, arrive_seq: int, known_skus: set[str]) -> tuple[NormalizedRecord | None, str]:
    """字段级校验 + 归一。返回 (记录, '') 或 (None, 拒绝原因)。"""
    record_id = _clean_str(raw.get("record_id"))
    record_type = _clean_str(raw.get("record_type"))
    basket_no = _clean_str(raw.get("basket_no"))
    if not record_id:
        return None, "缺少 record_id"
    if record_type not in {item.value for item in IngestRecordType}:
        return None, f"record_type={record_type or '空'} 不合法"
    if not basket_no:
        return None, "缺少 basket_no"

    occurred_at = _parse_ts(raw.get("occurred_at"))
    if occurred_at is None:
        return None, "occurred_at 缺失或不是 ISO 时间"
    try:
        source_seq = int(raw.get("source_seq") or 0)
    except (TypeError, ValueError):
        return None, "source_seq 不是整数"

    record = NormalizedRecord(
        record_id=record_id,
        record_type=record_type,
        basket_no=basket_no,
        occurred_at=occurred_at,
        source_seq=source_seq,
        arrive_seq=arrive_seq,
        same_as_no=_clean_str(raw.get("same_as_no")),
        reason=_clean_str(raw.get("reason")),
    )

    if record_type == IngestRecordType.VOID.value:
        if raw.get("lines"):
            return None, "作废记录不应携带明细"
        return record, ""

    if record_type == IngestRecordType.CORRECTION.value and not record.same_as_no:
        return None, "更正记录缺少 same_as_no"
    if record_type == IngestRecordType.CORRECTION.value and record.same_as_no == basket_no:
        return None, "更正记录的 same_as_no 不能指向自身"
    if record_type == IngestRecordType.SUPPLEMENT.value and record.same_as_no:
        return None, "补传记录不应声明 same_as_no"

    lines_raw = raw.get("lines")
    if not isinstance(lines_raw, list) or not lines_raw:
        return None, "缺少明细行"
    lines: list[dict] = []
    seen: set[str] = set()
    for line in lines_raw:
        if not isinstance(line, dict):
            return None, "明细行不是对象"
        sku = _clean_str(line.get("sku"))
        if not sku:
            return None, "明细行缺少 sku"
        if known_skus and sku not in known_skus:
            return None, f"未知 SKU {sku}"
        if sku in seen:
            return None, f"同一小票重复 SKU {sku}"
        seen.add(sku)
        try:
            qty = int(line.get("qty"))
        except (TypeError, ValueError):
            return None, f"{sku} 数量不是整数"
        if qty <= 0:
            return None, f"{sku} 数量必须为正"
        try:
            amount = float(line.get("amount"))
        except (TypeError, ValueError):
            return None, f"{sku} 金额不是数字"
        if not math.isfinite(amount) or amount < 0:
            return None, f"{sku} 金额不能为负"
        lines.append({"sku": sku, "qty": qty, "amount": f"{round(amount, 2):.2f}"})

    store_code = _clean_str(raw.get("store_code"))
    if not store_code:
        return None, "缺少 store_code"
    record.store_code = store_code
    record.store_name = _clean_str(raw.get("store_name")) or store_code
    record.store_tier = _clean_str(raw.get("store_tier"))
    if record.store_tier not in {"high", "mid", "low"}:
        return None, f"store_tier={record.store_tier or '空'} 不合法"
    record.channel = _clean_str(raw.get("channel")) or "pos"
    record.lines = lines
    try:
        record.item_count = sum(int(line["qty"]) for line in lines)
        record.net_amount = round(sum(float(line["amount"]) for line in lines), 2)
    except ValueError:
        return None, "金额格式不合法"
    return record, ""


def resolve(
    records: list[NormalizedRecord],
    batch_no: str,
    initial_versions: list[Version] | None = None,
) -> Resolution:
    """按发生顺序折算版本链；initial_versions 是库中已生效行（到达顺序早于本批）。"""
    versions: dict[str, list[Version]] = {}
    for seeded in initial_versions or []:
        versions.setdefault(seeded.basket_no, []).append(seeded)

    summaries: list[dict] = []
    counts = {result.value: 0 for result in IngestResult}
    event_seq: dict[str, int] = {}
    conflicted: set[str] = set()
    void_marks: set[str] = set()

    def add_summary(record: NormalizedRecord, result: str, note: str, target: str = "") -> None:
        counts[result] += 1
        event_seq[record.record_id] = len(summaries) + 1
        summaries.append(
            {
                "record_id": record.record_id,
                "basket_no": record.basket_no,
                "record_type": record.record_type,
                "result": result,
                "result_label": INGEST_RESULT_LABELS[result],
                "occurred_at": record.occurred_at.isoformat(),
                "source_seq": record.source_seq,
                "note": note,
                "target": target,
            }
        )

    def latest_active(basket_no: str) -> Version | None:
        for version in reversed(versions.get(basket_no, [])):
            if version.status == "active":
                return version
        return None

    for record in sorted(records, key=lambda item: item.sort_key):
        if record.record_type == IngestRecordType.VOID.value:
            versions.setdefault(record.basket_no, [])
            void_marks.add(record.basket_no)
            current = latest_active(record.basket_no)
            if current is not None:
                current.status = "voided"
                current.voided_by = record.record_id
                add_summary(record, IngestResult.VOIDED.value, f"撤销版本 v{current.version}")
            else:
                add_summary(
                    record, IngestResult.VOIDED.value,
                    "作废已登记，等待原票（原票晚到也不参与挖掘）",
                )
            continue

        if record.record_type == IngestRecordType.CORRECTION.value:
            target_no = record.same_as_no
            if target_no == record.basket_no:
                add_summary(record, IngestResult.REJECTED.value, "更正记录的 same_as_no 不能指向自身")
                continue
            target = latest_active(target_no)
            if target is None:
                add_summary(
                    record, IngestResult.REJECTED.value,
                    f"更正目标 {record.same_as_no} 无有效小票", target_no,
                )
                continue
            if target.store_code != record.store_code or not _same_instant(target.basket_ts, record.occurred_at):
                add_summary(
                    record, IngestResult.REJECTED.value,
                    "更正记录的门店 / 发生时间与目标小票不一致", target_no,
                )
                continue
            digest = content_hash(target_no, record.lines)
            if digest == target.content_hash:
                add_summary(record, IngestResult.DUPLICATE.value, f"与 {target_no} 有效版本内容一致", target_no)
                continue
            # 同一张票的两条更正若都落在同一条已有效版本上，视为互相冲突（后者拒绝）
            if target.record_id in conflicted:
                add_summary(
                    record, IngestResult.REJECTED.value,
                    f"{target_no} 的 v{target.version} 已被同批另一条更正取代", target_no,
                )
                continue
            conflicted.add(target.record_id)
            next_version = max(version.version for version in versions[target_no]) + 1
            target.status = "superseded"
            target.superseded_by = record.record_id
            versions[target_no].append(
                Version(
                    record_id=record.record_id,
                    basket_no=target_no,
                    version=next_version,
                    status="active",
                    store_code=target.store_code,
                    store_name=target.store_name,
                    store_tier=target.store_tier,
                    channel=target.channel,
                    basket_ts=target.basket_ts,
                    net_amount=record.net_amount,
                    item_count=record.item_count,
                    lines=record.lines,
                    content_hash=digest,
                    source_batch=batch_no,
                )
            )
            add_summary(record, IngestResult.CORRECTED.value, f"取代 {target_no} 的 v{target.version}", target_no)
            continue

        # 补传：同票同内容 → 重复；不同内容 → 拒绝（不许覆盖）；无有效版本 → 新增有效版本
        versions.setdefault(record.basket_no, [])
        chain = versions[record.basket_no]
        digest = content_hash(record.basket_no, record.lines)
        current = latest_active(record.basket_no)
        if current is not None and digest == current.content_hash:
            add_summary(record, IngestResult.DUPLICATE.value, f"与 {record.basket_no} 有效版本内容一致")
            continue
        next_version = max((version.version for version in chain), default=0) + 1
        if current is not None:
            add_summary(
                record, IngestResult.REJECTED.value,
                f"{record.basket_no} 已有不同内容（v{current.version}），改变内容须走作废或更正",
            )
            continue
        anchored = record.basket_no in void_marks or any(version.status == "voided" for version in chain)
        chain.append(
            Version(
                record_id=record.record_id,
                basket_no=record.basket_no,
                version=next_version,
                status="voided" if anchored else "active",
                store_code=record.store_code,
                store_name=record.store_name,
                store_tier=record.store_tier,
                channel=record.channel,
                basket_ts=record.occurred_at,
                net_amount=record.net_amount,
                item_count=record.item_count,
                lines=record.lines,
                content_hash=digest,
                source_batch=batch_no,
                voided_by=batch_no if anchored else "",
            )
        )
        if anchored:
            add_summary(record, IngestResult.VOIDED.value, "原票晚到，但已有作废记录，不参与挖掘")
        else:
            add_summary(record, IngestResult.RECEIVED.value, f"新增有效版本 v{next_version}")

    return Resolution(
        summaries=summaries,
        versions=[version for chain in versions.values() for version in chain],
        counts=counts,
        event_seq=event_seq,
    )


def precheck(raws: list[dict], known_skus: set[str]) -> tuple[list[NormalizedRecord], list[dict]]:
    """逐条字段校验：返回 (通过归一化的记录, 被拒绝的台账行)。

    到达序号从 1 起算，等于该记录在本批反复数组里的位置（1 起），
    用于发生时间完全相同时的稳定排序。
    """
    valid: list[NormalizedRecord] = []
    rejected: list[dict] = []
    for arrive_seq, raw in enumerate(raws, start=1):
        if not isinstance(raw, dict):
            rejected.append(
                {
                    "record_id": f"#{arrive_seq}",
                    "basket_no": "",
                    "record_type": "",
                    "result": IngestResult.REJECTED.value,
                    "result_label": INGEST_RESULT_LABELS[IngestResult.REJECTED.value],
                    "occurred_at": "",
                    "source_seq": 0,
                    "note": "记录不是对象",
                    "target": "",
                }
            )
            continue
        normalized, reason = normalize_record(raw, arrive_seq, known_skus)
        if normalized is None:
            rejected.append(
                {
                    "record_id": str(raw.get("record_id") or f"#{arrive_seq}"),
                    "basket_no": str(raw.get("basket_no") or ""),
                    "record_type": str(raw.get("record_type") or ""),
                    "result": IngestResult.REJECTED.value,
                    "result_label": INGEST_RESULT_LABELS[IngestResult.REJECTED.value],
                    "occurred_at": str(raw.get("occurred_at") or ""),
                    "source_seq": raw.get("source_seq") or 0,
                    "note": reason,
                    "target": "",
                }
            )
            continue
        valid.append(normalized)
    return valid, rejected


def normalize_and_resolve(
    raws: list[dict],
    batch_no: str,
    known_skus: set[str],
    initial_versions: list[Version] | None = None,
) -> Resolution:
    """入口函数：字段校验 + 版本折算，拒绝记录合并进台账与五类计数。"""
    valid, rejected = precheck(raws, known_skus)
    resolution = resolve(valid, batch_no, initial_versions=initial_versions)
    if rejected:
        resolution.summaries.extend(rejected)
        resolution.counts[IngestResult.REJECTED.value] += len(rejected)
        base = len(resolution.summaries) - len(rejected)
        for index, summary in enumerate(rejected, start=base + 1):
            resolution.event_seq[summary["record_id"]] = index
    return resolution
