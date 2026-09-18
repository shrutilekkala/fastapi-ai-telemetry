from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

from fastapi_ai_telemetry import (
    AITelemetryMiddleware,
    CompositeExporter,
    JsonLogExporter,
    PrometheusExporter,
    trace_model_call,
)


class SummaryRequest(BaseModel):
    text: str


app = FastAPI(title="AI Telemetry Example")
app.add_middleware(
    AITelemetryMiddleware,
    exporter=CompositeExporter(
        [JsonLogExporter(), PrometheusExporter(registry=REGISTRY, namespace="example")]
    ),
    service_name="summary-api",
    header_allowlist=("x-tenant",),
)


@app.post("/summarize")
def summarize(request: SummaryRequest) -> dict[str, str]:
    words = request.text.split()
    with trace_model_call("demo", "extractive-v1", metadata={"operation": "summarize"}) as call:
        summary = " ".join(words[:12])
        call.set_usage(input_tokens=len(words), output_tokens=len(summary.split()))
    return {"summary": summary}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
