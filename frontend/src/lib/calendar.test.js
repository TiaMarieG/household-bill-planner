import { describe, expect, it } from "vitest";
import {
  addDays,
  billState,
  gridRange,
  isMonthKey,
  monthGrid,
  monthLabel,
  paydaysBetween,
  shiftMonth,
  sortByUrgency,
  weekday,
} from "./calendar.js";
import { sumMoney, toCents } from "./money.js";

describe("day arithmetic", () => {
  it("steps across the November daylight-saving change without skipping or repeating", () => {
    const days = Array.from({ length: 4 }, (_, i) => addDays("2026-10-31", i));

    expect(days).toEqual(["2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03"]);
  });

  it.each([
    ["2026-11-01", 0],
    ["2026-11-06", 5],
    ["2026-11-07", 6],
    ["1969-12-31", 3],
  ])("knows %s falls on weekday %i", (iso, expected) => {
    expect(weekday(iso)).toBe(expected);
  });
});

describe("months", () => {
  it.each([
    ["2026-11", 1, "2026-12"],
    ["2026-12", 1, "2027-01"],
    ["2026-01", -1, "2025-12"],
    ["2026-03", -14, "2025-01"],
  ])("shifts %s by %i to %s", (key, delta, expected) => {
    expect(shiftMonth(key, delta)).toBe(expected);
  });

  it.each([
    ["2026-11", true],
    ["2026-13", false],
    ["2026-1", false],
    [null, false],
  ])("validates month key %s", (value, expected) => {
    expect(isMonthKey(value)).toBe(expected);
  });

  it("labels a month", () => {
    expect(monthLabel("2026-11")).toBe("November 2026");
  });
});

describe("monthGrid", () => {
  it.each([
    ["2026-02", 4, "2026-02-01", "2026-02-28"],
    ["2026-11", 5, "2026-11-01", "2026-12-05"],
    ["2026-08", 6, "2026-07-26", "2026-09-05"],
  ])("lays out %s in %i Sunday-first weeks from %s to %s", (key, rows, first, last) => {
    const weeks = monthGrid(key);

    expect(weeks).toHaveLength(rows);
    expect(weeks.every((week) => week.length === 7)).toBe(true);
    expect(gridRange(key)).toEqual({ start: first, end: last });
    expect(weekday(weeks[0][0].iso)).toBe(0);
  });

  it("marks spill-over days as outside the month", () => {
    const cells = monthGrid("2026-08").flat();

    expect(cells.filter((cell) => cell.inMonth)).toHaveLength(31);
    expect(cells[0]).toEqual({ iso: "2026-07-26", inMonth: false });
  });
});

describe("paydaysBetween", () => {
  it("finds weekly Fridays", () => {
    expect(paydaysBetween("2026-11-06", 1, "2026-11-01", "2026-11-30")).toEqual([
      "2026-11-06",
      "2026-11-13",
      "2026-11-20",
      "2026-11-27",
    ]);
  });

  it("finds bi-weekly paydays before the anchor", () => {
    expect(paydaysBetween("2026-11-06", 2, "2026-10-01", "2026-10-31")).toEqual(["2026-10-09", "2026-10-23"]);
  });
});

describe("billState", () => {
  it.each([
    ["paid_cleared", "2026-11-01", "cleared"],
    ["paid_pending", "2026-11-01", "pending"],
    ["unpaid", "2026-11-08", "overdue"],
    ["unpaid", "2026-11-09", "due"],
    ["unpaid", "2026-11-20", "due"],
  ])("%s due %s is %s on Nov 9", (status, due, expected) => {
    expect(billState(status, due, "2026-11-09")).toBe(expected);
  });
});

describe("money", () => {
  it("adds without floating-point error", () => {
    expect(sumMoney(["0.10", "0.20"])).toBe("0.30");
    expect(0.1 + 0.2).not.toBe(0.3);
  });

  it.each([
    [[], "0.00"],
    [["1450.00", "389.12", "79.99"], "1919.11"],
    [["-42.17", "10"], "-32.17"],
    [["5.5"], "5.50"],
  ])("sums %j to %s", (amounts, expected) => {
    expect(sumMoney(amounts)).toBe(expected);
  });

  it("rejects text that is not money", () => {
    expect(() => toCents("12.345")).toThrow();
  });
});

describe("sortByUrgency", () => {
  it("puts overdue first, then due, pending and paid, then sorts by name", () => {
    const bill = (name, status, due_date = "2026-11-01") => ({ name, status, due_date });
    const bills = [
      bill("Rent", "paid_cleared"),
      bill("Internet", "paid_pending"),
      bill("Water", "unpaid", "2026-11-20"),
      bill("Gym", "unpaid"),
      bill("Car", "paid_cleared"),
      bill("Electric", "unpaid", "2026-11-20"),
    ];

    expect(sortByUrgency(bills, "2026-11-09").map((b) => b.name)).toEqual([
      "Gym",
      "Electric",
      "Water",
      "Internet",
      "Car",
      "Rent",
    ]);
  });
});
