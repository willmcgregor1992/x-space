from __future__ import annotations

from datetime import UTC, datetime

from app.providers.spacex_parse import merge_launch, parse_tile, parse_timings_entry


def test_schedule_slip_updates_window():
    tile = {
        "link": "sl-15-15",
        "title": "Starlink Mission",
        "vehicle": "Falcon 9",
        "launchSite": "SLC-4E, California",
        "missionStatus": "upcoming",
        "correlationId": "abc",
        "isLive": False,
    }
    parsed = parse_tile(tile)
    first = parse_timings_entry(
        {
            "PrimaryLaunchDate": {"Seconds": 1792791000},
            "PrimaryLaunchWindow": {
                "Open": {"Seconds": 1792791000},
                "Close": {"Seconds": 1792805400},
            },
            "IsPrimaryLaunchTimeGiven": False,
        }
    )
    launch_a = merge_launch(parsed, first, None, fetched_at=datetime.now(tz=UTC))
    slipped = parse_timings_entry(
        {
            "PrimaryLaunchDate": {"Seconds": 1792791000 + 3600},
            "PrimaryLaunchWindow": {
                "Open": {"Seconds": 1792791000 + 3600},
                "Close": {"Seconds": 1792805400 + 3600},
            },
            "IsPrimaryLaunchTimeGiven": False,
        }
    )
    launch_b = merge_launch(parsed, slipped, None, fetched_at=datetime.now(tz=UTC))
    assert launch_b.launch_time_start != launch_a.launch_time_start
    assert (launch_b.launch_time_start - launch_a.launch_time_start).total_seconds() == 3600


def test_tzero_promotes_window_to_exact():
    tile = parse_tile(
        {
            "link": "sl-x",
            "title": "Starlink Mission",
            "vehicle": "Falcon 9",
            "launchSite": "SLC-4E, California",
            "missionStatus": "upcoming",
            "correlationId": "abc",
        }
    )
    timings = parse_timings_entry(
        {
            "PrimaryLaunchDate": {"Seconds": 1792791000},
            "PrimaryLaunchWindow": {
                "Open": {"Seconds": 1792791000},
                "Close": {"Seconds": 1792805400},
            },
            "TZeroLaunchDate": {"Seconds": 1792792800},
            "IsPrimaryLaunchTimeGiven": True,
        }
    )
    launch = merge_launch(tile, timings, None, fetched_at=datetime.now(tz=UTC))
    assert launch.is_exact_time is True
    assert launch.is_window is False
    assert launch.launch_time_start == datetime(2026, 10, 23, 22, 0, tzinfo=UTC)
