import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "@/api/client";
import type { Launch, MissionState } from "@/types";
import { parseSimulate } from "@/utils/time";

export function useMissionData(selectedId: string | null, simulateRaw: string | null) {
  const simulate = parseSimulate(simulateRaw) != null ? simulateRaw : null;
  const currentQuery = useQuery({
    queryKey: ["current", simulate],
    queryFn: () => api.current(simulate),
    refetchInterval: 30_000,
  });
  const upcomingQuery = useQuery({
    queryKey: ["upcoming"],
    queryFn: api.upcoming,
    refetchInterval: 60_000,
  });
  const recentQuery = useQuery({
    queryKey: ["recent"],
    queryFn: api.recent,
    refetchInterval: 60_000,
  });
  const liveQuery = useQuery({
    queryKey: ["live"],
    queryFn: api.live,
    refetchInterval: 20_000,
  });
  const detailQuery = useQuery({
    queryKey: ["launch", selectedId, simulate],
    queryFn: () => api.launch(selectedId!, simulate),
    enabled: Boolean(selectedId) && selectedId !== currentQuery.data?.launch?.id,
    refetchInterval: 20_000,
  });

  const launch: Launch | null = useMemo(() => {
    if (detailQuery.data?.launch) return detailQuery.data.launch;
    return currentQuery.data?.launch ?? null;
  }, [currentQuery.data, detailQuery.data]);

  const state: MissionState | null = useMemo(() => {
    if (detailQuery.data?.state && detailQuery.data.launch?.id === launch?.id) {
      return detailQuery.data.state;
    }
    if (currentQuery.data && currentQuery.data.launch?.id === launch?.id) {
      return currentQuery.data.state;
    }
    return detailQuery.data?.state ?? currentQuery.data?.state ?? null;
  }, [currentQuery.data, detailQuery.data, launch?.id]);

  const meta = detailQuery.data?.meta ?? currentQuery.data?.meta ?? upcomingQuery.data?.meta ?? null;
  const error = currentQuery.error ?? upcomingQuery.error ?? recentQuery.error ?? liveQuery.error;

  return {
    launch,
    state,
    meta,
    upcoming: upcomingQuery.data?.launches ?? [],
    recent: recentQuery.data?.launches ?? [],
    live: liveQuery.data?.launches ?? [],
    currentId: currentQuery.data?.launch?.id ?? null,
    isLoading: currentQuery.isLoading && !currentQuery.data,
    isError: Boolean(error),
    error,
    simulation: Boolean(meta?.simulation || simulate),
    refetchAll: () => {
      void currentQuery.refetch();
      void upcomingQuery.refetch();
      void recentQuery.refetch();
      void liveQuery.refetch();
    },
  };
}
