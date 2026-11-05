from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.budget import BillDue, IncomeDue, budget_window_containing, project_windows
from app.domain.pay import PayType, gross_pay, net_pay
from app.models import BalanceSnapshot, Earner, WorkWeek
from app.schemas import BalanceRead, PaycheckRead, SummaryRead, WeekHoursRead, WindowRead
from app.services.balances import latest_balance
from app.services.bills import list_occurrences
from app.services.earners import list_earners
from app.services.household import get_settings

OVERDUE_LOOKBACK_DAYS = 60


def build_summary(session: Session, window_count: int) -> SummaryRead:
    """Project payday-to-payday windows forward from the most recent bank balance."""
    schedule = get_settings(session).schedule()
    balance = latest_balance(session)

    first = budget_window_containing(schedule, balance.as_of_date)
    end = first.start + timedelta(days=schedule.period_days * window_count - 1)

    paychecks = [
        paycheck
        for earner in list_earners(session)
        for paycheck in _paychecks_for(session, earner, first.start, end, balance)
    ]
    paychecks.sort(key=lambda p: (p.payday, p.earner_name.lower(), p.earner_id))
    occurrences = list_occurrences(session, first.start - timedelta(days=OVERDUE_LOOKBACK_DAYS), end)

    summaries = project_windows(
        schedule,
        balance.as_of_date,
        window_count,
        balance.amount,
        incomes=[IncomeDue(p.earner_name, p.payday, p.net, p.deposited) for p in paychecks],
        bills=[BillDue(o.name, o.due_date, o.amount, o.status) for o in occurrences],
    )

    return SummaryRead(
        balance=BalanceRead.model_validate(balance),
        windows=[
            WindowRead(
                start=s.window.start,
                end=s.window.end,
                starting_balance=s.starting_balance,
                incoming=s.incoming,
                unpaid=s.unpaid,
                pending_withdrawal=s.pending_withdrawal,
                overdue=s.overdue,
                remaining=s.remaining,
                paychecks=[p for p in paychecks if s.window.contains(p.payday)],
                bills=[o for o in occurrences if s.window.contains(o.due_date)],
            )
            for s in summaries
        ],
    )


def _paychecks_for(
    session: Session, earner: Earner, start: date, end: date, balance: BalanceSnapshot
) -> list[PaycheckRead]:
    """Every paycheck one person receives within start..end, using saved or default hours."""
    domain = earner.to_domain()
    paydays = domain.schedule.paydays_between(start, end)
    if not paydays:
        return []

    first_week = domain.schedule.workweek_starts(paydays[0])[0]
    saved = {
        week.week_start: week.hours
        for week in session.scalars(
            select(WorkWeek).where(
                WorkWeek.earner_id == earner.id, WorkWeek.week_start.between(first_week, end)
            )
        )
    }

    paychecks = []
    for payday in paydays:
        weeks = []
        if domain.pay_type is PayType.HOURLY:
            weeks = [
                WeekHoursRead(
                    week_start=week_start,
                    hours=saved.get(week_start, earner.default_weekly_hours),
                    is_default=week_start not in saved,
                )
                for week_start in domain.schedule.workweek_starts(payday)
            ]
        gross = gross_pay(domain, [week.hours for week in weeks])
        paychecks.append(
            PaycheckRead(
                earner_id=earner.id,
                earner_name=earner.name,
                payday=payday,
                weeks=weeks,
                gross=gross,
                net=net_pay(domain, gross),
                uses_default_hours=any(week.is_default for week in weeks),
                deposited=_is_deposited(payday, balance),
            )
        )
    return paychecks


def _is_deposited(payday: date, balance: BalanceSnapshot) -> bool:
    """Whether a paycheck is already reflected in the balance reading."""
    if payday < balance.as_of_date:
        return True
    if payday == balance.as_of_date:
        return bool(balance.includes_same_day_pay)
    return False
