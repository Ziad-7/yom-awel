"""Export transport schemas without constructing providers or touching a database."""

import json
from pathlib import Path

from yom_awel.transport.app import create_app
from yom_awel.transport.settings import Settings

ROOT = Path(__file__).resolve().parents[3]
app = create_app(Settings(secret="schema-export-only-not-a-runtime-key"))
(ROOT / "contracts/openapi.json").write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
