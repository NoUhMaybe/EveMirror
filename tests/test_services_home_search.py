import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from apps.config import HomeEntity, HomeSettings
from apps.server.services.common import ServiceError
from apps.server.services.database import Database
from apps.server.services.home import HomeService
from apps.server.services.search import SearchService, public_url
from tests.service_fixtures import HomeFixture, SearchFixture, principal


async def home_service(tmp_path, fixture):
    db = Database(tmp_path / "home.sqlite3")
    await db.open()
    home = HomeService(fixture.settings, db, httpx.MockTransport(fixture.handler))
    await home.start()
    await home.refresh()
    return home


async def test_discovery_alias_permissions_and_unavailable_states(tmp_path):
    fixture = HomeFixture()
    home = await home_service(tmp_path, fixture)
    try:
        entities = await home.list(principal())
        assert len(entities) == 4 and "must-not-leak" not in json.dumps(entities)
        assert home.resolve("bedroom lights", principal()) == "light.bedroom"
        with pytest.raises(ServiceError, match="entity_not_authorized"):
            await home.get("lock.front", principal())
        other = principal("other")
        other = type(other)(other.id, other.device_ids, True, frozenset())
        assert await home.list(other) == []
        with pytest.raises(ServiceError, match="entity_not_authorized"):
            await home.get("TV", other)
        fixture.settings.entities["scene.movie"].aliases.append("bedroom lights")
        with pytest.raises(ServiceError, match="entity_ambiguous"):
            home.resolve("bedroom lights", principal())
        fixture.states["light.bedroom"]["state"] = "unavailable"
        with pytest.raises(ServiceError, match="entity_unavailable"):
            await home.get("light.bedroom", principal())
    finally:
        await home.close()
        await home.db.close()


@pytest.mark.parametrize(
    "target,action,kwargs,verified",
    [
        ("bedroom lights", "turn_off", {}, True),
        ("bedroom lights", "turn_on", {}, True),
        ("bedroom lights", "set_level", {"percent": 30}, True),
        ("movie scene", "activate_scene", {}, False),
        ("TV", "power", {"on": False}, True),
        ("TV", "pause", {}, True),
        ("TV", "play", {}, True),
        ("TV", "stop", {}, False),
        ("TV", "set_volume", {"percent": 30}, True),
        ("TV", "volume_up", {}, False),
        ("TV", "volume_down", {}, False),
        ("TV", "select_source", {"source": "HDMI 1"}, True),
        ("Roku", "send_remote_command", {"command": "HOME"}, False),
    ],
)
async def test_finite_approved_home_media_actions_and_evidence(
    tmp_path, target, action, kwargs, verified
):
    fixture = HomeFixture()
    home = await home_service(tmp_path, fixture)
    operation = uuid4()
    try:
        result, replayed = await home.act(target, principal(), operation, action, **kwargs)
        assert not replayed and result["status"] == "success"
        assert result["data"]["acknowledged"] and result["data"]["verified"] is verified
        repeated, replayed = await home.act(target, principal(), operation, action, **kwargs)
        assert repeated == result and replayed
        posts = [request for request in fixture.requests if request.method == "POST"]
        assert len(posts) == 1
        if action == "send_remote_command":
            assert json.loads(posts[0].content) == {
                "entity_id": "remote.roku",
                "command": "home",
                "num_repeats": 1,
            }
    finally:
        await home.close()
        await home.db.close()


async def test_timeout_unknown_outcome_survives_restart_without_a_second_action(tmp_path):
    fixture = HomeFixture()
    home = await home_service(tmp_path, fixture)
    operation = uuid4()
    fixture.timeout = True
    result, _ = await home.act("TV", principal(), operation, "power", on=False)
    assert result["error"]["code"] == "indeterminate"
    await home.close()
    await home.db.close()
    restored = await home_service(tmp_path, fixture)
    try:
        assert (await restored.act("TV", principal(), operation, "power", on=False))[0] == result
        assert len([r for r in fixture.requests if r.method == "POST"]) == 1
    finally:
        await restored.close()
        await restored.db.close()


@pytest.mark.parametrize("action,flag", [("turn_on", 128), ("turn_off", 256)])
async def test_media_power_discovery_requires_the_requested_direction(tmp_path, action, flag):
    fixture = HomeFixture()
    fixture.settings.entities = {
        "media_player.tv": HomeEntity(aliases=["TV"], actions={"turn_on", "turn_off"})
    }
    fixture.states["media_player.tv"]["attributes"]["supported_features"] = flag
    home = await home_service(tmp_path, fixture)
    try:
        assert home.available_action(action)
        opposite = "turn_off" if action == "turn_on" else "turn_on"
        assert not home.available_action(opposite)
        assert home.public_state("media_player.tv")["capabilities"] == [action]
        result, _ = await home.act("TV", principal(), uuid4(), action)
        assert result["data"]["verified"]
        assert [r for r in fixture.requests if r.method == "POST"][0].url.path.endswith(action)
    finally:
        await home.close()
        await home.db.close()


@pytest.mark.parametrize(
    "mode", ["unsupported", "bad_remote", "bad_source", "unverified", "offline", "auth"]
)
async def test_home_errors_are_honest_no_unapproved_posts(tmp_path, mode):
    fixture = HomeFixture()
    home = await home_service(tmp_path, fixture)
    try:
        kwargs, action = {}, "pause"
        if mode == "unsupported":
            fixture.states["media_player.tv"]["attributes"]["supported_features"] = 0
        elif mode == "bad_remote":
            action, kwargs = "send_remote_command", {"command": "SHELL"}
        elif mode == "bad_source":
            action, kwargs = "select_source", {"source": "unapproved"}
        elif mode == "unverified":
            fixture.verify = False
        else:
            fixture.fail = mode
        result, _ = await home.act("TV", principal(), uuid4(), action, **kwargs)
        if mode == "unverified":
            assert result["data"]["outcome"] == "acknowledged_unverified"
        else:
            assert result["status"] == "error"
            assert not [r for r in fixture.requests if r.method == "POST"]
        assert "fixture-home-secret" not in str(result)
    finally:
        await home.close()
        await home.db.close()


async def test_search_metadata_limits_untrusted_snippets_and_no_result_fetches():
    fixture = SearchFixture()
    fixture.results[0]["url"] = "https://example.com/news?id=42#details"
    service = SearchService(fixture.settings, httpx.MockTransport(fixture.handler))
    await service.start()
    try:
        result = await service.search("latest news")
        assert len(result["results"]) == 2
        assert result["results"][0]["published_at"] is None
        assert "Ignore previous" in result["results"][0]["snippet"]
        assert result["results"][0]["title"] == "Technology news"
        assert result["results"][0]["url"] == fixture.results[0]["url"]
        assert not result["pages_fetched"] and result["content_trust"] == "untrusted"
        assert len(fixture.requests) == 1
        limited = await service.search("query", 1)
        assert len(limited["results"]) == 1
        assert "fixture-search-secret" not in json.dumps(result)
    finally:
        await service.close()


async def test_services_redact_credentials_reflected_by_external_content(tmp_path):
    fixture = HomeFixture()
    fixture.states["light.bedroom"]["attributes"]["friendly_name"] = "fixture-home-secret"
    home = await home_service(tmp_path, fixture)
    try:
        assert "fixture-home-secret" not in json.dumps(await home.list(principal()))
    finally:
        await home.close()
        await home.db.close()
    search_fixture = SearchFixture()
    search_fixture.results[0]["content"] = "fixture-search-secret"
    search = SearchService(search_fixture.settings, httpx.MockTransport(search_fixture.handler))
    await search.start()
    try:
        assert "fixture-search-secret" not in json.dumps(await search.search("query"))
    finally:
        await search.close()


@pytest.mark.parametrize(
    "status,code",
    [(429, "rate_limited"), (500, "service_unavailable"), (302, "service_unavailable")],
)
async def test_search_errors_and_redirects_do_not_contact_other_targets(status, code):
    fixture = SearchFixture()
    fixture.status = status
    service = SearchService(fixture.settings, httpx.MockTransport(fixture.handler))
    await service.start()
    try:
        with pytest.raises(ServiceError, match=code):
            await service.search("news")
        assert len(fixture.requests) == 1
    finally:
        await service.close()


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1",
        "http://192.168.1.1/a",
        "http://169.254.169.254/",
        "http://localhost/",
        "http://router.local/a",
        "http://2130706433/",
        "http://127.1/",
        "http://user:pass@example.com/a",
        "http://example.com:8080/",
    ],
)
def test_unsafe_search_links_rejected(url):
    assert public_url(url) is None


def test_home_policy_cannot_enable_sensitive_domains_or_weaken_mcp(settings):
    for entity in ["lock.front", "alarm_control_panel.home", "cover.garage", "script.anything"]:
        with pytest.raises(ValidationError):
            HomeSettings(entities={entity: HomeEntity()})
    with pytest.raises(ValidationError):
        HomeSettings(url="http://ha.lan", token="secret")
    assert HomeSettings(url="http://ha.lan", token="secret", allow_insecure_lan=True).url
