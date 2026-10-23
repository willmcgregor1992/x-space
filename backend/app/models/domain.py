from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    Confidence,
    DataSource,
    LaunchStatus,
    LiveStatus,
    VisualizerMode,
)

T = TypeVar("T")


class Provenance(BaseModel):
    source: DataSource = DataSource.SPACEX
    confidence: Confidence = Confidence.OFFICIAL
    note: str | None = None


class Provenanced(BaseModel, Generic[T]):
    value: T
    provenance: Provenance = Field(default_factory=Provenance)


class Milestone(BaseModel):
    key: str
    name: str
    t_plus_seconds: int
    description: str = ""
    phase: str | None = None
    is_estimated: bool = True
    source: DataSource = DataSource.MISSION_PROFILE
    visual_role: str | None = None


class BoosterInformation(BaseModel):
    serial: str | None = None
    flight_number: int | None = None
    summary: str | None = None
    provenance: Provenance = Field(
        default_factory=lambda: Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL)
    )


class PayloadInformation(BaseModel):
    summary: str | None = None
    satellite_count: int | None = None
    provenance: Provenance = Field(
        default_factory=lambda: Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL)
    )


class Webcast(BaseModel):
    url: str | None = None
    video_id: str | None = None
    provider: str | None = None
    title: str | None = None
    is_featured: bool = False
    provenance: Provenance = Field(
        default_factory=lambda: Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL)
    )


class Launch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    mission_name: str
    vehicle: str | None = None
    launch_site: str | None = None
    landing_site: str | None = None
    landing_method: str | None = None
    launch_time_start: datetime | None = None
    launch_time_end: datetime | None = None
    launch_timezone: str = "UTC"
    is_exact_time: bool = False
    is_window: bool = False
    tzero_paused: bool = False
    tzero_hold_seconds: int | None = None
    official_url: str
    webcast_url: str | None = None
    webcasts: list[Webcast] = Field(default_factory=list)
    description: str | None = None
    status: LaunchStatus = LaunchStatus.UNKNOWN
    mission_type: str | None = None
    booster_information: BoosterInformation | None = None
    payload_information: PayloadInformation | None = None
    source_updated_at: datetime | None = None
    fetched_at: datetime
    cms_status: str | None = None
    cms_is_live: bool = False
    call_to_action: str | None = None
    correlation_id: str | None = None
    iss_enabled: bool = False
    iss_tense: str | None = None
    return_datetime_text: str | None = None
    image_url: str | None = None
    profile_id: str | None = None
    milestones: list[Milestone] = Field(default_factory=list)
    field_provenance: dict[str, Provenance] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("launch_time_start", "launch_time_end", "source_updated_at", "fetched_at")
    @classmethod
    def require_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime is not allowed")
        return value


class MissionState(BaseModel):
    state: LaunchStatus
    t_plus_seconds: int | None = None
    progress: float = 0.0
    current_phase: str
    previous_milestone: Milestone | None = None
    next_milestone: Milestone | None = None
    next_milestone_eta: datetime | None = None
    confidence: Confidence = Confidence.ESTIMATED
    is_estimated: bool = True
    visualizer_mode: VisualizerMode = VisualizerMode.PRELAUNCH
    live_status: LiveStatus = LiveStatus.OFFLINE
    clock_label: str = "TBD"
    clock_prefix: str = ""
    hold: bool = False
    notes: list[str] = Field(default_factory=list)


class MissionProfile(BaseModel):
    id: str
    name: str
    vehicles: list[str] = Field(default_factory=list)
    mission_types: list[str] = Field(default_factory=list)
    visualizer: VisualizerMode = VisualizerMode.ASCENT
    active_duration_seconds: int = 7200
    complete_after_seconds: int = 9000
    webcast_lead_seconds: int = 600
    milestones: list[Milestone] = Field(default_factory=list)


class IngestionResult(BaseModel):
    ok: bool
    used_cache: bool = False
    launches_upserted: int = 0
    error: str | None = None
    source_updated_at: datetime | None = None
    fetched_at: datetime
    stale_seconds: int | None = None
