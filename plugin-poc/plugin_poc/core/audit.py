from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_audit_record(
    state_dir: str | Path,
    *,
    capability_id: str,
    workspace: str,
    agent: str,
    user: str,
    success: bool,
    error_code: str | None,
    input_data: dict[str, Any],
    duration_ms: int,
) -> dict[str, Any]:
    record = {
        "created_at": datetime.now(UTC).isoformat(),
        "capability_id": capability_id,
        "workspace": workspace,
        "agent": agent,
        "user": user,
        "success": success,
        "error_code": error_code,
        "input_keys": sorted(input_data.keys()),
        "duration_ms": duration_ms,
    }
    path = Path(state_dir).resolve() / "audit_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        file.write("\n")
    return record


def list_audit_records(state_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(state_dir).resolve() / "audit_log.jsonl"
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records

