"""Actor-bound idempotency for operational receiving."""
from alembic import op
import sqlalchemy as sa
revision='034'
down_revision='033'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('inventory_receipt_operations',
        sa.Column('id',sa.Integer,primary_key=True),
        sa.Column('request_key',sa.String(128),nullable=False,unique=True),
        sa.Column('actor_id',sa.String(64),nullable=False),
        sa.Column('payload_hash',sa.String(64),nullable=False),
        sa.Column('receipt_id',sa.Integer,sa.ForeignKey('goods_receipts.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table('inventory_receipt_operations')
