const MS_PER_DAY = 86_400_000;
export const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** Whole-day number for a "YYYY-MM-DD" date, immune to daylight-saving shifts. */
export function dayNumber(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return Date.UTC(year, month - 1, day) / MS_PER_DAY;
}

/** "YYYY-MM-DD" for a whole-day number from dayNumber. */
export function fromDayNumber(number) {
  return new Date(number * MS_PER_DAY).toISOString().slice(0, 10);
}

/** The date a given number of days after (or before, if negative) an ISO date. */
export function addDays(iso, days) {
  return fromDayNumber(dayNumber(iso) + days);
}

/** Day of the week for an ISO date: 0 = Sunday through 6 = Saturday. */
export function weekday(iso) {
  return (((dayNumber(iso) + 4) % 7) + 7) % 7;
}

/** True when the value is a valid "YYYY-MM" month key. */
export function isMonthKey(value) {
  return typeof value === "string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

/** The "YYYY-MM" month containing an ISO date. */
export function monthKeyOf(iso) {
  return iso.slice(0, 7);
}

/** Move a "YYYY-MM" month forward or back by a number of months. */
export function shiftMonth(key, delta) {
  const [year, month] = key.split("-").map(Number);
  const index = year * 12 + (month - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

/** Human label such as "November 2026". */
export function monthLabel(key) {
  const [year, month] = key.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

/** Weeks (Sunday to Saturday) covering a month, including spill-over days from neighbouring months. */
export function monthGrid(key) {
  const first = `${key}-01`;
  const last = addDays(`${shiftMonth(key, 1)}-01`, -1);
  const start = addDays(first, -weekday(first));
  const end = addDays(last, 6 - weekday(last));

  const weeks = [];
  for (let day = dayNumber(start); day <= dayNumber(end); day += 7) {
    weeks.push(
      Array.from({ length: 7 }, (_, offset) => {
        const iso = fromDayNumber(day + offset);
        return { iso, inMonth: monthKeyOf(iso) === key };
      })
    );
  }
  return weeks;
}

/** First and last ISO dates shown in a month's grid. */
export function gridRange(key) {
  const weeks = monthGrid(key);
  return { start: weeks[0][0].iso, end: weeks.at(-1)[6].iso };
}

/** Every payday on a cycle (anchor payday, repeating every N weeks) within start..end inclusive. */
export function paydaysBetween(anchorIso, weeksPerPeriod, startIso, endIso) {
  const period = 7 * weeksPerPeriod;
  const start = dayNumber(startIso);
  const offset = (((dayNumber(anchorIso) - start) % period) + period) % period;
  const paydays = [];
  for (let day = start + offset; day <= dayNumber(endIso); day += period) {
    paydays.push(fromDayNumber(day));
  }
  return paydays;
}

/** Display state for a bill on a given day: paid, pending withdrawal, due, or overdue. */
export function billState(status, dueIso, todayIso) {
  if (status === "paid_cleared") return "cleared";
  if (status === "paid_pending") return "pending";
  return dueIso < todayIso ? "overdue" : "due";
}

export const STATE_LABELS = {
  cleared: "Paid – cleared",
  pending: "Paid – not withdrawn",
  due: "Due",
  overdue: "Overdue",
};

const STATE_ORDER = { overdue: 0, due: 1, pending: 2, cleared: 3 };

/** One day's bills, most urgent first (overdue, due, pending, paid), then by name. */
export function sortByUrgency(bills, todayIso) {
  return [...bills].sort(
    (a, b) =>
      STATE_ORDER[billState(a.status, a.due_date, todayIso)] - STATE_ORDER[billState(b.status, b.due_date, todayIso)] ||
      a.name.localeCompare(b.name)
  );
}
