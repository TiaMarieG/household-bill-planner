from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import EarnerCreate, EarnerRead, EarnerUpdate, WorkWeekRead, WorkWeekWrite
from app.services import earners as service

router = APIRouter(prefix="/api/earners", tags=["earners"])
SessionDep = Annotated[Session, Depends(get_session)]


def _not_found(earner_id: int) -> HTTPException:
    """404 response for a missing person."""
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Earner {earner_id} not found")


@router.get("", response_model=list[EarnerRead])
def list_earners(session: SessionDep, include_inactive: bool = False):
    """List people, hiding archived ones unless include_inactive is true."""
    return service.list_earners(session, include_inactive)


@router.post("", response_model=EarnerRead, status_code=status.HTTP_201_CREATED)
def create_earner(data: EarnerCreate, session: SessionDep):
    """Add a person and their pay settings."""
    return service.create_earner(session, data)


@router.get("/{earner_id}", response_model=EarnerRead)
def get_earner(earner_id: int, session: SessionDep):
    """Fetch one person."""
    try:
        return service.get_earner(session, earner_id)
    except service.EarnerNotFound:
        raise _not_found(earner_id)


@router.patch("/{earner_id}", response_model=EarnerRead)
def update_earner(earner_id: int, data: EarnerUpdate, session: SessionDep):
    """Change pay settings; schedule changes drop hours for weeks that no longer line up."""
    try:
        return service.update_earner(session, earner_id, data)
    except service.EarnerNotFound:
        raise _not_found(earner_id)
    except service.InvalidEarnerChange as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.delete("/{earner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_earner(earner_id: int, session: SessionDep):
    """Permanently delete a person and their recorded hours."""
    try:
        service.delete_earner(session, earner_id)
    except service.EarnerNotFound:
        raise _not_found(earner_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{earner_id}/hours", response_model=list[WorkWeekRead])
def list_hours(
    earner_id: int,
    session: SessionDep,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    """Recorded hours for weeks starting between start and end; missing weeks use default hours."""
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "end cannot be before start")
    try:
        return service.list_hours(session, earner_id, start, end)
    except service.EarnerNotFound:
        raise _not_found(earner_id)


@router.put("/{earner_id}/hours/{week_start}", response_model=WorkWeekRead)
def set_hours(earner_id: int, week_start: date, data: WorkWeekWrite, session: SessionDep):
    """Record hours worked in the workweek that starts on week_start."""
    try:
        return service.set_hours(session, earner_id, week_start, data.hours)
    except service.EarnerNotFound:
        raise _not_found(earner_id)
    except service.InvalidEarnerChange as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.delete("/{earner_id}/hours/{week_start}", status_code=status.HTTP_204_NO_CONTENT)
def clear_hours(earner_id: int, week_start: date, session: SessionDep):
    """Remove recorded hours so the week uses the person's default hours again."""
    try:
        service.clear_hours(session, earner_id, week_start)
    except service.EarnerNotFound:
        raise _not_found(earner_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
