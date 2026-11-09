/** Convert an API money string such as "-42.5" to an exact whole number of cents. */
export function toCents(amount) {
  const match = /^(-)?(\d+)(?:\.(\d{1,2}))?$/.exec(String(amount).trim());
  if (!match) throw new Error(`Not a money amount: ${amount}`);
  const [, sign, whole, fraction = ""] = match;
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  return sign ? -cents : cents;
}

/** Add money strings exactly (in whole cents) and return the total as a "1234.56" string, for display totals. */
export function sumMoney(amounts) {
  const cents = amounts.reduce((total, amount) => total + toCents(amount), 0);
  const sign = cents < 0 ? "-" : "";
  const absolute = Math.abs(cents);
  return `${sign}${Math.floor(absolute / 100)}.${String(absolute % 100).padStart(2, "0")}`;
}
