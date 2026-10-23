from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import Launch, Milestone, MissionState, Provenance
from app.models.enums import Confidence, LiveStatus


class ProvenanceOut(BaseModel):
    source: str
    confidence: Confidence
    note: str | None = None


class MilestoneOut(BaseModel):
    key: str
    name: str
    t_plus_seconds: int
    description: str
    phase: str | None = None
    is_estimated: bool
    source: str
    visual_role: str | None = None


class BoosterOut(BaseModel):
    serial: str | None = None
    flight_number: int | None = None
    summary: str | None = None


class PayloadOut(BaseModel):
    summary: str | None = None
    satellite_count: int | None = None


class LaunchOut(BaseModel):
    id: str
    slug: str
    mission_name: str
    vehicle: str | None = None
    launch_site: str | None = None
    landing_site: str | None = None
    landing_method: str | None = None
    launch_time_start: datetime | None = None
    launch_time_end: datetime | None = None
    launch_timezone: str
    is_exact_time: bool
    is_window: bool
    tzero_paused: bool
    tzero_hold_seconds: int | None = None
    official_url: str
    webcast_url: str | None = None
    description: str | None = None
    status: str
    mission_type: str | None = None
    booster_information: BoosterOut | None = None
    payload_information: PayloadOut | None = None
    source_updated_at: datetime | None = None
    fetched_at: datetime
    cms_status: str | None = None
    cms_is_live: bool
    call_to_action: str | None = None
    iss_enabled: bool
    iss_tense: str | None = None
    return_datetime_text: str | None = None
    profile_id: str | None = None
    milestones: list[MilestoneOut] = Field(default_factory=list)
    provenance: dict[str, ProvenanceOut] = Field(default_factory=dict)
    live_status: LiveStatus | None = None


class MissionStateOut(BaseModel):
    state: str
    t_plus_seconds: int | None
    progress: float
    current_phase: str
    previous_milestone: MilestoneOut | None
    next_milestone: MilestoneOut | None
    next_milestone_eta: datetime | None
    confidence: Confidence
    is_estimated: bool
    visualizer_mode: str
    live_status: LiveStatus
    clock_label: str
    clock_prefix: str
    hold: bool
    notes: list[str] = Field(default_factory=list)


class BannerOut(BaseModel):
    code: str
    title: str
    message: str


class MetaOut(BaseModel):
    server_time: datetime
    data_updated_at: datetime | None = None
    stale_seconds: int | None = None
    used_cache: bool = False
    banner: BannerOut | None = None
    simulation: bool = False


class CurrentResponse(BaseModel):
    launch: LaunchOut | None
    state: MissionStateOut | None
    meta: MetaOut


class LaunchListResponse(BaseModel):
    launches: list[LaunchOut]
    meta: MetaOut


class LaunchDetailResponse(BaseModel):
    launch: LaunchOut
    state: MissionStateOut
    meta: MetaOut


class HealthResponse(BaseModel):
    status: str
    server_time: datetime
    last_ingest_ok: bool | None = None
    last_ingest_at: datetime | None = None
    used_cache: bool = False
    database: str = "ok"


def milestone_out(item: Milestone | None) -> MilestoneOut | None:
    if item is None:
        return None
    return MilestoneOut(
        key=item.key,
        name=item.name,
        t_plus_seconds=item.t_plus_seconds,
        description=item.description,
        phase=item.phase,
        is_estimated=item.is_estimated,
        source=str(item.source),
        visual_role=item.visual_role,
    )


def provenance_out(item: Provenance) -> ProvenanceOut:
    return ProvenanceOut(source=str(item.source), confidence=item.confidence, note=item.note)


def launch_out(launch: Launch, live_status: LiveStatus | None = None) -> LaunchOut:
    booster = None
    if launch.booster_information:
        booster = BoosterOut(
            serial=launch.booster_information.serial,
            flight_number=launch.booster_information.flight_number,
            summary=launch.booster_information.summary,
        )
    payload = None
    if launch.payload_information:
        payload = PayloadOut(
            summary=launch.payload_information.summary,
            satellite_count=launch.payload_information.satellite_count,
        )
    return LaunchOut(
        id=launch.id,
        slug=launch.slug,
        mission_name=launch.mission_name,
        vehicle=launch.vehicle,
        launch_site=launch.launch_site,
        landing_site=launch.landing_site,
        landing_method=launch.landing_method,
        launch_time_start=launch.launch_time_start,
        launch_time_end=launch.launch_time_end,
        launch_timezone=launch.launch_timezone,
        is_exact_time=launch.is_exact_time,
        is_window=launch.is_window,
        tzero_paused=launch.tzero_paused,
        tzero_hold_seconds=launch.tzero_hold_seconds,
        official_url=launch.official_url,
        webcast_url=launch.webcast_url,
        description=launch.description,
        status=str(launch.status),
        mission_type=launch.mission_type,
        booster_information=booster,
        payload_information=payload,
        source_updated_at=launch.source_updated_at,
        fetched_at=launch.fetched_at,
        cms_status=launch.cms_status,
        cms_is_live=launch.cms_is_live,
        call_to_action=launch.call_to_action,
        iss_enabled=launch.iss_enabled,
        iss_tense=launch.iss_tense,
        return_datetime_text=launch.return_datetime_text,
        profile_id=launch.profile_id,
        milestones=[milestone_out(item) for item in launch.milestones if milestone_out(item)],
        provenance={key: provenance_out(value) for key, value in launch.field_provenance.items()},
        live_status=live_status,
    )


def state_out(state: MissionState) -> MissionStateOut:
    return MissionStateOut(
        state=str(state.state),
        t_plus_seconds=state.t_plus_seconds,
        progress=state.progress,
        current_phase=state.current_phase,
        previous_milestone=milestone_out(state.previous_milestone),
        next_milestone=milestone_out(state.next_milestone),
        next_milestone_eta=state.next_milestone_eta,
        confidence=state.confidence,
        is_estimated=state.is_estimated,
        visualizer_mode=str(state.visualizer_mode),
        live_status=state.live_status,
        clock_label=state.clock_label,
        clock_prefix=state.clock_prefix,
        hold=state.hold,
        notes=state.notes,
    )
