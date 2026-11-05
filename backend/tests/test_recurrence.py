from datetime import date

import pytest

from app.domain.recurrence import Frequency, RecurrenceRule, occurrences_between


def test_one_time_bill_inside_window():
    rule = RecurrenceRule(Frequency.ONCE, anchor=date(2026, 11, 20))

    assert occurrences_between(rule, date(2026, 11, 1), date(2026, 11, 30)) == [date(2026, 11, 20)]


def test_one_time_bill_outside_window():
    rule = RecurrenceRule(Frequency.ONCE, anchor=date(2026, 12, 5))

    assert occurrences_between(rule, date(2026, 11, 1), date(2026, 11, 30)) == []


def test_every_28_days_crosses_month_and_year_boundaries():
    rule = RecurrenceRule(Frequency.DAYS, anchor=date(2026, 10, 9), interval=28)

    result = occurrences_between(rule, date(2026, 11, 1), date(2027, 1, 31))

    assert result == [date(2026, 11, 6), date(2026, 12, 4), date(2027, 1, 1), date(2027, 1, 29)]


def test_every_30_days_drifts_through_the_month():
    rule = RecurrenceRule(Frequency.DAYS, anchor=date(2026, 1, 1), interval=30)

    result = occurrences_between(rule, date(2026, 1, 1), date(2026, 4, 30))

    assert result == [date(2026, 1, 1), date(2026, 1, 31), date(2026, 3, 2), date(2026, 4, 1)]


def test_every_two_weeks():
    rule = RecurrenceRule(Frequency.WEEKS, anchor=date(2026, 11, 6), interval=2)

    result = occurrences_between(rule, date(2026, 11, 1), date(2026, 12, 31))

    assert result == [date(2026, 11, 6), date(2026, 11, 20), date(2026, 12, 4), date(2026, 12, 18)]


def test_window_starting_mid_cycle_finds_next_due_date():
    rule = RecurrenceRule(Frequency.DAYS, anchor=date(2026, 1, 1), interval=28)

    result = occurrences_between(rule, date(2026, 1, 2), date(2026, 2, 28))

    assert result == [date(2026, 1, 29), date(2026, 2, 26)]


def test_monthly_on_31st_clamps_to_short_months_without_drifting():
    rule = RecurrenceRule(Frequency.MONTHS, anchor=date(2026, 1, 31))

    result = occurrences_between(rule, date(2026, 1, 1), date(2026, 5, 31))

    assert result == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ]


def test_monthly_on_29th_lands_on_leap_day():
    rule = RecurrenceRule(Frequency.MONTHS, anchor=date(2027, 12, 29))

    assert occurrences_between(rule, date(2028, 2, 1), date(2028, 2, 29)) == [date(2028, 2, 29)]


def test_quarterly_bill():
    rule = RecurrenceRule(Frequency.MONTHS, anchor=date(2026, 1, 15), interval=3)

    result = occurrences_between(rule, date(2026, 1, 1), date(2026, 12, 31))

    assert result == [date(2026, 1, 15), date(2026, 4, 15), date(2026, 7, 15), date(2026, 10, 15)]


def test_monthly_window_far_after_anchor():
    rule = RecurrenceRule(Frequency.MONTHS, anchor=date(2020, 3, 1), interval=6)

    assert occurrences_between(rule, date(2026, 1, 1), date(2026, 12, 31)) == [
        date(2026, 3, 1),
        date(2026, 9, 1),
    ]


def test_window_before_anchor_returns_nothing():
    rule = RecurrenceRule(Frequency.MONTHS, anchor=date(2027, 1, 1))

    assert occurrences_between(rule, date(2026, 11, 1), date(2026, 11, 30)) == []


def test_until_stops_the_schedule():
    rule = RecurrenceRule(
        Frequency.MONTHS, anchor=date(2026, 1, 10), until=date(2026, 3, 10)
    )

    result = occurrences_between(rule, date(2026, 1, 1), date(2026, 12, 31))

    assert result == [date(2026, 1, 10), date(2026, 2, 10), date(2026, 3, 10)]


def test_window_bounds_are_inclusive():
    rule = RecurrenceRule(Frequency.WEEKS, anchor=date(2026, 11, 6))

    result = occurrences_between(rule, date(2026, 11, 6), date(2026, 11, 13))

    assert result == [date(2026, 11, 6), date(2026, 11, 13)]


@pytest.mark.parametrize("interval", [0, -1])
def test_rejects_non_positive_interval(interval):
    with pytest.raises(ValueError):
        RecurrenceRule(Frequency.DAYS, anchor=date(2026, 1, 1), interval=interval)


def test_rejects_until_before_anchor():
    with pytest.raises(ValueError):
        RecurrenceRule(Frequency.MONTHS, anchor=date(2026, 5, 1), until=date(2026, 4, 1))


def test_rejects_reversed_window():
    rule = RecurrenceRule(Frequency.MONTHS, anchor=date(2026, 1, 1))

    with pytest.raises(ValueError):
        occurrences_between(rule, date(2026, 2, 1), date(2026, 1, 1))
