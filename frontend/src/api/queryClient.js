import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./client.js";

/** Retry network and server failures twice, but never retry a request the server rejected. */
export function shouldRetry(failureCount, error) {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

/** Shared cache; refetching when the window regains focus picks up changes the other person made. */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        retry: shouldRetry,
      },
    },
  });
}
