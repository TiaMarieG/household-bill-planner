from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BalanceSnapshot
from app.schemas import BalanceCreate
from app.services.earners import list_earners

MAX_DAYS_AHEAD = 1


class NoBalanceRecorded(Exception):
    """Raised when a balance is needed but none has been entered yet."""


class BalanceNotFound(Exception):
    """Raised when a balance id does not exist."""


class InvalidBalance(Exception):
    """Raised when a balance reading is missing information or cannot be right."""


def record_balance(session: Session, data: BalanceCreate, today: date) -> BalanceSnapshot:
    """Save a balance reading, requiring an answer about same-day pay only when it is a payday."""
    if data.as_of_date > today + timedelta(days=MAX_DAYS_AHEAD):
        raise InvalidBalance("as_of_date cannot be in the future")

    paid_today = [e.name for e in list_earners(session) if e.schedule().is_payday(data.as_of_date)]
    if paid_today and data.includes_same_day_pay is None:
        raise InvalidBalance(
            f"{data.as_of_date} is a payday for {', '.join(paid_today)}; "
            "set includes_same_day_pay to say whether that pay is already in this balance"
        )

    snapshot = BalanceSnapshot(
        amount=data.amount,
        as_of_date=data.as_of_date,
        includes_same_day_pay=data.includes_same_day_pay if paid_today else None,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def latest_balance(session: Session) -> BalanceSnapshot:
    """The reading with the latest as-of date (newest entry wins ties), or NoBalanceRecorded."""
    snapshot = session.scalars(
        select(BalanceSnapshot)
        .order_by(BalanceSnapshot.as_of_date.desc(), BalanceSnapshot.id.desc())
        .limit(1)
    ).first()
    if snapshot is None:
        raise NoBalanceRecorded
    return snapshot


def list_balances(session: Session, limit: int) -> list[BalanceSnapshot]:
    """Most recent readings first."""
    return list(
        session.scalars(
            select(BalanceSnapshot)
            .order_by(BalanceSnapshot.as_of_date.desc(), BalanceSnapshot.id.desc())
            .limit(limit)
        )
    )


def delete_balance(session: Session, balance_id: int) -> None:
    """Remove a mistaken reading; the previous one becomes current again."""
    snapshot = session.get(BalanceSnapshot, balance_id)
    if snapshot is None:
        raise BalanceNotFound(balance_id)
    session.delete(snapshot)
    session.commit()
