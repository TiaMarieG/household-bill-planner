import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockApi, renderApp } from "../test/render.jsx";

const occurrence = (bill_id, name, due_date, amount, status = "unpaid", amount_overridden = false) => ({
  bill_id,
  name,
  due_date,
  amount,
  status,
  amount_overridden,
});

function novemberBills() {
  return [
    occurrence(1, "Rent", "2026-11-01", "1450.00", "paid_cleared"),
    occurrence(2, "Car payment", "2026-11-01", "389.12", "paid_cleared"),
    occurrence(3, "Internet", "2026-11-01", "79.99", "paid_pending"),
    occurrence(4, "Phone plan", "2026-11-01", "85.00", "unpaid", true),
    occurrence(5, "Streaming", "2026-11-01", "22.99", "paid_cleared"),
    occurrence(6, "Insurance", "2026-11-01", "18.50", "paid_cleared"),
    occurrence(7, "Electric", "2026-11-12", "96.40"),
  ];
}

const ALEX = { id: 1, name: "Alex", anchor_payday: "2026-11-06", weeks_per_period: 1 };

function setup({ path = "/?month=2026-11", bills = novemberBills(), occurrenceStatus = 200, routes = {} } = {}) {
  const state = { bills };
  const calls = mockApi({
    "/health": { body: { status: "ok" } },
    "/earners": { body: [ALEX] },
    "GET /occurrences": () => ({ status: occurrenceStatus, body: state.bills }),
    ...routes,
  });
  renderApp(path);
  return { calls, state };
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 9, 10, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

const dayButton = (date) => screen.getByRole("button", { name: new RegExp(`^${date}(:|$)`) });

describe("month grid", () => {
  it("requests every visible day, including spill-over days", async () => {
    const { calls } = setup();

    await screen.findByText("Electric");

    expect(calls.find((call) => call.path === "/occurrences").query).toEqual({
      start: "2026-11-01",
      end: "2026-12-05",
    });
  });

  it("shows month totals and the overdue count", async () => {
    setup();

    expect(await screen.findByText("$2,142.00")).toBeInTheDocument();
    expect(screen.getByText("$181.40")).toBeInTheDocument();
    expect(screen.getByText("1 bill")).toBeInTheDocument();
  });

  it("shows the three most urgent bills on a crowded day, then +N more", async () => {
    setup();

    await screen.findByText("Electric");
    const cell = dayButton("Sunday, November 1");

    const visible = within(cell).getAllByText(/./, { selector: ".day-bill-name" }).map((el) => el.textContent);
    expect(visible).toEqual(["Phone plan", "Internet", "Car payment"]);
    expect(within(cell).getByText("+3 more")).toBeInTheDocument();
  });

  it("describes each day for screen readers", async () => {
    setup();

    await screen.findByText("Electric");

    expect(dayButton("Sunday, November 1")).toHaveAccessibleName(
      "Sunday, November 1: 6 bills, $2,045.60, 1 overdue"
    );
    expect(dayButton("Monday, November 9")).toHaveAccessibleName("Monday, November 9: today");
  });

  it("marks paydays", async () => {
    setup();

    await screen.findByText("Electric");

    expect(dayButton("Friday, November 6")).toHaveAccessibleName("Friday, November 6: payday for Alex");
  });

  it("moves between months and keeps the month in the address", async () => {
    const { calls } = setup();
    await screen.findByText("Electric");

    await userEvent.click(screen.getByRole("button", { name: "Next month" }));

    expect(screen.getByRole("heading", { level: 1, name: "December 2026" })).toBeInTheDocument();
    await waitFor(() => expect(calls.at(-1).query).toEqual({ start: "2026-11-29", end: "2027-01-02" }));
    expect(screen.getByRole("button", { name: "Today" })).toBeEnabled();
  });

  it("falls back to the current month for an invalid month in the address", () => {
    setup({ path: "/?month=2026-13" });

    expect(screen.getByRole("heading", { level: 1, name: "November 2026" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Today" })).toBeDisabled();
  });

  it("shows an error with a retry button when bills can't load", async () => {
    setup({ occurrenceStatus: 500 });

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't load bills");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("says so when a month has no bills", async () => {
    setup({ bills: [] });

    expect(await screen.findByText("No bills due this month.")).toBeInTheDocument();
  });
});

describe("day panel", () => {
  async function openFirst() {
    await screen.findByText("Electric");
    await userEvent.click(dayButton("Sunday, November 1"));
    return screen.getByRole("dialog", { name: "Sunday, November 1" });
  }

  it("lists every bill for the day with the day's total", async () => {
    setup();

    const panel = await openFirst();

    const names = within(panel).getAllByText(/./, { selector: ".panel-bill-name" }).map((el) => el.textContent);
    expect(names).toEqual(["Phone plan", "Internet", "Car payment", "Insurance", "Rent", "Streaming"]);
    expect(within(panel).getByText("$2,045.60")).toBeInTheDocument();
    expect(within(panel).getByText("Overdue")).toBeInTheDocument();
    expect(within(panel).getByText("Paid – not withdrawn", { selector: ".state-badge" })).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { name: "Sunday, November 1" })).toHaveFocus();
  });

  it("saves a status change and keeps a one-off amount", async () => {
    const { calls, state } = setup({
      routes: {
        "PUT /bills/4/occurrences/2026-11-01": ({ body }) => {
          state.bills = state.bills.map((bill) => (bill.bill_id === 4 ? { ...bill, status: body.status } : bill));
          return { body: state.bills.find((bill) => bill.bill_id === 4) };
        },
      },
    });
    const panel = await openFirst();

    const phone = within(panel).getByRole("group", { name: "Status of Phone plan" });
    await userEvent.click(within(phone).getByRole("radio", { name: "Paid – not withdrawn" }));

    const put = calls.find((call) => call.method === "PUT");
    expect(put.path).toBe("/bills/4/occurrences/2026-11-01");
    expect(put.body).toEqual({ status: "paid_pending", amount_override: "85.00" });
    await waitFor(() => expect(within(phone).getByRole("radio", { name: "Paid – not withdrawn" })).toBeChecked());
  });

  it("sends no override for a bill at its normal amount", async () => {
    const { calls } = setup({ routes: { "PUT /bills/1/occurrences/2026-11-01": { body: {} } } });
    const panel = await openFirst();

    const rent = within(panel).getByRole("group", { name: "Status of Rent" });
    await userEvent.click(within(rent).getByRole("radio", { name: "Unpaid" }));

    expect(calls.find((call) => call.method === "PUT").body).toEqual({ status: "unpaid", amount_override: null });
  });

  it("shows an error when a status change fails", async () => {
    setup({ routes: { "PUT /bills/1/occurrences/2026-11-01": { status: 500, body: { detail: "Database down" } } } });
    const panel = await openFirst();

    const rent = within(panel).getByRole("group", { name: "Status of Rent" });
    await userEvent.click(within(rent).getByRole("radio", { name: "Unpaid" }));

    expect(await within(panel).findByRole("alert")).toHaveTextContent("Couldn't save: Database down");
  });

  it("closes with Escape and returns focus to the day", async () => {
    setup();
    await openFirst();

    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(dayButton("Sunday, November 1")).toHaveFocus());
  });

  it("opens from the address so a refresh keeps it open", async () => {
    setup({ path: "/?month=2026-11&day=2026-11-12" });

    const panel = await screen.findByRole("dialog", { name: "Thursday, November 12" });

    expect(await within(panel).findByText("Electric")).toBeInTheDocument();
  });
});
