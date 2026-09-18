from prometheus_client import CollectorRegistry, generate_latest

from fastapi_ai_telemetry import ModelCall, PrometheusExporter, RequestTrace


def test_prometheus_exporter_emits_request_and_model_metrics() -> None:
    registry = CollectorRegistry()
    exporter = PrometheusExporter(registry=registry, namespace="test_ai")
    trace = RequestTrace(
        request_id="request-1",
        service="inventory-api",
        method="POST",
        path="/ask",
        route="/ask",
        status_code=200,
        duration_ms=125,
        model_calls=[
            ModelCall(
                provider="openai",
                model="test-model",
                duration_ms=80,
                input_tokens=10,
                output_tokens=3,
            )
        ],
    )

    exporter.emit(trace)
    metrics = generate_latest(registry).decode()

    assert 'test_ai_http_requests_total{method="POST",route="/ask"' in metrics
    assert 'test_ai_model_calls_total{model="test-model",provider="openai"' in metrics
    assert 'direction="input"' in metrics
