"""Audited price replacements, closures and idempotent CSV confirmations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='033'
down_revision='032'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('sales_price_entries',sa.Column('cancelled',sa.Boolean,nullable=False,server_default=sa.false()))
    op.create_table('sales_price_operations',sa.Column('id',sa.Integer,primary_key=True),
        sa.Column('request_key',sa.String(128),nullable=False,unique=True),sa.Column('actor_id',sa.String(64),nullable=False),
        sa.Column('payload_hash',sa.String(64),nullable=False),sa.Column('result',JSONB,nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
def downgrade():
    op.drop_table('sales_price_operations')
    op.drop_column('sales_price_entries','cancelled')
