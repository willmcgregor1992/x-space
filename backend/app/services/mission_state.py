from __future__ import annotations

from datetime import datetime

from app.core.time import add_seconds, ensure_utc
from app.models.domain import Launch, Milestone, MissionProfile, MissionState
from app.models.enums import Confidence, LaunchStatus, LiveStatus, VisualizerMode
from app.services.profiles import merge_milestones, select_profile

COUNTDOWN_THRESHOLD_SECONDS = 6 * 3600
WEBCAST_LEAD_FALLBACK = 600
ASCENT_ORBIT_SECONDS = 520


class MissionStateEngine:
    def compute(
        self,
        launch: Launch,
        now: datetime,
        profile: MissionProfile | None = None,
        *,
        simulated: bool = False,
    ) -> MissionState:
        now_utc = ensure_utc(now)
        profile = profile or select_profile(launch.vehicle, launch.mission_type, launch.iss_enabled)
        milestones = merge_milestones(profile, launch.milestones)
        t0 = self._effective_t0(launch)
        t_plus = self._t_plus(launch, t0, now_utc)
        live_status = self.live_status(launch, now_utc, profile, t_plus)
        state = self._state(launch, now_utc, profile, t0, t_plus, live_status)
        previous, current_phase, nxt = self._milestone_window(milestones, t_plus, state)
        progress = self._progress(milestones, t_plus, state)
        visualizer = self._visualizer(profile, state, t_plus, launch)
        is_estimated = self._is_estimated(launch, state, t_plus)
        confidence = Confidence.ESTIMATED if is_estimated else Confidence.OFFICIAL
        clock_prefix, clock_label = self._clock(launch, t0, t_plus, state)
        notes = self._notes(launch, state, is_estimated, simulated)
        next_eta = None
        if nxt and t0 is not None and t_plus is not None and not launch.tzero_paused:
            next_eta = add_seconds(t0, nxt.t_plus_seconds)
        return MissionState(
            state=state,
            t_plus_seconds=None if t_plus is None else int(round(t_plus)),
            progress=progress,
            current_phase=current_phase,
            previous_milestone=previous,
            next_milestone=nxt,
            next_milestone_eta=next_eta,
            confidence=confidence,
            is_estimated=is_estimated,
            visualizer_mode=visualizer,
            live_status=live_status,
            clock_label=clock_label,
            clock_prefix=clock_prefix,
            hold=launch.tzero_paused,
            notes=notes,
        )

    def _effective_t0(self, launch: Launch) -> datetime | None:
        if launch.is_window and not launch.is_exact_time and not launch.tzero_paused:
            return None
        return launch.launch_time_start

    def _t_plus(self, launch: Launch, t0: datetime | None, now: datetime) -> float | None:
        if launch.tzero_paused and launch.tzero_hold_seconds is not None:
            return -float(launch.tzero_hold_seconds)
        if t0 is None:
            return None
        return (now - ensure_utc(t0)).total_seconds()

    def live_status(
        self,
        launch: Launch,
        now: datetime,
        profile: MissionProfile,
        t_plus: float | None,
    ) -> LiveStatus:
        cms = (launch.cms_status or "").lower()
        if cms == "final" or launch.status == LaunchStatus.MISSION_COMPLETE:
            if t_plus is not None and 0 <= t_plus <= profile.active_duration_seconds:
                return LiveStatus.MISSION_ACTIVE
            return LiveStatus.COMPLETED
        signals = 0
        if launch.cms_is_live:
            signals += 2
        cta = (launch.call_to_action or "").strip().upper()
        if cta == "WATCH" and launch.cms_is_live:
            signals += 1
        if launch.is_window and launch.launch_time_start and launch.launch_time_end:
            if ensure_utc(launch.launch_time_start) <= now <= ensure_utc(launch.launch_time_end):
                signals += 1
                if signals >= 2 or launch.cms_is_live:
                    return LiveStatus.WEBCAST_LIVE if launch.cms_is_live else LiveStatus.LAUNCH_WINDOW
                return LiveStatus.LAUNCH_WINDOW
        if t_plus is not None:
            if 0 <= t_plus <= profile.active_duration_seconds:
                if cms == "in-progress" and t_plus > 3 * 3600 and launch.iss_enabled:
                    return LiveStatus.OFFLINE
                return LiveStatus.MISSION_ACTIVE
            lead = profile.webcast_lead_seconds or WEBCAST_LEAD_FALLBACK
            if -lead <= t_plus < 0:
                if launch.cms_is_live:
                    return LiveStatus.WEBCAST_LIVE
                return LiveStatus.PRELAUNCH
        if cms == "in-progress" and launch.iss_enabled:
            return LiveStatus.OFFLINE
        if cms == "upcoming":
            return LiveStatus.PRELAUNCH if t_plus is not None and t_plus > -6 * 3600 else LiveStatus.OFFLINE
        if signals >= 2:
            return LiveStatus.WEBCAST_LIVE
        return LiveStatus.OFFLINE

    def _state(
        self,
        launch: Launch,
        now: datetime,
        profile: MissionProfile,
        t0: datetime | None,
        t_plus: float | None,
        live: LiveStatus,
    ) -> LaunchStatus:
        cms = (launch.cms_status or "").lower()
        if cms == "final":
            if t_plus is not None and 0 <= t_plus <= profile.complete_after_seconds:
                return self._inflight_status(t_plus, launch)
            return LaunchStatus.MISSION_COMPLETE
        if launch.status == LaunchStatus.SCRUBBED:
            return LaunchStatus.SCRUBBED
        if launch.status == LaunchStatus.DELAYED:
            return LaunchStatus.DELAYED
        if live == LiveStatus.WEBCAST_LIVE and (t_plus is None or t_plus < 0):
            return LaunchStatus.WEBCAST_LIVE
        if live == LiveStatus.LAUNCH_WINDOW and (t_plus is None or t_plus < 0):
            return LaunchStatus.WINDOW_OPEN
        if t_plus is None:
            if launch.is_window and launch.launch_time_start and launch.launch_time_end:
                start = ensure_utc(launch.launch_time_start)
                end = ensure_utc(launch.launch_time_end)
                if start <= now <= end:
                    return LaunchStatus.WINDOW_OPEN
                if now > end and cms == "upcoming":
                    return LaunchStatus.DELAYED
            return LaunchStatus.SCHEDULED if cms == "upcoming" else launch.status
        if t_plus < 0:
            if abs(t_plus) <= COUNTDOWN_THRESHOLD_SECONDS:
                return LaunchStatus.COUNTDOWN
            return LaunchStatus.SCHEDULED
        if t_plus == 0:
            return LaunchStatus.LAUNCHED
        if cms == "in-progress" and launch.iss_enabled and t_plus > profile.active_duration_seconds:
            return LaunchStatus.IN_FLIGHT
        if t_plus > profile.complete_after_seconds and cms != "in-progress":
            return LaunchStatus.MISSION_COMPLETE
        return self._inflight_status(t_plus, launch)

    def _inflight_status(self, t_plus: float, launch: Launch) -> LaunchStatus:
        landed = _first_t(launch, {"landing", "boosters_land"})
        deployed = _first_t(launch, {"deploy"})
        if deployed is not None and t_plus >= deployed:
            return LaunchStatus.PAYLOAD_DEPLOYED
        if landed is not None and t_plus >= landed:
            return LaunchStatus.BOOSTER_LANDED
        if t_plus < 3:
            return LaunchStatus.LAUNCHED
        return LaunchStatus.IN_FLIGHT

    def _milestone_window(
        self, milestones: list[Milestone], t_plus: float | None, state: LaunchStatus
    ) -> tuple[Milestone | None, str, Milestone | None]:
        post = [m for m in milestones if m.t_plus_seconds >= 0]
        if not post:
            return None, _phase_from_state(state), None
        if t_plus is None or t_plus < 0:
            first = post[0]
            return None, "Pre-launch", first
        previous = None
        nxt = None
        current_phase = post[0].phase or post[0].name
        for item in post:
            if item.t_plus_seconds <= t_plus:
                previous = item
                current_phase = item.phase or item.name
            elif nxt is None:
                nxt = item
                break
        if state == LaunchStatus.MISSION_COMPLETE:
            current_phase = "Mission complete"
        if previous and previous.key == "docking":
            current_phase = "Docked"
        return previous, current_phase, nxt

    def _progress(self, milestones: list[Milestone], t_plus: float | None, state: LaunchStatus) -> float:
        post = [m for m in milestones if m.t_plus_seconds >= 0]
        if state in {LaunchStatus.SCHEDULED, LaunchStatus.COUNTDOWN, LaunchStatus.WINDOW_OPEN, LaunchStatus.WEBCAST_LIVE}:
            return 0.0
        if state == LaunchStatus.MISSION_COMPLETE:
            return 1.0
        if t_plus is None or not post:
            return 0.0
        last = post[-1].t_plus_seconds or 1
        raw = t_plus / last
        return max(0.0, min(1.0, round(raw, 4)))

    def _visualizer(
        self, profile: MissionProfile, state: LaunchStatus, t_plus: float | None, launch: Launch
    ) -> VisualizerMode:
        if profile.visualizer == VisualizerMode.STARSHIP:
            if t_plus is None or t_plus < 0:
                return VisualizerMode.PRELAUNCH
            if state == LaunchStatus.MISSION_COMPLETE:
                return VisualizerMode.COMPLETE
            return VisualizerMode.STARSHIP
        if profile.visualizer == VisualizerMode.ISS or launch.iss_enabled:
            if t_plus is None or t_plus < 0:
                return VisualizerMode.PRELAUNCH
            if t_plus < ASCENT_ORBIT_SECONDS:
                return VisualizerMode.ASCENT
            return VisualizerMode.ISS
        if t_plus is None or t_plus < 0:
            return VisualizerMode.PRELAUNCH
        if state == LaunchStatus.MISSION_COMPLETE:
            return VisualizerMode.COMPLETE
        if t_plus >= ASCENT_ORBIT_SECONDS:
            return VisualizerMode.ORBIT
        return VisualizerMode.ASCENT

    def _is_estimated(self, launch: Launch, state: LaunchStatus, t_plus: float | None) -> bool:
        if launch.cms_status == "final" and state == LaunchStatus.MISSION_COMPLETE:
            return False
        if launch.cms_status == "in-progress" and launch.iss_tense == "present":
            return False
        if t_plus is not None and t_plus >= 0:
            return True
        return False

    def _clock(
        self,
        launch: Launch,
        t0: datetime | None,
        t_plus: float | None,
        state: LaunchStatus,
    ) -> tuple[str, str]:
        if launch.tzero_paused and launch.tzero_hold_seconds is not None:
            return "T−", _format_hms(launch.tzero_hold_seconds)
        if state == LaunchStatus.WINDOW_OPEN:
            return "WINDOW", "OPEN"
        if t_plus is None:
            if launch.is_window:
                return "WINDOW", "SET"
            return "", "TBD"
        if t_plus < 0:
            return "T−", _format_hms(int(round(-t_plus)))
        return "T+", _format_hms(int(round(t_plus)))

    def _notes(self, launch: Launch, state: LaunchStatus, is_estimated: bool, simulated: bool) -> list[str]:
        notes: list[str] = []
        if simulated:
            notes.append("SIMULATION — development only. Not persisted.")
        if is_estimated and state in {
            LaunchStatus.LAUNCHED,
            LaunchStatus.IN_FLIGHT,
            LaunchStatus.PAYLOAD_DEPLOYED,
            LaunchStatus.BOOSTER_LANDED,
        }:
            notes.append("Estimated mission position — not real telemetry.")
        if launch.is_window and not launch.is_exact_time and state in {
            LaunchStatus.SCHEDULED,
            LaunchStatus.WINDOW_OPEN,
        }:
            notes.append("Launch window, not a confirmed T−0.")
        if launch.tzero_paused:
            notes.append("Official countdown is holding.")
        return notes


def _first_t(launch: Launch, keys: set[str]) -> int | None:
    times = [m.t_plus_seconds for m in launch.milestones if m.key in keys]
    return min(times) if times else None


def _phase_from_state(state: LaunchStatus) -> str:
    return {
        LaunchStatus.SCHEDULED: "Scheduled",
        LaunchStatus.COUNTDOWN: "Countdown",
        LaunchStatus.WINDOW_OPEN: "Launch window",
        LaunchStatus.WEBCAST_LIVE: "Webcast",
        LaunchStatus.LAUNCHED: "Liftoff",
        LaunchStatus.IN_FLIGHT: "In flight",
        LaunchStatus.PAYLOAD_DEPLOYED: "Payload deployed",
        LaunchStatus.BOOSTER_LANDED: "Booster landed",
        LaunchStatus.MISSION_COMPLETE: "Mission complete",
        LaunchStatus.DELAYED: "Delayed",
        LaunchStatus.SCRUBBED: "Scrubbed",
    }.get(state, "Unknown")


def _format_hms(total_seconds: int) -> str:
    seconds = abs(int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
