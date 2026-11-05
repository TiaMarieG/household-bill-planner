from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Earner, WorkWeek
from app.schemas import EarnerCreate, EarnerUpdate

SCHEDULE_FIELDS = {"anchor_payday", "weeks_per_period", "days_from_period_end_to_payday"}
NULLABLE_FIELDS = {"hourly_rate", "annual_salary"}


class EarnerNotFound(Exception):
    """Raised when an earner id does not exist."""


class InvalidEarnerChange(Exception):
    """Raised when a requested change would leave pay settings or hours invalid."""


def list_earners(session: Session, include_inactive: bool = False) -> list[Earner]:
    """All people ordered by name, optionally including archived ones."""
    query = select(Earner).order_by(Earner.name, Earner.id)
    if not include_inactive:
        query = query.where(Earner.is_active.is_(True))
    return list(session.scalars(query))


def get_earner(session: Session, earner_id: int) -> Earner:
    """Fetch one person or raise EarnerNotFound."""
    earner = session.get(Earner, earner_id)
    if earner is None:
        raise EarnerNotFound(earner_id)
    return earner


def create_earner(session: Session, data: EarnerCreate) -> Earner:
    """Insert a new person and return them."""
    earner = Earner(**data.model_dump())
    session.add(earner)
    session.commit()
    session.refresh(earner)
    return earner


def update_earner(session: Session, earner_id: int, data: EarnerUpdate) -> Earner:
    """Apply the provided fields, dropping stored hours that no longer line up with the new schedule."""
    earner = get_earner(session, earner_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field not in NULLABLE_FIELDS:
            session.rollback()
            raise InvalidEarnerChange(f"{field} cannot be null")
        setattr(earner, field, value)

    try:
        schedule = earner.to_domain().schedule
    except ValueError as error:
        session.rollback()
        raise InvalidEarnerChange(str(error)) from error

    if SCHEDULE_FIELDS & changes.keys():
        for week in list(earner.work_weeks):
            if not schedule.is_workweek_start(week.week_start):
                earner.work_weeks.remove(week)

    session.commit()
    session.refresh(earner)
    return earner


def delete_earner(session: Session, earner_id: int) -> None:
    """Permanently delete a person and all of their recorded hours."""
    session.delete(get_earner(session, earner_id))
    session.commit()


def list_hours(session: Session, earner_id: int, start: date, end: date) -> list[WorkWeek]:
    """Recorded hours for one person with week starts within start..end."""
    get_earner(session, earner_id)
    return list(
        session.scalars(
            select(WorkWeek)
            .where(WorkWeek.earner_id == earner_id, WorkWeek.week_start.between(start, end))
            .order_by(WorkWeek.week_start)
        )
    )


def set_hours(session: Session, earner_id: int, week_start: date, hours: Decimal) -> WorkWeek:
    """Record the hours one person worked in the workweek starting on week_start."""
    earner = get_earner(session, earner_id)
    if not earner.schedule().is_workweek_start(week_start):
        raise InvalidEarnerChange(f"{week_start} is not the first day of a workweek for {earner.name}")

    upsert = (
        insert(WorkWeek)
        .values(earner_id=earner_id, week_start=week_start, hours=hours)
        .on_conflict_do_update(
            constraint="uq_work_weeks_earner_id_week_start", set_={"hours": hours}
        )
        .returning(WorkWeek)
    )
    row = session.scalars(upsert, execution_options={"populate_existing": True}).one()
    session.commit()
    return row


def clear_hours(session: Session, earner_id: int, week_start: date) -> None:
    """Remove recorded hours so the week falls back to the person's default hours."""
    get_earner(session, earner_id)
    session.execute(
        delete(WorkWeek).where(WorkWeek.earner_id == earner_id, WorkWeek.week_start == week_start)
    )
    session.commit()
