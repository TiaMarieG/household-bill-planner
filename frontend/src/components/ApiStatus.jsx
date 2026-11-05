import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client.js";

/** Small indicator that turns red when the backend cannot be reached. */
export default function ApiStatus() {
  const { isError, isPending } = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => apiFetch("/health", { signal }),
    refetchInterval: 60_000,
  });

  if (isPending || !isError) return null;

  return (
    <p className="api-status" role="alert">
      Can't reach the server. Changes won't be saved until it's back.
    </p>
  );
}
