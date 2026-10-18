"""Fixed administrator endpoints, no redirects/proxies, bounded JSON decoding."""

import json

import httpx

from apps.server.redaction import redact
from apps.server.services.common import ServiceError


def http_client(duration: float, token=None, transport=None):
    return httpx.AsyncClient(
        timeout=duration,
        trust_env=False,
        follow_redirects=False,
        transport=transport,
        headers={"Authorization": "Bearer " + token} if token else {},
    )


async def request_json(client, method, url, *, mutates=False, max_bytes=524288, **kwargs):
    try:
        async with client.stream(method, url, **kwargs) as response:
            if response.status_code in {401, 403}:
                raise ServiceError(
                    "authentication_failed",
                    "Service rejected its configured credentials or access.",
                )
            if response.status_code == 429:
                raise ServiceError("rate_limited", "Service rate limit exceeded.")
            if response.status_code == 404:
                raise ServiceError("not_found", "Configured service resource was not found.")
            if not 200 <= response.status_code < 300:
                code = (
                    "indeterminate"
                    if mutates and response.status_code >= 500
                    else "service_unavailable"
                )
                raise ServiceError(code, "Service request failed; redirects are not followed.")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise ServiceError(
                        "indeterminate" if mutates else "response_too_large",
                        "Service response exceeded the limit.",
                    )
            credential = client.headers.get("Authorization", "")
            return redact(
                json.loads(content), [credential[7:]] if credential.startswith("Bearer ") else []
            )
    except ServiceError:
        raise
    except httpx.TimeoutException:
        raise ServiceError(
            "indeterminate" if mutates else "service_timeout",
            "Service timed out; mutations are not retried.",
        ) from None
    except httpx.HTTPError:
        raise ServiceError(
            "indeterminate" if mutates else "service_unavailable", "Service connection failed."
        ) from None
    except (ValueError, TypeError):
        raise ServiceError(
            "indeterminate" if mutates else "invalid_response", "Service returned invalid JSON."
        ) from None
