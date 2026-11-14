"""Initial relational schema, constraints and ownership indexes."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(254), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("password_hash", sa.String(300), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("notifications", sa.Boolean(), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("sessions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("csrf", sa.String(64), nullable=False), sa.Column("expires", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_table("transactions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("amount", sa.Numeric(14,2), nullable=False), sa.Column("kind", sa.String(10), nullable=False), sa.Column("category", sa.String(40), nullable=False), sa.Column("date", sa.Date(), nullable=False), sa.Column("notes", sa.String(500), nullable=False), sa.CheckConstraint("amount > 0"), sa.CheckConstraint("kind IN ('income', 'expense')"))
    op.create_index("ix_tx_user_date", "transactions", ["user_id", "date"])
    op.create_table("budgets", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("month", sa.String(7), nullable=False), sa.Column("category", sa.String(40), nullable=False), sa.Column("amount", sa.Numeric(14,2), nullable=False), sa.UniqueConstraint("user_id", "month", "category"), sa.CheckConstraint("amount > 0"))
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])
    op.create_table("subscriptions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("amount", sa.Numeric(14,2), nullable=False), sa.Column("cycle", sa.String(10), nullable=False), sa.Column("next_due", sa.Date(), nullable=False), sa.Column("category", sa.String(40), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.CheckConstraint("amount > 0"), sa.CheckConstraint("cycle IN ('monthly', 'yearly')"))
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])


def downgrade():
    for table in ["subscriptions", "budgets", "transactions", "sessions", "users"]:
        op.drop_table(table)
