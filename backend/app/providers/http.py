from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ProviderHttpError(RuntimeError):
    pass


class TransientHttpError(ProviderHttpError):
    pass


class SpaceXHttpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            headers={"User-Agent": settings.spacex_user_agent, "Accept": "application/json"},
            timeout=httpx.Timeout(settings.spacex_http_timeout_seconds),
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_json(self, url: str, *, bust_cache: bool = False) -> Any:
        return await self._get_json(url, bust_cache=bust_cache)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, TransientHttpError)),
    )
    async def _get_json(self, url: str, *, bust_cache: bool = False) -> Any:
        params = {"_": int(__import__("time").time())} if bust_cache else None
        try:
            response = await self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("spacex request failed url=%s error=%s", url, exc)
            raise
        if response.status_code >= 500 or response.status_code == 429:
            raise TransientHttpError(f"{url} returned {response.status_code}")
        if response.status_code >= 400:
            raise ProviderHttpError(f"{url} returned {response.status_code}")
        if not response.content:
            raise ProviderHttpError(f"{url} returned an empty body")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderHttpError(f"{url} returned non-JSON") from exc
