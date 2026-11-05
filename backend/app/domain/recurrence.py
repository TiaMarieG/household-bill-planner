import math
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from dateutil.relativedelta import relativedelta


class Frequency(str, Enum):
    """How a bill repeats."""

    ONCE = "once"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


@dataclass(frozen=True)
class RecurrenceRule:
    """When a bill comes due: a first due date, how often it repeats, and an optional last date."""

    frequency: Frequency
    anchor: date
    interval: int = 1
    until: date | None = None

    def __post_init__(self) -> None:
        """Reject rules that could never produce a sensible schedule."""
        if self.interval < 1:
            raise ValueError("interval must be at least 1")
        if self.until is not None and self.until < self.anchor:
            raise ValueError("until cannot be before the anchor date")


def occurrences_between(rule: RecurrenceRule, start: date, end: date) -> list[date]:
    """Return every due date produced by the rule within start..end, inclusive, in order."""
    if end < start:
        raise ValueError("end cannot be before start")

    first = max(start, rule.anchor)
    last = end if rule.until is None else min(end, rule.until)
    if first > last:
        return []

    if rule.frequency is Frequency.ONCE:
        return [rule.anchor] if first <= rule.anchor <= last else []
    if rule.frequency is Frequency.MONTHS:
        return _monthly(rule.anchor, rule.interval, first, last)

    step_days = rule.interval * (7 if rule.frequency is Frequency.WEEKS else 1)
    return _fixed_step(rule.anchor, step_days, first, last)


def _fixed_step(anchor: date, step_days: int, first: date, last: date) -> list[date]:
    """List anchor + k * step_days for every k that lands within first..last."""
    step = timedelta(days=step_days)
    current = anchor + step * math.ceil((first - anchor).days / step_days)
    dates = []
    while current <= last:
        dates.append(current)
        current += step
    return dates


def _monthly(anchor: date, interval: int, first: date, last: date) -> list[date]:
    """List anchor + k * interval months within first..last, clamping to each month's last day."""
    months_to_first = (first.year - anchor.year) * 12 + (first.month - anchor.month)
    k = months_to_first // interval
    dates = []
    while True:
        current = anchor + relativedelta(months=k * interval)
        if current > last:
            return dates
        if current >= first:
            dates.append(current)
        k += 1
