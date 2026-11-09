from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.domain.budget import BillStatus
from app.models import Bill, BillOccurrence
from app.seed import SeedRefused, most_recent_friday, seed
from app.services.bills import list_occurrences
from app.services.summary import build_summary

MONDAY = date(2026, 11, 9)


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 6), date(2026, 11, 6)),
        (MONDAY, date(2026, 11, 6)),
        (date(2026, 11, 5), date(2026, 10, 30)),
    ],
)
def test_most_recent_friday(today, expected):
    assert most_recent_friday(today) == expected


def test_seed_creates_household(db_session):
    counts = seed(db_session, MONDAY)

    assert counts["people"] == 2
    assert counts["bills"] == db_session.scalar(select(func.count()).select_from(Bill)) == 15


def test_first_of_month_is_crowded(db_session):
    seed(db_session, MONDAY)

    due_on_first = list_occurrences(db_session, date(2026, 11, 1), date(2026, 11, 1))

    assert len(due_on_first) >= 6


def test_history_has_one_pending_one_overdue_and_the_rest_cleared(db_session):
    seed(db_session, MONDAY)

    past = list_occurrences(db_session, date(2026, 8, 1), MONDAY - timedelta(days=1))
    statuses = [o.status for o in past]

    assert statuses.count(BillStatus.PAID_PENDING) == 1
    assert statuses.count(BillStatus.UNPAID) == 1
    assert statuses.count(BillStatus.PAID_CLEARED) == len(past) - 2


def test_seeded_data_produces_a_summary(db_session):
    seed(db_session, MONDAY)

    summary = build_summary(db_session, window_count=6)

    assert summary.balance.as_of_date == MONDAY
    assert len(summary.windows) == 6
    assert not any(paycheck.uses_default_hours for paycheck in summary.windows[1].paychecks)
    assert all(paycheck.uses_default_hours for paycheck in summary.windows[2].paychecks)
    assert summary.windows[0].overdue > 0


def test_refuses_to_overwrite_without_reset(db_session):
    seed(db_session, MONDAY)

    with pytest.raises(SeedRefused):
        seed(db_session, MONDAY)


def test_reset_replaces_existing_data(db_session):
    seed(db_session, MONDAY)

    seed(db_session, MONDAY, reset=True)

    assert db_session.scalar(select(func.count()).select_from(Bill)) == 15


@pytest.mark.parametrize(
    "today",
    [date(2026, 1, 31), date(2028, 2, 29), date(2026, 11, 6), date(2026, 12, 31), date(2027, 3, 1)],
)
def test_seed_works_on_awkward_dates(db_session, today):
    seed(db_session, today)

    assert build_summary(db_session, window_count=3).windows
    assert db_session.scalar(select(func.count()).select_from(BillOccurrence)) > 0
