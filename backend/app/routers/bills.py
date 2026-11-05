from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import BillCreate, BillRead, BillUpdate, OccurrenceRead, OccurrenceUpdate
from app.services import bills as service

MAX_RANGE_DAYS = 400

router = APIRouter(prefix="/api", tags=["bills"])
SessionDep = Annotated[Session, Depends(get_session)]


def _not_found(bill_id: int) -> HTTPException:
    """404 response for a missing bill."""
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Bill {bill_id} not found")


@router.get("/bills", response_model=list[BillRead])
def list_bills(session: SessionDep, include_inactive: bool = False):
    """List bills, hiding archived ones unless include_inactive is true."""
    return service.list_bills(session, include_inactive)


@router.post("/bills", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(data: BillCreate, session: SessionDep):
    """Add a bill."""
    return service.create_bill(session, data)


@router.get("/bills/{bill_id}", response_model=BillRead)
def get_bill(bill_id: int, session: SessionDep):
    """Fetch one bill."""
    try:
        return service.get_bill(session, bill_id)
    except service.BillNotFound:
        raise _not_found(bill_id)


@router.patch("/bills/{bill_id}", response_model=BillRead)
def update_bill(bill_id: int, data: BillUpdate, session: SessionDep):
    """Change some fields of a bill; schedule changes drop statuses for dates that no longer exist."""
    try:
        return service.update_bill(session, bill_id, data)
    except service.BillNotFound:
        raise _not_found(bill_id)
    except service.InvalidBillChange as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.delete("/bills/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(bill_id: int, session: SessionDep):
    """Permanently delete a bill and its payment history."""
    try:
        service.delete_bill(session, bill_id)
    except service.BillNotFound:
        raise _not_found(bill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/occurrences", response_model=list[OccurrenceRead])
def list_occurrences(
    session: SessionDep,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    """Every due date of every active bill between start and end, inclusive."""
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "end cannot be before start")
    if (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"range cannot exceed {MAX_RANGE_DAYS} days"
        )
    return service.list_occurrences(session, start, end)


@router.put("/bills/{bill_id}/occurrences/{due_date}", response_model=OccurrenceRead)
def set_occurrence(bill_id: int, due_date: date, data: OccurrenceUpdate, session: SessionDep):
    """Set the status (and optional one-off amount) for one due date of a bill."""
    try:
        return service.set_occurrence(
            session, bill_id, due_date, data.status, data.amount_override
        )
    except service.BillNotFound:
        raise _not_found(bill_id)
    except service.InvalidBillChange as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
