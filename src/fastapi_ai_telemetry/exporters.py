from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Awaitable, Iterable
from typing import Protocol

from .models import RequestTrace


class TraceExporter(Protocol):
    def emit(self, trace: RequestTrace) -> Awaitable[None] | None: ...


async def emit_trace(exporter: TraceExporter, trace: RequestTrace) -> None:
    result = exporter.emit(trace)
    if inspect.isawaitable(result):
        await result


class InMemoryExporter:
    """Thread-safe-enough async collector intended for tests and local development."""

    def __init__(self) -> None:
        self.traces: list[dict[str, object]] = []
        self._lock = asyncio.Lock()

    async def emit(self, trace: RequestTrace) -> None:
        async with self._lock:
            self.traces.append(trace.to_dict())

    async def clear(self) -> None:
        async with self._lock:
            self.traces.clear()


class JsonLogExporter:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("fastapi_ai_telemetry")

    def emit(self, trace: RequestTrace) -> None:
        self.logger.info(json.dumps(trace.to_dict(), sort_keys=True, separators=(",", ":")))


class CompositeExporter:
    def __init__(self, exporters: Iterable[TraceExporter]) -> None:
        self.exporters = tuple(exporters)

    async def emit(self, trace: RequestTrace) -> None:
        for exporter in self.exporters:
            await emit_trace(exporter, trace)
