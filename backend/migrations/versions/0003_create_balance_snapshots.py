"""create balance snapshots

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the bank balance history table."""
    op.create_table('balance_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('as_of_date', sa.Date(), nullable=False),
    sa.Column('includes_same_day_pay', sa.Boolean(), nullable=True),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_balance_snapshots'))
    )
    op.create_index(op.f('ix_balance_snapshots_as_of_date'), 'balance_snapshots', ['as_of_date'], unique=False)


def downgrade() -> None:
    """Drop the bank balance history table."""
    op.drop_index(op.f('ix_balance_snapshots_as_of_date'), table_name='balance_snapshots')
    op.drop_table('balance_snapshots')
