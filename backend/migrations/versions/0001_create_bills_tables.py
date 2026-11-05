"""create bills tables

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FREQUENCY = sa.Enum(
    "once", "days", "weeks", "months",
    name="frequency", native_enum=False, create_constraint=True, length=20,
)
BILL_STATUS = sa.Enum(
    "unpaid", "paid_pending", "paid_cleared",
    name="billstatus", native_enum=False, create_constraint=True, length=20,
)


def upgrade() -> None:
    """Create the bills table and the per-due-date status table."""
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("frequency", FREQUENCY, nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("anchor_date", sa.Date(), nullable=False),
        sa.Column("until_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_bills_amount_positive")),
        sa.CheckConstraint("interval_count >= 1", name=op.f("ck_bills_interval_positive")),
        sa.CheckConstraint(
            "until_date IS NULL OR until_date >= anchor_date", name=op.f("ck_bills_until_after_anchor")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bills")),
    )
    op.create_table(
        "bill_occurrences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", BILL_STATUS, server_default="unpaid", nullable=False),
        sa.Column("amount_override", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "amount_override IS NULL OR amount_override > 0",
            name=op.f("ck_bill_occurrences_amount_override_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"], ["bills.id"], name=op.f("fk_bill_occurrences_bill_id_bills"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bill_occurrences")),
        sa.UniqueConstraint("bill_id", "due_date", name="uq_bill_occurrences_bill_id_due_date"),
    )


def downgrade() -> None:
    """Drop both tables, children first."""
    op.drop_table("bill_occurrences")
    op.drop_table("bills")
