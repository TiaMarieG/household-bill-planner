"""create household earners and hours

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create household settings, earners and weekly hours tables."""
    op.create_table('earners',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('pay_type', sa.Enum('hourly', 'salary', name='paytype', native_enum=False, create_constraint=True, length=20), nullable=False),
    sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('annual_salary', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('withholding_percent', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('default_weekly_hours', sa.Numeric(precision=5, scale=2), server_default='40', nullable=False),
    sa.Column('overtime_threshold_hours', sa.Numeric(precision=5, scale=2), server_default='40', nullable=False),
    sa.Column('overtime_multiplier', sa.Numeric(precision=4, scale=2), server_default='1.5', nullable=False),
    sa.Column('anchor_payday', sa.Date(), nullable=False),
    sa.Column('weeks_per_period', sa.Integer(), server_default='1', nullable=False),
    sa.Column('days_from_period_end_to_payday', sa.Integer(), server_default='6', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint(
        "(pay_type = 'hourly' AND COALESCE(hourly_rate, 0) > 0)"
        " OR (pay_type = 'salary' AND COALESCE(annual_salary, 0) > 0)",
        name=op.f('ck_earners_pay_matches_type'),
    ),
    sa.CheckConstraint('days_from_period_end_to_payday >= 0', name=op.f('ck_earners_payday_lag_non_negative')),
    sa.CheckConstraint('default_weekly_hours >= 0 AND default_weekly_hours <= 168', name=op.f('ck_earners_default_hours_range')),
    sa.CheckConstraint('overtime_multiplier >= 1', name=op.f('ck_earners_overtime_multiplier_min')),
    sa.CheckConstraint('overtime_threshold_hours > 0', name=op.f('ck_earners_overtime_threshold_positive')),
    sa.CheckConstraint('weeks_per_period >= 1', name=op.f('ck_earners_weeks_positive')),
    sa.CheckConstraint('withholding_percent >= 0 AND withholding_percent < 100', name=op.f('ck_earners_withholding_range')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_earners'))
    )
    op.create_table('household_settings',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('budget_anchor_payday', sa.Date(), nullable=False),
    sa.Column('budget_weeks_per_period', sa.Integer(), server_default='1', nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('budget_weeks_per_period >= 1', name=op.f('ck_household_settings_weeks_positive')),
    sa.CheckConstraint('id = 1', name=op.f('ck_household_settings_single_row')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_household_settings'))
    )
    op.create_table('work_weeks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('earner_id', sa.Integer(), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('hours', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('hours >= 0 AND hours <= 168', name=op.f('ck_work_weeks_hours_range')),
    sa.ForeignKeyConstraint(['earner_id'], ['earners.id'], name=op.f('fk_work_weeks_earner_id_earners'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_work_weeks')),
    sa.UniqueConstraint('earner_id', 'week_start', name='uq_work_weeks_earner_id_week_start')
    )


def downgrade() -> None:
    """Drop the tables in reverse dependency order."""
    op.drop_table('work_weeks')
    op.drop_table('household_settings')
    op.drop_table('earners')
