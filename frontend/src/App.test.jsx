import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { mockSystemTheme } from "./test/setup.js";
import { mockApi, renderApp } from "./test/render.jsx";
import { THEME_STORAGE_KEY } from "./theme/ThemeProvider.jsx";

beforeEach(() => {
  mockApi({ "/health": { body: { status: "ok" } } });
});

describe("navigation", () => {
  it("shows every main page link and marks the current one", () => {
    renderApp("/week");

    const nav = screen.getByRole("navigation", { name: "Main" });
    for (const label of ["Calendar", "Week", "Bills", "Settings"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(nav.querySelector('[aria-current="page"]')).toHaveTextContent("Week");
  });

  it("moves between pages", async () => {
    renderApp("/");

    await userEvent.click(screen.getByRole("link", { name: "Bills" }));

    expect(screen.getByRole("heading", { level: 1, name: "Bills" })).toBeInTheDocument();
  });

  it("shows a not-found page for unknown addresses", () => {
    renderApp("/nope");

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("theme", () => {
  it("follows the system preference by default", () => {
    mockSystemTheme(true);

    renderApp();

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();
  });

  it("updates when the system preference changes", () => {
    const system = mockSystemTheme(false);
    renderApp();

    act(() => system.change(true));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("saves an explicit choice and ignores the system after that", async () => {
    const system = mockSystemTheme(false);
    renderApp();

    await userEvent.click(screen.getByRole("radio", { name: "Dark" }));
    act(() => system.change(false));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("restores the saved choice on the next visit", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    mockSystemTheme(true);

    renderApp();

    expect(document.documentElement.dataset.theme).toBe("light");
    expect(screen.getByRole("radio", { name: "Light" })).toBeChecked();
  });

  it("falls back to system when the saved value is invalid", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "purple");

    renderApp();

    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();
  });
});

describe("server status", () => {
  it("warns when the API cannot be reached", async () => {
    mockApi({ "/health": { status: 503, body: { detail: "down" } } });

    renderApp();

    expect(await screen.findByRole("alert")).toHaveTextContent("Can't reach the server");
  });

  it("stays quiet when the API is healthy", async () => {
    renderApp();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
