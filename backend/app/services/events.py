from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from app.core.time import utcnow


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=32)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: str, data: dict[str, Any]) -> None:
        payload = json.dumps({"event": event, "data": data, "server_time": utcnow().isoformat()})
        stale: list[asyncio.Queue[str]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self.unsubscribe(queue)

    async def heartbeat(self) -> None:
        await self.publish("heartbeat", {"ts": datetime.now().astimezone().isoformat()})


async def sse_stream(broker: EventBroker) -> AsyncIterator[str]:
    queue = broker.subscribe()
    try:
        yield _format("ready", {"ok": True})
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            yield f"data: {message}\n\n"
    finally:
        broker.unsubscribe(queue)


def _format(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps({"event": event, "data": data, "server_time": utcnow().isoformat()})
    return f"data: {payload}\n\n"
