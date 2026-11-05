import { NavLink, Outlet } from "react-router";
import ApiStatus from "./ApiStatus.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

export const NAV_ITEMS = [
  { to: "/", label: "Calendar", end: true },
  { to: "/week", label: "Week" },
  { to: "/bills", label: "Bills" },
  { to: "/settings", label: "Settings" },
];

/** App shell: header with navigation and theme control, connection warning, and the current page. */
export default function Layout() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="app-header">
        <span className="app-title">Bill Planner</span>
        <nav aria-label="Main">
          <ul className="nav-list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <ThemeToggle />
      </header>
      <ApiStatus />
      <main id="main" className="app-main" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
