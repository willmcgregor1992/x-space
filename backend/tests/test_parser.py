from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core.time import parse_site_local as site_local
from app.core.time import window_spans_midnight
from app.models.enums import LaunchStatus
from app.providers.sanitize import html_to_text
from app.providers.spacex_parse import (
    detect_suspicious_empty,
    parse_clock_to_seconds,
    parse_mission_detail,
    parse_tile,
    parse_timings_entry,
    webcast_url,
)


def test_upcoming_tile_has_slug_and_status(fixtures):
    tile = fixtures["upcoming"][0]
    parsed = parse_tile(tile)
    assert parsed["slug"] == "sl-15-15"
    assert parsed["status"] == LaunchStatus.SCHEDULED
    assert parsed["vehicle"] == "Falcon 9"
    assert parsed["launch_site"] and "SLC-4E" in parsed["launch_site"]


def test_timings_window_not_exact(fixtures):
    corr = fixtures["upcoming"][0]["correlationId"]
    parsed = parse_timings_entry(fixtures["timings"][corr])
    assert parsed["start"] == datetime(2026, 10, 23, 21, 30, tzinfo=UTC)
    assert parsed["end"] == datetime(2026, 10, 24, 1, 30, tzinfo=UTC)
    assert parsed["is_window"] is True
    assert parsed["exact"] is False
    assert window_spans_midnight(parsed["start"], parsed["end"]) is True


def test_merge_does_not_treat_window_open_as_t0(fixtures, sample_launches):
    launches, _ = sample_launches
    next_up = next(item for item in launches if item.slug == "sl-15-15")
    assert next_up.is_window is True
    assert next_up.is_exact_time is False
    assert next_up.launch_time_start.hour == 21


def test_in_progress_iss_mission(fixtures, sample_launches):
    launches, _ = sample_launches
    crs = next(item for item in launches if item.slug == "crs35")
    assert crs.cms_status == "in-progress"
    assert crs.status == LaunchStatus.IN_FLIGHT
    assert crs.iss_enabled is True
    assert crs.iss_tense == "present"
    assert crs.booster_information and crs.booster_information.flight_number == 8
    assert crs.landing_site and "Landing Zone 40" in crs.landing_site


def test_mission_detail_starlink_milestones(fixtures):
    detail = parse_mission_detail(fixtures["details"]["sl-15-15"])
    keys = {item.key for item in detail["post_milestones"]}
    assert "max_q" in keys
    assert "meco" in keys
    assert "landing" in keys
    assert "deploy" in keys
    assert detail["webcast_url"].startswith("https://x.com/i/broadcasts/")
    assert "Of Course I Still Love You" in (detail["landing_site"] or "")
    assert detail["booster"].flight_number == 36


def test_starship_profile_milestones(fixtures):
    detail = parse_mission_detail(fixtures["details"]["starship-flight-11"])
    keys = {item.key for item in detail["post_milestones"]}
    assert "hot_stage" in keys
    assert "liftoff" in keys


def test_html_stripped_not_rendered():
    text = html_to_text('Falcon 9 launched 27 <a href="https://www.starlink.com/">Starlink</a> satellites.')
    assert "<a" not in text
    assert "Starlink" in text


def test_clock_parser_and_prelaunch_sign():
    assert parse_clock_to_seconds("00:02:26") == 146
    assert parse_clock_to_seconds("01:02:04") == 3724
    assert parse_clock_to_seconds("08:24") == 504


def test_site_local_california_dst():
    utc = site_local("2026-10-23", "14:30:00", "SLC-4E, California")
    assert utc is not None
    assert utc.tzinfo is not None
    # 14:30 PDT = 21:30 UTC during DST
    assert utc == datetime(2026, 10, 23, 21, 30, tzinfo=UTC)


def test_florida_window_crossing_midnight():
    start = site_local("2026-06-01", "19:00:00", "SLC-40, Florida")
    end = site_local("2026-06-01", "23:30:00", "SLC-40, Florida")
    assert start is not None and end is not None
    assert end > start
    assert window_spans_midnight(start, end)


def test_suspicious_empty_payloads():
    assert detect_suspicious_empty(None, [], {}) == "missing launch payload"
    assert detect_suspicious_empty([], "nope", {}) == "launch payload is not a list"
    assert detect_suspicious_empty([], [{"id": 1}], "bad") == "timings payload is not an object"
    assert detect_suspicious_empty([], [], {}) == "empty launch catalog"
    assert detect_suspicious_empty([], [{"id": 1}], {}) is None


def test_webcast_url_types():
    assert webcast_url({"videoId": "1YGNrbnzdqLGw", "streamingVideoType": "x-live-studio"}).endswith(
        "/1YGNrbnzdqLGw"
    )
    assert "status" in webcast_url({"videoId": "1961181999567368275", "streamingVideoType": "x.com"})


def test_parser_rejects_tile_without_slug():
    with pytest.raises(ValueError):
        parse_tile({"title": "Nope"})


def test_failed_parse_does_not_drop_valid_siblings(provider, fixtures):
    tiles = list(fixtures["tiles"]) + [{"title": "broken"}]
    launches, meta = provider.build_launches(
        upcoming_raw=fixtures["upcoming"],
        tiles_raw=tiles,
        timings_raw=fixtures["timings"],
        details_raw=fixtures["details"],
        fetched_at=datetime.now(tz=UTC),
    )
    assert launches
    assert meta["parse_errors"] >= 1
    assert any(item.slug == "sl-15-15" for item in launches)
