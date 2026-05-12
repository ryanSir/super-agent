from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..management.manager import list_capabilities
from ..shared.errors import PluginPocError
from ..shared.io import load_yaml


class DataSourceRuntimeError(PluginPocError):
    """Raised when data source runtime operations fail."""


def list_data_sources(state_dir: str | Path, workspace: str, agent: str) -> list[dict[str, Any]]:
    sources = []
    for capability in list_capabilities(state_dir, workspace, agent):
        if capability.get("type") == "data_source":
            sources.append(capability)
    return sources


def query_data_source(
    capability: dict[str, Any],
    input_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        config = _load_config(capability)
        records = _load_records(capability, config)
    except DataSourceRuntimeError as exc:
        return None, {"code": "data_source_error", "message": str(exc)}

    query = str(input_data.get("query", "")).strip().lower()
    limit = int(input_data.get("limit", 20))
    channel_id = input_data.get("channel_id")

    matched = []
    for record in records:
        if channel_id and record.get("channel_id") != channel_id:
            continue
        if query and not _record_contains(record, query):
            continue
        matched.append(record)
        if len(matched) >= limit:
            break

    return {
        "message": "data source query succeeded",
        "source": capability.get("name"),
        "total": len(matched),
        "items": matched,
    }, None


def _load_config(capability: dict[str, Any]) -> dict[str, Any]:
    install_dir = capability.get("install_dir")
    source = capability.get("source")
    if not install_dir or not source:
        raise DataSourceRuntimeError("data source capability is missing install_dir or source")

    data = load_yaml(Path(install_dir) / "source" / source)
    if not isinstance(data, dict):
        raise DataSourceRuntimeError("data source config must be an object")
    return data


def _load_records(capability: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    source_type = config.get("type")
    if source_type != "local_json":
        raise DataSourceRuntimeError(f"unsupported data source type: {source_type}")

    install_dir = Path(capability["install_dir"])
    data_path = install_dir / "source" / str(config.get("path", ""))
    try:
        data_path.resolve().relative_to((install_dir / "source").resolve())
    except ValueError as exc:
        raise DataSourceRuntimeError("data source path must stay inside plugin source") from exc

    if not data_path.exists():
        raise DataSourceRuntimeError(f"data source file does not exist: {config.get('path')}")
    with data_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise DataSourceRuntimeError("data source JSON must be a list of objects")
    return data


def _record_contains(record: dict[str, Any], query: str) -> bool:
    return any(query in str(value).lower() for value in record.values())
