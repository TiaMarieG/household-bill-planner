import { createContext, useContext, useEffect, useMemo, useState } from "react";

export const THEME_STORAGE_KEY = "bill-planner-theme";
export const THEME_CHOICES = ["system", "light", "dark"];

const ThemeContext = createContext(null);
const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Read the saved choice, falling back to "system" when storage is empty, invalid or blocked. */
function readStoredChoice() {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return THEME_CHOICES.includes(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

/** Save the choice; failures (private browsing, blocked storage) only cost persistence. */
function storeChoice(choice) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    return;
  }
}

/** Whether the operating system currently prefers dark mode. */
function systemPrefersDark() {
  return window.matchMedia?.(DARK_QUERY).matches ?? false;
}

/** Provides the theme choice and applies the resolved light/dark theme to <html data-theme>. */
export function ThemeProvider({ children }) {
  const [choice, setChoice] = useState(readStoredChoice);
  const [prefersDark, setPrefersDark] = useState(systemPrefersDark);

  useEffect(() => {
    const media = window.matchMedia?.(DARK_QUERY);
    if (!media) return undefined;
    const onChange = (event) => setPrefersDark(event.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const resolved = choice === "system" ? (prefersDark ? "dark" : "light") : choice;

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
  }, [resolved]);

  const value = useMemo(
    () => ({
      choice,
      resolved,
      setChoice(next) {
        setChoice(next);
        storeChoice(next);
      },
    }),
    [choice, resolved]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/** Access the current theme choice, the resolved theme, and a setter. */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside ThemeProvider");
  return context;
}
