"""treasury Inc-3 — payments + allocations; payable version/status

Revision ID: 004
Revises: 003
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payables",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.drop_constraint("ck_payables_status", "payables", type_="check")
    op.create_check_constraint(
        "ck_payables_status",
        "payables",
        "status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'CANCELLED')",
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("external_reference", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="REGISTERED"),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("register_without_document", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('REGISTERED', 'CANCELLED')", name="ck_payments_status"),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
    )
    op.create_index("ix_payments_supplier_id", "payments", ["supplier_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"])

    op.create_table(
        "payment_allocation_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "payment_id", "idempotency_key", name="uq_payment_alloc_batch_idempotency"
        ),
    )
    op.create_index(
        "ix_payment_allocation_batches_payment_id", "payment_allocation_batches", ["payment_id"]
    )

    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("payable_id", sa.Integer(), sa.ForeignKey("payables.id"), nullable=False),
        sa.Column(
            "batch_id", sa.Integer(), sa.ForeignKey("payment_allocation_batches.id"), nullable=False
        ),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_by_actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_payment_allocations_amount_positive"),
    )
    op.create_index("ix_payment_allocations_payment_id", "payment_allocations", ["payment_id"])
    op.create_index("ix_payment_allocations_payable_id", "payment_allocations", ["payable_id"])
    op.create_index("ix_payment_allocations_batch_id", "payment_allocations", ["batch_id"])


def downgrade() -> None:
    op.drop_table("payment_allocations")
    op.drop_table("payment_allocation_batches")
    op.drop_table("payments")
    op.drop_constraint("ck_payables_status", "payables", type_="check")
    op.create_check_constraint(
        "ck_payables_status",
        "payables",
        "status IN ('OPEN', 'CANCELLED')",
    )
    op.drop_column("payables", "version")
