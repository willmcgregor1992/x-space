import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

export function useEventStream(enabled = true): void {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!enabled) return;
    const source = new EventSource("/api/events/stream");
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { event?: string };
        if (payload.event === "launches_updated") {
          void queryClient.invalidateQueries();
        }
      } catch {
        /* ignore malformed events */
      }
    };
    return () => source.close();
  }, [enabled, queryClient]);
}
