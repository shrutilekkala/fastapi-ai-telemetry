from __future__ import annotations

import logging
from collections.abc import Iterable
from time import perf_counter
from typing import Any
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .context import reset_current_trace, set_current_trace
from .exporters import TraceExporter, emit_trace
from .models import RequestTrace

_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}
_LOGGER = logging.getLogger("fastapi_ai_telemetry")


def _safe_request_id(candidate: str | None) -> str:
    if candidate and len(candidate) <= 128 and all(32 <= ord(char) < 127 for char in candidate):
        return candidate
    return str(uuid4())


class AITelemetryMiddleware:
    """Pure ASGI middleware for request and model-call telemetry."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        exporter: TraceExporter,
        service_name: str = "fastapi-app",
        request_id_header: str = "x-request-id",
        header_allowlist: Iterable[str] = (),
    ) -> None:
        self.app = app
        self.exporter = exporter
        self.service_name = service_name
        self.request_id_header = request_id_header.lower()
        self.header_allowlist = {header.lower() for header in header_allowlist}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        request_id = _safe_request_id(raw_headers.get(self.request_id_header))
        captured_headers = {
            key: "[REDACTED]" if key in _SENSITIVE_HEADERS else value
            for key, value in raw_headers.items()
            if key in self.header_allowlist
        }
        trace = RequestTrace(
            request_id=request_id,
            service=self.service_name,
            method=scope.get("method", ""),
            path=scope.get("path", ""),
            route=scope.get("path", ""),
            request_headers=captured_headers,
        )
        token = set_current_trace(trace)
        started_at = perf_counter()

        async def send_with_trace(message: Message) -> None:
            if message["type"] == "http.response.start":
                trace.status_code = int(message["status"])
                header_name = self.request_id_header.encode("latin-1")
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != header_name
                ]
                headers.append(
                    (self.request_id_header.encode("latin-1"), request_id.encode("latin-1"))
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        except Exception as error:
            trace.status_code = 500
            trace.error_type = type(error).__name__
            raise
        finally:
            trace.duration_ms = round((perf_counter() - started_at) * 1000, 3)
            route: Any = scope.get("route")
            trace.route = getattr(route, "path", trace.path)
            reset_current_trace(token)
            try:
                await emit_trace(self.exporter, trace)
            except Exception:
                # Observability must never become an application outage.
                _LOGGER.exception("telemetry exporter failed")
