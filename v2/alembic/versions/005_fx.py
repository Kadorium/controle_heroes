"""treasury Inc-4 — FX three views (plan/quote/execution/valuation)

Revision ID: 005
Revises: 004
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_plan_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payable_id", sa.Integer(), sa.ForeignKey("payables.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("foreign_currency", sa.String(8), nullable=False),
        sa.Column("base_currency", sa.String(8), nullable=False, server_default="BRL"),
        sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supersedes_id", sa.Integer(), sa.ForeignKey("fx_plan_rates.id"), nullable=True),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("kind IN ('INITIAL', 'REFORECAST', 'CORRECTION')", name="ck_fx_plan_kind"),
        sa.CheckConstraint("rate > 0", name="ck_fx_plan_rate_positive"),
        sa.CheckConstraint("base_currency = 'BRL'", name="ck_fx_plan_base_brl"),
        sa.UniqueConstraint("payable_id", "idempotency_key", name="uq_fx_plan_idempotency"),
    )
    op.create_index("ix_fx_plan_payable_current", "fx_plan_rates", ["payable_id", "is_current"])

    op.create_table(
        "fx_market_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("foreign_currency", sa.String(8), nullable=False),
        sa.Column("base_currency", sa.String(8), nullable=False, server_default="BRL"),
        sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("rate > 0", name="ck_fx_quote_rate_positive"),
        sa.CheckConstraint("base_currency = 'BRL'", name="ck_fx_quote_base_brl"),
    )
    op.create_index(
        "ix_fx_quote_pair_retrieved",
        "fx_market_quotes",
        ["foreign_currency", "base_currency", "retrieved_at"],
    )

    op.create_table(
        "fx_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("foreign_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("brl_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("execution_date", sa.Date(), nullable=False),
        sa.Column("external_reference", sa.String(128), nullable=True),
        sa.Column("register_without_document", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("foreign_amount > 0", name="ck_fx_exec_foreign_positive"),
        sa.CheckConstraint("brl_amount > 0", name="ck_fx_exec_brl_positive"),
        sa.CheckConstraint("rate > 0", name="ck_fx_exec_rate_positive"),
        sa.UniqueConstraint("payment_id", "idempotency_key", name="uq_fx_exec_idempotency"),
    )
    op.create_index("ix_fx_exec_payment", "fx_executions", ["payment_id"])

    op.create_table(
        "fx_execution_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fx_execution_id", sa.Integer(), sa.ForeignKey("fx_executions.id"), nullable=False),
        sa.Column(
            "payment_allocation_id",
            sa.Integer(),
            sa.ForeignKey("payment_allocations.id"),
            nullable=False,
        ),
        sa.Column("foreign_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("brl_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("foreign_amount > 0", name="ck_fx_link_foreign_positive"),
        sa.CheckConstraint("brl_amount > 0", name="ck_fx_link_brl_positive"),
    )
    op.create_index("ix_fx_link_execution", "fx_execution_allocations", ["fx_execution_id"])
    op.create_index("ix_fx_link_allocation", "fx_execution_allocations", ["payment_allocation_id"])

    op.create_table(
        "fx_allocation_valuations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "payment_allocation_id",
            sa.Integer(),
            sa.ForeignKey("payment_allocations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("planned_rate_id", sa.Integer(), sa.ForeignKey("fx_plan_rates.id"), nullable=False),
        sa.Column("planned_rate_snapshot", sa.Numeric(18, 6), nullable=False),
        sa.Column("realized_rate_snapshot", sa.Numeric(18, 6), nullable=False),
        sa.Column("foreign_amount_snapshot", sa.Numeric(18, 4), nullable=False),
        sa.Column("planned_brl", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_brl", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_result_vs_reference", sa.Numeric(18, 4), nullable=False),
        sa.Column("reference_kind", sa.String(32), nullable=False, server_default="CURRENT_AT_FREEZE"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fx_allocation_valuations")
    op.drop_table("fx_execution_allocations")
    op.drop_table("fx_executions")
    op.drop_index("ix_fx_quote_pair_retrieved", table_name="fx_market_quotes")
    op.drop_table("fx_market_quotes")
    op.drop_index("ix_fx_plan_payable_current", table_name="fx_plan_rates")
    op.drop_table("fx_plan_rates")
