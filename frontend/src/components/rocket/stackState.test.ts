import { poseOffset, resolveVehicleKind, stackConfig } from "./stackState";
import type { Milestone } from "@/types";

function marks(...keys: string[]): Milestone[] {
  const times: Record<string, number> = {
    booster_sep: 147,
    boosters_land: 467,
    stage_sep: 149,
    fairing: 180,
    landing: 500,
    hot_stage: 159,
    landing_burn: 380,
  };
  return keys.map((key) => ({
    key,
    name: key,
    t_plus_seconds: times[key],
    description: key,
    phase: null,
    is_estimated: true,
    source: "mission_profile",
    visual_role: "ascent",
  }));
}

describe("stackConfig", () => {
  it("maps vehicle names", () => {
    expect(resolveVehicleKind("Falcon Heavy")).toBe("falcon_heavy");
    expect(resolveVehicleKind("Starship")).toBe("starship");
    expect(resolveVehicleKind("Falcon 9")).toBe("falcon9");
  });

  it("keeps the stack together before T0", () => {
    const config = stackConfig("Falcon 9", marks("stage_sep", "fairing"), null);
    expect(config.firstStage).toBe("attached");
    expect(config.fairing).toBe("attached");
    expect(config.caption).toMatch(/Falcon 9 stack/i);
  });

  it("drops the Falcon 9 first stage after stage sep", () => {
    const config = stackConfig("Falcon 9", marks("stage_sep", "fairing", "landing"), 180);
    expect(config.firstStage).toBe("separating");
    expect(config.fairing).toBe("jettisoned");
    expect(config.caption).toMatch(/falling away/i);
  });

  it("separates Falcon Heavy side boosters", () => {
    const config = stackConfig("Falcon Heavy", marks("booster_sep", "stage_sep", "boosters_land"), 148);
    expect(config.sideBoosters).toBe("separating");
    expect(config.firstStage).toBe("attached");
    expect(poseOffset("separating", "left")[0]).toBeLessThan(0);
    expect(poseOffset("separating", "right")[0]).toBeGreaterThan(0);
  });

  it("drops Super Heavy after hot-staging", () => {
    const config = stackConfig("Starship", marks("hot_stage", "landing_burn"), 200);
    expect(config.superHeavy).toBe("separating");
    expect(config.caption).toMatch(/booster falling away/i);
  });
});
