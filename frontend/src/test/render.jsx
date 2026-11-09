import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import App from "../App.jsx";
import { ThemeProvider } from "../theme/ThemeProvider.jsx";

/** Render the whole app at a given address with a fresh cache and no retries. */
export function renderApp(path = "/") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

/**
 * Replace fetch with a fake API. Routes are keyed "METHOD /path" or just "/path" (any method);
 * a handler is a response object or a function receiving { query, body }. Returns the list of calls.
 */
export function mockApi(routes) {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    const parsed = new URL(String(url), "http://localhost");
    const path = parsed.pathname.replace(/^\/api/, "");
    const method = options.method ?? "GET";
    const call = {
      method,
      path,
      query: Object.fromEntries(parsed.searchParams),
      body: options.body ? JSON.parse(options.body) : undefined,
    };
    calls.push(call);

    const handler = routes[`${method} ${path}`] ?? routes[path];
    if (!handler) return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
    const { status = 200, body } = typeof handler === "function" ? handler(call) : handler;
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  };
  return calls;
}
