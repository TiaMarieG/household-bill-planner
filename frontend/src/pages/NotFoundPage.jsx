import { Link } from "react-router";

/** Shown for any address that doesn't match a page. */
export default function NotFoundPage() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        <Link to="/">Back to the calendar</Link>
      </p>
    </section>
  );
}
