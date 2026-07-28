"""treasury Inc-4 follow-up — unique current plan + link integrity aids

Revision ID: 006
Revises: 005
Create Date: 2026-07-23
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Uma FxPlanRate.is_current=true por payable (não impede histórico)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_fx_plan_one_current_per_payable
        ON fx_plan_rates (payable_id)
        WHERE is_current IS TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_fx_plan_one_current_per_payable")
