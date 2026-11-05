from sqlalchemy.orm import Session

from app.models import HouseholdSettings
from app.schemas import HouseholdSettingsWrite


class SettingsNotConfigured(Exception):
    """Raised when household settings are needed but have not been saved yet."""


def get_settings(session: Session) -> HouseholdSettings:
    """The household settings row, or SettingsNotConfigured if it does not exist yet."""
    settings = session.get(HouseholdSettings, 1)
    if settings is None:
        raise SettingsNotConfigured
    return settings


def save_settings(session: Session, data: HouseholdSettingsWrite) -> HouseholdSettings:
    """Create the household settings row or replace its values."""
    settings = session.get(HouseholdSettings, 1) or HouseholdSettings(id=1)
    settings.budget_anchor_payday = data.budget_anchor_payday
    settings.budget_weeks_per_period = data.budget_weeks_per_period
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings
