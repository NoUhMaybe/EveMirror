import json
from pathlib import Path

from pydantic import TypeAdapter

from apps.server.services.events import ApplicationSnapshot, SemanticEvent


def schema():
    return TypeAdapter(ApplicationSnapshot | SemanticEvent).json_schema()


if __name__ == "__main__":
    Path("packages/application/schema.json").write_text(
        json.dumps(schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
