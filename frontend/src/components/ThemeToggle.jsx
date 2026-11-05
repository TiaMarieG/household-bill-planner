import { THEME_CHOICES, useTheme } from "../theme/ThemeProvider.jsx";

const LABELS = { system: "System", light: "Light", dark: "Dark" };

/** Segmented control for choosing System, Light or Dark theme. */
export default function ThemeToggle() {
  const { choice, setChoice } = useTheme();

  return (
    <div className="theme-toggle" role="radiogroup" aria-label="Theme">
      {THEME_CHOICES.map((option) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={choice === option}
          className={choice === option ? "is-selected" : undefined}
          onClick={() => setChoice(option)}
        >
          {LABELS[option]}
        </button>
      ))}
    </div>
  );
}
