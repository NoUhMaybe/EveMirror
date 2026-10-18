"""Generate the language-neutral schema. Run from the repository root."""

import json
from pathlib import Path

from packages.protocol import MESSAGE_ADAPTER

if __name__ == "__main__":
    target = Path("packages/protocol/schema.json")
    target.write_text(json.dumps(MESSAGE_ADAPTER.json_schema(), indent=2) + "\n", encoding="utf-8")
