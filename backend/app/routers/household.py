from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import HouseholdSettingsRead, HouseholdSettingsWrite
from app.services import household as service

router = APIRouter(prefix="/api", tags=["household"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/settings", response_model=HouseholdSettingsRead)
def get_settings(session: SessionDep):
    """Household settings; 404 until they have been saved for the first time."""
    try:
        return service.get_settings(session)
    except service.SettingsNotConfigured:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Household settings have not been set up")


@router.put("/settings", response_model=HouseholdSettingsRead)
def save_settings(data: HouseholdSettingsWrite, session: SessionDep):
    """Create or replace the household settings."""
    return service.save_settings(session, data)
