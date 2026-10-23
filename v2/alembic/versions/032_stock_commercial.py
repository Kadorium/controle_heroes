"""Persistent sales price history and actor-scoped stock queries (additive)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("sales_price_lists", sa.Column("id",sa.Integer,primary_key=True),
        sa.Column("code",sa.String(64),nullable=False,unique=True),sa.Column("name",sa.String(128),nullable=False),
        sa.Column("channel",sa.String(64),nullable=False),sa.Column("currency",sa.String(3),nullable=False),sa.Column("nature",sa.String(32),nullable=False))
    op.create_table("sales_price_entries",sa.Column("id",sa.Integer,primary_key=True),
        sa.Column("list_id",sa.Integer,sa.ForeignKey("sales_price_lists.id"),nullable=False,index=True),
        sa.Column("product_id",sa.Integer,sa.ForeignKey("products.id"),nullable=False,index=True),
        sa.Column("unit",sa.String(16),nullable=False),sa.Column("amount",sa.Numeric(18,4),nullable=False),
        sa.Column("valid_from",sa.Date,nullable=False),sa.Column("valid_to",sa.Date),sa.Column("request_key",sa.String(128),nullable=False),
        sa.Column("actor_id",sa.String(64),nullable=False),sa.Column("reason",sa.String(512),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.UniqueConstraint("request_key",name="uq_sales_price_request"),sa.CheckConstraint("amount > 0",name="ck_sales_price_positive"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from",name="ck_sales_price_dates"))
    op.create_table("reporting_stock_views",sa.Column("id",sa.Integer,primary_key=True),sa.Column("actor_id",sa.String(64),nullable=False,index=True),
        sa.Column("name",sa.String(128),nullable=False),sa.Column("config",JSONB,nullable=False),sa.Column("is_default",sa.Boolean,nullable=False),
        sa.Column("version",sa.Integer,nullable=False),sa.Column("schema_version",sa.Integer,nullable=False),sa.UniqueConstraint("actor_id","name",name="uq_stock_view_actor_name"))
    op.create_index("uq_stock_view_default","reporting_stock_views",["actor_id"],unique=True,postgresql_where=sa.text("is_default"))

def downgrade():
    op.drop_table("reporting_stock_views")
    op.drop_table("sales_price_entries")
    op.drop_table("sales_price_lists")
