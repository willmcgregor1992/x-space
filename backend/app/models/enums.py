from enum import StrEnum


class LaunchStatus(StrEnum):
    SCHEDULED = "scheduled"
    WINDOW_OPEN = "window_open"
    WEBCAST_LIVE = "webcast_live"
    COUNTDOWN = "countdown"
    LAUNCHED = "launched"
    IN_FLIGHT = "in_flight"
    PAYLOAD_DEPLOYED = "payload_deployed"
    BOOSTER_LANDED = "booster_landed"
    MISSION_COMPLETE = "mission_complete"
    DELAYED = "delayed"
    SCRUBBED = "scrubbed"
    UNKNOWN = "unknown"


class LiveStatus(StrEnum):
    OFFLINE = "offline"
    PRELAUNCH = "prelaunch"
    WEBCAST_LIVE = "webcast_live"
    LAUNCH_WINDOW = "launch_window"
    MISSION_ACTIVE = "mission_active"
    COMPLETED = "completed"


class Confidence(StrEnum):
    OFFICIAL = "official"
    ESTIMATED = "estimated"


class DataSource(StrEnum):
    SPACEX = "spacex.com"
    MISSION_PROFILE = "mission_profile"
    ESTIMATED = "estimated"
    CACHE = "cache"
    SIMULATION = "simulation"


class VehicleFamily(StrEnum):
    FALCON_9 = "Falcon 9"
    FALCON_HEAVY = "Falcon Heavy"
    STARSHIP = "Starship"
    FALCON_1 = "Falcon 1"
    UNKNOWN = "Unknown"


class VisualizerMode(StrEnum):
    PRELAUNCH = "prelaunch"
    ASCENT = "ascent"
    ORBIT = "orbit"
    ISS = "iss"
    STARSHIP = "starship"
    COMPLETE = "complete"
