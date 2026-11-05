from datetime import date
from decimal import Decimal

import pytest

from app.domain.money import to_cents
from app.domain.pay import (
    Earner,
    PaySchedule,
    PayType,
    gross_pay,
    net_pay,
    withholding_rate_from_paystub,
)

FRIDAY = date(2026, 11, 6)
WEEKLY = PaySchedule(anchor_payday=FRIDAY)
BIWEEKLY = PaySchedule(anchor_payday=FRIDAY, weeks_per_period=2)


def hourly(rate="20", schedule=WEEKLY, withholding="0.18"):
    return Earner(
        name="Alex",
        pay_type=PayType.HOURLY,
        schedule=schedule,
        withholding_rate=Decimal(withholding),
        hourly_rate=Decimal(rate),
    )


def salaried(salary="52000", schedule=WEEKLY):
    return Earner(
        name="Sam",
        pay_type=PayType.SALARY,
        schedule=schedule,
        withholding_rate=Decimal("0.2"),
        annual_salary=Decimal(salary),
    )


def test_anchor_is_a_friday():
    assert FRIDAY.weekday() == 4


def test_weekly_paydays():
    assert WEEKLY.paydays_between(date(2026, 11, 1), date(2026, 11, 30)) == [
        date(2026, 11, 6),
        date(2026, 11, 13),
        date(2026, 11, 20),
        date(2026, 11, 27),
    ]


def test_biweekly_paydays():
    assert BIWEEKLY.paydays_between(date(2026, 11, 1), date(2026, 12, 31)) == [
        date(2026, 11, 6),
        date(2026, 11, 20),
        date(2026, 12, 4),
        date(2026, 12, 18),
    ]


def test_paydays_before_anchor_are_found():
    assert BIWEEKLY.paydays_between(date(2026, 10, 1), date(2026, 10, 31)) == [
        date(2026, 10, 9),
        date(2026, 10, 23),
    ]


def test_weekly_pay_period_ends_saturday_before_payday():
    assert WEEKLY.pay_period_for(date(2026, 11, 13)) == (date(2026, 11, 1), date(2026, 11, 7))


def test_biweekly_pay_period_covers_two_weeks():
    assert BIWEEKLY.pay_period_for(date(2026, 11, 20)) == (date(2026, 11, 1), date(2026, 11, 14))


def test_pay_period_rejects_non_payday():
    with pytest.raises(ValueError):
        WEEKLY.pay_period_for(date(2026, 11, 12))


def test_hourly_without_overtime():
    assert gross_pay(hourly(), [Decimal("38")]) == Decimal("760.00")


def test_hourly_with_overtime():
    assert gross_pay(hourly(), [Decimal("45")]) == Decimal("950.00")


def test_biweekly_overtime_is_calculated_per_week_not_per_period():
    result = gross_pay(hourly(schedule=BIWEEKLY), [Decimal("45"), Decimal("35")])

    assert result == Decimal("1650.00")


def test_fractional_hours():
    assert gross_pay(hourly(rate="18.75"), [Decimal("37.25")]) == Decimal("698.44")


def test_hourly_requires_hours_for_each_week():
    with pytest.raises(ValueError):
        gross_pay(hourly(schedule=BIWEEKLY), [Decimal("40")])


def test_hourly_rejects_negative_hours():
    with pytest.raises(ValueError):
        gross_pay(hourly(), [Decimal("-1")])


def test_weekly_salary_ignores_hours():
    assert gross_pay(salaried(), [Decimal("60")]) == Decimal("1000.00")


def test_biweekly_salary():
    assert gross_pay(salaried(schedule=BIWEEKLY), []) == Decimal("2000.00")


def test_net_pay_applies_flat_withholding():
    assert net_pay(hourly(withholding="0.18"), Decimal("950.00")) == Decimal("779.00")


def test_withholding_rate_from_paystub():
    assert withholding_rate_from_paystub(Decimal("1000.00"), Decimal("815.50")) == Decimal("0.1845")


def test_paystub_rejects_net_above_gross():
    with pytest.raises(ValueError):
        withholding_rate_from_paystub(Decimal("100"), Decimal("120"))


@pytest.mark.parametrize("rate", ["-0.01", "1", "1.5"])
def test_rejects_invalid_withholding_rate(rate):
    with pytest.raises(ValueError):
        hourly(withholding=rate)


def test_hourly_earner_requires_rate():
    with pytest.raises(ValueError):
        hourly(rate="0")


def test_salaried_earner_requires_salary():
    with pytest.raises(ValueError):
        salaried(salary="0")


def test_to_cents_rounds_half_up():
    assert to_cents(Decimal("10.005")) == Decimal("10.01")
    assert to_cents(Decimal("10.004")) == Decimal("10.00")
