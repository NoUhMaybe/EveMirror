from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

Permission = Literal["read_only", "low_risk", "sensitive"]


@dataclass(frozen=True)
class Principal:
    id: str
    device_ids: frozenset[str]
    allow_mutations: bool = False
    home_entities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ToolContext:
    principal: Principal
    session_id: UUID
    turn_id: UUID
    device_id: str | None = None
    operation_id: UUID | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolResult:
    status: Literal["success", "error"]
    data: Any = None
    code: str | None = None
    message: str | None = None
    replayed: bool = False

    @classmethod
    def error(cls, code: str, message: str) -> ToolResult:
        return cls("error", code=code, message=message)

    def payload(self) -> dict:
        if self.status == "success":
            result = {"status": self.status, "data": self.data}
        else:
            result = {"status": self.status, "error": {"code": self.code, "message": self.message}}
            if self.data is not None:
                result["error"]["details"] = self.data
        if self.replayed:
            result["replayed"] = True
        return result


@dataclass
class Tool:
    definition: ToolDefinition
    handler: Callable[[dict, ToolContext], Awaitable[ToolResult]]
    permission: Permission = "read_only"
    mutates: bool = False
    requires_confirmation: bool = False
    timeout: float = 10
    available: Callable[[], bool] = lambda: True
    argument_model: type[BaseModel] | None = None
    operation_identity: Literal["arguments", "call"] = "arguments"
