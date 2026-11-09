const PATHS = {
  cleared: <path d="M3.5 8.5l3 3 6-7" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
  pending: (
    <>
      <circle cx="8" cy="8" r="6" fill="none" strokeWidth="1.75" />
      <path d="M8 4.5V8l2.5 1.5" fill="none" strokeWidth="1.75" strokeLinecap="round" />
    </>
  ),
  due: <circle cx="8" cy="8" r="5.5" fill="none" strokeWidth="1.75" />,
  overdue: (
    <>
      <circle cx="8" cy="8" r="7" stroke="none" fill="currentColor" />
      <path d="M8 4.25v4.5M8 11.25v.5" stroke="var(--surface)" strokeWidth="2" strokeLinecap="round" />
    </>
  ),
};

/** Small icon whose shape (check, clock, ring, filled alert) distinguishes each bill state without relying on color. */
export default function StatusIcon({ state }) {
  return (
    <svg
      className={`status-icon status-${state}`}
      viewBox="0 0 16 16"
      stroke="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[state]}
    </svg>
  );
}
