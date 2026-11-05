from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from app.domain.money import to_cents

WEEKS_PER_YEAR = Decimal(52)


class PayType(str, Enum):
    """Whether pay is calculated from hours worked or a fixed salary."""

    HOURLY = "hourly"
    SALARY = "salary"


@dataclass(frozen=True)
class PaySchedule:
    """How often someone is paid and how their pay period lines up with payday."""

    anchor_payday: date
    weeks_per_period: int = 1
    days_from_period_end_to_payday: int = 6

    def __post_init__(self) -> None:
        """Reject schedules that cannot describe a real pay cycle."""
        if self.weeks_per_period < 1:
            raise ValueError("weeks_per_period must be at least 1")
        if self.days_from_period_end_to_payday < 0:
            raise ValueError("days_from_period_end_to_payday cannot be negative")

    @property
    def period_days(self) -> int:
        """Length of one pay period in days."""
        return 7 * self.weeks_per_period

    def is_payday(self, day: date) -> bool:
        """True when the given date falls on this schedule's payday cycle."""
        return (day - self.anchor_payday).days % self.period_days == 0

    def paydays_between(self, start: date, end: date) -> list[date]:
        """Every payday within start..end, inclusive, whether before or after the anchor."""
        if end < start:
            raise ValueError("end cannot be before start")
        step = timedelta(days=self.period_days)
        current = start + timedelta(days=(self.anchor_payday - start).days % self.period_days)
        paydays = []
        while current <= end:
            paydays.append(current)
            current += step
        return paydays

    def pay_period_for(self, payday: date) -> tuple[date, date]:
        """First and last day of the work that is paid on the given payday."""
        if not self.is_payday(payday):
            raise ValueError(f"{payday} is not a payday on this schedule")
        end = payday - timedelta(days=self.days_from_period_end_to_payday)
        start = end - timedelta(days=self.period_days - 1)
        return start, end


@dataclass(frozen=True)
class Earner:
    """One person's pay settings: how they're paid, when, and their estimated withholding."""

    name: str
    pay_type: PayType
    schedule: PaySchedule
    withholding_rate: Decimal
    hourly_rate: Decimal = Decimal("0")
    annual_salary: Decimal = Decimal("0")
    overtime_threshold_hours: Decimal = Decimal("40")
    overtime_multiplier: Decimal = Decimal("1.5")

    def __post_init__(self) -> None:
        """Reject pay settings that would produce meaningless estimates."""
        if not Decimal("0") <= self.withholding_rate < Decimal("1"):
            raise ValueError("withholding_rate must be between 0 (inclusive) and 1 (exclusive)")
        if self.pay_type is PayType.HOURLY and self.hourly_rate <= 0:
            raise ValueError("hourly earners need a positive hourly_rate")
        if self.pay_type is PayType.SALARY and self.annual_salary <= 0:
            raise ValueError("salaried earners need a positive annual_salary")


def gross_pay(earner: Earner, weekly_hours: list[Decimal]) -> Decimal:
    """Gross pay for one pay period; hourly overtime is applied per workweek, not per period."""
    if earner.pay_type is PayType.SALARY:
        return to_cents(earner.annual_salary * earner.schedule.weeks_per_period / WEEKS_PER_YEAR)

    if len(weekly_hours) != earner.schedule.weeks_per_period:
        raise ValueError(
            f"expected hours for {earner.schedule.weeks_per_period} week(s), got {len(weekly_hours)}"
        )
    if any(hours < 0 for hours in weekly_hours):
        raise ValueError("hours cannot be negative")

    return to_cents(sum((_week_pay(earner, hours) for hours in weekly_hours), Decimal("0")))


def _week_pay(earner: Earner, hours: Decimal) -> Decimal:
    """Pay for a single workweek, splitting regular and overtime hours."""
    regular = min(hours, earner.overtime_threshold_hours)
    overtime = max(hours - earner.overtime_threshold_hours, Decimal("0"))
    return earner.hourly_rate * (regular + overtime * earner.overtime_multiplier)


def net_pay(earner: Earner, gross: Decimal) -> Decimal:
    """Estimated take-home pay after the earner's flat withholding percentage."""
    return to_cents(gross * (1 - earner.withholding_rate))


def withholding_rate_from_paystub(gross: Decimal, net: Decimal) -> Decimal:
    """Effective withholding rate implied by one paystub's gross and net amounts."""
    if gross <= 0:
        raise ValueError("gross must be positive")
    if not Decimal("0") <= net <= gross:
        raise ValueError("net must be between 0 and gross")
    return ((gross - net) / gross).quantize(Decimal("0.0001"))
