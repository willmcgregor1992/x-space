from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

SITE_TIMEZONES: dict[str, str] = {
    "FLORIDA": "America/New_York",
    "SLC-40": "America/New_York",
    "SLC-37": "America/New_York",
    "LC-39A": "America/New_York",
    "CALIFORNIA": "America/Los_Angeles",
    "SLC-4E": "America/Los_Angeles",
    "VANDENBERG": "America/Los_Angeles",
    "TEXAS": "America/Chicago",
    "STARBASE": "America/Chicago",
    "PAD 1": "America/Chicago",
    "PAD 2": "America/Chicago",
    "OMELEK": "Pacific/Kwajalein",
}


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("naive datetime is not allowed")
    return value.astimezone(UTC)


def assume_utc(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; treat stored timestamps as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def from_unix_seconds(seconds: int | float | None) -> datetime | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(float(seconds), tz=UTC)


def parse_site_local(date: str | None, time: str | None, launch_site: str | None) -> datetime | None:
    """Interpret SpaceX tile date+time as launch-site local, return UTC."""
    if not date:
        return None
    clock = time or "00:00:00"
    if len(clock) == 5:
        clock = f"{clock}:00"
    try:
        naive = datetime.fromisoformat(f"{date}T{clock}")
    except ValueError:
        return None
    zone = ZoneInfo(timezone_for_site(launch_site))
    local = naive.replace(tzinfo=zone)
    return local.astimezone(UTC)


def timezone_for_site(launch_site: str | None) -> str:
    if not launch_site:
        return "UTC"
    token = launch_site.upper()
    for needle, zone in SITE_TIMEZONES.items():
        if needle in token:
            return zone
    return "UTC"


def window_spans_midnight(start: datetime, end: datetime) -> bool:
    start_u = ensure_utc(start)
    end_u = ensure_utc(end)
    return start_u.date() != end_u.date()


def seconds_until(target: datetime, now: datetime) -> float:
    return (ensure_utc(target) - ensure_utc(now)).total_seconds()


def clamp_non_negative(value: float) -> float:
    return value if value >= 0 else 0.0


def add_seconds(origin: datetime, seconds: float) -> datetime:
    return ensure_utc(origin) + timedelta(seconds=seconds)
