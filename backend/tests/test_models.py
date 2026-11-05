from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.domain.budget import BillStatus
from app.domain.recurrence import Frequency
from app.models import Bill, BillOccurrence


def make_bill(**overrides) -> Bill:
    values = {
        "name": "Phone",
        "amount": Decimal("65.00"),
        "frequency": Frequency.MONTHS,
        "anchor_date": date(2026, 11, 8),
    }
    return Bill(**(values | overrides))


def test_bill_round_trips_with_exact_decimal(db_session):
    db_session.add(make_bill(amount=Decimal("0.10") + Decimal("0.20")))
    db_session.commit()

    stored = db_session.scalars(select(Bill)).one()

    assert stored.amount == Decimal("0.30")
    assert stored.interval_count == 1
    assert stored.is_active is True


def test_enums_are_stored_as_lowercase_values(db_session):
    bill = make_bill(frequency=Frequency.DAYS, interval_count=28)
    bill.occurrences.append(BillOccurrence(due_date=date(2026, 11, 8), status=BillStatus.PAID_PENDING))
    db_session.add(bill)
    db_session.commit()

    raw = db_session.execute(
        text("SELECT b.frequency, o.status FROM bills b JOIN bill_occurrences o ON o.bill_id = b.id")
    ).one()

    assert tuple(raw) == ("days", "paid_pending")


def test_rule_is_built_from_stored_schedule(db_session):
    bill = make_bill(frequency=Frequency.WEEKS, interval_count=2, until_date=date(2027, 1, 1))

    rule = bill.rule()

    assert (rule.frequency, rule.anchor, rule.interval, rule.until) == (
        Frequency.WEEKS,
        date(2026, 11, 8),
        2,
        date(2027, 1, 1),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": Decimal("0")},
        {"amount": Decimal("-5")},
        {"interval_count": 0},
        {"until_date": date(2026, 1, 1)},
    ],
)
def test_database_rejects_invalid_bills(db_session, overrides):
    db_session.add(make_bill(**overrides))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_unknown_status(db_session):
    bill = make_bill()
    db_session.add(bill)
    db_session.flush()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text("INSERT INTO bill_occurrences (bill_id, due_date, status) VALUES (:id, '2026-11-08', 'paid')"),
            {"id": bill.id},
        )


def test_one_status_row_per_bill_due_date(db_session):
    bill = make_bill()
    bill.occurrences.append(BillOccurrence(due_date=date(2026, 11, 8)))
    bill.occurrences.append(BillOccurrence(due_date=date(2026, 11, 8)))
    db_session.add(bill)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_bill_deletes_its_status_rows_in_the_database(db_session):
    bill = make_bill()
    bill.occurrences.append(BillOccurrence(due_date=date(2026, 11, 8), status=BillStatus.PAID_CLEARED))
    db_session.add(bill)
    db_session.commit()

    db_session.execute(text("DELETE FROM bills WHERE id = :id"), {"id": bill.id})

    assert db_session.scalar(text("SELECT count(*) FROM bill_occurrences")) == 0


def test_household_settings_allow_only_one_row(db_session):
    db_session.execute(
        text("INSERT INTO household_settings (id, budget_anchor_payday) VALUES (1, '2026-11-06')")
    )

    with pytest.raises(IntegrityError):
        db_session.execute(
            text("INSERT INTO household_settings (id, budget_anchor_payday) VALUES (2, '2026-11-06')")
        )


@pytest.mark.parametrize(
    ("pay_type", "hourly_rate", "annual_salary"),
    [("hourly", None, 50000), ("salary", 20, None), ("hourly", 0, None)],
)
def test_database_requires_pay_amount_matching_pay_type(db_session, pay_type, hourly_rate, annual_salary):
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO earners (name, pay_type, hourly_rate, annual_salary, withholding_percent,"
                " anchor_payday) VALUES ('Alex', :pay_type, :rate, :salary, 18, '2026-11-06')"
            ),
            {"pay_type": pay_type, "rate": hourly_rate, "salary": annual_salary},
        )
