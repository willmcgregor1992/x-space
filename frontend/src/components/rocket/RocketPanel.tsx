import { Component, useEffect, type ReactNode } from "react";
import { motion } from "framer-motion";
import type { Launch, MissionState } from "@/types";
import { displayValue, localTPlus } from "@/utils/time";
import { ProvenanceHint } from "@/components/common/ProvenanceHint";
import { RocketModel, preloadRocket } from "@/components/rocket/RocketModel";
import { VehicleSilhouette } from "@/components/rocket/VehicleSilhouette";
import { stackConfig } from "@/components/rocket/stackState";

class ModelBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function RocketPanel({
  launch,
  state,
  now,
  reducedMotion,
}: {
  launch: Launch | null;
  state: MissionState | null;
  now: Date;
  reducedMotion: boolean;
}) {
  const tPlus = launch ? (localTPlus(launch, now) ?? state?.t_plus_seconds ?? null) : null;
  const config = stackConfig(launch?.vehicle, launch?.milestones ?? [], tPlus);
  useEffect(() => {
    if (launch) preloadRocket(config.kind);
  }, [launch, config.kind]);
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
      <ModelBoundary fallback={<VehicleSilhouette vehicle={launch.vehicle} />}>
        <RocketModel config={config} reducedMotion={reducedMotion} />
      </ModelBoundary>
      <p className="text-center font-cond text-sm tracking-[0.16em] text-ember/90">{config.caption.toUpperCase()}</p>
      <p className="text-center text-[0.65rem] text-mist">{config.note}</p>
      <Row label="Vehicle" value={launch.vehicle} />
      <Row label="Launch site" value={launch.launch_site} />
      <Row label="Landing" value={launch.landing_site ?? launch.landing_method} />
      <Row label="Booster" value={booster?.serial ?? null} />
      <Row label="Flight" value={booster?.flight_number ?? null} />
      <Row label="Mission type" value={launch.mission_type} />
      <Row label="Live status" value={state?.live_status?.replaceAll("_", " ") ?? "offline"} />
      {booster?.summary && <p className="text-xs leading-relaxed text-mist">{booster.summary}</p>}
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
