from contextvars import ContextVar, Token

from .models import RequestTrace

_current_trace: ContextVar[RequestTrace | None] = ContextVar(
    "fastapi_ai_telemetry_current_trace", default=None
)


def get_current_trace() -> RequestTrace | None:
    return _current_trace.get()


def set_current_trace(trace: RequestTrace) -> Token[RequestTrace | None]:
    return _current_trace.set(trace)


def reset_current_trace(token: Token[RequestTrace | None]) -> None:
    _current_trace.reset(token)
