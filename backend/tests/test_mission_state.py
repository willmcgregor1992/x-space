from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.domain import Launch
from app.models.enums import LaunchStatus, LiveStatus, VisualizerMode
from app.services.mission_state import MissionStateEngine
from app.services.profiles import merge_milestones, select_profile

ENGINE = MissionStateEngine()


def _launch(**kwargs) -> Launch:
    now = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
    base = dict(
        id="demo",
        slug="demo",
        mission_name="Starlink Mission",
        vehicle="Falcon 9",
        launch_site="SLC-4E, California",
        official_url="https://www.spacex.com/launches/demo",
        fetched_at=now,
        launch_time_start=datetime(2026, 10, 23, 21, 30, tzinfo=UTC),
        launch_time_end=datetime(2026, 10, 23, 21, 30, tzinfo=UTC),
        is_exact_time=True,
        is_window=False,
        cms_status="upcoming",
        mission_type="starlink",
    )
    base.update(kwargs)
    launch = Launch(**base)
    profile = select_profile(launch.vehicle, launch.mission_type, launch.iss_enabled)
    launch.milestones = merge_milestones(profile, launch.milestones)
    launch.profile_id = profile.id
    return launch


def test_before_launch_countdown():
    launch = _launch()
    now = launch.launch_time_start - timedelta(hours=2)
    state = ENGINE.compute(launch, now)
    assert state.state == LaunchStatus.COUNTDOWN
    assert state.t_plus_seconds == -7200
    assert state.progress == 0
    assert state.visualizer_mode == VisualizerMode.PRELAUNCH
    assert state.clock_prefix == "T−"


def test_window_is_not_t0():
    launch = _launch(
        is_exact_time=False,
        is_window=True,
        launch_time_end=datetime(2026, 10, 24, 1, 30, tzinfo=UTC),
    )
    now = datetime(2026, 10, 23, 22, 0, tzinfo=UTC)
    state = ENGINE.compute(launch, now)
    assert state.state == LaunchStatus.WINDOW_OPEN
    assert state.t_plus_seconds is None
    assert state.progress == 0
    assert "window" in " ".join(state.notes).lower()


def test_exact_t0_transitions():
    launch = _launch()
    state = ENGINE.compute(launch, launch.launch_time_start)
    assert state.state == LaunchStatus.LAUNCHED
    assert state.t_plus_seconds == 0
    assert state.clock_prefix == "T+"


def test_after_launch_estimated_progress():
    launch = _launch()
    now = launch.launch_time_start + timedelta(seconds=180)
    state = ENGINE.compute(launch, now)
    assert state.state == LaunchStatus.IN_FLIGHT
    assert state.t_plus_seconds == 180
    assert 0 < state.progress < 1
    assert state.is_estimated is True
    assert state.visualizer_mode == VisualizerMode.ASCENT
    assert any("Estimated" in note for note in state.notes)


def test_completed_mission():
    launch = _launch(cms_status="final", status=LaunchStatus.MISSION_COMPLETE)
    now = launch.launch_time_start + timedelta(hours=5)
    state = ENGINE.compute(launch, now)
    assert state.state == LaunchStatus.MISSION_COMPLETE
    assert state.progress == 1
    assert state.live_status == LiveStatus.COMPLETED
    assert state.is_estimated is False


def test_missing_milestone_data_uses_profile():
    launch = _launch(milestones=[])
    profile = select_profile(launch.vehicle, launch.mission_type, False)
    now = launch.launch_time_start + timedelta(seconds=80)
    state = ENGINE.compute(launch, now, profile)
    assert state.previous_milestone is not None
    assert state.next_milestone is not None
    assert state.previous_milestone.is_estimated is True


def test_iss_docked_is_not_launch_live():
    launch = _launch(
        mission_name="CRS-35 Mission",
        mission_type="resupply",
        cms_status="in-progress",
        iss_enabled=True,
        iss_tense="present",
        launch_time_start=datetime(2026, 10, 13, 10, 33, tzinfo=UTC),
        launch_time_end=datetime(2026, 10, 13, 10, 33, tzinfo=UTC),
    )
    now = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
    state = ENGINE.compute(launch, now)
    assert state.visualizer_mode == VisualizerMode.ISS
    assert state.live_status == LiveStatus.OFFLINE
    assert state.current_phase == "Docked"
    assert state.is_estimated is False


def test_hold_clock():
    launch = _launch(tzero_paused=True, tzero_hold_seconds=95, is_exact_time=True)
    state = ENGINE.compute(launch, datetime(2026, 10, 23, 21, 40, tzinfo=UTC))
    assert state.hold is True
    assert state.t_plus_seconds == -95
    assert state.clock_label.endswith("01:35")


def test_stale_source_does_not_change_math():
    fetched = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    launch = _launch(fetched_at=fetched, source_updated_at=fetched)
    now = launch.launch_time_start - timedelta(minutes=10)
    state = ENGINE.compute(launch, now)
    assert state.t_plus_seconds == -600
