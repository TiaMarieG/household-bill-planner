import { useEffect, useState } from "react";

/** Placeholder home screen that confirms the frontend can reach the API. */
export default function App() {
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <main className="app">
      <h1>Household Bill Planner</h1>
      <p>API status: {apiStatus}</p>
    </main>
  );
}
