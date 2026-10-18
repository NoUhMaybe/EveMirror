"""Finite native HA actions. No arbitrary services, payloads, conversation agent or scripts."""

import asyncio
import time

from apps.server.services.common import ServiceError, utc_now
from apps.server.services.http import http_client, request_json

# Official media_player entity feature flags, not guessed device capabilities.
MEDIA_FEATURES = {
    "pause": 1,
    "set_volume": 4,
    "volume_up": 1024,
    "volume_down": 1024,
    "select_source": 2048,
    "stop": 4096,
    "play": 16384,
}
MEDIA_SERVICES = {
    "play": "media_play",
    "pause": "media_pause",
    "stop": "media_stop",
    "set_volume": "volume_set",
    "volume_up": "volume_up",
    "volume_down": "volume_down",
    "select_source": "select_source",
}


class HomeService:
    def __init__(self, settings, database, transport=None):
        self.settings, self.db, self.transport = settings, database, transport
        self.client = None
        self.states, self.services = {}, set()
        self.updated, self.error = None, None
        self.lock = asyncio.Lock()
        self.discovered_at = float("-inf")

    @property
    def configured(self):
        return bool(self.settings.url and self.settings.token and self.settings.entities)

    async def start(self):
        if self.configured:
            self.client = http_client(
                self.settings.timeout, self.settings.token.get_secret_value(), self.transport
            )

    def _url(self, path):
        return self.settings.url + "/api/" + path

    async def refresh(self, force=False):
        if self.client is None:
            return
        async with self.lock:
            if not force and time.monotonic() - self.discovered_at < self.settings.discovery_ttl:
                return
            self.discovered_at = time.monotonic()
            try:
                states = await request_json(self.client, "GET", self._url("states"))
                services = await request_json(self.client, "GET", self._url("services"))
                if not isinstance(states, list) or not isinstance(services, list):
                    raise ServiceError(
                        "invalid_response", "Invalid Home Assistant discovery response."
                    )
                self.states = {
                    row["entity_id"]: row
                    for row in states
                    if isinstance(row, dict)
                    and row.get("entity_id") in self.settings.entities
                    and isinstance(row.get("attributes"), dict)
                }
                self.services = {
                    (row["domain"], service)
                    for row in services
                    if isinstance(row, dict) and isinstance(row.get("services"), dict)
                    for service in row["services"]
                }
                self.updated, self.error = utc_now().isoformat(), None
            except (ServiceError, KeyError, TypeError):
                self.error = "home_unavailable"
                self.states, self.services = {}, set()

    def resolve(self, target, principal):
        allowed = set(self.settings.entities) & principal.home_entities
        matches = [
            entity
            for entity in allowed
            if target.casefold()
            in {
                entity.casefold(),
                *[alias.casefold() for alias in self.settings.entities[entity].aliases],
                str(
                    self.states.get(entity, {}).get("attributes", {}).get("friendly_name", "")
                ).casefold(),
            }
        ]
        if len(matches) != 1:
            raise ServiceError(
                "entity_ambiguous" if matches else "entity_not_authorized",
                "Select exactly one approved entity by ID or configured alias.",
                {"candidates": sorted(matches)},
            )
        return matches[0]

    def supported(self, entity, action, on=True):
        policy = self.settings.entities[entity]
        if action not in policy.actions:
            return False
        row = self.states.get(entity)
        if not row:
            return False
        domain = entity.split(".")[0]
        attrs = row["attributes"]
        features = attrs.get("supported_features", 0)
        features = features if isinstance(features, int) else 0
        if domain == "media_player":
            if action == "send_remote_command":
                return bool(
                    policy.remote_entity
                    and policy.remote_commands
                    and ("remote", "send_command") in self.services
                )
            if action in {"turn_on", "turn_off", "power"}:
                on = on if action == "power" else action == "turn_on"
                flag = 128 if on else 256
                return (
                    bool(features & flag)
                    and (domain, "turn_on" if on else "turn_off") in self.services
                )
            service = MEDIA_SERVICES.get(action)
            return bool(
                service and features & MEDIA_FEATURES[action] and (domain, service) in self.services
            )
        if domain in {"light", "switch"} and action in {"turn_on", "turn_off"}:
            return (domain, action) in self.services
        if domain == "light" and action == "set_level":
            modes = attrs.get("supported_color_modes", [])
            return (
                isinstance(modes, list)
                and any(
                    mode
                    in {"brightness", "color_temp", "hs", "xy", "rgb", "rgbw", "rgbww", "white"}
                    for mode in modes
                )
                and (domain, "turn_on") in self.services
            )
        return (
            domain == "scene"
            and action == "activate_scene"
            and ("scene", "turn_on") in self.services
        )

    def available_action(self, action):
        return (
            self.configured
            and self.db.available
            and any(
                self.supported(entity, action, True)
                or (action == "power" and self.supported(entity, action, False))
                for entity in self.settings.entities
            )
        )

    def public_state(self, entity, row=None):
        row = row or self.states.get(entity)
        if not row:
            raise ServiceError("entity_unavailable", "Approved entity is not currently available.")
        attrs = row.get("attributes", {})
        return {
            "entity_id": entity,
            "name": str(attrs.get("friendly_name", entity))[:160],
            "state": str(row.get("state", "unknown"))[:160],
            "source": "home-assistant",
            "observed_at": utc_now().isoformat(),
            "last_updated": row.get("last_updated"),
            "attributes": {
                key: attrs[key]
                for key in (
                    "brightness",
                    "volume_level",
                    "source",
                    "source_list",
                    "media_title",
                    "unit_of_measurement",
                )
                if key in attrs
            },
            "capabilities": [
                action
                for action in self.settings.entities[entity].actions
                if self.supported(entity, action)
                or (action == "power" and self.supported(entity, action, False))
            ],
        }

    async def list(self, principal):
        if self.client is None:
            raise ServiceError("home_unconfigured", "Home Assistant is not configured.")
        await self.refresh()
        if self.error:
            raise ServiceError(self.error, "Home Assistant discovery is unavailable.")
        return [
            self.public_state(entity) for entity in self.states if entity in principal.home_entities
        ]

    async def get(self, target, principal):
        entity = self.resolve(target, principal)
        if self.client is None:
            raise ServiceError("home_unconfigured", "Home Assistant is not configured.")
        try:
            row = await request_json(self.client, "GET", self._url("states/" + entity))
        except ServiceError as exc:
            if exc.code == "not_found":
                raise ServiceError("entity_unavailable", "Approved entity is absent.") from None
            raise
        if (
            not isinstance(row, dict)
            or row.get("entity_id") != entity
            or not isinstance(row.get("attributes"), dict)
        ):
            raise ServiceError("invalid_response", "Invalid Home Assistant state response.")
        self.states[entity] = row
        state = self.public_state(entity, row)
        if state["state"] in {"unavailable", "unknown"}:
            raise ServiceError("entity_unavailable", "Approved entity reports no usable state.")
        return state

    async def act(
        self,
        target,
        principal,
        operation_id,
        action,
        *,
        percent=None,
        source=None,
        command=None,
        on=True,
    ):
        if self.client is None:
            raise ServiceError("home_unconfigured", "Home Assistant is not configured.")
        entity = self.resolve(target, principal)
        # Check the durable operation identity before performing even a new read/verification.
        arguments = [entity, action, percent, source, command, on]
        replayed, receipt = await self.db.run(
            lambda c: self.db.reserve(c, principal.id, operation_id, "home.action", arguments)
        )
        if replayed:
            return receipt, True
        try:
            observed = await self.get(entity, principal)
            domain = entity.split(".")[0]
            effective_on = on if action == "power" else action != "turn_off"
            if not self.supported(entity, action, effective_on):
                raise ServiceError(
                    "unsupported_capability",
                    "The approved device does not support this allowed operation.",
                )
            payload = {"entity_id": entity}
            if action in {"power", "turn_on", "turn_off"}:
                service = "turn_on" if effective_on else "turn_off"
                expected = "on" if effective_on else "off"
            elif action in {"set_level", "set_volume"}:
                if not isinstance(percent, int) or not 0 <= percent <= 100:
                    raise ServiceError(
                        "invalid_arguments", "Level must be an integer from 0 to 100."
                    )
                service, expected = (
                    ("turn_on", "on") if action == "set_level" else ("volume_set", None)
                )
                payload["brightness_pct" if action == "set_level" else "volume_level"] = (
                    percent if action == "set_level" else percent / 100
                )
            elif action == "activate_scene":
                service, expected = "turn_on", None
            elif action == "send_remote_command":
                policy = self.settings.entities[entity]
                if command not in policy.remote_commands:
                    raise ServiceError(
                        "unsupported_capability", "Remote button is not approved for this device."
                    )
                domain, service, expected = "remote", "send_command", None
                payload = {
                    "entity_id": policy.remote_entity,
                    "command": policy.remote_commands[command],
                    "num_repeats": 1,
                }
            else:
                service, expected = (
                    MEDIA_SERVICES[action],
                    {"play": "playing", "pause": "paused"}.get(action),
                )
                if action == "select_source":
                    choices = self.states[entity]["attributes"].get("source_list", [])
                    if not isinstance(source, str) or source not in choices:
                        raise ServiceError(
                            "unsupported_capability",
                            "Select an advertised source from the approved device.",
                        )
                    payload["source"] = source
            await request_json(
                self.client,
                "POST",
                self._url(f"services/{domain}/{service}"),
                json=payload,
                mutates=True,
            )
            verified, observed_after = False, None
            try:
                observed_after = await self.get(entity, principal)
                verified = expected is not None and observed_after["state"] == expected
                if action == "set_volume":
                    verified = observed_after["attributes"].get("volume_level") == percent / 100
                elif action == "set_level":
                    level = observed_after["attributes"].get("brightness")
                    verified = (
                        isinstance(level, int | float) and abs(level / 255 * 100 - percent) <= 1
                    )
                elif action == "select_source":
                    verified = observed_after["attributes"].get("source") == source
            except ServiceError:
                pass
            result = {
                "status": "success",
                "data": {
                    "entity_id": entity,
                    "operation_id": str(operation_id),
                    "acknowledged": True,
                    "verified": verified,
                    "outcome": "observed" if verified else "acknowledged_unverified",
                    "state": observed_after,
                    "previous_state": observed["state"],
                },
            }
        except ServiceError as exc:
            result = {"status": "error", "error": {"code": exc.code, "message": exc.message}}
        await self.db.run(lambda c: self.db.complete(c, principal.id, operation_id, result))
        return result, False

    async def close(self):
        if self.client:
            await self.client.aclose()
