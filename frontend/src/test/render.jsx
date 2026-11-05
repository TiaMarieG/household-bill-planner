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

/** Replace fetch with a function that answers each "/api/..." path from a map. */
export function mockApi(routes) {
  globalThis.fetch = async (url) => {
    const path = String(url).replace(/^\/api/, "");
    const handler = routes[path];
    if (!handler) return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
    const { status = 200, body } = typeof handler === "function" ? handler() : handler;
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  };
}
