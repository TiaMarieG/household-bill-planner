from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_session
from app.schemas import BalanceCreate, BalanceRead, SummaryRead
from app.services import balances, summary
from app.services.household import SettingsNotConfigured

router = APIRouter(prefix="/api", tags=["balance & summary"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/balances", response_model=BalanceRead, status_code=status.HTTP_201_CREATED)
def record_balance(
    data: BalanceCreate, session: SessionDep, today: Annotated[date, Depends(get_today)]
):
    """Save a bank balance reading; on a payday, say whether that day's pay is already included."""
    try:
        return balances.record_balance(session, data, today)
    except balances.InvalidBalance as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.get("/balances", response_model=list[BalanceRead])
def list_balances(session: SessionDep, limit: Annotated[int, Query(ge=1, le=200)] = 20):
    """Balance history, newest first."""
    return balances.list_balances(session, limit)


@router.get("/balances/latest", response_model=BalanceRead)
def latest_balance(session: SessionDep):
    """The current balance reading; 404 until one has been entered."""
    try:
        return balances.latest_balance(session)
    except balances.NoBalanceRecorded:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No balance has been entered yet")


@router.delete("/balances/{balance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_balance(balance_id: int, session: SessionDep):
    """Delete a mistaken reading."""
    try:
        balances.delete_balance(session, balance_id)
    except balances.BalanceNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Balance {balance_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=SummaryRead)
def get_summary(session: SessionDep, windows: Annotated[int, Query(ge=1, le=26)] = 6):
    """Payday-to-payday windows projected forward from the current balance."""
    try:
        return summary.build_summary(session, windows)
    except SettingsNotConfigured:
        raise HTTPException(status.HTTP_409_CONFLICT, "Set up household settings first")
    except balances.NoBalanceRecorded:
        raise HTTPException(status.HTTP_409_CONFLICT, "Enter a bank balance first")
