from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.budget import BillStatus
from app.domain.pay import PayType
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


Percent = Annotated[Decimal, Field(ge=0, lt=100, max_digits=5, decimal_places=2)]
Hours = Annotated[Decimal, Field(ge=0, le=168, max_digits=5, decimal_places=2)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class HouseholdSettingsWrite(BaseModel):
    """The payday cycle that defines payday-to-payday budget weeks."""

    budget_anchor_payday: date
    budget_weeks_per_period: int = Field(default=1, ge=1, le=4)


class HouseholdSettingsRead(HouseholdSettingsWrite):
    """Household settings as returned by the API."""

    model_config = ConfigDict(from_attributes=True)


class EarnerCreate(BaseModel):
    """Fields required to add a person who brings in pay."""

    name: PersonName
    pay_type: PayType
    hourly_rate: Money | None = None
    annual_salary: Money | None = None
    withholding_percent: Percent
    default_weekly_hours: Hours = Decimal("40")
    overtime_threshold_hours: Annotated[Decimal, Field(gt=0, le=168, decimal_places=2)] = Decimal("40")
    overtime_multiplier: Annotated[Decimal, Field(ge=1, le=3, decimal_places=2)] = Decimal("1.5")
    anchor_payday: date
    weeks_per_period: int = Field(default=1, ge=1, le=4)
    days_from_period_end_to_payday: int = Field(default=6, ge=0, le=31)

    @model_validator(mode="after")
    def _pay_matches_type(self) -> "EarnerCreate":
        """Hourly people need an hourly rate; salaried people need an annual salary."""
        if self.pay_type is PayType.HOURLY and self.hourly_rate is None:
            raise ValueError("hourly_rate is required for hourly pay")
        if self.pay_type is PayType.SALARY and self.annual_salary is None:
            raise ValueError("annual_salary is required for salary pay")
        return self


class EarnerUpdate(BaseModel):
    """Fields that can be changed on a person; omitted fields stay as they are."""

    name: PersonName | None = None
    pay_type: PayType | None = None
    hourly_rate: Money | None = None
    annual_salary: Money | None = None
    withholding_percent: Percent | None = None
    default_weekly_hours: Hours | None = None
    overtime_threshold_hours: Annotated[Decimal, Field(gt=0, le=168, decimal_places=2)] | None = None
    overtime_multiplier: Annotated[Decimal, Field(ge=1, le=3, decimal_places=2)] | None = None
    anchor_payday: date | None = None
    weeks_per_period: int | None = Field(default=None, ge=1, le=4)
    days_from_period_end_to_payday: int | None = Field(default=None, ge=0, le=31)
    is_active: bool | None = None


class EarnerRead(BaseModel):
    """A person's pay settings as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    pay_type: PayType
    hourly_rate: Decimal | None
    annual_salary: Decimal | None
    withholding_percent: Decimal
    default_weekly_hours: Decimal
    overtime_threshold_hours: Decimal
    overtime_multiplier: Decimal
    anchor_payday: date
    weeks_per_period: int
    days_from_period_end_to_payday: int
    is_active: bool


class WorkWeekWrite(BaseModel):
    """Hours actually worked in one workweek."""

    hours: Hours


class WorkWeekRead(BaseModel):
    """Stored hours for one person and workweek."""

    model_config = ConfigDict(from_attributes=True)

    earner_id: int
    week_start: date
    hours: Decimal


SignedMoney = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


class BalanceCreate(BaseModel):
    """A bank balance reading; includes_same_day_pay is required only when as_of_date is a payday."""

    amount: SignedMoney
    as_of_date: date
    includes_same_day_pay: bool | None = None


class BalanceRead(BaseModel):
    """A stored bank balance reading."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    as_of_date: date
    includes_same_day_pay: bool | None
    recorded_at: datetime


class WeekHoursRead(BaseModel):
    """Hours used for one workweek of a paycheck, and whether they are the person's default."""

    week_start: date
    hours: Decimal
    is_default: bool


class PaycheckRead(BaseModel):
    """One expected paycheck with the numbers behind it."""

    earner_id: int
    earner_name: str
    payday: date
    weeks: list[WeekHoursRead]
    gross: Decimal
    net: Decimal
    uses_default_hours: bool
    deposited: bool


class WindowRead(BaseModel):
    """One payday-to-payday window: starting balance, money in, bills, and what is left."""

    start: date
    end: date
    starting_balance: Decimal
    incoming: Decimal
    unpaid: Decimal
    pending_withdrawal: Decimal
    overdue: Decimal
    remaining: Decimal
    paychecks: list[PaycheckRead]
    bills: list[OccurrenceRead]


class SummaryRead(BaseModel):
    """The balance the projection starts from and the windows that follow it."""

    balance: BalanceRead
    windows: list[WindowRead]
