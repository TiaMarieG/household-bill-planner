from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.domain.budget import BillStatus
from app.domain.recurrence import occurrences_between
from app.models import Bill, BillOccurrence
from app.schemas import BillCreate, BillUpdate, OccurrenceRead

SCHEDULE_FIELDS = {"frequency", "interval_count", "anchor_date", "until_date"}


class BillNotFound(Exception):
    """Raised when a bill id does not exist."""


class InvalidBillChange(Exception):
    """Raised when a requested change would leave a bill or occurrence in an invalid state."""


def list_bills(session: Session, include_inactive: bool = False) -> list[Bill]:
    """All bills ordered by name, optionally including archived ones."""
    query = select(Bill).order_by(Bill.name, Bill.id)
    if not include_inactive:
        query = query.where(Bill.is_active.is_(True))
    return list(session.scalars(query))


def get_bill(session: Session, bill_id: int) -> Bill:
    """Fetch one bill or raise BillNotFound."""
    bill = session.get(Bill, bill_id)
    if bill is None:
        raise BillNotFound(bill_id)
    return bill


def create_bill(session: Session, data: BillCreate) -> Bill:
    """Insert a new bill and return it."""
    bill = Bill(**data.model_dump())
    session.add(bill)
    session.commit()
    session.refresh(bill)
    return bill


def update_bill(session: Session, bill_id: int, data: BillUpdate) -> Bill:
    """Apply the provided fields to a bill, dropping statuses for dates the new schedule no longer has."""
    bill = get_bill(session, bill_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field != "until_date":
            raise InvalidBillChange(f"{field} cannot be null")
        setattr(bill, field, value)

    try:
        rule = bill.rule()
    except ValueError as error:
        session.rollback()
        raise InvalidBillChange(str(error)) from error

    if SCHEDULE_FIELDS & changes.keys():
        for occurrence in list(bill.occurrences):
            if occurrences_between(rule, occurrence.due_date, occurrence.due_date) != [occurrence.due_date]:
                bill.occurrences.remove(occurrence)

    session.commit()
    session.refresh(bill)
    return bill


def delete_bill(session: Session, bill_id: int) -> None:
    """Permanently delete a bill and all of its due-date statuses."""
    session.delete(get_bill(session, bill_id))
    session.commit()


def list_occurrences(session: Session, start: date, end: date) -> list[OccurrenceRead]:
    """Every due date of every active bill within start..end, merged with any stored status."""
    bills = list_bills(session)
    stored = {
        (row.bill_id, row.due_date): row
        for row in session.scalars(
            select(BillOccurrence).where(
                BillOccurrence.bill_id.in_([bill.id for bill in bills]),
                BillOccurrence.due_date.between(start, end),
            )
        )
    }

    results = []
    for bill in bills:
        for due_date in occurrences_between(bill.rule(), start, end):
            results.append(_to_read(bill, due_date, stored.get((bill.id, due_date))))
    return sorted(results, key=lambda item: (item.due_date, item.name.lower(), item.bill_id))


def set_occurrence(
    session: Session,
    bill_id: int,
    due_date: date,
    status: BillStatus,
    amount_override: Decimal | None,
) -> OccurrenceRead:
    """Record the status (and optional one-off amount) for one due date of a bill."""
    bill = get_bill(session, bill_id)
    if occurrences_between(bill.rule(), due_date, due_date) != [due_date]:
        raise InvalidBillChange(f"{bill.name} is not due on {due_date}")

    if status is BillStatus.UNPAID and amount_override is None:
        session.execute(
            delete(BillOccurrence).where(
                BillOccurrence.bill_id == bill_id, BillOccurrence.due_date == due_date
            )
        )
        session.commit()
        return _to_read(bill, due_date, None)

    upsert = (
        insert(BillOccurrence)
        .values(bill_id=bill_id, due_date=due_date, status=status, amount_override=amount_override)
        .on_conflict_do_update(
            constraint="uq_bill_occurrences_bill_id_due_date",
            set_={"status": status, "amount_override": amount_override},
        )
        .returning(BillOccurrence)
    )
    row = session.scalars(upsert, execution_options={"populate_existing": True}).one()
    session.commit()
    return _to_read(bill, due_date, row)


def _to_read(bill: Bill, due_date: date, stored: BillOccurrence | None) -> OccurrenceRead:
    """Combine a bill's defaults with a stored status row, if there is one."""
    override = stored.amount_override if stored is not None else None
    return OccurrenceRead(
        bill_id=bill.id,
        name=bill.name,
        due_date=due_date,
        amount=override if override is not None else bill.amount,
        status=stored.status if stored is not None else BillStatus.UNPAID,
        amount_overridden=override is not None,
    )
