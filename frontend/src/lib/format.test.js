import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, parseISODate, toISODate } from "./format.js";

describe("formatMoney", () => {
  it.each([
    ["1234.5", "$1,234.50"],
    ["0.00", "$0.00"],
    ["-42.17", "-$42.17"],
    ["1000000.00", "$1,000,000.00"],
  ])("formats %s as %s", (input, expected) => {
    expect(formatMoney(input)).toBe(expected);
  });

  it.each([null, undefined, "", "abc"])("returns an empty string for %s", (input) => {
    expect(formatMoney(input)).toBe("");
  });
});

describe("dates", () => {
  it("parses ISO dates as local calendar days, not UTC midnight", () => {
    const date = parseISODate("2026-11-06");

    expect([date.getFullYear(), date.getMonth(), date.getDate()]).toEqual([2026, 10, 6]);
  });

  it("round-trips through toISODate", () => {
    expect(toISODate(parseISODate("2026-01-31"))).toBe("2026-01-31");
  });

  it("formats a short readable date", () => {
    expect(formatDate("2026-11-06")).toBe("Fri, Nov 6");
  });
});
