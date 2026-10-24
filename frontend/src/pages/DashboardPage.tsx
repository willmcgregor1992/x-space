import { useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/Header";
import { LaunchSelector } from "@/components/launches/LaunchSelector";
import { MissionInfoPanel } from "@/components/mission/MissionInfoPanel";
import { RocketPanel } from "@/components/rocket/RocketPanel";
import { StatusBanners } from "@/components/status/Banners";
import { MissionTimeline } from "@/components/timeline/MissionTimeline";
import { JourneyVisualizer } from "@/components/visualizer/JourneyVisualizer";
import { useEventStream } from "@/hooks/useEventStream";
import { useMissionData } from "@/hooks/useMissionData";
import { useSyncedNow } from "@/hooks/useSyncedNow";
import { usePreferences } from "@/stores/preferences";
import type { Launch, SelectorTab } from "@/types";

export function DashboardPage() {
  const simulate = new URLSearchParams(window.location.search).get("simulate");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<SelectorTab>("NEXT");
  const [timeFlash, setTimeFlash] = useState(false);
  const reducedMotion = useReducedMotion() ?? false;
  const clockMode = usePreferences((s) => s.clockMode);
  const setClockMode = usePreferences((s) => s.setClockMode);
  const data = useMissionData(selectedId, simulate);
  useEventStream(true);
  const now = useSyncedNow(data.meta?.server_time);

  useEffect(() => {
    if (!selectedId && data.currentId) setSelectedId(data.currentId);
  }, [data.currentId, selectedId]);

  const selectedLaunch = useMemo(() => {
    const pools = [...data.live, ...data.upcoming, ...data.recent, data.launch].filter(Boolean) as Launch[];
    return pools.find((item) => item.id === selectedId) ?? data.launch;
  }, [data.launch, data.live, data.upcoming, data.recent, selectedId]);

  useEffect(() => {
    if (!selectedLaunch?.launch_time_start) return;
    setTimeFlash(true);
    const id = window.setTimeout(() => setTimeFlash(false), 1600);
    return () => window.clearTimeout(id);
  }, [selectedLaunch?.launch_time_start]);

  const list =
    tab === "LIVE" ? data.live : tab === "RECENT" ? data.recent : tab === "NEXT" ? data.upcoming.slice(0, 1) : data.upcoming;

  return (
    <div className="min-h-screen">
      <Header
        now={now}
        clockMode={clockMode}
        onClockMode={setClockMode}
        liveStatus={data.state?.live_status}
      />
      <main className="mx-auto grid max-w-[1600px] gap-3 p-3 md:p-4">
        <StatusBanners
          banner={data.meta?.banner}
          simulation={data.simulation}
          launchUpdated={timeFlash}
        />
        <ApiErrorBanner show={data.isError} />
        <div className="grid gap-3 lg:grid-cols-[280px_minmax(0,1fr)_280px] lg:items-stretch">
          <div className="order-1">
            <MissionInfoPanel launch={selectedLaunch} state={data.state} now={now} clockMode={clockMode} />
          </div>
          <div className="order-2 min-h-[360px]">
            <JourneyVisualizer
              launch={selectedLaunch}
              state={data.state}
              now={now}
              reducedMotion={reducedMotion}
            />
          </div>
          <div className="order-3">
            <RocketPanel
              launch={selectedLaunch}
              state={data.state}
              now={now}
              reducedMotion={reducedMotion}
            />
          </div>
        </div>
        <div className="order-4">
          <MissionTimeline launch={selectedLaunch} state={data.state} now={now} />
        </div>
        <div className="order-5">
        <LaunchSelector
          tab={tab}
          onTab={setTab}
          launches={list}
          selectedId={selectedLaunch?.id ?? null}
          onSelect={setSelectedId}
          clockMode={clockMode}
          now={now}
        />
        </div>
      </main>
    </div>
  );
}

export function ApiErrorBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div className="panel p-3">
      <p className="label text-alert">Source unavailable</p>
      <p className="text-sm text-mist">
        The control API could not be reached. Cached mission data will be used when the backend still has a last good snapshot.
      </p>
    </div>
  );
}
