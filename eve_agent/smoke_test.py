"""
Phase 5 smoke test runner for Eve agent.

Usage:
    python smoke_test.py --list
    python smoke_test.py --routing-only
    python smoke_test.py
"""

import argparse
import sys
from dataclasses import dataclass
from typing import List, Optional

from agent import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    SYSTEM_PROMPT,
    ask_ollama,
    build_messages,
)
from tooling import maybe_call_tools, should_enable_thinking


@dataclass
class TestCase:
    category: str
    prompt: str
    expect_weather: bool
    expect_week: Optional[bool]
    expect_smart_home_attempt: bool
    expect_think: Optional[bool]


TEST_CASES: List[TestCase] = [
    TestCase(
        category="Daily Weather",
        prompt="Is it hot outside right now?",
        expect_weather=True,
        expect_week=False,
        expect_smart_home_attempt=False,
        expect_think=False,
    ),
    TestCase(
        category="Daily Weather",
        prompt="What's the weather today?",
        expect_weather=True,
        expect_week=False,
        expect_smart_home_attempt=False,
        expect_think=False,
    ),
    TestCase(
        category="Weekly Weather",
        prompt="What's the weather this week in Frisco?",
        expect_weather=True,
        expect_week=True,
        expect_smart_home_attempt=False,
        expect_think=False,
    ),
    TestCase(
        category="Weekly Weather",
        prompt="Give me a 7 day forecast with rain estimate and humidity.",
        expect_weather=True,
        expect_week=True,
        expect_smart_home_attempt=False,
        expect_think=False,
    ),
    TestCase(
        category="Smart Home Stub",
        prompt="Turn the bedroom light off.",
        expect_weather=False,
        expect_week=None,
        expect_smart_home_attempt=True,
        expect_think=False,
    ),
    TestCase(
        category="Smart Home Stub",
        prompt="Turn on the kitchen lights.",
        expect_weather=False,
        expect_week=None,
        expect_smart_home_attempt=True,
        expect_think=False,
    ),
    TestCase(
        category="Complex Reasoning",
        prompt=(
            "Compare tomorrow's weather with my schedule and suggest when I should leave "
            "if I need 45 minutes to get ready and traffic may be bad."
        ),
        expect_weather=True,
        expect_week=True,
        expect_smart_home_attempt=False,
        expect_think=True,
    ),
    TestCase(
        category="General Chat",
        prompt="Say only READY.",
        expect_weather=False,
        expect_week=None,
        expect_smart_home_attempt=False,
        expect_think=False,
    ),
]


def print_cases() -> None:
    print("Smoke test prompt bank:\n")
    for i, case in enumerate(TEST_CASES, start=1):
        print(f"{i:02d}. [{case.category}] {case.prompt}")


def run_case(case: TestCase, model: str, ollama_url: str, routing_only: bool) -> bool:
    notes, payload = maybe_call_tools(case.prompt)
    think = should_enable_thinking(case.prompt)

    weather_present = "weather" in payload
    smart_home_present = "smart_home_attempt" in payload
    week_value = None
    if weather_present:
        week_value = bool(payload.get("weather", {}).get("includes_week_forecast"))

    ok = True
    failures: List[str] = []

    if weather_present != case.expect_weather:
        ok = False
        failures.append(f"expected weather={case.expect_weather}, got {weather_present}")

    if case.expect_week is not None and week_value != case.expect_week:
        ok = False
        failures.append(f"expected week={case.expect_week}, got {week_value}")

    if smart_home_present != case.expect_smart_home_attempt:
        ok = False
        failures.append(
            f"expected smart_home_attempt={case.expect_smart_home_attempt}, got {smart_home_present}"
        )

    if case.expect_think is not None and think != case.expect_think:
        ok = False
        failures.append(f"expected think={case.expect_think}, got {think}")

    response_excerpt = "(routing only)"
    if not routing_only:
        base_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        request_messages = build_messages(base_messages, case.prompt)
        try:
            reply = ask_ollama(ollama_url, model, request_messages, think=think)
            response_excerpt = reply[:180].replace("\n", " ")
        except Exception as exc:
            ok = False
            failures.append(f"ollama request failed: {exc}")

    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {case.category}: {case.prompt}")
    print(f"  think={think} weather={weather_present} week={week_value} smart_home={smart_home_present}")
    print(f"  response: {response_excerpt}")
    if failures:
        for item in failures:
            print(f"  - {item}")
    if notes:
        for n in notes:
            print(f"  note: {n}")
    print()

    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Eve agent smoke test runner")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama base URL")
    parser.add_argument("--routing-only", action="store_true", help="Skip model calls; test tool routing/think flags only")
    parser.add_argument("--list", action="store_true", help="Print prompt bank and exit")
    args = parser.parse_args()

    if args.list:
        print_cases()
        return

    print("Running Eve smoke tests...\n")
    passed = 0
    for case in TEST_CASES:
        if run_case(case, args.model, args.ollama_url, args.routing_only):
            passed += 1

    total = len(TEST_CASES)
    print(f"Summary: {passed}/{total} passed")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
