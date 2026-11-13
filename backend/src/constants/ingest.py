"""每日补传导入的枚举与口径常量。

三类补传记录（同一套字段，靠 record_type 区分语义）：
  supplement  正常补传：同一内容重复出现即判重复
  void        作废：撤销某张小票；若该票此前未出现，则以「作废占位」等待原票，
              原票晚到时同样不参与挖掘
  correction  更正：以「same_as_no」声明它更正哪一张有效小票；同一批内可链式更正，
              取链尾内容。晚到的更正只会影响之后的新分析，已发布建议单不动。
"""
from __future__ import annotations

from enum import Enum


class IngestRecordType(str, Enum):
    SUPPLEMENT = "supplement"
    VOID = "void"
    CORRECTION = "correction"


INGEST_RECORD_TYPE_LABELS: dict[str, str] = {
    IngestRecordType.SUPPLEMENT.value: "补传",
    IngestRecordType.VOID.value: "作废",
    IngestRecordType.CORRECTION.value: "更正",
}

# 一次导入中每张小票的处置结果（导入页五类计数 + 终态）
class IngestResult(str, Enum):
    RECEIVED = "received"      # 接收：新增一条有效小票版本
    DUPLICATE = "duplicate"    # 重复：内容与现有有效版本一致，不新增
    VOIDED = "voided"          # 作废：撤销有效小票 / 记录作废占位
    CORRECTED = "corrected"    # 更正：为已有效小票追加新版本
    REJECTED = "rejected"      # 拒绝：缺字段、负数量、未知 SKU 等

INGEST_RESULT_LABELS: dict[str, str] = {
    IngestResult.RECEIVED.value: "接收",
    IngestResult.DUPLICATE.value: "重复",
    IngestResult.VOIDED.value: "作废",
    IngestResult.CORRECTED.value: "更正",
    IngestResult.REJECTED.value: "拒绝",
}

INGEST_RESULT_ORDER: tuple[str, ...] = (
    IngestResult.RECEIVED.value,
    IngestResult.DUPLICATE.value,
    IngestResult.VOIDED.value,
    IngestResult.CORRECTED.value,
    IngestResult.REJECTED.value,
)

# 终态（参与挖掘的最终有效小票）状态
INGEST_ITEM_STATUS_LABELS: dict[str, str] = {
    "active": "有效",
    "superseded": "已被更正取代",
    "voided": "已作废",
}
