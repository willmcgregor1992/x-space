from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.core.time import from_unix_seconds, parse_site_local, timezone_for_site, utcnow
from app.models.domain import (
    BoosterInformation,
    Launch,
    Milestone,
    PayloadInformation,
    Provenance,
    Webcast,
)
from app.models.enums import Confidence, DataSource, LaunchStatus, VehicleFamily
from app.providers.sanitize import html_to_text, sanitize_url

_ALLOWED_HOSTS = (
    "www.spacex.com",
    "spacex.com",
    "content.spacex.com",
    "sxcontent9668.azureedge.us",
    "x.com",
    "twitter.com",
    "www.starlink.com",
    "starlink.com",
)

CMS_STATUS_MAP = {
    "upcoming": LaunchStatus.SCHEDULED,
    "in-progress": LaunchStatus.IN_FLIGHT,
    "final": LaunchStatus.MISSION_COMPLETE,
}

MILESTONE_KEY_RULES: list[tuple[str, str, str]] = [
    (r"\bliftoff\b|\bexcitement guaranteed\b", "liftoff", "Liftoff"),
    (r"\bmax q\b", "max_q", "Max Q"),
    (r"\bbeco\b|side booster engine cutoff", "beco", "BECO"),
    (r"side boosters separate|booster separation", "booster_sep", "Booster sep"),
    (r"\bmeco\b|main engine cutoff", "meco", "MECO"),
    (r"hot-staging|hot staging", "hot_stage", "Hot-staging"),
    (r"stages separate|stage separation", "stage_sep", "Stage sep"),
    (r"ses-1|2nd stage engine starts|second.stage ignition", "ses1", "SES-1"),
    (r"fairing", "fairing", "Fairing sep"),
    (r"boostback", "boostback", "Boostback"),
    (r"entry burn", "entry_burn", "Entry burn"),
    (r"landing burn", "landing_burn", "Landing burn"),
    (r"side boosters land|\bboosters land\b", "boosters_land", "Boosters land"),
    (r"1st stage landing|\bfirst stage landing\b|\blanding\b", "landing", "Landing"),
    (r"seco-1|seco 1|2nd stage engine cutoff \(seco-1\)", "seco1", "SECO-1"),
    (r"dragon separates", "dragon_sep", "Dragon sep"),
    (r"nosecone", "nosecone", "Nosecone open"),
    (r"ses-2", "ses2", "SES-2"),
    (r"seco-2", "seco2", "SECO-2"),
    (r"deploy", "deploy", "Deployment"),
    (r"dock", "docking", "Docking"),
    (r"raptor in-space relight", "relight", "Raptor relight"),
    (r"\bentry\b", "entry", "Entry"),
    (r"landing flip|landing burn start", "landing_flip", "Landing burn"),
]


def unix_from_proto(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict) and value.get("Seconds") is not None:
        return int(value["Seconds"])
    return None


def parse_iso_aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def map_cms_status(raw: str | None) -> LaunchStatus:
    if not raw:
        return LaunchStatus.UNKNOWN
    return CMS_STATUS_MAP.get(raw.strip().lower(), LaunchStatus.UNKNOWN)


def vehicle_family(vehicle: str | None) -> VehicleFamily:
    if not vehicle:
        return VehicleFamily.UNKNOWN
    token = vehicle.lower()
    if "heavy" in token:
        return VehicleFamily.FALCON_HEAVY
    if "starship" in token or "super heavy" in token:
        return VehicleFamily.STARSHIP
    if "falcon 1" in token:
        return VehicleFamily.FALCON_1
    if "falcon" in token:
        return VehicleFamily.FALCON_9
    return VehicleFamily.UNKNOWN


def official_url(slug: str, site_base: str = "https://www.spacex.com") -> str:
    return f"{site_base.rstrip('/')}/launches/{slug}"


def webcast_url(webcast: dict[str, Any]) -> str | None:
    video_id = str(webcast.get("videoId") or "").strip()
    kind = str(webcast.get("streamingVideoType") or "").strip().lower()
    if not video_id:
        return None
    if kind in {"x-live-studio", "xlive", "broadcast"}:
        return sanitize_url(f"https://x.com/i/broadcasts/{video_id}", _ALLOWED_HOSTS)
    if kind in {"x.com", "twitter"}:
        if video_id.isdigit():
            return sanitize_url(f"https://x.com/i/status/{video_id}", _ALLOWED_HOSTS)
        return sanitize_url(f"https://x.com/i/broadcasts/{video_id}", _ALLOWED_HOSTS)
    return sanitize_url(f"https://x.com/i/broadcasts/{video_id}", _ALLOWED_HOSTS)


def parse_clock_to_seconds(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.strip().replace("−", "-").replace("–", "-")
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("+-").strip()
    parts = [p for p in re.split(r"[:.]", cleaned) if p != ""]
    if not parts or not all(p.isdigit() for p in parts):
        return None
    nums = [int(p) for p in parts]
    if len(nums) == 3:
        hours, minutes, seconds = nums
    elif len(nums) == 2:
        hours = 0
        minutes, seconds = nums
    elif len(nums) == 1:
        hours = 0
        minutes = 0
        seconds = nums[0]
    else:
        return None
    total = hours * 3600 + minutes * 60 + seconds
    return -total if negative else total


def milestone_key_from_description(description: str) -> tuple[str, str]:
    lowered = description.lower()
    for pattern, key, name in MILESTONE_KEY_RULES:
        if re.search(pattern, lowered):
            return key, name
    slug = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")[:48] or "event"
    title = re.sub(r"\s+", " ", description).strip()
    return slug, title[:48]


def parse_timeline_entries(timeline: dict[str, Any] | None, *, prelaunch: bool = False) -> list[Milestone]:
    if not timeline:
        return []
    disclaimer = (timeline.get("disclaimer") or "").lower()
    estimated = "approximate" in disclaimer or True  # SpaceX marks these as approximate
    entries = timeline.get("timelineEntries") or []
    milestones: list[Milestone] = []
    seen: dict[str, int] = {}
    for entry in entries:
        description = html_to_text(entry.get("description")) or ""
        seconds = parse_clock_to_seconds(entry.get("time"))
        if seconds is None:
            continue
        if prelaunch:
            seconds = -abs(seconds)
        key, name = milestone_key_from_description(description)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = f"{key}_{seen[key]}"
        milestones.append(
            Milestone(
                key=key,
                name=name,
                t_plus_seconds=seconds,
                description=description,
                is_estimated=estimated,
                source=DataSource.SPACEX,
            )
        )
    return milestones


_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
}


def _parse_ordinal(token: str) -> int | None:
    token = token.lower()
    if token in _ORDINALS:
        return _ORDINALS[token]
    match = re.match(r"(\d+)(?:st|nd|rd|th)?$", token)
    if match:
        return int(match.group(1))
    return None


def extract_booster(paragraphs: list[str]) -> BoosterInformation | None:
    blob = " ".join(paragraphs)
    flight = None
    serial = None
    summary = None
    flight_match = re.search(
        r"(?:will be|was) the ([A-Za-z0-9]+)(?:st|nd|rd|th)? flight (?:for|of) the (?:first stage(?: booster)?|Falcon 9 first stage booster)",
        blob,
        flags=re.I,
    )
    if flight_match:
        flight = _parse_ordinal(flight_match.group(1))
    serial_match = re.search(r"\b(B1\d{3}(?:\.\d+)?)\b", blob)
    if serial_match:
        serial = serial_match.group(1)
    sentence_match = re.search(
        r"((?:This (?:will be|was) the [A-Za-z0-9]+(?:st|nd|rd|th)? flight)[^.]+(?:\.|$))",
        blob,
        flags=re.I,
    )
    if sentence_match:
        summary = sentence_match.group(1).strip()
    if not any([flight, serial, summary]):
        return None
    return BoosterInformation(serial=serial, flight_number=flight, summary=summary)


def extract_landing_details(paragraphs: list[str], tile_return_site: str | None) -> tuple[str | None, str | None]:
    blob = " ".join(paragraphs)
    named = re.search(
        r"land(?:ed|ing)? on (?:the )?([A-Z][A-Za-z0-9'’ \-]+?) droneship",
        blob,
    )
    lz = re.search(r"land(?:ed|ing)? on Landing Zone ([0-9A-Z\-]+)", blob, flags=re.I)
    method = tile_return_site.strip() if tile_return_site else None
    site = None
    if named:
        site = named.group(1).strip()
        method = method or "Droneship"
    elif lz:
        site = f"Landing Zone {lz.group(1).strip()}"
        method = method or "Landing Zone"
    elif method:
        site = method
    return method, site


def extract_payload(paragraphs: list[str], mission_type: str | None) -> PayloadInformation | None:
    blob = " ".join(paragraphs)
    count = None
    match = re.search(r"launch(?:ed|ing)? of (\d+)\s+Starlink", blob, flags=re.I)
    if not match:
        match = re.search(r"launched (\d+)\s+<|launched (\d+)\s+Starlink", blob, flags=re.I)
    if match:
        for group in match.groups():
            if group:
                count = int(group)
                break
    summary = None
    if count:
        summary = f"{count} Starlink satellites"
    elif mission_type:
        summary = None
    if not summary and not count:
        return None
    return PayloadInformation(summary=summary, satellite_count=count)


def parse_timings_entry(raw: dict[str, Any]) -> dict[str, Any]:
    window = raw.get("PrimaryLaunchWindow") or {}
    start = from_unix_seconds(unix_from_proto(raw.get("PrimaryLaunchDate")))
    window_open = from_unix_seconds(unix_from_proto(window.get("Open"))) if isinstance(window, dict) else None
    window_close = from_unix_seconds(unix_from_proto(window.get("Close"))) if isinstance(window, dict) else None
    tzero = from_unix_seconds(unix_from_proto(raw.get("TZeroLaunchDate")))
    paused = bool(raw.get("TZeroPaused"))
    hold = raw.get("TZeroValue")
    hold_seconds = int(hold) if isinstance(hold, (int, float)) else None
    exact = bool(raw.get("IsPrimaryLaunchTimeGiven")) or tzero is not None
    if window_open and start is None:
        start = window_open
    end = window_close
    if exact and tzero:
        start = tzero
        if not end:
            end = tzero
    is_window = bool(start and end and end != start and not exact)
    return {
        "start": start,
        "end": end or start,
        "tzero": tzero,
        "paused": paused,
        "hold_seconds": hold_seconds,
        "exact": exact and not is_window,
        "is_window": is_window,
        "order": raw.get("Order"),
    }


def _image_url(tile: dict[str, Any]) -> str | None:
    for key in ("imageDesktop", "imageMobile"):
        block = tile.get(key) or {}
        if isinstance(block, dict):
            url = block.get("url")
            if url:
                return sanitize_url(url, _ALLOWED_HOSTS)
    return None


def parse_tile(tile: dict[str, Any], *, site_base: str = "https://www.spacex.com") -> dict[str, Any]:
    slug = str(tile.get("link") or "").strip()
    if not slug:
        raise ValueError("launch tile missing link/slug")
    title = (tile.get("title") or tile.get("shortTitle") or "").strip()
    if not title:
        raise ValueError(f"launch tile {slug} missing title")
    launch_site = (tile.get("launchSite") or None)
    if isinstance(launch_site, str):
        launch_site = launch_site.strip() or None
    tile_start = parse_site_local(tile.get("launchDate"), tile.get("launchTime"), launch_site)
    tile_end = parse_site_local(tile.get("endDate") or tile.get("launchDate"), tile.get("endTime"), launch_site)
    override = tile.get("override") or {}
    override_start = None
    override_end = None
    if isinstance(override, dict):
        if override.get("date") and override.get("time"):
            override_start = parse_site_local(override.get("date"), override.get("time"), launch_site)
        if override.get("windowOpenDate"):
            override_start = parse_site_local(
                override.get("windowOpenDate"), override.get("windowOpenTime"), launch_site
            )
        if override.get("windowCloseDate"):
            override_end = parse_site_local(
                override.get("windowCloseDate"), override.get("windowCloseTime"), launch_site
            )
    cms_status = (tile.get("missionStatus") or "").strip() or None
    return {
        "id": slug,
        "slug": slug,
        "cms_id": tile.get("id"),
        "document_id": tile.get("documentId"),
        "correlation_id": tile.get("correlationId"),
        "mission_name": title,
        "vehicle": (tile.get("vehicle") or None),
        "launch_site": launch_site,
        "landing_site": (tile.get("returnSite") or None),
        "mission_type": tile.get("missionType"),
        "cms_status": cms_status,
        "cms_is_live": bool(tile.get("isLive")),
        "call_to_action": tile.get("callToAction"),
        "status": map_cms_status(cms_status),
        "tile_start": override_start or tile_start,
        "tile_end": override_end or tile_end or override_start or tile_start,
        "show_exact": str(tile.get("showLaunchTimeInsteadOfWindow") or "").lower() == "true",
        "return_datetime_text": tile.get("returnDateTime"),
        "official_url": official_url(slug, site_base),
        "image_url": _image_url(tile),
        "source_updated_at": parse_iso_aware(tile.get("updatedAt"))
        or parse_iso_aware(tile.get("publishedAt")),
    }


def parse_mission_detail(raw: dict[str, Any]) -> dict[str, Any]:
    paragraphs = [html_to_text(p.get("content")) or "" for p in (raw.get("paragraphs") or []) if p]
    paragraphs = [p for p in paragraphs if p]
    webcasts: list[Webcast] = []
    for item in raw.get("webcasts") or []:
        url = webcast_url(item)
        webcasts.append(
            Webcast(
                url=url,
                video_id=item.get("videoId"),
                provider=item.get("streamingVideoType"),
                title=item.get("title"),
                is_featured=bool(item.get("isFeatured")),
            )
        )
    featured = next((w for w in webcasts if w.is_featured and w.url), None)
    primary = featured or next((w for w in webcasts if w.url), None)
    pre = parse_timeline_entries(raw.get("preLaunchTimeline"), prelaunch=True)
    post = parse_timeline_entries(raw.get("postLaunchTimeline"), prelaunch=False)
    landing_method, landing_site = extract_landing_details(paragraphs, None)
    return {
        "description": "\n\n".join(paragraphs) or None,
        "paragraphs": paragraphs,
        "webcasts": webcasts,
        "webcast_url": primary.url if primary else None,
        "pre_milestones": pre,
        "post_milestones": post,
        "booster": extract_booster(paragraphs),
        "payload": extract_payload(paragraphs, raw.get("missionType")),
        "landing_method": landing_method,
        "landing_site": landing_site,
        "iss_enabled": bool(raw.get("toTheIssEnabled")),
        "iss_tense": raw.get("toTheIssTense"),
        "title": raw.get("title"),
        "mission_id": raw.get("missionId") or raw.get("link"),
        "correlation_id": raw.get("correlationId"),
        "call_to_action": raw.get("callToAction"),
    }


def merge_launch(
    tile: dict[str, Any],
    timings: dict[str, Any] | None,
    detail: dict[str, Any] | None,
    *,
    fetched_at: datetime | None = None,
) -> Launch:
    fetched = fetched_at or utcnow()
    start = tile.get("tile_start")
    end = tile.get("tile_end")
    exact = bool(tile.get("show_exact"))
    is_window = False
    paused = False
    hold = None
    if timings:
        start = timings.get("tzero") or timings.get("start") or start
        end = timings.get("end") or end or start
        exact = bool(timings.get("exact") or exact)
        is_window = bool(timings.get("is_window")) and not exact
        paused = bool(timings.get("paused"))
        hold = timings.get("hold_seconds")
    if start and end and end < start:
        # Window crossing is represented as end > start in UTC; if inverted, keep start.
        end = start
    if start and end and end > start and not exact:
        is_window = True
    if start and end and end == start:
        is_window = False

    landing_method = tile.get("landing_site")
    landing_site = tile.get("landing_site")
    description = None
    webcasts: list[Webcast] = []
    webcast_url_value = None
    booster = None
    payload = None
    milestones: list[Milestone] = []
    iss_enabled = False
    iss_tense = None
    if detail:
        description = detail.get("description")
        webcasts = detail.get("webcasts") or []
        webcast_url_value = detail.get("webcast_url")
        booster = detail.get("booster")
        payload = detail.get("payload")
        landing_method = detail.get("landing_method") or landing_method
        landing_site = detail.get("landing_site") or landing_site
        milestones = (detail.get("post_milestones") or []) + []
        iss_enabled = bool(detail.get("iss_enabled"))
        iss_tense = detail.get("iss_tense")
        if detail.get("title") and not tile.get("mission_name"):
            tile["mission_name"] = detail["title"]

    provenance = {
        "mission_name": Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL),
        "vehicle": Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL),
        "launch_site": Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL),
        "launch_time": Provenance(
            source=DataSource.SPACEX,
            confidence=Confidence.OFFICIAL,
            note="window" if is_window else ("exact" if exact else "scheduled"),
        ),
        "webcast": Provenance(source=DataSource.SPACEX, confidence=Confidence.OFFICIAL),
    }

    return Launch(
        id=tile["slug"],
        slug=tile["slug"],
        mission_name=tile["mission_name"],
        vehicle=tile.get("vehicle"),
        launch_site=tile.get("launch_site"),
        landing_site=landing_site,
        landing_method=landing_method,
        launch_time_start=start,
        launch_time_end=end,
        launch_timezone=timezone_for_site(tile.get("launch_site")),
        is_exact_time=bool(exact and start and not is_window),
        is_window=is_window,
        tzero_paused=paused,
        tzero_hold_seconds=hold,
        official_url=tile["official_url"],
        webcast_url=webcast_url_value,
        webcasts=webcasts,
        description=description,
        status=tile.get("status") or LaunchStatus.UNKNOWN,
        mission_type=tile.get("mission_type"),
        booster_information=booster,
        payload_information=payload,
        source_updated_at=tile.get("source_updated_at") or fetched,
        fetched_at=fetched,
        cms_status=tile.get("cms_status"),
        cms_is_live=bool(tile.get("cms_is_live")),
        call_to_action=tile.get("call_to_action"),
        correlation_id=tile.get("correlation_id"),
        iss_enabled=iss_enabled,
        iss_tense=iss_tense,
        return_datetime_text=tile.get("return_datetime_text"),
        image_url=tile.get("image_url"),
        milestones=milestones,
        field_provenance=provenance,
        extra={
            "cms_id": tile.get("cms_id"),
            "document_id": tile.get("document_id"),
            "timing_order": timings.get("order") if timings else None,
        },
    )


def detect_suspicious_empty(upcoming: Any, tiles: Any, timings: Any) -> str | None:
    if upcoming is None or tiles is None:
        return "missing launch payload"
    if not isinstance(upcoming, list) or not isinstance(tiles, list):
        return "launch payload is not a list"
    if timings is not None and not isinstance(timings, dict):
        return "timings payload is not an object"
    if len(tiles) == 0:
        return "empty launch catalog"
    return None
