import type { Milestone } from "@/types";

export type VehicleKind = "falcon9" | "falcon_heavy" | "starship";
export type StagePose = "attached" | "separating" | "away";

export interface StackConfig {
  kind: VehicleKind;
  heightM: number;
  sideBoosters: StagePose;
  firstStage: StagePose;
  superHeavy: StagePose;
  fairing: "attached" | "jettisoned";
  caption: string;
  note: string;
}

export function resolveVehicleKind(vehicle: string | null | undefined): VehicleKind {
  const kind = (vehicle ?? "").toLowerCase();
  if (kind.includes("heavy")) return "falcon_heavy";
  if (kind.includes("starship")) return "starship";
  return "falcon9";
}

function reached(milestones: Milestone[], key: string, tPlus: number | null): boolean {
  if (tPlus == null) return false;
  const item = milestones.find((milestone) => milestone.key === key);
  return item != null && tPlus >= item.t_plus_seconds;
}

export function stackConfig(
  vehicle: string | null | undefined,
  milestones: Milestone[],
  tPlus: number | null,
): StackConfig {
  const kind = resolveVehicleKind(vehicle);
  if (kind === "falcon_heavy") {
    const sideBoosters: StagePose = reached(milestones, "boosters_land", tPlus)
      ? "away"
      : reached(milestones, "booster_sep", tPlus)
        ? "separating"
        : "attached";
    const firstStage: StagePose = reached(milestones, "stage_sep", tPlus) ? "separating" : "attached";
    const fairing = reached(milestones, "fairing", tPlus) ? "jettisoned" : "attached";
    return {
      kind,
      heightM: 70,
      sideBoosters,
      firstStage,
      superHeavy: "attached",
      fairing,
      caption: heavyCaption(sideBoosters, firstStage, fairing),
      note: "Estimated stack from the mission profile — not telemetry.",
    };
  }
  if (kind === "starship") {
    const superHeavy: StagePose = reached(milestones, "landing_burn", tPlus)
      ? "away"
      : reached(milestones, "hot_stage", tPlus)
        ? "separating"
        : "attached";
    return {
      kind,
      heightM: 124,
      sideBoosters: "attached",
      firstStage: "attached",
      superHeavy,
      fairing: "attached",
      caption:
        superHeavy === "away"
          ? "Super Heavy downrange"
          : superHeavy === "separating"
            ? "Hot-staging — booster falling away"
            : "Starship + Super Heavy stack",
      note: "Estimated stack from the mission profile — not telemetry.",
    };
  }
  const firstStage: StagePose = reached(milestones, "landing", tPlus)
    ? "away"
    : reached(milestones, "stage_sep", tPlus)
      ? "separating"
      : "attached";
  const fairing = reached(milestones, "fairing", tPlus) ? "jettisoned" : "attached";
  return {
    kind,
    heightM: 70,
    sideBoosters: "attached",
    firstStage,
    superHeavy: "attached",
    fairing,
    caption:
      firstStage === "away"
        ? "First stage downrange"
        : firstStage === "separating"
          ? "Stage sep — booster falling away"
          : fairing === "jettisoned"
            ? "Fairing jettisoned"
            : "Falcon 9 stack",
    note: "Estimated stack from the mission profile — not telemetry.",
  };
}

function heavyCaption(side: StagePose, core: StagePose, fairing: StackConfig["fairing"]): string {
  if (core === "separating") return "Core stage separating";
  if (side === "away") return "Side boosters downrange";
  if (side === "separating") return "Side boosters falling away";
  if (fairing === "jettisoned") return "Fairing jettisoned";
  return "Falcon Heavy stack";
}

export function poseOffset(
  pose: StagePose,
  axis: "left" | "right" | "down",
): [number, number, number] {
  const drop = pose === "away" ? 36 : pose === "separating" ? 14 : 0;
  const spread = pose === "away" ? 16 : pose === "separating" ? 7 : 0;
  if (axis === "left") return [-spread, -drop, 0];
  if (axis === "right") return [spread, -drop, 0];
  return [0, -drop, 0];
}
