import { motion } from "framer-motion";
import type { Launch, MissionState } from "@/types";
import { displayValue } from "@/utils/time";
import { VehicleSilhouette } from "@/components/rocket/VehicleSilhouette";
import { ProvenanceHint } from "@/components/common/ProvenanceHint";

export function RocketPanel({ launch, state }: { launch: Launch | null; state: MissionState | null }) {
  if (!launch) {
    return (
      <aside className="panel p-4">
        <p className="label">Vehicle</p>
        <p className="text-sm text-mist">—</p>
      </aside>
    );
  }
  const booster = launch.booster_information;
  return (
    <motion.aside
      key={launch.id}
      initial={{ opacity: 0.4 }}
      animate={{ opacity: 1 }}
      className="panel flex flex-col gap-4 p-4"
    >
      <p className="label">Rocket / mission</p>
      <div className="flex justify-center py-2">
        <VehicleSilhouette vehicle={launch.vehicle} />
      </div>
      <Row label="Vehicle" value={launch.vehicle} />
      <Row label="Launch site" value={launch.launch_site} />
      <Row label="Landing" value={launch.landing_site ?? launch.landing_method} />
      <Row label="Booster" value={booster?.serial ?? null} />
      <Row label="Flight" value={booster?.flight_number ?? null} />
      <Row label="Mission type" value={launch.mission_type} />
      <Row label="Live status" value={state?.live_status?.replaceAll("_", " ") ?? "offline"} />
      {booster?.summary && (
        <p className="text-xs leading-relaxed text-mist">{booster.summary}</p>
      )}
      <ProvenanceHint provenance={launch.provenance.vehicle} />
      <p className="mt-auto text-[0.65rem] leading-relaxed text-mist">
        Fuel, velocity, altitude and engine state are omitted unless SpaceX publishes them.
      </p>
    </motion.aside>
  );
}

function Row({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-white/5 py-1.5">
      <span className="label">{label}</span>
      <span className="text-right text-sm">{displayValue(value)}</span>
    </div>
  );
}
