from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_ai_telemetry import AITelemetryMiddleware, InMemoryExporter, trace_model_call


def build_client(exporter: object, *, allowlist: tuple[str, ...] = ()) -> TestClient:
    app = FastAPI()
    app.add_middleware(
        AITelemetryMiddleware,
        exporter=exporter,
        service_name="inventory-api",
        header_allowlist=allowlist,
    )

    @app.get("/items/{item_id}")
    def get_item(item_id: int) -> dict[str, int]:
        with trace_model_call("openai", "test-model", metadata={"operation": "classify"}) as call:
            call.set_usage(input_tokens=12, output_tokens=4)
        return {"item_id": item_id}

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("expected test failure")

    return TestClient(app, raise_server_exceptions=False)


def test_records_route_model_usage_and_request_id() -> None:
    exporter = InMemoryExporter()
    client = build_client(exporter)

    response = client.get("/items/42", headers={"x-request-id": "trace-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "trace-123"
    trace = exporter.traces[0]
    assert trace["route"] == "/items/{item_id}"
    assert trace["path"] == "/items/42"
    assert trace["input_tokens"] == 12
    assert trace["output_tokens"] == 4
    assert trace["model_calls"][0]["metadata"] == {"operation": "classify"}


def test_only_allowlisted_headers_are_captured_and_secrets_are_redacted() -> None:
    exporter = InMemoryExporter()
    client = build_client(exporter, allowlist=("authorization", "x-tenant"))

    client.get(
        "/items/1",
        headers={"authorization": "Bearer secret", "x-tenant": "north", "x-ignore": "value"},
    )

    headers = exporter.traces[0]["request_headers"]
    assert headers == {"authorization": "[REDACTED]", "x-tenant": "north"}


def test_invalid_request_id_is_replaced() -> None:
    exporter = InMemoryExporter()
    client = build_client(exporter)

    response = client.get("/items/1", headers={"x-request-id": "a" * 129})

    assert response.headers["x-request-id"] != "a" * 129
    assert len(response.headers["x-request-id"]) == 36


def test_application_errors_are_recorded() -> None:
    exporter = InMemoryExporter()
    client = build_client(exporter)

    response = client.get("/failure")

    assert response.status_code == 500
    assert exporter.traces[0]["status_code"] == 500
    assert exporter.traces[0]["error_type"] == "RuntimeError"


def test_exporter_failure_does_not_break_the_application() -> None:
    class FailingExporter:
        def emit(self, trace: object) -> None:
            raise RuntimeError("collector unavailable")

    client = build_client(FailingExporter())
    response = client.get("/items/7")

    assert response.status_code == 200
    assert response.json() == {"item_id": 7}
