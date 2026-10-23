import type { Provenance } from "@/types";

const LABELS: Record<string, string> = {
  "spacex.com": "Official SpaceX data",
  mission_profile: "Estimated from mission profile",
  estimated: "Estimated journey position",
  cache: "Cached SpaceX data",
  simulation: "Simulation — not live telemetry",
};

export function ProvenanceHint({ provenance }: { provenance?: Provenance | null }) {
  if (!provenance) return null;
  const label = LABELS[provenance.source] ?? provenance.source;
  return (
    <span className="label mt-1 block text-[0.58rem] text-mist/80" title={provenance.note ?? label}>
      {label}
    </span>
  );
}
