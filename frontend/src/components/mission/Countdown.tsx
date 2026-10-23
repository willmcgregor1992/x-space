import { localTPlus } from "@/utils/time";
import { formatHms } from "@/utils/time";
import type { Launch, MissionState } from "@/types";

export function Countdown({
  launch,
  state,
  now,
}: {
  launch: Launch;
  state: MissionState | null;
  now: Date;
}) {
  const tPlus = localTPlus(launch, now);
  const windowOnly = launch.is_window && !launch.is_exact_time;
  let prefix = state?.clock_prefix ?? "";
  let label = state?.clock_label ?? "TBD";
  if (windowOnly && tPlus === null) {
    prefix = now >= new Date(launch.launch_time_start ?? 0) ? "WINDOW" : "WINDOW";
    const start = launch.launch_time_start ? new Date(launch.launch_time_start) : null;
    if (start && now < start) {
      prefix = "OPENS";
      label = formatHms((start.getTime() - now.getTime()) / 1000);
    } else {
      label = "OPEN";
    }
  } else if (tPlus != null) {
    prefix = tPlus < 0 ? "T−" : "T+";
    label = formatHms(tPlus);
  }

  return (
    <div aria-live="polite" aria-atomic="true">
      <p className="label">{windowOnly && tPlus === null ? "Launch window" : prefix === "T+" ? "Mission elapsed" : "Countdown"}</p>
      <p className="mt-1 font-mono text-4xl tabular tracking-tight md:text-5xl">
        <span className="text-mist">{prefix === "T−" || prefix === "T+" ? prefix : prefix}</span>{" "}
        {label}
      </p>
      {state?.hold && <p className="label mt-2 text-live">Hold</p>}
    </div>
  );
}
