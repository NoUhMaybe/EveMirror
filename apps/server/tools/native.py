from datetime import UTC, datetime
from uuid import uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field

from apps.server.gateway import Gateway, GatewayError
from apps.server.providers.base import json_text
from apps.server.tools.base import Tool, ToolDefinition, ToolResult
from apps.server.tools.registry import ToolRegistry
from packages.protocol import DeviceId, GetStatus, SetBrightness


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class NoArguments(Arguments):
    pass


class DeviceArguments(Arguments):
    device_id: DeviceId | None = None


class BrightnessArguments(DeviceArguments):
    percent: int = Field(ge=0, le=100)


def register_native(registry: ToolRegistry, gateway: Gateway, clock=None):
    clock = clock or (lambda: datetime.now(UTC))

    async def get_time(arguments, context):
        return ToolResult("success", {"utc": clock().isoformat(), "timezone": "UTC"})

    registry.register(
        Tool(
            ToolDefinition(
                "system.get_time",
                "Get the current UTC date and time.",
                NoArguments.model_json_schema(),
            ),
            get_time,
            argument_model=NoArguments,
        )
    )

    def device(arguments, context):
        device_id = arguments.get("device_id") or context.device_id
        if device_id is None and len(context.principal.device_ids) == 1:
            device_id = next(iter(context.principal.device_ids))
        if device_id not in context.principal.device_ids:
            return None
        return device_id

    async def command(arguments, context, mutate):
        device_id = device(arguments, context)
        if device_id is None:
            return ToolResult.error("device_not_authorized", "Select an authorized mirror device.")
        payload = (
            SetBrightness(action="set_brightness", percent=arguments["percent"])
            if mutate
            else GetStatus(action="get_status")
        )
        # Stable across API retries, new tool IDs, and server restarts for the same turn/action.
        request_id = (
            uuid5(
                context.turn_id, context.principal.id + device_id + json_text(payload.model_dump())
            )
            if mutate
            else uuid4()
        )
        try:
            ack = await gateway.command(device_id, request_id, payload)
        except GatewayError as exc:
            return ToolResult.error(exc.code, "Mirror command failed; its outcome may be unknown.")
        if ack.payload.status == "error":
            return ToolResult.error(
                ack.payload.code,
                "The edge reported a command failure.",
            )
        return ToolResult(
            "success",
            {
                "device_id": device_id,
                "ack_status": ack.payload.status,
                "replayed": ack.payload.replayed,
                "hardware": ack.payload.hardware.model_dump(mode="json"),
                "note": "Target is acknowledged, not measured; "
                "fade completion and actual brightness are unknown.",
            },
        )

    async def get_status(arguments, context):
        return await command(arguments, context, False)

    async def set_brightness(arguments, context):
        return await command(arguments, context, True)

    registry.register(
        Tool(
            ToolDefinition(
                "mirror.get_status",
                "Get acknowledged target brightness and hardware availability. "
                "Actual brightness is unknown.",
                DeviceArguments.model_json_schema(),
            ),
            get_status,
            argument_model=DeviceArguments,
        )
    )
    registry.register(
        Tool(
            ToolDefinition(
                "mirror.set_brightness",
                "Set target brightness (0 to 100). ACK starts a fade; completion is unknown.",
                BrightnessArguments.model_json_schema(),
            ),
            set_brightness,
            permission="low_risk",
            mutates=True,
            argument_model=BrightnessArguments,
        )
    )
