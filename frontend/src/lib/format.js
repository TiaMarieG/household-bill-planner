const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

/** Format an API money string such as "1234.5" or "-42.17" as "$1,234.50" or "-$42.17" for display only. */
export function formatMoney(amount) {
  if (amount === null || amount === undefined || amount === "") return "";
  const value = Number(amount);
  return Number.isFinite(value) ? currency.format(value) : "";
}

/** Read a "YYYY-MM-DD" string as a local calendar date, never shifted by time zone. */
export function parseISODate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** Write a local Date as "YYYY-MM-DD" for the API. */
export function toISODate(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/** Short readable date such as "Fri, Nov 6". */
export function formatDate(isoDate) {
  return parseISODate(isoDate).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/** Long readable date such as "Sunday, November 1". */
export function formatLongDate(isoDate) {
  return parseISODate(isoDate).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}
