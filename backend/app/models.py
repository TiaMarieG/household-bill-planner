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
