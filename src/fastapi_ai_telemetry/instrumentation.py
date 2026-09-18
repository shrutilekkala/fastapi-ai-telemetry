from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from time import perf_counter

from .context import get_current_trace
from .models import ModelCall

Metadata = Mapping[str, str | int | float | bool | None]


@contextmanager
def trace_model_call(
    provider: str,
    model: str,
    *,
    metadata: Metadata | None = None,
) -> Iterator[ModelCall]:
    """Record one model call inside the active request trace.

    Prompt and response bodies are deliberately not accepted. Applications opt in
    only to operational metadata and aggregate token counts.
    """

    call = ModelCall(provider=provider, model=model, metadata=dict(metadata or {}))
    started_at = perf_counter()
    try:
        yield call
    except Exception as error:
        call.success = False
        call.error_type = type(error).__name__
        raise
    finally:
        call.duration_ms = round((perf_counter() - started_at) * 1000, 3)
        trace = get_current_trace()
        if trace is not None:
            trace.model_calls.append(call)
