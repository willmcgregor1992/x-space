from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models.domain import Milestone, MissionProfile
from app.models.enums import DataSource, VehicleFamily, VisualizerMode
from app.providers.spacex_parse import vehicle_family

PROFILES_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"


@lru_cache
def load_profiles() -> dict[str, MissionProfile]:
    profiles: dict[str, MissionProfile] = {}
    for path in sorted(PROFILES_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        milestones = [Milestone.model_validate(item) for item in raw.get("milestones", [])]
        for milestone in milestones:
            if milestone.source == DataSource.SPACEX and not milestone.is_estimated:
                continue
            milestone.source = DataSource.MISSION_PROFILE
            milestone.is_estimated = True
        profiles[raw["id"]] = MissionProfile(
            id=raw["id"],
            name=raw["name"],
            vehicles=raw.get("vehicles") or [],
            mission_types=raw.get("mission_types") or [],
            visualizer=VisualizerMode(raw.get("visualizer", "ascent")),
            active_duration_seconds=int(raw.get("active_duration_seconds", 7200)),
            complete_after_seconds=int(raw.get("complete_after_seconds", 9000)),
            webcast_lead_seconds=int(raw.get("webcast_lead_seconds", 600)),
            milestones=milestones,
        )
    return profiles


def select_profile(vehicle: str | None, mission_type: str | None, iss_enabled: bool = False) -> MissionProfile:
    profiles = load_profiles()
    if iss_enabled or (mission_type or "") in {"hsf", "resupply"}:
        return profiles["dragon_iss"]
    family = vehicle_family(vehicle)
    if family == VehicleFamily.STARSHIP or (mission_type or "") == "starship":
        return profiles["starship"]
    if family == VehicleFamily.FALCON_HEAVY:
        return profiles["falcon_heavy"]
    return profiles["falcon9_orbital"]


def merge_milestones(profile: MissionProfile, sourced: list[Milestone]) -> list[Milestone]:
    """Prefer SpaceX timeline times when a key matches; keep profile structure."""
    sourced_by_key = {item.key: item for item in sourced if item.t_plus_seconds >= 0}
    merged: list[Milestone] = []
    used: set[str] = set()
    for item in profile.milestones:
        if item.key in sourced_by_key:
            official = sourced_by_key[item.key]
            merged.append(
                item.model_copy(
                    update={
                        "t_plus_seconds": official.t_plus_seconds,
                        "description": official.description or item.description,
                        "source": DataSource.SPACEX,
                        "is_estimated": True,
                    }
                )
            )
            used.add(item.key)
        else:
            merged.append(item)
    extras = [
        item
        for item in sourced
        if item.key not in used and item.t_plus_seconds >= 0 and item.key not in {m.key for m in merged}
    ]
    combined = merged + extras
    combined.sort(key=lambda m: (m.t_plus_seconds, m.name))
    return combined
