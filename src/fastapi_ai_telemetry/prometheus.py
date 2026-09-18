from __future__ import annotations

from typing import Any

from .models import RequestTrace


class PrometheusExporter:
    """Translate completed traces into bounded-cardinality Prometheus metrics."""

    def __init__(self, *, registry: Any = None, namespace: str = "ai_telemetry") -> None:
        try:
            from prometheus_client import REGISTRY, Counter, Histogram
        except ImportError as error:  # pragma: no cover - exercised without the optional extra
            raise RuntimeError(
                "PrometheusExporter requires `pip install fastapi-ai-telemetry[prometheus]`"
            ) from error

        registry = registry or REGISTRY
        self.requests = Counter(
            f"{namespace}_http_requests_total",
            "Completed HTTP requests.",
            ("service", "method", "route", "status"),
            registry=registry,
        )
        self.request_duration = Histogram(
            f"{namespace}_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            ("service", "method", "route"),
            registry=registry,
        )
        self.model_calls = Counter(
            f"{namespace}_model_calls_total",
            "Instrumented model calls.",
            ("service", "provider", "model", "success"),
            registry=registry,
        )
        self.model_duration = Histogram(
            f"{namespace}_model_call_duration_seconds",
            "Model-call duration in seconds.",
            ("service", "provider", "model"),
            registry=registry,
        )
        self.model_tokens = Counter(
            f"{namespace}_model_tokens_total",
            "Model tokens by direction.",
            ("service", "provider", "model", "direction"),
            registry=registry,
        )

    def emit(self, trace: RequestTrace) -> None:
        request_labels = (trace.service, trace.method, trace.route, str(trace.status_code))
        self.requests.labels(*request_labels).inc()
        self.request_duration.labels(trace.service, trace.method, trace.route).observe(
            trace.duration_ms / 1000
        )

        for call in trace.model_calls:
            labels = (trace.service, call.provider, call.model)
            self.model_calls.labels(*labels, str(call.success).lower()).inc()
            self.model_duration.labels(*labels).observe(call.duration_ms / 1000)
            self.model_tokens.labels(*labels, "input").inc(call.input_tokens)
            self.model_tokens.labels(*labels, "output").inc(call.output_tokens)
