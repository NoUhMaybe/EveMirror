import json
from pathlib import Path

from pydantic import TypeAdapter

from apps.server.browser.models import BrowserFrame
from apps.server.services.events import ApplicationSnapshot, SemanticEvent
from apps.server.speech.state import VoiceSnapshot


def schema():
    return TypeAdapter(ApplicationSnapshot | SemanticEvent).json_schema()


def voice_schema():
    return VoiceSnapshot.model_json_schema()


def browser_schema():
    return BrowserFrame.model_json_schema()


if __name__ == "__main__":
    Path("packages/application/schema.json").write_text(
        json.dumps(schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    Path("packages/application/voice.schema.json").write_text(
        json.dumps(voice_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    Path("packages/application/browser.schema.json").write_text(
        json.dumps(browser_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
