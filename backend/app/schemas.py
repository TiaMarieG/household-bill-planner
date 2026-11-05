from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.budget import BillStatus
from app.domain.recurrence import Frequency

Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
BillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class BillCreate(BaseModel):
    """Fields required to add a bill."""

    name: BillName
    amount: Money
    frequency: Frequency
    interval_count: int = Field(default=1, ge=1, le=366)
    anchor_date: date
    until_date: date | None = None

    @model_validator(mode="after")
    def _until_not_before_anchor(self) -> "BillCreate":
        """Reject an end date that comes before the first due date."""
        if self.until_date is not None and self.until_date < self.anchor_date:
            raise ValueError("until_date cannot be before anchor_date")
        return self


class BillUpdate(BaseModel):
    """Fields that can be changed on an existing bill; omitted fields stay as they are."""

    name: BillName | None = None
    amount: Money | None = None
    frequency: Frequency | None = None
    interval_count: int | None = Field(default=None, ge=1, le=366)
    anchor_date: date | None = None
    until_date: date | None = None
    is_active: bool | None = None


class BillRead(BaseModel):
    """A bill as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount: Decimal
    frequency: Frequency
    interval_count: int
    anchor_date: date
    until_date: date | None
    is_active: bool


class OccurrenceRead(BaseModel):
    """One due date of a bill, with the amount and status that apply to that date."""

    bill_id: int
    name: str
    due_date: date
    amount: Decimal
    status: BillStatus
    amount_overridden: bool


class OccurrenceUpdate(BaseModel):
    """New status for one due date, plus an optional one-off amount (null uses the bill's amount)."""

    status: BillStatus
    amount_override: Money | None = None
