"""Only trusted registration and local JSON Schema references are accepted."""

import re

from jsonschema import Draft202012Validator
from referencing import Registry

from apps.config import AgentLimits
from apps.server.providers.base import json_text
from apps.server.tools.base import Principal, Tool
from apps.server.tools.permissions import denied


def validate_schema(schema: dict):
    if len(json_text(schema).encode()) > 32768 or schema.get("type") != "object":
        raise ValueError("Tool schema must be a bounded JSON object schema")
    nodes = 0

    def visit(value, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 2048 or depth > 32:
            raise ValueError("Tool schema is too complex")
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"$ref", "$dynamicRef"} and (
                    not isinstance(item, str) or not item.startswith("#")
                ):
                    raise ValueError("External schema references are forbidden")
                if key == "$id":
                    raise ValueError("Schema base URI overrides are forbidden")
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                visit(item, depth + 1)

    visit(schema)
    Draft202012Validator.check_schema(schema)


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        name = tool.definition.name
        if not re.fullmatch(r"[a-z][a-z0-9_.]{0,127}", name) or name in self.tools:
            raise ValueError("Invalid or duplicate canonical tool name")
        if tool.mutates and tool.permission == "read_only":
            raise ValueError("Mutating tools require a state-change permission")
        validate_schema(tool.definition.parameters)
        self.tools[name] = tool

    def definitions(self, principal: Principal, limits: AgentLimits):
        return [
            tool.definition
            for tool in self.tools.values()
            if tool.available() and not denied(tool, principal, limits)
        ]

    def validate(self, tool: Tool, arguments: dict) -> dict:
        # Empty registry disables network retrieval even for a subsequently modified schema.
        Draft202012Validator(tool.definition.parameters, registry=Registry()).validate(arguments)
        if tool.argument_model:
            return tool.argument_model.model_validate_json(
                json_text(arguments), strict=True
            ).model_dump(mode="json")
        return arguments

    def status(self, principal, limits):
        return [
            {
                "name": name,
                "available": tool.available(),
                "permission": tool.permission,
                "mutates": tool.mutates,
                "requires_confirmation": tool.requires_confirmation,
                "allowed": denied(tool, principal, limits) is None,
            }
            for name, tool in self.tools.items()
        ]
