export type ClockMode = "LOCAL" | "UTC";

export function parseIso(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatHms(totalSeconds: number): string {
  const seconds = Math.abs(Math.trunc(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  if (hours > 0) return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
  return `${pad(minutes)}:${pad(secs)}`;
}

export function formatClock(prefix: string, seconds: number | null, fallback: string): string {
  if (seconds === null) return fallback;
  if (prefix === "WINDOW") return fallback;
  const sign = seconds < 0 ? "T−" : "T+";
  return `${sign} ${formatHms(seconds)}`;
}

export function localTPlus(launch: {
  launch_time_start: string | null;
  is_exact_time: boolean;
  is_window: boolean;
  tzero_paused: boolean;
  tzero_hold_seconds: number | null;
}, now: Date): number | null {
  if (launch.tzero_paused && launch.tzero_hold_seconds != null) {
    return -launch.tzero_hold_seconds;
  }
  if (launch.is_window && !launch.is_exact_time) return null;
  const start = parseIso(launch.launch_time_start);
  if (!start) return null;
  return Math.round((now.getTime() - start.getTime()) / 1000);
}

export function formatDateTime(value: string | Date | null, mode: ClockMode): string {
  const date = typeof value === "string" ? parseIso(value) : value;
  if (!date) return "—";
  const opts: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
    timeZone: mode === "UTC" ? "UTC" : undefined,
  };
  const formatted = new Intl.DateTimeFormat("en-GB", opts).format(date);
  return mode === "UTC" ? `${formatted} UTC` : formatted;
}

export function formatWindow(
  start: string | null,
  end: string | null,
  mode: ClockMode,
): string {
  const a = parseIso(start);
  const b = parseIso(end);
  if (!a && !b) return "TBD";
  if (a && b && a.getTime() !== b.getTime()) {
    const opts: Intl.DateTimeFormatOptions = {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
      timeZone: mode === "UTC" ? "UTC" : undefined,
    };
    const day: Intl.DateTimeFormatOptions = {
      month: "short",
      day: "2-digit",
      timeZone: mode === "UTC" ? "UTC" : undefined,
    };
    const left = new Intl.DateTimeFormat("en-GB", opts).format(a);
    const right = new Intl.DateTimeFormat("en-GB", opts).format(b);
    const date = new Intl.DateTimeFormat("en-GB", day).format(a);
    return `${date}  ${left}–${right} ${mode === "UTC" ? "UTC" : ""}`.trim();
  }
  return formatDateTime(a, mode);
}

export function minutesAgo(from: string | null, now: Date): number | null {
  const then = parseIso(from);
  if (!then) return null;
  return Math.max(0, Math.round((now.getTime() - then.getTime()) / 60000));
}

export function parseSimulate(raw: string | null): number | null {
  if (!raw) return null;
  const token = raw.trim().toLowerCase();
  const named: Record<string, number> = {
    t0: 0,
    "tplus-0": 0,
    "tminus-600": -600,
    "tminus-30": -30,
    "tplus-60": 60,
    "tplus-180": 180,
    "tplus-480": 480,
    "tplus-3600": 3600,
  };
  if (token in named) return named[token];
  const plus = token.match(/^tplus-(\d+)$/);
  if (plus) return Number(plus[1]);
  const minus = token.match(/^tminus-(\d+)$/);
  if (minus) return -Number(minus[1]);
  return null;
}

export function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}
