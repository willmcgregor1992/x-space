from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, Request

from app.core.time import utcnow
from app.services.ingestion import stale_banner
from app.services.mission_state import MissionStateEngine


def parse_simulate(raw: str | None, is_development: bool) -> int | None:
    if not raw:
        return None
    if not is_development:
        raise HTTPException(status_code=400, detail="Simulation is only available in development.")
    token = raw.strip().lower().replace("_", "-")
    mapping = {
        "t0": 0,
        "tplus-0": 0,
        "tminus-0": 0,
        "tminus-600": -600,
        "tminus-10m": -600,
        "tminus-30": -30,
        "tplus-60": 60,
        "tplus-180": 180,
        "tplus-480": 480,
        "tplus-3600": 3600,
    }
    if token in mapping:
        return mapping[token]
    if token.startswith("tplus-") and token[6:].isdigit():
        return int(token[6:])
    if token.startswith("tminus-") and token[7:].isdigit():
        return -int(token[7:])
    raise HTTPException(status_code=400, detail="Unrecognized simulate value.")


def simulated_now(launch_t0, offset_seconds: int | None):
    now = utcnow()
    if offset_seconds is None or launch_t0 is None:
        return now, False
    return launch_t0 + timedelta(seconds=offset_seconds), True


def engine(request: Request) -> MissionStateEngine:
    return request.app.state.engine


def banner_for(request: Request):
    ingestion = request.app.state.ingestion
    return stale_banner(ingestion.last_success_at, ingestion.last_error)
