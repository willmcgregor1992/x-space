import { ExternalLink } from "lucide-react";
import type { Launch, MissionState } from "@/types";
import type { ClockMode } from "@/utils/time";
import { displayValue, formatWindow, minutesAgo } from "@/utils/time";
import { Countdown } from "@/components/mission/Countdown";
import { ProvenanceHint } from "@/components/common/ProvenanceHint";

export function MissionInfoPanel({
  launch,
  state,
  now,
  clockMode,
}: {
  launch: Launch | null;
  state: MissionState | null;
  now: Date;
  clockMode: ClockMode;
}) {
  if (!launch) {
    return (
      <aside className="panel flex flex-col gap-4 p-4">
        <p className="label">Next launch</p>
        <p className="text-sm text-mist">No upcoming launch found in cached SpaceX data.</p>
      </aside>
    );
  }

  const stale = minutesAgo(launch.fetched_at, now);
  return (
    <aside className="panel flex flex-col gap-5 p-4">
      <div>
        <p className="label">
          {launch.cms_status === "in-progress" ? "On orbit" : "Next launch"}
        </p>
        <h2 className="mt-1 font-cond text-2xl tracking-[0.08em]">{launch.mission_name}</h2>
        <p className="text-sm text-mist">{displayValue(launch.vehicle)}</p>
      </div>
      <Countdown launch={launch} state={state} now={now} />
      {launch.is_window && !launch.is_exact_time && (
        <div>
          <p className="label">Launch window</p>
          <p className="font-mono text-sm tabular">
            {formatWindow(launch.launch_time_start, launch.launch_time_end, clockMode)}
          </p>
          <p className="mt-1 text-xs text-mist">Not a confirmed T−0.</p>
        </div>
      )}
      <Field label="Launch site" value={launch.launch_site} />
      <Field label="Landing" value={launch.landing_site ?? launch.landing_method} />
      <Field label="Mission type" value={launch.mission_type} />
      <div>
        <p className="label">Phase</p>
        <p>{state?.current_phase ?? "—"}</p>
        <ProvenanceHint
          provenance={{
            source: state?.is_estimated ? "estimated" : "spacex.com",
            confidence: state?.is_estimated ? "estimated" : "official",
            note: null,
          }}
        />
      </div>
      <div className="mt-auto flex flex-col gap-2 pt-2">
        <a
          className="focus-ring inline-flex items-center gap-2 text-sm text-paper/90 underline-offset-4 hover:underline"
          href={launch.official_url}
          target="_blank"
          rel="noreferrer"
        >
          Official mission page <ExternalLink className="h-3.5 w-3.5" />
        </a>
        {launch.webcast_url && (
          <a
            className="focus-ring inline-flex items-center gap-2 text-sm text-ember underline-offset-4 hover:underline"
            href={launch.webcast_url}
            target="_blank"
            rel="noreferrer"
          >
            Official live coverage <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        {stale != null && (
          <p className="text-[0.7rem] text-mist">Using data last updated {stale} minute{stale === 1 ? "" : "s"} ago</p>
        )}
      </div>
    </aside>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p className="text-sm">{value?.trim() ? value : "—"}</p>
    </div>
  );
}
