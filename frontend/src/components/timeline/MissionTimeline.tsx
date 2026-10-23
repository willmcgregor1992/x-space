import { useState } from "react";
import type { Launch, Milestone, MissionState } from "@/types";
import { formatHms, localTPlus } from "@/utils/time";

export function MissionTimeline({
  launch,
  state,
  now,
}: {
  launch: Launch | null;
  state: MissionState | null;
  now: Date;
}) {
  const [selected, setSelected] = useState<Milestone | null>(null);
  if (!launch) {
    return (
      <section className="panel p-4">
        <p className="label">Mission timeline</p>
        <p className="text-sm text-mist">No timeline available.</p>
      </section>
    );
  }
  const items = launch.milestones.filter((item) => item.t_plus_seconds >= 0);
  const tPlus = localTPlus(launch, now);
  const last = items.at(-1)?.t_plus_seconds ?? 1;
  const progress = tPlus == null || tPlus < 0 ? 0 : Math.min(1, tPlus / last);
  const active = selected ?? state?.previous_milestone ?? items[0] ?? null;

  return (
    <section className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="label">Mission timeline</p>
        <p className="label text-ember/80">
          {state?.is_estimated ? "Estimated T+" : "Reported timeline"}
        </p>
      </div>
      <div className="relative overflow-x-auto pb-2">
        <div className="relative mx-4 mt-8 min-w-[640px]">
          <div className="absolute left-0 right-0 top-2 h-px bg-white/15" />
          <div
            className="absolute left-0 top-2 h-px bg-ember/80 transition-[width] duration-700"
            style={{ width: `${progress * 100}%` }}
          />
          <ol className="relative flex justify-between">
            {items.map((item) => {
              const done = tPlus != null && tPlus >= item.t_plus_seconds;
              const current = state?.previous_milestone?.key === item.key;
              return (
                <li key={item.key} className="flex flex-col items-center">
                  <button
                    type="button"
                    className="focus-ring flex flex-col items-center gap-2"
                    onClick={() => setSelected(item)}
                    aria-pressed={active?.key === item.key}
                    aria-label={`${item.name} at T+ ${formatHms(item.t_plus_seconds)}`}
                  >
                    <span
                      className={`block h-2.5 w-2.5 rounded-full border ${
                        current
                          ? "border-ember bg-ember shadow-[0_0_8px_#d4783a]"
                          : done
                            ? "border-paper bg-paper"
                            : "border-white/30 bg-ink"
                      }`}
                    />
                    <span className="label text-center text-[0.58rem] text-paper/80">{item.name}</span>
                    <span className="font-mono text-[0.65rem] tabular text-mist">
                      {formatHms(item.t_plus_seconds)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
      {active && (
        <div className="mt-4 border-t border-white/10 pt-3">
          <p className="font-cond tracking-[0.12em]">{active.name.toUpperCase()}</p>
          <p className="font-mono text-sm tabular">T+ {formatHms(active.t_plus_seconds)}</p>
          <p className="mt-1 text-sm text-mist">{active.description || "—"}</p>
          <p className="label mt-2">
            {active.is_estimated ? "Estimated from mission profile / SpaceX approximate timeline" : "Authoritative"}
          </p>
        </div>
      )}
    </section>
  );
}
