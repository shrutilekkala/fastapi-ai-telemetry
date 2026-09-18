import pytest

from fastapi_ai_telemetry import ModelCall, trace_model_call


def test_token_counts_must_be_non_negative() -> None:
    call = ModelCall(provider="provider", model="model")

    with pytest.raises(ValueError, match="non-negative"):
        call.set_usage(input_tokens=-1)


def test_model_errors_are_reraised() -> None:
    with pytest.raises(RuntimeError, match="model unavailable"):
        with trace_model_call("provider", "model"):
            raise RuntimeError("model unavailable")
