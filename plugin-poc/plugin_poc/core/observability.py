from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_runtime_event(
    state_dir: str | Path,
    *,
    event_type: str,
    capability: dict[str, Any],
    runtime: str | None,
    success: bool,
    duration_ms: int,
    error_code: str | None = None,
) -> dict[str, Any]:
    event = {
        "created_at": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "plugin_id": capability.get("plugin_id"),
        "version": capability.get("version"),
        "capability_id": capability.get("capability_id"),
        "capability_type": capability.get("type"),
        "runtime": runtime,
        "success": success,
        "error_code": error_code,
        "duration_ms": duration_ms,
    }
    path = Path(state_dir).resolve() / "runtime_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
        file.write("\n")
    return event


def list_runtime_events(state_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(state_dir).resolve() / "runtime_events.jsonl"
    if not path.exists():
        return []
    events = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))
    return events
