"""
Phase 5 test tool module.
This is a lightweight placeholder that mirrors the tool behavior wired into the
agent during Phase 5 and is intentionally non-destructive.
"""

from eve_agent.tooling import get_current_time, get_current_weather


def get_current_weather_tool(location: str = "Frisco, Texas") -> dict:
    return get_current_weather(location)


def get_current_time_tool() -> dict:
    return get_current_time()


def set_light_tool(room: str, state: str) -> dict:
    return {
        "status": "attempted_not_executed",
        "room": room,
        "state": state,
        "details": "Smart-home actions are intentionally stubbed in this phase.",
    }


def show_dashboard_tool(view: str) -> dict:
    return {
        "status": "attempted_not_executed",
        "view": view,
        "details": "Dashboard controls are intentionally stubbed in this phase.",
    }
