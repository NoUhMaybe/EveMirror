import ipaddress
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

from apps.config import http_endpoint
from apps.server.services.common import ServiceError, utc_now
from apps.server.services.http import http_client, request_json


def public_url(value):
    try:
        if not isinstance(value, str) or len(value) > 2048:
            return None
        if "\\" in value or any(char.isspace() or ord(char) < 32 for char in value):
            return None
        parsed = urlsplit(value)
        # Result citations may legitimately have query parameters and fragments.
        # Endpoint policy still validates their scheme/authority without fetching.
        http_endpoint(parsed._replace(query="", fragment="").geturl())
        host = parsed.hostname.lower().rstrip(".")
        if "." not in host or host.endswith((".local", ".localhost", ".internal", ".home", ".lan")):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            if host.replace(".", "").isdigit() or host.startswith("0x"):
                return None
        if parsed.port not in {None, 80, 443}:
            return None
        return value
    except (ValueError, TypeError, AttributeError):
        return None


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def plain(value, limit):
    parser = TextOnly()
    parser.feed(str(value)[: limit * 4])
    return " ".join("".join(parser.parts).split())[:limit]


class SearchService:
    def __init__(self, settings, transport=None):
        self.settings, self.transport, self.client = settings, transport, None
        self.error = None

    async def start(self):
        if self.settings.url:
            self.client = http_client(
                self.settings.timeout,
                self.settings.token.get_secret_value() if self.settings.token else None,
                self.transport,
            )

    async def search(self, query, count=5):
        if self.client is None:
            raise ServiceError("search_unconfigured", "Search is not configured.")
        if not isinstance(query, str) or not query.strip() or len(query) > 256:
            raise ServiceError(
                "invalid_arguments", "Search query must contain 1 to 256 characters."
            )
        count = min(count, self.settings.max_results)
        try:
            data = await request_json(
                self.client,
                "GET",
                self.settings.url,
                params={"q": query, "format": "json", "pageno": 1},
                max_bytes=262144,
            )
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise ServiceError("invalid_response", "Search provider returned invalid results.")
            results = []
            for row in data["results"][:50]:
                if not isinstance(row, dict) or not isinstance(row.get("title"), str):
                    continue
                url = public_url(row.get("url"))
                if not url:
                    continue
                published = row.get("publishedDate")
                try:
                    published = (
                        datetime.fromisoformat(published).isoformat()
                        if isinstance(published, str)
                        else None
                    )
                except ValueError:
                    published = None
                results.append(
                    {
                        "title": plain(row["title"], 240),
                        "url": url,
                        "snippet": plain(row.get("content", ""), 1000),
                        "published_at": published,
                        "engine": plain(row.get("engine", ""), 80) or None,
                    }
                )
                if len(results) >= count:
                    break
            self.error = None
            return {
                "provider": "searxng",
                "retrieved_at": utc_now().isoformat(),
                "results": results,
                "content_trust": "untrusted",
                "pages_fetched": False,
            }
        except ServiceError as exc:
            self.error = exc.code
            raise

    async def close(self):
        if self.client:
            await self.client.aclose()
