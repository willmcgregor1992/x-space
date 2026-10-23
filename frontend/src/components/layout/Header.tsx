import { Radio } from "lucide-react";
import type { LiveStatus } from "@/types";
import type { ClockMode } from "@/utils/time";
import { formatDateTime } from "@/utils/time";

export function Header({
  now,
  clockMode,
  onClockMode,
  liveStatus,
}: {
  now: Date;
  clockMode: ClockMode;
  onClockMode: (mode: ClockMode) => void;
  liveStatus: LiveStatus | null | undefined;
}) {
  const live =
    liveStatus === "webcast_live" || liveStatus === "mission_active" || liveStatus === "launch_window";
  return (
    <header className="flex items-center justify-between gap-4 border-b border-white/10 px-4 py-3 md:px-6">
      <div>
        <p className="label">SpaceX</p>
        <h1 className="font-cond text-xl font-medium tracking-[0.14em] md:text-2xl">
          MISSION CONTROL
        </h1>
      </div>
      <div className="flex items-center gap-4">
        <div
          className="flex items-center gap-2"
          aria-live="polite"
          aria-label={live ? "Mission live" : "No live launch"}
        >
          <Radio
            className={`h-4 w-4 ${live ? "text-ember animate-pulse" : "text-mist"}`}
            aria-hidden
          />
          <span className="label text-[0.62rem]">
            {live ? liveStatus?.replace("_", " ") : "standby"}
          </span>
        </div>
        <div className="text-right">
          <p className="label">{clockMode}</p>
          <p className="font-mono text-sm tabular">{formatDateTime(now, clockMode)}</p>
        </div>
        <div className="flex border border-white/10">
          {(["LOCAL", "UTC"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`focus-ring px-2 py-1 font-cond text-[0.65rem] tracking-label ${
                clockMode === mode ? "bg-white/10 text-paper" : "text-mist"
              }`}
              onClick={() => onClockMode(mode)}
              aria-pressed={clockMode === mode}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
