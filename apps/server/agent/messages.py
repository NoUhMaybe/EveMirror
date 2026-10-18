"""Internal contracts. Provider state is private and never serialized into the public API."""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] | str


@dataclass
class LLMMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    call_id: str | None = None
    tool_name: str | None = None
    is_error: bool = False
    provider: str | None = None
    provider_data: Any = field(default=None, repr=False)


@dataclass(frozen=True)
class GenerationSettings:
    max_output_tokens: int = 1024
    temperature: float | None = None
    think: bool | None = None
    reasoning_effort: str | None = None


@dataclass
class LLMResponse:
    message: LLMMessage
    provider: str
    model: str
    status: Literal["complete", "tool_calls", "length", "refused"] = "complete"
    usage: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentStreamEvent:
    """Reserved normalized interface; adapters currently implement non-streaming generation."""

    type: Literal["text_delta", "tool_call_complete", "final", "cancelled", "error"]
    text: str = ""
    call: ToolCall | None = None
    response: LLMResponse | None = None
    error_code: str | None = None
