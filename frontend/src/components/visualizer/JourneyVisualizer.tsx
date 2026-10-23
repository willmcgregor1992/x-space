import { useMemo } from "react";
import type { Launch, Milestone, MissionState } from "@/types";
import { localTPlus } from "@/utils/time";

interface Point {
  x: number;
  y: number;
}

function cubic(p0: Point, p1: Point, p2: Point, p3: Point, t: number): Point {
  const u = 1 - t;
  return {
    x: u ** 3 * p0.x + 3 * u ** 2 * t * p1.x + 3 * u * t ** 2 * p2.x + t ** 3 * p3.x,
    y: u ** 3 * p0.y + 3 * u ** 2 * t * p1.y + 3 * u * t ** 2 * p2.y + t ** 3 * p3.y,
  };
}

function orbitPoint(cx: number, cy: number, rx: number, ry: number, t: number): Point {
  const angle = -Math.PI / 2 + t * Math.PI * 1.65;
  return { x: cx + Math.cos(angle) * rx, y: cy + Math.sin(angle) * ry };
}

export function JourneyVisualizer({
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
  const tPlus = launch ? localTPlus(launch, now) : null;
  const mode = state?.visualizer_mode ?? "prelaunch";
  const milestones = launch?.milestones.filter((m) => m.t_plus_seconds >= 0) ?? [];
  const lastT = milestones.at(-1)?.t_plus_seconds ?? 4200;
  const progress =
    tPlus == null || tPlus < 0 ? 0 : Math.min(1, Math.max(0, tPlus / lastT));

  const pad: Point = { x: 210, y: 520 };
  const c1: Point = { x: 280, y: 280 };
  const c2: Point = { x: 430, y: 140 };
  const orbit: Point = { x: 640, y: 210 };
  const earth = mode === "prelaunch" || mode === "ascent" ? { x: 210, y: 545, r: 78 } : { x: 500, y: 360, r: 92 };

  const vehicle = useMemo(() => {
    if (mode === "orbit" || mode === "iss" || mode === "complete") {
      return orbitPoint(earth.x, earth.y, 210, 128, Math.min(0.92, 0.12 + progress * 0.8));
    }
    if (mode === "starship") {
      const t = Math.min(1, progress * 1.1);
      if (t < 0.45) return cubic(pad, c1, c2, orbit, t / 0.45);
      return orbitPoint(500, 330, 230, 140, (t - 0.45) / 0.55);
    }
    const t = mode === "prelaunch" ? 0 : Math.min(1, progress / 0.22);
    return cubic(pad, c1, c2, orbit, t);
  }, [mode, progress, earth.x, earth.y, pad, c1, c2, orbit]);

  const ascentPath = `M ${pad.x} ${pad.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${orbit.x} ${orbit.y}`;
  const estimated = state?.is_estimated !== false;

  return (
    <section
      className="panel relative flex min-h-[340px] flex-1 flex-col overflow-hidden md:min-h-[520px]"
      aria-label="Mission journey visualizer"
    >
      <div className="flex items-start justify-between px-4 pt-3">
        <div>
          <p className="label">Schematic trajectory</p>
          <p className="font-cond text-lg tracking-[0.12em]">
            {launch?.mission_name ?? "NO MISSION"}
          </p>
        </div>
        <p className="label text-right text-ember/90">
          {estimated ? "Estimated position" : "Reported status"}
        </p>
      </div>
      <svg
        viewBox="0 0 1000 720"
        className="h-full w-full flex-1"
        role="img"
        aria-labelledby="viz-title viz-desc"
      >
        <title id="viz-title">{launch ? `${launch.mission_name} journey` : "Mission journey"}</title>
        <desc id="viz-desc">
          {state
            ? `${state.current_phase}. ${estimated ? "Position is estimated from the mission profile, not telemetry." : "Status reported by SpaceX."}`
            : "No mission selected."}
        </desc>
        <defs>
          <radialGradient id="earthGlow" cx="38%" cy="32%" r="70%">
            <stop offset="0%" stopColor="#9bb4c9" stopOpacity="0.55" />
            <stop offset="42%" stopColor="#243246" />
            <stop offset="100%" stopColor="#0b1018" />
          </radialGradient>
          <linearGradient id="pathGlow" x1="0" x2="1">
            <stop offset="0%" stopColor="#d4783a" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#8eb0cc" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {Array.from({ length: 8 }).map((_, i) => (
          <line
            key={`h-${i}`}
            x1="40"
            x2="960"
            y1={80 + i * 78}
            y2={80 + i * 78}
            stroke="rgba(232,236,245,0.045)"
          />
        ))}
        {Array.from({ length: 6 }).map((_, i) => (
          <circle
            key={`o-${i}`}
            cx={earth.x}
            cy={earth.y}
            r={earth.r + 48 + i * 38}
            fill="none"
            stroke="rgba(109,138,168,0.12)"
          />
        ))}

        <circle cx={earth.x} cy={earth.y} r={earth.r + 10} fill="none" stroke="rgba(142,176,204,0.25)" />
        <circle cx={earth.x} cy={earth.y} r={earth.r} fill="url(#earthGlow)" />
        <path
          d={`M ${earth.x - 48} ${earth.y - 10} C ${earth.x - 10} ${earth.y - 40}, ${earth.x + 30} ${earth.y - 18}, ${earth.x + 52} ${earth.y + 8}`}
          fill="none"
          stroke="rgba(180,200,214,0.35)"
          strokeWidth="1.2"
        />
        <text x={earth.x} y={earth.y + earth.r + 22} textAnchor="middle" fill="#8b93a7" fontSize="11" letterSpacing="0.28em">
          EARTH
        </text>

        {(mode === "prelaunch" || mode === "ascent" || mode === "starship") && (
          <>
            <path d={ascentPath} fill="none" stroke="rgba(109,138,168,0.28)" strokeWidth="1.4" strokeDasharray="5 7" />
            <path
              d={ascentPath}
              fill="none"
              stroke="url(#pathGlow)"
              strokeWidth="1.8"
              pathLength={1000}
              strokeDasharray={`${Math.max(8, progress * 1000)} 1000`}
            />
          </>
        )}

        {(mode === "orbit" || mode === "iss" || mode === "complete") && (
          <>
            <ellipse
              cx={earth.x}
              cy={earth.y}
              rx="210"
              ry="128"
              fill="none"
              stroke="rgba(109,138,168,0.25)"
              strokeDasharray="4 8"
            />
            <ellipse
              cx={earth.x}
              cy={earth.y}
              rx="210"
              ry="128"
              fill="none"
              stroke="#8eb0cc"
              strokeWidth="1.6"
              pathLength={1000}
              strokeDasharray={`${progress * 780} 1000`}
              transform={`rotate(-18 ${earth.x} ${earth.y})`}
            />
          </>
        )}

        {mode === "iss" && (
          <g transform={`translate(${earth.x + 168} ${earth.y - 78})`}>
            <rect x="-10" y="-4" width="20" height="8" fill="#d8dee8" />
            <rect x="-22" y="-2" width="12" height="4" fill="#6d8aa8" />
            <rect x="10" y="-2" width="12" height="4" fill="#6d8aa8" />
            <text y="-14" textAnchor="middle" fill="#8b93a7" fontSize="10" letterSpacing="0.24em">
              ISS
            </text>
          </g>
        )}

        {milestones.slice(0, 8).map((item, index) => {
          const t = lastT ? item.t_plus_seconds / lastT : 0;
          const point =
            mode === "orbit" || mode === "iss"
              ? orbitPoint(earth.x, earth.y, 210, 128, Math.min(0.92, 0.08 + t * 0.8))
              : cubic(pad, c1, c2, orbit, Math.min(1, t / 0.35));
          const done = tPlus != null && tPlus >= item.t_plus_seconds;
          const current = state?.previous_milestone?.key === item.key;
          return (
            <MilestoneNode
              key={item.key}
              item={item}
              point={point}
              done={done}
              current={current}
              index={index}
              reducedMotion={reducedMotion}
            />
          );
        })}

        <g transform={`translate(${vehicle.x} ${vehicle.y})`}>
          {!reducedMotion && (
            <circle r="16" fill="none" stroke="#d4783a" strokeOpacity="0.45">
              <animate attributeName="r" values="10;18;10" dur="2.8s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.5;0.15;0.5" dur="2.8s" repeatCount="indefinite" />
            </circle>
          )}
          <path d="M 0 -11 L 5 8 L 0 4 L -5 8 Z" fill="#f4f6fa" />
        </g>
      </svg>
      <div className="flex items-center justify-between border-t border-white/10 px-4 py-2 text-xs text-mist">
        <span>{state?.current_phase ?? "Awaiting mission"}</span>
        <span className="font-mono tabular">
          {state?.clock_prefix} {state?.clock_label}
        </span>
      </div>
    </section>
  );
}

function MilestoneNode({
  item,
  point,
  done,
  current,
  index,
  reducedMotion,
}: {
  item: Milestone;
  point: Point;
  done: boolean;
  current: boolean;
  index: number;
  reducedMotion: boolean;
}) {
  const fill = current ? "#d4783a" : done ? "#c9d4e2" : "#1b2430";
  const stroke = current ? "#d4783a" : "rgba(232,236,245,0.35)";
  const labelSide = index % 2 === 0 ? -18 : 16;
  return (
    <g transform={`translate(${point.x} ${point.y})`}>
      <circle r={current ? 4.5 : 3} fill={fill} stroke={stroke} />
      {current && !reducedMotion && (
        <circle r="8" fill="none" stroke="#d4783a" strokeOpacity="0.7">
          <animate attributeName="r" values="6;11;6" dur="2.2s" repeatCount="indefinite" />
        </circle>
      )}
      <text
        y={labelSide}
        textAnchor="middle"
        fill={done || current ? "#e8eaef" : "#6d7384"}
        fontSize="9"
        letterSpacing="0.18em"
      >
        {item.name.toUpperCase()}
      </text>
    </g>
  );
}
