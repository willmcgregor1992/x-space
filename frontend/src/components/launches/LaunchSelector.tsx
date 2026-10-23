import type { Launch, SelectorTab } from "@/types";
import type { ClockMode } from "@/utils/time";
import { displayValue, formatDateTime, formatHms, localTPlus } from "@/utils/time";

export function LaunchSelector({
  tab,
  onTab,
  launches,
  selectedId,
  onSelect,
  clockMode,
  now,
}: {
  tab: SelectorTab;
  onTab: (tab: SelectorTab) => void;
  launches: Launch[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  clockMode: ClockMode;
  now: Date;
}) {
  const tabs: SelectorTab[] = ["LIVE", "NEXT", "UPCOMING", "RECENT"];
  return (
    <section className="panel p-3 md:p-4">
      <div role="tablist" aria-label="Launch lists" className="mb-3 flex gap-1">
        {tabs.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={tab === item}
            className={`focus-ring px-3 py-1 font-cond text-[0.7rem] tracking-label ${
              tab === item ? "bg-white/10 text-paper" : "text-mist"
            }`}
            onClick={() => onTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      {launches.length === 0 ? (
        <p className="px-1 py-6 text-sm text-mist">
          {tab === "LIVE" ? "No live mission." : "No missions in this list."}
        </p>
      ) : (
        <ul className="divide-y divide-white/5">
          {launches.map((launch) => {
            const tPlus = localTPlus(launch, now);
            return (
              <li key={launch.id}>
                <button
                  type="button"
                  onClick={() => onSelect(launch.id)}
                  className={`focus-ring flex w-full items-center justify-between gap-3 px-2 py-2.5 text-left ${
                    selectedId === launch.id ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                >
                  <span>
                    <span className="block font-cond tracking-[0.08em]">{launch.mission_name}</span>
                    <span className="text-xs text-mist">
                      {displayValue(launch.vehicle)} · {displayValue(launch.launch_site)}
                    </span>
                  </span>
                  <span className="text-right">
                    <span className="block font-mono text-xs tabular text-paper/90">
                      {tPlus == null
                        ? formatDateTime(launch.launch_time_start, clockMode)
                        : `${tPlus < 0 ? "T−" : "T+"} ${formatHms(tPlus)}`}
                    </span>
                    {launch.is_window && !launch.is_exact_time && (
                      <span className="label text-[0.55rem]">Window</span>
                    )}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
