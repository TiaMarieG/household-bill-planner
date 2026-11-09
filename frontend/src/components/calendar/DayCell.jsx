import { billState } from "../../lib/calendar.js";
import { formatLongDate, formatMoney } from "../../lib/format.js";
import { sumMoney } from "../../lib/money.js";
import StatusIcon from "./StatusIcon.jsx";

export const MAX_VISIBLE_BILLS = 3;

/** Screen-reader summary of a day, e.g. "Sunday, November 1: 6 bills, $2,045.60, 1 overdue, payday for Alex". */
function describeDay(iso, bills, paidPeople, today) {
  const details = [];
  if (bills.length > 0) {
    details.push(`${bills.length} ${bills.length === 1 ? "bill" : "bills"}`);
    details.push(formatMoney(sumMoney(bills.map((bill) => bill.amount))));
    const overdue = bills.filter((bill) => billState(bill.status, bill.due_date, today) === "overdue").length;
    if (overdue > 0) details.push(`${overdue} overdue`);
  }
  if (paidPeople.length > 0) details.push(`payday for ${paidPeople.join(" and ")}`);
  if (iso === today) details.push("today");
  const date = formatLongDate(iso);
  return details.length > 0 ? `${date}: ${details.join(", ")}` : date;
}

/** One day in the month grid: date, payday marker, up to three bills, and a "+N more" count. */
export default function DayCell({ iso, inMonth, bills, paidPeople, today, onOpen, ref }) {
  const visible = bills.slice(0, MAX_VISIBLE_BILLS);
  const hidden = bills.length - visible.length;
  const hasOverdue = bills.some((bill) => billState(bill.status, bill.due_date, today) === "overdue");
  const classes = ["day-cell", !inMonth && "is-outside", iso === today && "is-today"].filter(Boolean).join(" ");

  return (
    <button
      ref={ref}
      type="button"
      className={classes}
      onClick={() => onOpen(iso)}
      aria-label={describeDay(iso, bills, paidPeople, today)}
    >
      <span className="day-header" aria-hidden="true">
        <span className="day-number">{Number(iso.slice(8))}</span>
        {paidPeople.length > 0 && <span className="payday-tag">Payday</span>}
      </span>
      {bills.length > 0 && (
        <span className={hasOverdue ? "day-count has-overdue" : "day-count"} aria-hidden="true">
          {bills.length}
        </span>
      )}
      <span className="day-bills" aria-hidden="true">
        {visible.map((bill) => {
          const state = billState(bill.status, bill.due_date, today);
          return (
            <span key={bill.bill_id} className={`day-bill bill-${state}`}>
              <StatusIcon state={state} />
              <span className="day-bill-name">{bill.name}</span>
            </span>
          );
        })}
        {hidden > 0 && <span className="day-more">+{hidden} more</span>}
      </span>
    </button>
  );
}
