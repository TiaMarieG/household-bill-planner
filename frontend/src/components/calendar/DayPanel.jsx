import { useEffect, useRef } from "react";
import { useSetBillStatus } from "../../api/hooks.js";
import { billState, STATE_LABELS } from "../../lib/calendar.js";
import { formatLongDate, formatMoney } from "../../lib/format.js";
import { sumMoney } from "../../lib/money.js";
import StatusControl from "./StatusControl.jsx";
import StatusIcon from "./StatusIcon.jsx";

/** Side panel listing every bill due on one day, with its total and a status control for each bill. */
export default function DayPanel({ iso, bills, paidPeople, today, onClose }) {
  const headingRef = useRef(null);
  const setStatus = useSetBillStatus();
  const headingId = `day-panel-${iso}`;

  useEffect(() => {
    headingRef.current?.focus();
  }, [iso]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <aside className="day-panel" role="dialog" aria-labelledby={headingId}>
      <header className="day-panel-header">
        <h2 id={headingId} ref={headingRef} tabIndex={-1}>
          {formatLongDate(iso)}
        </h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close day details">
          ×
        </button>
      </header>

      {paidPeople.length > 0 && <p className="payday-note">Payday for {paidPeople.join(" and ")}</p>}

      {bills.length === 0 ? (
        <p className="muted">No bills due.</p>
      ) : (
        <>
          <p className="day-panel-total">
            {bills.length} {bills.length === 1 ? "bill" : "bills"} ·{" "}
            <strong>{formatMoney(sumMoney(bills.map((bill) => bill.amount)))}</strong>
          </p>
          {setStatus.isError && (
            <p className="form-error" role="alert">
              Couldn't save: {setStatus.error.message}
            </p>
          )}
          <ul className="day-panel-list">
            {bills.map((bill) => {
              const state = billState(bill.status, bill.due_date, today);
              const saving = setStatus.isPending && setStatus.variables?.occurrence.bill_id === bill.bill_id;
              return (
                <li key={bill.bill_id} className={`panel-bill bill-${state}`}>
                  <div className="panel-bill-row">
                    <span className="panel-bill-name">{bill.name}</span>
                    <span className="panel-bill-amount">{formatMoney(bill.amount)}</span>
                  </div>
                  <div className="panel-bill-row">
                    <span className={`state-badge state-${state}`}>
                      <StatusIcon state={state} /> {STATE_LABELS[state]}
                    </span>
                    {bill.amount_overridden && <span className="muted small">One-off amount</span>}
                  </div>
                  <StatusControl
                    occurrence={bill}
                    disabled={saving}
                    onChange={(status) => setStatus.mutate({ occurrence: bill, status })}
                  />
                </li>
              );
            })}
          </ul>
        </>
      )}
    </aside>
  );
}
