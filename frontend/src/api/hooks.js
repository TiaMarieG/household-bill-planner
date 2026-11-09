import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client.js";

/** Every bill due date between two ISO dates, with its status and amount. */
export function useOccurrences(start, end) {
  return useQuery({
    queryKey: ["occurrences", start, end],
    queryFn: ({ signal }) =>
      apiFetch(`/occurrences?${new URLSearchParams({ start, end })}`, { signal }),
  });
}

/** Active people and their pay schedules. */
export function useEarners() {
  return useQuery({
    queryKey: ["earners"],
    queryFn: ({ signal }) => apiFetch("/earners", { signal }),
  });
}

/** Change one due date's status, keeping any one-off amount it already has. */
export function useSetBillStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ occurrence, status }) =>
      apiFetch(`/bills/${occurrence.bill_id}/occurrences/${occurrence.due_date}`, {
        method: "PUT",
        body: {
          status,
          amount_override: occurrence.amount_overridden ? occurrence.amount : null,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["occurrences"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    },
  });
}
