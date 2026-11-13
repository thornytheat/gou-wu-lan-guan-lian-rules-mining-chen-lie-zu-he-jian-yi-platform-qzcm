"""补传解析不变量：唯一有效内容、重复不新增、作废不参与、更正只影响之后的分析。

全部纯函数测试（不连 DB）：输入是「按到达顺序的记录数组」，期望值手算。
"""
from __future__ import annotations

import pytest

from src.services.ingest_core import (
    NormalizedRecord,
    Resolution,
    Version,
    content_hash,
    normalize_and_resolve,
    normalize_record,
    resolve,
)

KNOWN = {"N01", "N02", "N03", "I01"}
T0 = "2026-10-11T12:30:00+08:00"


def line(sku: str, qty: int, amount: float) -> dict:
    return {"sku": sku, "qty": qty, "amount": amount}


def normalized_lines(lines: list[dict]) -> list[dict]:
    """归一化后的金额是两位小数字符串（与落库格式一致）。"""
    return [{**item, "amount": f"{float(item['amount']):.2f}"} for item in lines]


def record(record_id: str, record_type: str, basket_no: str, *, occurred_at: str = T0, seq: int = 1, **extra) -> dict:
    payload = {
        "record_id": record_id,
        "record_type": record_type,
        "basket_no": basket_no,
        "occurred_at": occurred_at,
        "source_seq": seq,
        "store_code": "S09",
        "store_name": "临港二店",
        "store_tier": "low",
        "channel": "pos",
    }
    payload.update(extra)
    return payload


def normalize_all(raws: list[dict]) -> list:
    out = []
    for arrive, raw in enumerate(raws, start=1):
        parsed, reason = normalize_record(raw, arrive, KNOWN)
        out.append((parsed, reason))
    return out


def run(raws: list[dict], batch_no: str = "ING-1", initial: list[Version] | None = None):
    """走与 ingest_service 相同的入口：字段校验 + 版本折算（拒绝计入台账）。"""
    result = normalize_and_resolve(raws, batch_no, KNOWN, initial_versions=initial)
    return result


BASE_LINES = [line("N01", 1, 15.72), line("N02", 1, 7.14)]
CORRECTED_LINES = [line("N01", 1, 15.72), line("N02", 2, 14.28)]


def test_duplicate_content_does_not_add_a_version() -> None:
    """同一张票重复补传：第一次接收，第二次重复；版本链只有一条。"""
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES),
            record("A2", "supplement", "BR-1", lines=BASE_LINES, seq=2),
        ]
    )
    assert result.counts == {"received": 1, "duplicate": 1, "voided": 0, "corrected": 0, "rejected": 0}
    assert [version.status for version in result.versions] == ["active"]
    assert result.final_basket_count == 1


def test_same_basket_without_correction_marker_is_rejected_not_overwritten() -> None:
    """旧内容不能被直接覆盖：不同内容的普通补传 → 拒绝，原有效版本保持。"""
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES),
            record("A2", "supplement", "BR-1", lines=CORRECTED_LINES, seq=2),
        ]
    )
    assert result.counts["rejected"] == 1
    assert [version.lines for version in result.final_versions] == [normalized_lines(BASE_LINES)]


def test_correction_supersedes_previous_version_and_keeps_history() -> None:
    """更正声明 same_as_no → 新版本生效，旧版本 superseded（历史保留）。"""
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES),
            record(
                "C1", "correction", "BR-1-COR", same_as_no="BR-1", lines=CORRECTED_LINES, seq=2,
            ),
        ]
    )
    assert result.counts["corrected"] == 1
    assert [(version.basket_no, version.version, version.status) for version in result.versions] == [
        ("BR-1", 1, "superseded"),
        ("BR-1", 2, "active"),
    ]
    final = result.final_versions[0]
    assert final.version == 2
    assert final.lines == normalized_lines(CORRECTED_LINES)
    assert final.content_hash == content_hash("BR-1", normalized_lines(CORRECTED_LINES))


def test_correction_with_identical_content_is_duplicate() -> None:
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES),
            record("C1", "correction", "BR-1-COR", same_as_no="BR-1", lines=BASE_LINES, seq=2),
        ]
    )
    assert result.counts["duplicate"] == 1
    assert [(version.version, version.status) for version in result.versions] == [(1, "active")]


def test_correction_requires_existing_target_and_matching_store_time() -> None:
    """更正目标不存在 / 门店或发生时间不一致 → 拒绝。"""
    result = run(
        [
            record("C1", "correction", "NEW-1", same_as_no="MISSING", lines=BASE_LINES, seq=1),
            record("A1", "supplement", "BR-1", lines=BASE_LINES, seq=2),
            record(
                "C2", "correction", "NEW-2", same_as_no="BR-1", lines=CORRECTED_LINES,
                store_code="S01", seq=3,
            ),
        ]
    )
    assert result.counts["rejected"] == 2
    assert [version.status for version in result.versions] == ["active"]
    assert not [version for version in result.versions if version.basket_no == "NEW-1"]


def test_void_cancels_prior_version_and_blocks_late_supplement() -> None:
    """作废既撤销已有效版本，也阻断晚到的原票（原票 VOIDED，不参与挖掘）。"""
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES),
            record("V1", "void", "BR-1", seq=2),
            record("A2", "supplement", "BR-1", lines=BASE_LINES, seq=3),
        ]
    )
    assert result.counts["received"] == 1
    assert result.counts["voided"] == 2
    assert result.final_versions == []
    assert [(version.version, version.status) for version in result.versions] == [
        (1, "voided"),
        (2, "voided"),
    ]


def test_void_registered_before_original_arrives() -> None:
    """作废先到：原票之后的补传同样不生效。"""
    result = run(
        [
            record("V1", "void", "BR-9", seq=1),
            record("A1", "supplement", "BR-9", lines=BASE_LINES, seq=2),
        ]
    )
    assert [version.status for version in result.versions] == ["voided"]
    assert result.final_basket_count == 0


def test_occurrence_order_beats_upload_order() -> None:
    """先上传的记录发生时间更晚：按发生顺序，先发生的旧内容才是有效版本。

    后上传的「新内容」没有更正声明 → 拒绝，不能用上传先后直接覆盖旧内容。
    """
    late_old = record("A1", "supplement", "BR-1", occurred_at="2026-10-05T09:00:00+08:00", lines=BASE_LINES)
    early_new = record("A2", "supplement", "BR-1", occurred_at="2026-10-06T09:00:00+08:00", lines=CORRECTED_LINES, seq=2)
    result = run([early_new, late_old])
    assert result.counts == {"received": 1, "duplicate": 0, "voided": 0, "corrected": 0, "rejected": 1}
    assert result.final_versions[0].lines == normalized_lines(BASE_LINES)
    assert result.final_versions[0].version == 1


def test_rejections_do_not_mutate_existing_versions() -> None:
    """字段不合法：未知 SKU / 数量非正 / 缺发生时间 / 作废带明细 → 全部拒绝。"""
    bad = [
        record("R1", "supplement", "BR-BAD-1", lines=[line("ZZZ", 1, 1.0)], seq=1),
        record("R2", "supplement", "BR-BAD-2", lines=[line("N01", 0, 0.0)], seq=2),
        record("R3", "supplement", "BR-BAD-3", occurred_at="不是时间", lines=BASE_LINES, seq=3),
        record("R4", "void", "BR-BAD-4", lines=BASE_LINES, seq=4),
        record("R5", "correction", "BR-BAD-5", lines=BASE_LINES, seq=5),
    ]
    result = run(
        [record("A1", "supplement", "BR-OK", lines=BASE_LINES)] + bad
    )
    assert result.counts["received"] == 1
    assert result.counts["rejected"] == 5
    assert [(version.basket_no, version.status) for version in result.versions] == [("BR-OK", "active")]


def test_chained_corrections_follow_occurrence_order() -> None:
    """同一批里针对同一张票的两条更正：按发生顺序链式演进，最后一条成为 v3。"""
    second = [line("N01", 2, 31.44), line("N02", 1, 7.14)]
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES),
            record("C1", "correction", "BR-1-C1", same_as_no="BR-1", lines=CORRECTED_LINES, seq=2),
            record("C2", "correction", "BR-1-C2", same_as_no="BR-1", lines=second, seq=3),
        ]
    )
    assert result.counts["corrected"] == 2
    assert [(version.version, version.status) for version in result.versions] == [
        (1, "superseded"),
        (2, "superseded"),
        (3, "active"),
    ]
    assert result.final_versions[0].lines == normalized_lines(second)


def test_initial_versions_are_evolved_not_recreated() -> None:
    """跨批次：库中已有有效版本参与判定（重复 / 作废 / 更正都不重复建行）。"""
    seeded = Version(
        record_id="SEED:v1",
        basket_no="BR-1",
        version=1,
        status="active",
        store_code="S09",
        store_name="临港二店",
        store_tier="low",
        channel="pos",
        basket_ts=__import__("datetime").datetime.fromisoformat(T0),
        net_amount=22.86,
        item_count=2,
        lines=normalized_lines(BASE_LINES),
        content_hash=content_hash("BR-1", normalized_lines(BASE_LINES)),
    )
    result = run(
        [
            record("A1", "supplement", "BR-1", lines=BASE_LINES, seq=1),
            record("C1", "correction", "BR-1-COR", same_as_no="BR-1", lines=CORRECTED_LINES, seq=2),
        ],
        batch_no="ING-2",
        initial=[seeded],
    )
    assert result.counts["duplicate"] == 1
    assert result.counts["corrected"] == 1
    assert seeded.status == "superseded"
    assert seeded.superseded_by == "C1"
    assert seeded.db_row_id == ""  # 纯函数不决定落库
    assert len(result.versions) == 2


def test_content_hash_ignores_amount_and_line_order() -> None:
    """内容指纹只看 (sku, qty)：金额尾差 / 行顺序不制造重复版本。"""
    reordered = [line("N02", 1, 7.20), line("N01", 1, 15.80)]
    assert content_hash("BR-1", BASE_LINES) == content_hash("BR-1", reordered)
    assert content_hash("BR-1", BASE_LINES) != content_hash("BR-1", CORRECTED_LINES)
