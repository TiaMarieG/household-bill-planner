from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain import pay
from app.domain.budget import BillStatus
from app.domain.recurrence import Frequency, RecurrenceRule


def _enum_column(enum_class: type) -> Enum:
    """Store an enum as its lowercase value in a VARCHAR with a CHECK constraint."""
    return Enum(
        enum_class,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


class Bill(Base):
    """A recurring (or one-time) bill and the rule that decides its due dates."""

    __tablename__ = "bills"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("interval_count >= 1", name="interval_positive"),
        CheckConstraint("until_date IS NULL OR until_date >= anchor_date", name="until_after_anchor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    frequency: Mapped[Frequency] = mapped_column(_enum_column(Frequency))
    interval_count: Mapped[int] = mapped_column(default=1, server_default="1")
    anchor_date: Mapped[date]
    until_date: Mapped[date | None]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    occurrences: Mapped[list["BillOccurrence"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan", passive_deletes=True
    )

    def rule(self) -> RecurrenceRule:
        """Build the domain recurrence rule from this bill's stored schedule."""
        return RecurrenceRule(self.frequency, self.anchor_date, self.interval_count, self.until_date)


class BillOccurrence(Base):
    """Status (and optional one-off amount) for a single due date of a bill.

    Rows exist only for due dates that differ from the default of unpaid at the bill's
    normal amount; every other due date is generated from the bill's recurrence rule.
    """

    __tablename__ = "bill_occurrences"
    __table_args__ = (
        UniqueConstraint("bill_id", "due_date", name="uq_bill_occurrences_bill_id_due_date"),
        CheckConstraint(
            "amount_override IS NULL OR amount_override > 0", name="amount_override_positive"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"))
    due_date: Mapped[date]
    status: Mapped[BillStatus] = mapped_column(
        _enum_column(BillStatus), default=BillStatus.UNPAID, server_default=BillStatus.UNPAID.value
    )
    amount_override: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bill: Mapped[Bill] = relationship(back_populates="occurrences")


class HouseholdSettings(Base):
    """The single row of household-wide settings: the payday cycle that defines budget weeks."""

    __tablename__ = "household_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("budget_weeks_per_period >= 1", name="weeks_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, default=1)
    budget_anchor_payday: Mapped[date]
    budget_weeks_per_period: Mapped[int] = mapped_column(default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def schedule(self) -> pay.PaySchedule:
        """The payday cycle used to split time into payday-to-payday budget windows."""
        return pay.PaySchedule(
            anchor_payday=self.budget_anchor_payday, weeks_per_period=self.budget_weeks_per_period
        )


class Earner(Base):
    """One person's pay settings and pay schedule."""

    __tablename__ = "earners"
    __table_args__ = (
        CheckConstraint(
            "withholding_percent >= 0 AND withholding_percent < 100", name="withholding_range"
        ),
        CheckConstraint(
            "(pay_type = 'hourly' AND COALESCE(hourly_rate, 0) > 0)"
            " OR (pay_type = 'salary' AND COALESCE(annual_salary, 0) > 0)",
            name="pay_matches_type",
        ),
        CheckConstraint(
            "default_weekly_hours >= 0 AND default_weekly_hours <= 168", name="default_hours_range"
        ),
        CheckConstraint("overtime_threshold_hours > 0", name="overtime_threshold_positive"),
        CheckConstraint("overtime_multiplier >= 1", name="overtime_multiplier_min"),
        CheckConstraint("weeks_per_period >= 1", name="weeks_positive"),
        CheckConstraint("days_from_period_end_to_payday >= 0", name="payday_lag_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    pay_type: Mapped[pay.PayType] = mapped_column(_enum_column(pay.PayType))
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    annual_salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    withholding_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    default_weekly_hours: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("40"), server_default="40"
    )
    overtime_threshold_hours: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("40"), server_default="40"
    )
    overtime_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("1.5"), server_default="1.5"
    )
    anchor_payday: Mapped[date]
    weeks_per_period: Mapped[int] = mapped_column(default=1, server_default="1")
    days_from_period_end_to_payday: Mapped[int] = mapped_column(default=6, server_default="6")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    work_weeks: Mapped[list["WorkWeek"]] = relationship(
        back_populates="earner", cascade="all, delete-orphan", passive_deletes=True
    )

    def schedule(self) -> pay.PaySchedule:
        """This person's pay cycle."""
        return pay.PaySchedule(
            anchor_payday=self.anchor_payday,
            weeks_per_period=self.weeks_per_period,
            days_from_period_end_to_payday=self.days_from_period_end_to_payday,
        )

    def to_domain(self) -> pay.Earner:
        """Convert to the domain object used for pay calculations, validating it on the way."""
        return pay.Earner(
            name=self.name,
            pay_type=self.pay_type,
            schedule=self.schedule(),
            withholding_rate=self.withholding_percent / 100,
            hourly_rate=self.hourly_rate or Decimal("0"),
            annual_salary=self.annual_salary or Decimal("0"),
            overtime_threshold_hours=self.overtime_threshold_hours,
            overtime_multiplier=self.overtime_multiplier,
        )


class WorkWeek(Base):
    """Actual hours one person worked in one workweek; weeks without a row use their default hours."""

    __tablename__ = "work_weeks"
    __table_args__ = (
        UniqueConstraint("earner_id", "week_start", name="uq_work_weeks_earner_id_week_start"),
        CheckConstraint("hours >= 0 AND hours <= 168", name="hours_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    earner_id: Mapped[int] = mapped_column(ForeignKey("earners.id", ondelete="CASCADE"))
    week_start: Mapped[date]
    hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    earner: Mapped[Earner] = relationship(back_populates="work_weeks")


class BalanceSnapshot(Base):
    """A bank balance as of a given date; the most recent one is the current balance."""

    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    as_of_date: Mapped[date] = mapped_column(index=True)
    includes_same_day_pay: Mapped[bool | None]
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
