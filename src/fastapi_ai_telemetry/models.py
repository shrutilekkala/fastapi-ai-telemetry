from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ModelCall:
    provider: str
    model: str
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    success: bool = True
    error_type: str | None = None
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def set_usage(self, *, input_tokens: int = 0, output_tokens: int = 0) -> None:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must be non-negative")
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RequestTrace:
    request_id: str
    service: str
    method: str
    path: str
    route: str
    status_code: int = 500
    duration_ms: float = 0.0
    error_type: str | None = None
    request_headers: dict[str, str] = field(default_factory=dict)
    model_calls: list[ModelCall] = field(default_factory=list)

    @property
    def input_tokens(self) -> int:
        return sum(call.input_tokens for call in self.model_calls)

    @property
    def output_tokens(self) -> int:
        return sum(call.output_tokens for call in self.model_calls)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "service": self.service,
            "method": self.method,
            "path": self.path,
            "route": self.route,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "request_headers": dict(self.request_headers),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model_calls": [call.to_dict() for call in self.model_calls],
        }
