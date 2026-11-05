import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

/** Install a controllable matchMedia, which jsdom does not provide. */
export function mockSystemTheme(prefersDark) {
  const listeners = new Set();
  const media = {
    matches: prefersDark,
    media: "(prefers-color-scheme: dark)",
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
  };
  window.matchMedia = vi.fn(() => media);
  return {
    change(nextPrefersDark) {
      media.matches = nextPrefersDark;
      listeners.forEach((listener) => listener({ matches: nextPrefersDark }));
    },
  };
}

beforeEach(() => {
  mockSystemTheme(false);
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

afterEach(() => {
  cleanup();
});
