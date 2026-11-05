from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from app.domain.pay import PaySchedule

ZERO = Decimal("0.00")


class BillStatus(str, Enum):
    """Where a bill payment stands relative to the bank balance."""

    UNPAID = "unpaid"
    PAID_PENDING = "paid_pending"
    PAID_CLEARED = "paid_cleared"


@dataclass(frozen=True)
class BillDue:
    """A single due date of a bill, with its own payment status."""

    name: str
    due_date: date
    amount: Decimal
    status: BillStatus = BillStatus.UNPAID


@dataclass(frozen=True)
class IncomeDue:
    """An expected paycheck; deposited means it is already in the entered bank balance."""

    earner_name: str
    payday: date
    amount: Decimal
    deposited: bool = False


@dataclass(frozen=True)
class BudgetWindow:
    """A payday-to-payday span: from a payday through the day before the next one."""

    start: date
    end: date

    def contains(self, day: date) -> bool:
        """True when the date falls inside this window."""
        return self.start <= day <= self.end


@dataclass(frozen=True)
class WindowSummary:
    """Totals for one budget window, from the starting balance to what is left over."""

    window: BudgetWindow
    starting_balance: Decimal
    incoming: Decimal
    unpaid: Decimal
    pending_withdrawal: Decimal
    overdue: Decimal
    remaining: Decimal
    bills: tuple[BillDue, ...]


def budget_window_containing(schedule: PaySchedule, day: date) -> BudgetWindow:
    """The payday-to-payday window on the household schedule that includes the given date."""
    offset = (day - schedule.anchor_payday).days % schedule.period_days
    start = day - timedelta(days=offset)
    return BudgetWindow(start, start + timedelta(days=schedule.period_days - 1))


def summarize_window(
    window: BudgetWindow,
    starting_balance: Decimal,
    incomes: list[IncomeDue],
    bills: list[BillDue],
    include_overdue: bool = True,
) -> WindowSummary:
    """Totals for one window; cleared bills and deposited pay are already in the starting balance."""
    outstanding = [
        bill
        for bill in bills
        if bill.status is not BillStatus.PAID_CLEARED
        and bill.due_date <= window.end
        and (include_overdue or bill.due_date >= window.start)
    ]
    in_window = tuple(
        sorted((bill for bill in bills if window.contains(bill.due_date)), key=lambda b: b.due_date)
    )

    incoming = sum(
        (i.amount for i in incomes if window.contains(i.payday) and not i.deposited), ZERO
    )
    unpaid = sum((b.amount for b in outstanding if b.status is BillStatus.UNPAID), ZERO)
    pending = sum((b.amount for b in outstanding if b.status is BillStatus.PAID_PENDING), ZERO)
    overdue = sum((b.amount for b in outstanding if b.due_date < window.start), ZERO)

    return WindowSummary(
        window=window,
        starting_balance=starting_balance,
        incoming=incoming,
        unpaid=unpaid,
        pending_withdrawal=pending,
        overdue=overdue,
        remaining=starting_balance + incoming - unpaid - pending,
        bills=in_window,
    )


def project_windows(
    schedule: PaySchedule,
    from_day: date,
    count: int,
    starting_balance: Decimal,
    incomes: list[IncomeDue],
    bills: list[BillDue],
) -> list[WindowSummary]:
    """Chain consecutive windows, each starting with the previous window's remaining balance."""
    if count < 1:
        raise ValueError("count must be at least 1")

    summaries = []
    window = budget_window_containing(schedule, from_day)
    balance = starting_balance
    for index in range(count):
        summary = summarize_window(window, balance, incomes, bills, include_overdue=index == 0)
        summaries.append(summary)
        balance = summary.remaining
        next_start = window.end + timedelta(days=1)
        window = BudgetWindow(next_start, next_start + timedelta(days=schedule.period_days - 1))
    return summaries
