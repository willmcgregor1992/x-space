from __future__ import annotations

from datetime import datetime

from app.core.time import ensure_utc
from app.models.domain import Launch, MissionState
from app.models.enums import LaunchStatus, LiveStatus
from app.services.mission_state import MissionStateEngine
from app.services.profiles import select_profile

ACTIVE_LIVE = {LiveStatus.WEBCAST_LIVE, LiveStatus.LAUNCH_WINDOW, LiveStatus.MISSION_ACTIVE}
PRE_LAUNCH_STATES = {
    LaunchStatus.SCHEDULED,
    LaunchStatus.COUNTDOWN,
    LaunchStatus.WINDOW_OPEN,
    LaunchStatus.WEBCAST_LIVE,
}


def annotate(launch: Launch, now: datetime, engine: MissionStateEngine) -> tuple[Launch, MissionState]:
    profile = select_profile(launch.vehicle, launch.mission_type, launch.iss_enabled)
    state = engine.compute(launch, now, profile)
    launch.status = state.state
    launch.profile_id = profile.id
    return launch, state


def select_current(launches: list[Launch], now: datetime, engine: MissionStateEngine) -> Launch | None:
    scored: list[tuple[int, datetime, Launch]] = []
    for launch in launches:
        _, state = annotate(launch, now, engine)
        if state.live_status in ACTIVE_LIVE and not (
            launch.iss_enabled and state.t_plus_seconds and state.t_plus_seconds > 3 * 3600
        ):
            scored.append((0, launch.launch_time_start or now, launch))
        elif launch.cms_status == "upcoming" or state.state in PRE_LAUNCH_STATES:
            scored.append((1, launch.launch_time_start or now, launch))
    if not scored:
        upcoming = upcoming_launches(launches, now, engine)
        return upcoming[0] if upcoming else None
    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[0][2]


def upcoming_launches(launches: list[Launch], now: datetime, engine: MissionStateEngine) -> list[Launch]:
    items: list[Launch] = []
    for launch in launches:
        _, state = annotate(launch, now, engine)
        if launch.cms_status == "upcoming" or state.state in PRE_LAUNCH_STATES:
            items.append(launch)
    items.sort(key=lambda item: item.launch_time_start or ensure_utc(now.replace(year=2099)))
    return items


def recent_launches(launches: list[Launch], now: datetime, engine: MissionStateEngine) -> list[Launch]:
    items: list[Launch] = []
    for launch in launches:
        _, state = annotate(launch, now, engine)
        if launch.cms_status == "final" or state.state == LaunchStatus.MISSION_COMPLETE:
            if launch.iss_enabled and launch.cms_status == "in-progress":
                continue
            items.append(launch)
    items.sort(key=lambda item: item.launch_time_start or now, reverse=True)
    return items


def live_launches(launches: list[Launch], now: datetime, engine: MissionStateEngine) -> list[Launch]:
    items: list[Launch] = []
    for launch in launches:
        _, state = annotate(launch, now, engine)
        if state.live_status in ACTIVE_LIVE or launch.cms_status == "in-progress":
            items.append(launch)
    items.sort(key=lambda item: (0 if item.cms_is_live else 1, item.launch_time_start or now))
    return items
