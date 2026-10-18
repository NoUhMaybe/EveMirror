"""Shared credential comparison; agent clients never acquire operator/device access."""

import secrets

from fastapi import Header, HTTPException

from apps.config import ServerSettings
from apps.server.tools.base import Principal


def authenticated(header: str | None, expected: str) -> bool:
    if not header or not header.startswith("Bearer "):
        return False
    return secrets.compare_digest(header[7:].encode(), expected.encode())


def agent_principal(settings: ServerSettings, header: str | None) -> Principal | None:
    if authenticated(header, settings.operator_token.get_secret_value()):
        return Principal(
            "operator",
            frozenset(settings.edge_tokens),
            allow_mutations=True,
            home_entities=frozenset(settings.home.entities),
        )
    for name, client in settings.agent_clients.items():
        if authenticated(header, client.token.get_secret_value()):
            return Principal(
                "client:" + name,
                frozenset(client.device_ids),
                client.allow_mutations,
                frozenset(client.home_entities) & settings.home.entities.keys(),
            )
    return None


def principal_dependency(settings):
    async def principal(
        authorization: str | None = Header(None), origin: str | None = Header(None)
    ):
        identity = agent_principal(settings, authorization)
        if origin is not None or identity is None:
            raise HTTPException(401, "unauthorized")
        return identity

    return principal
