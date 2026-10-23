export type Confidence = "official" | "estimated";
export type LiveStatus =
  | "offline"
  | "prelaunch"
  | "webcast_live"
  | "launch_window"
  | "mission_active"
  | "completed";

export interface Provenance {
  source: string;
  confidence: Confidence;
  note: string | null;
}

export interface Milestone {
  key: string;
  name: string;
  t_plus_seconds: number;
  description: string;
  phase: string | null;
  is_estimated: boolean;
  source: string;
  visual_role: string | null;
}

export interface Launch {
  id: string;
  slug: string;
  mission_name: string;
  vehicle: string | null;
  launch_site: string | null;
  landing_site: string | null;
  landing_method: string | null;
  launch_time_start: string | null;
  launch_time_end: string | null;
  launch_timezone: string;
  is_exact_time: boolean;
  is_window: boolean;
  tzero_paused: boolean;
  tzero_hold_seconds: number | null;
  official_url: string;
  webcast_url: string | null;
  description: string | null;
  status: string;
  mission_type: string | null;
  booster_information: {
    serial: string | null;
    flight_number: number | null;
    summary: string | null;
  } | null;
  payload_information: {
    summary: string | null;
    satellite_count: number | null;
  } | null;
  source_updated_at: string | null;
  fetched_at: string;
  cms_status: string | null;
  cms_is_live: boolean;
  call_to_action: string | null;
  iss_enabled: boolean;
  iss_tense: string | null;
  return_datetime_text: string | null;
  profile_id: string | null;
  milestones: Milestone[];
  provenance: Record<string, Provenance>;
  live_status: LiveStatus | null;
}

export interface MissionState {
  state: string;
  t_plus_seconds: number | null;
  progress: number;
  current_phase: string;
  previous_milestone: Milestone | null;
  next_milestone: Milestone | null;
  next_milestone_eta: string | null;
  confidence: Confidence;
  is_estimated: boolean;
  visualizer_mode: string;
  live_status: LiveStatus;
  clock_label: string;
  clock_prefix: string;
  hold: boolean;
  notes: string[];
}

export interface Banner {
  code: string;
  title: string;
  message: string;
}

export interface Meta {
  server_time: string;
  data_updated_at: string | null;
  stale_seconds: number | null;
  used_cache: boolean;
  banner: Banner | null;
  simulation: boolean;
}

export interface CurrentResponse {
  launch: Launch | null;
  state: MissionState | null;
  meta: Meta;
}

export interface LaunchListResponse {
  launches: Launch[];
  meta: Meta;
}

export interface LaunchDetailResponse {
  launch: Launch;
  state: MissionState;
  meta: Meta;
}

export type SelectorTab = "LIVE" | "NEXT" | "UPCOMING" | "RECENT";
