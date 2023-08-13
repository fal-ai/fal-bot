from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx
from httpx import HTTPStatusError

from fal_bot import config


@dataclass
class _Status:
    ...


@dataclass
class Queued(_Status):
    position: int


@dataclass
class InProgress(_Status):
    logs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Completed(_Status):
    ...


@dataclass
class RequestHandle:
    request_id: str


@dataclass
class QueueClient:
    session: httpx.AsyncClient

    async def submit(self, data: dict[str, Any]) -> RequestHandle:
        response = await self.session.post("/submit/", json=data)
        response.raise_for_status()

        data = response.json()
        return RequestHandle(data["request_id"])

    async def status(self, request: RequestHandle) -> _Status:
        response = await self.session.get(f"/requests/{request.request_id}/status/")
        response.raise_for_status()

        if response.status_code == 200:
            return Completed()

        data = response.json()
        if data["status"] == "IN_QUEUE":
            return Queued(position=data["queue_position"])
        elif data["status"] == "IN_PROGRESS":
            return InProgress(logs=data["logs"])
        else:
            raise ValueError(f"Unknown status: {data['status']}")

    async def result(self, request: RequestHandle) -> dict[str, Any]:
        response = await self.session.get(f"/requests/{request.request_id}/response/")
        response.raise_for_status()

        data = response.json()
        return data

    async def poll_until_ready(
        self,
        request: RequestHandle,
        *,
        __poll_delay: float = 0.2,
    ) -> AsyncIterator[Queued | InProgress]:
        while True:
            status = await self.status(request)

            if isinstance(status, Completed):
                return

            yield status  # type: ignore
            await asyncio.sleep(__poll_delay)


@asynccontextmanager
async def queue_client(
    url: str,
    *,
    on_error: Callable[[HTTPStatusError], Awaitable[None]] | None = None,
) -> AsyncIterator[QueueClient]:
    async with httpx.AsyncClient(
        base_url=url + "/fal/queue",
        headers={"Authorization": f"Key {config.FAL_SECRET}"},
    ) as client:
        try:
            yield QueueClient(client)
        except HTTPStatusError as e:
            if on_error is None:
                raise
            else:
                await on_error(e)
