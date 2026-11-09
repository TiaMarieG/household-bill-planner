import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.domain.budget import BillStatus
from app.domain.pay import PayType
from app.domain.recurrence import Frequency, occurrences_between
from app.models import BalanceSnapshot, Bill, BillOccurrence, Earner, HouseholdSettings, WorkWeek

SEEDED_MODELS = (BillOccurrence, Bill, WorkWeek, Earner, BalanceSnapshot, HouseholdSettings)
FRIDAY = 4
HISTORY_MONTHS = 3

MONTHLY_BILLS = [
    ("Rent", "1450.00", 1),
    ("Car payment", "389.12", 1),
    ("Internet", "79.99", 1),
    ("Phone plan", "85.00", 1),
    ("Streaming bundle", "22.99", 1),
    ("Renter's insurance", "18.50", 1),
    ("Electric", "96.40", 12),
    ("Car insurance", "142.00", 15),
    ("Gym", "34.99", 15),
    ("Credit card minimum", "65.00", 22),
    ("Student loan", "210.00", 28),
]


class SeedRefused(Exception):
    """Raised when seeding would overwrite existing data without --reset, or run in production."""


def most_recent_friday(today: date) -> date:
    """Today if it is a Friday, otherwise the Friday before it."""
    return today - timedelta(days=(today.weekday() - FRIDAY) % 7)


def has_data(session: Session) -> bool:
    """True when any table the seed writes to already has rows."""
    return any(session.scalar(select(func.count()).select_from(model)) for model in SEEDED_MODELS)


def _bills(month_start: date) -> list[Bill]:
    """Fake bills anchored a few months back so the calendar has history to show."""
    history_start = month_start - relativedelta(months=HISTORY_MONTHS)
    bills = [
        Bill(
            name=name,
            amount=Decimal(amount),
            frequency=Frequency.MONTHS,
            anchor_date=history_start.replace(day=day),
        )
        for name, amount, day in MONTHLY_BILLS
    ]
    bills += [
        Bill(
            name="Alex's prescription",
            amount=Decimal("25.00"),
            frequency=Frequency.DAYS,
            interval_count=28,
            anchor_date=history_start + timedelta(days=4),
        ),
        Bill(
            name="Sam's prescription",
            amount=Decimal("15.00"),
            frequency=Frequency.DAYS,
            interval_count=30,
            anchor_date=history_start + timedelta(days=9),
        ),
        Bill(
            name="Water & sewer",
            amount=Decimal("128.75"),
            frequency=Frequency.MONTHS,
            interval_count=3,
            anchor_date=history_start.replace(day=20),
        ),
        Bill(
            name="Car registration",
            amount=Decimal("96.00"),
            frequency=Frequency.ONCE,
            anchor_date=month_start + relativedelta(months=1, days=7),
        ),
    ]
    return bills


def _mark_history(bills: list[Bill], today: date) -> None:
    """Clear every past due date, then leave the latest one pending and the one before it unpaid (overdue)."""
    past = sorted(
        (
            (due, bill)
            for bill in bills
            if bill.anchor_date < today
            for due in occurrences_between(bill.rule(), bill.anchor_date, today - timedelta(days=1))
        ),
        key=lambda pair: (pair[0], pair[1].name),
    )
    for due, bill in past[:-2]:
        bill.occurrences.append(BillOccurrence(due_date=due, status=BillStatus.PAID_CLEARED))
    if len(past) >= 2:
        due, bill = past[-1]
        bill.occurrences.append(BillOccurrence(due_date=due, status=BillStatus.PAID_PENDING))


def seed(session: Session, today: date, reset: bool = False) -> dict[str, int]:
    """Fill the database with a fake two-person household whose dates are relative to today."""
    if has_data(session):
        if not reset:
            raise SeedRefused("The database already has data. Rerun with --reset to replace it.")
        for model in SEEDED_MODELS:
            session.execute(delete(model))

    payday = most_recent_friday(today)
    session.add(HouseholdSettings(id=1, budget_anchor_payday=payday))

    people = [
        Earner(
            name="Alex",
            pay_type=PayType.HOURLY,
            hourly_rate=Decimal("23.50"),
            withholding_percent=Decimal("17.80"),
            anchor_payday=payday,
        ),
        Earner(
            name="Sam",
            pay_type=PayType.HOURLY,
            hourly_rate=Decimal("19.25"),
            withholding_percent=Decimal("15.60"),
            default_weekly_hours=Decimal("36"),
            anchor_payday=payday,
        ),
    ]
    session.add_all(people)
    bills = _bills(today.replace(day=1))
    session.add_all(bills)
    session.flush()

    last_full_week = people[0].schedule().workweek_starts(payday + timedelta(days=7))[0]
    people[0].work_weeks.append(WorkWeek(week_start=last_full_week, hours=Decimal("44.5")))
    people[1].work_weeks.append(WorkWeek(week_start=last_full_week, hours=Decimal("32")))
    _mark_history(bills, today)

    session.add(
        BalanceSnapshot(
            amount=Decimal("1840.27"),
            as_of_date=today,
            includes_same_day_pay=False if today == payday else None,
        )
    )
    session.commit()
    return {
        "people": len(people),
        "bills": len(bills),
        "payment_records": sum(len(bill.occurrences) for bill in bills),
    }


def main() -> int:
    """Command-line entry point: python -m app.seed [--reset]."""
    parser = argparse.ArgumentParser(description="Fill the local database with fake sample data.")
    parser.add_argument("--reset", action="store_true", help="delete existing data first")
    args = parser.parse_args()

    if get_settings().app_env == "production":
        print("Refusing to seed: APP_ENV is production.", file=sys.stderr)
        return 1

    with SessionLocal() as session:
        try:
            counts = seed(session, date.today(), reset=args.reset)
        except SeedRefused as error:
            print(error, file=sys.stderr)
            return 1

    print(
        f"Seeded {counts['people']} people, {counts['bills']} bills and "
        f"{counts['payment_records']} payment records."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
