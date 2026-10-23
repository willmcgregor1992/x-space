import { describe, expect, it } from "vitest";
import { formatClock, formatHms, localTPlus, parseSimulate } from "./time";

describe("countdown math", () => {
  const exact = {
    launch_time_start: "2026-10-23T21:30:00.000Z",
    is_exact_time: true,
    is_window: false,
    tzero_paused: false,
    tzero_hold_seconds: null as number | null,
  };

  it("formats T− before launch", () => {
    const now = new Date("2026-10-23T20:06:18.000Z");
    const seconds = localTPlus(exact, now);
    expect(seconds).toBe(-5022);
    expect(formatClock("T−", seconds, "TBD")).toBe("T− 01:23:42");
  });

  it("transitions through T0 into T+", () => {
    expect(localTPlus(exact, new Date("2026-10-23T21:30:00.000Z"))).toBe(0);
    expect(formatClock("T+", 0, "TBD")).toBe("T+ 00:00");
    expect(localTPlus(exact, new Date("2026-10-23T21:31:43.000Z"))).toBe(103);
    expect(formatHms(103)).toBe("01:43");
  });

  it("does not invent T0 for a launch window", () => {
    const windowed = { ...exact, is_exact_time: false, is_window: true };
    expect(localTPlus(windowed, new Date("2026-10-23T22:00:00.000Z"))).toBeNull();
  });

  it("parses simulate query values", () => {
    expect(parseSimulate("tplus-180")).toBe(180);
    expect(parseSimulate("tminus-30")).toBe(-30);
    expect(parseSimulate("t0")).toBe(0);
  });
});
