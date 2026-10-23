from __future__ import annotations

from typing import Protocol

from app.models.domain import Launch


class LaunchProvider(Protocol):
    """Future providers (weather, TLE, pad conditions) implement this surface."""

    name: str

    async def fetch_launches(self) -> list[Launch]:
        """Return normalized launches. Must not raise away the last good cache."""
        ...
