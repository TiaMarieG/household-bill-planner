from datetime import date
from decimal import Decimal

from app.domain.budget import (
    BillDue,
    BillStatus,
    BudgetWindow,
    IncomeDue,
    budget_window_containing,
    project_windows,
    summarize_window,
)
from app.domain.pay import PaySchedule

WEEKLY = PaySchedule(anchor_payday=date(2026, 11, 6))
NOV_6_WINDOW = BudgetWindow(date(2026, 11, 6), date(2026, 11, 12))


def bill(name, day, amount, status=BillStatus.UNPAID):
    return BillDue(name, date(2026, 11, day), Decimal(amount), status)


def pay(day, amount, deposited=False):
    return IncomeDue("Alex", date(2026, 11, day), Decimal(amount), deposited)


def test_window_starts_on_payday():
    assert budget_window_containing(WEEKLY, date(2026, 11, 6)) == NOV_6_WINDOW


def test_window_ends_day_before_next_payday():
    assert budget_window_containing(WEEKLY, date(2026, 11, 12)) == NOV_6_WINDOW


def test_window_before_anchor():
    assert budget_window_containing(WEEKLY, date(2026, 10, 31)) == BudgetWindow(
        date(2026, 10, 30), date(2026, 11, 5)
    )


def test_biweekly_window_is_fourteen_days():
    schedule = PaySchedule(anchor_payday=date(2026, 11, 6), weeks_per_period=2)

    assert budget_window_containing(schedule, date(2026, 11, 15)) == BudgetWindow(
        date(2026, 11, 6), date(2026, 11, 19)
    )


def test_remaining_is_balance_plus_incoming_minus_bills():
    summary = summarize_window(
        NOV_6_WINDOW,
        Decimal("500.00"),
        incomes=[pay(6, "780.00")],
        bills=[bill("Phone", 8, "65.00"), bill("Internet", 10, "80.00")],
    )

    assert summary.incoming == Decimal("780.00")
    assert summary.unpaid == Decimal("145.00")
    assert summary.remaining == Decimal("1135.00")


def test_paid_pending_still_reduces_remaining_but_cleared_does_not():
    summary = summarize_window(
        NOV_6_WINDOW,
        Decimal("1000.00"),
        incomes=[],
        bills=[
            bill("Phone", 8, "65.00", BillStatus.PAID_PENDING),
            bill("Internet", 7, "80.00", BillStatus.PAID_CLEARED),
        ],
    )

    assert summary.pending_withdrawal == Decimal("65.00")
    assert summary.unpaid == Decimal("0")
    assert summary.remaining == Decimal("935.00")


def test_cleared_bill_still_listed_for_the_window():
    summary = summarize_window(
        NOV_6_WINDOW,
        Decimal("0"),
        incomes=[],
        bills=[bill("Internet", 7, "80.00", BillStatus.PAID_CLEARED)],
    )

    assert [b.name for b in summary.bills] == ["Internet"]


def test_deposited_pay_is_not_counted_twice():
    summary = summarize_window(
        NOV_6_WINDOW, Decimal("1280.00"), incomes=[pay(6, "780.00", deposited=True)], bills=[]
    )

    assert summary.incoming == Decimal("0")
    assert summary.remaining == Decimal("1280.00")


def test_bills_and_pay_outside_window_are_ignored():
    summary = summarize_window(
        NOV_6_WINDOW,
        Decimal("100.00"),
        incomes=[pay(13, "780.00")],
        bills=[bill("Rent", 15, "1200.00")],
    )

    assert summary.remaining == Decimal("100.00")
    assert summary.bills == ()


def test_overdue_unpaid_bill_is_carried_into_current_window():
    summary = summarize_window(
        NOV_6_WINDOW, Decimal("300.00"), incomes=[], bills=[bill("Water", 3, "45.00")]
    )

    assert summary.overdue == Decimal("45.00")
    assert summary.remaining == Decimal("255.00")


def test_shortfall_produces_negative_remaining():
    summary = summarize_window(
        NOV_6_WINDOW, Decimal("50.00"), incomes=[], bills=[bill("Car", 9, "300.00")]
    )

    assert summary.remaining == Decimal("-250.00")


def test_projection_chains_remaining_balances_without_double_counting_overdue():
    summaries = project_windows(
        WEEKLY,
        from_day=date(2026, 11, 7),
        count=3,
        starting_balance=Decimal("200.00"),
        incomes=[pay(6, "700.00"), pay(13, "700.00"), pay(20, "700.00")],
        bills=[
            bill("Water", 3, "50.00"),
            bill("Phone", 8, "100.00"),
            bill("Rent", 15, "1000.00"),
            bill("Insurance", 21, "150.00"),
        ],
    )

    assert [s.window.start for s in summaries] == [
        date(2026, 11, 6),
        date(2026, 11, 13),
        date(2026, 11, 20),
    ]
    assert [s.remaining for s in summaries] == [
        Decimal("750.00"),
        Decimal("450.00"),
        Decimal("1000.00"),
    ]
    assert [s.overdue for s in summaries] == [Decimal("50.00"), Decimal("0"), Decimal("0")]
