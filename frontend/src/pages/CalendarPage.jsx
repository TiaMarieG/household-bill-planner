import { useCallback, useMemo, useRef } from "react";
import { useSearchParams } from "react-router";
import { useEarners, useOccurrences } from "../api/hooks.js";
import DayCell from "../components/calendar/DayCell.jsx";
import DayPanel from "../components/calendar/DayPanel.jsx";
import {
  WEEKDAYS,
  billState,
  gridRange,
  isMonthKey,
  monthGrid,
  monthKeyOf,
  monthLabel,
  paydaysBetween,
  shiftMonth,
  sortByUrgency,
} from "../lib/calendar.js";
import { formatMoney, toISODate } from "../lib/format.js";
import { sumMoney } from "../lib/money.js";
import "./CalendarPage.css";

/** Group bill occurrences by due date, most urgent first within each day. */
function byDate(occurrences, today) {
  const groups = new Map();
  for (const occurrence of occurrences) {
    if (!groups.has(occurrence.due_date)) groups.set(occurrence.due_date, []);
    groups.get(occurrence.due_date).push(occurrence);
  }
  for (const [day, bills] of groups) groups.set(day, sortByUrgency(bills, today));
  return groups;
}

/** Names of people paid on each date in the range, keyed by date. */
function paydaysByDate(earners, start, end) {
  const groups = new Map();
  for (const earner of earners) {
    for (const day of paydaysBetween(earner.anchor_payday, earner.weeks_per_period, start, end)) {
      if (!groups.has(day)) groups.set(day, []);
      groups.get(day).push(earner.name);
    }
  }
  return groups;
}

/** Month view of every bill due date, with paydays, overdue flags and a panel for each day's details. */
export default function CalendarPage() {
  const [params, setParams] = useSearchParams();
  const today = toISODate(new Date());
  const month = isMonthKey(params.get("month")) ? params.get("month") : monthKeyOf(today);
  const selected = /^\d{4}-\d{2}-\d{2}$/.test(params.get("day") ?? "") ? params.get("day") : null;
  const { start, end } = gridRange(month);
  const weeks = useMemo(() => monthGrid(month), [month]);
  const dayRefs = useRef(new Map());

  const occurrences = useOccurrences(start, end);
  const earners = useEarners();
  const billsByDate = useMemo(() => byDate(occurrences.data ?? [], today), [occurrences.data, today]);
  const paydays = useMemo(() => paydaysByDate(earners.data ?? [], start, end), [earners.data, start, end]);

  const monthBills = (occurrences.data ?? []).filter((bill) => monthKeyOf(bill.due_date) === month);
  const stillToPay = monthBills.filter((bill) => bill.status === "unpaid");
  const overdueCount = (occurrences.data ?? []).filter(
    (bill) => billState(bill.status, bill.due_date, today) === "overdue"
  ).length;

  const goToMonth = (key) => setParams({ month: key });
  const openDay = (iso) => setParams({ month, day: iso });
  const closeDay = useCallback(() => {
    const returnTo = selected;
    setParams({ month });
    requestAnimationFrame(() => dayRefs.current.get(returnTo)?.focus());
  }, [month, selected, setParams]);

  return (
    <section className={selected ? "calendar-page has-panel" : "calendar-page"}>
      <div className="calendar-main">
        <header className="calendar-toolbar">
          <h1>{monthLabel(month)}</h1>
          <div className="calendar-nav">
            <button type="button" onClick={() => goToMonth(shiftMonth(month, -1))} aria-label="Previous month">
              ‹
            </button>
            <button type="button" onClick={() => goToMonth(monthKeyOf(today))} disabled={month === monthKeyOf(today)}>
              Today
            </button>
            <button type="button" onClick={() => goToMonth(shiftMonth(month, 1))} aria-label="Next month">
              ›
            </button>
          </div>
        </header>

        {occurrences.isSuccess && (
          <dl className="month-stats">
            <div>
              <dt>Due this month</dt>
              <dd>{formatMoney(sumMoney(monthBills.map((bill) => bill.amount)))}</dd>
            </div>
            <div>
              <dt>Still unpaid</dt>
              <dd>{formatMoney(sumMoney(stillToPay.map((bill) => bill.amount)))}</dd>
            </div>
            {overdueCount > 0 && (
              <div className="stat-overdue">
                <dt>Overdue</dt>
                <dd>
                  {overdueCount} {overdueCount === 1 ? "bill" : "bills"}
                </dd>
              </div>
            )}
          </dl>
        )}

        {occurrences.isPending && <p className="muted">Loading bills…</p>}
        {occurrences.isError && (
          <div className="form-error" role="alert">
            <p>Couldn't load bills: {occurrences.error.message}</p>
            <button type="button" onClick={() => occurrences.refetch()}>
              Try again
            </button>
          </div>
        )}
        {occurrences.isSuccess && monthBills.length === 0 && (
          <p className="muted">No bills due this month.</p>
        )}

        <table className="month-grid" aria-label={`Bills for ${monthLabel(month)}`}>
          <thead>
            <tr>
              {WEEKDAYS.map((day) => (
                <th key={day} scope="col">
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {weeks.map((week) => (
              <tr key={week[0].iso}>
                {week.map((cell) => (
                  <td key={cell.iso} className={cell.iso === selected ? "is-selected" : undefined}>
                    <DayCell
                      ref={(node) => dayRefs.current.set(cell.iso, node)}
                      iso={cell.iso}
                      inMonth={cell.inMonth}
                      bills={billsByDate.get(cell.iso) ?? []}
                      paidPeople={paydays.get(cell.iso) ?? []}
                      today={today}
                      onOpen={openDay}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <DayPanel
          iso={selected}
          bills={billsByDate.get(selected) ?? []}
          paidPeople={paydays.get(selected) ?? []}
          today={today}
          onClose={closeDay}
        />
      )}
    </section>
  );
}
