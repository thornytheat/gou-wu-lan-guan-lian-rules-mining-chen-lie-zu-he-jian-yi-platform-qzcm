"""初始表结构（演示环境实际由 scripts/bootstrap_db.py 建表）。

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "basketrule"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(200), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_table(
        "skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(24), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False, server_default="件"),
        sa.Column("shelf_hint", sa.String(80), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_table(
        "order_baskets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("basket_no", sa.String(40), nullable=False),
        sa.Column("store_code", sa.String(16), nullable=False),
        sa.Column("store_name", sa.String(80), nullable=False),
        sa.Column("store_tier", sa.String(12), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("basket_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("net_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("lines", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("source_batch", sa.String(48), nullable=False, server_default=""),
        sa.Column("superseded_by", sa.String(48), nullable=False, server_default=""),
        sa.Column("voided_by", sa.String(48), nullable=False, server_default=""),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("ix_basket_tier", "order_baskets", ["store_tier"], schema=SCHEMA)
    op.create_index("ix_basket_status", "order_baskets", ["status"], schema=SCHEMA)
    op.create_index("ix_basket_no", "order_baskets", ["basket_no"], schema=SCHEMA)
    op.create_table(
        "basket_ingest_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_no", sa.String(48), nullable=False, unique=True),
        sa.Column("source", sa.String(40), nullable=False, server_default="daily-upload"),
        sa.Column("file_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="applied"),
        sa.Column("received_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("voided_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("corrected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_seq", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("imported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id"), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("trace_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_table(
        "mining_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_label", sa.String(60), nullable=False, unique=True),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("frequent_itemsets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_rules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_rules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stable_rules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("basket_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("itemsets", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_table(
        "rule_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_key", sa.String(120), nullable=False, unique=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.mining_runs.id"), nullable=False),
        sa.Column("antecedent", postgresql.JSONB(), nullable=False),
        sa.Column("consequent", postgresql.JSONB(), nullable=False),
        sa.Column("support", sa.Numeric(8, 5), nullable=False),
        sa.Column("confidence", sa.Numeric(8, 5), nullable=False),
        sa.Column("lift", sa.Numeric(8, 4), nullable=False),
        sa.Column("conviction", sa.Numeric(10, 4), nullable=False),
        sa.Column("cooccur_count", sa.Integer(), nullable=False),
        sa.Column("counterexample_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tier_high_lift", sa.Numeric(8, 4), nullable=True),
        sa.Column("tier_mid_lift", sa.Numeric(8, 4), nullable=True),
        sa.Column("tier_low_lift", sa.Numeric(8, 4), nullable=True),
        sa.Column("ci_low", sa.Numeric(8, 4), nullable=True),
        sa.Column("ci_high", sa.Numeric(8, 4), nullable=True),
        sa.Column("tier_detail", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("uplift_month", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("conflict_group", sa.String(80), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_table(
        "rule_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.rule_candidates.id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.users.id"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_table(
        "planogram_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slot_key", sa.String(140), nullable=False, unique=True),
        sa.Column("plan_code", sa.String(40), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.rule_candidates.id"), nullable=False),
        sa.Column("shelf_label", sa.String(80), nullable=False),
        sa.Column("zone", sa.String(40), nullable=False),
        sa.Column("conflict_group", sa.String(80), nullable=False),
        sa.Column("position_index", sa.Integer(), nullable=False),
        sa.Column("est_uplift", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(200), nullable=False, server_default=""),
        sa.Column("actor_role", sa.String(20), nullable=False, server_default=""),
        sa.Column("entity_type", sa.String(40), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.Column("client_ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("trace_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in (
        "audit_logs",
        "basket_ingest_records",
        "planogram_slots",
        "rule_reviews",
        "rule_candidates",
        "mining_runs",
        "order_baskets",
        "skus",
        "users",
    ):
        op.drop_table(table, schema=SCHEMA)
