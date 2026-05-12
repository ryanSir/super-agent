from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..shared.errors import PluginPocError
from ..shared.io import dump_json, load_yaml


class RuntimeHostError(PluginPocError):
    """Raised when runtime host operations fail."""


def start_runtime(
    state_dir: str | Path,
    plugin_id: str,
    version: str,
    mode: str = "local_daemon",
) -> dict[str, Any]:
    state = Path(state_dir).resolve()
    installed = _installed_entry(state, plugin_id, version)
    install_dir = Path(installed["install_dir"])
    manifest = load_yaml(install_dir / "manifest.yaml")
    if not isinstance(manifest, dict):
        raise RuntimeHostError(f"invalid manifest for {plugin_id}@{version}")

    record = {
        "plugin_id": plugin_id,
        "version": version,
        "mode": mode,
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "health": "ok",
        "adapters": _stdio_adapters(plugin_id, manifest),
    }
    runtimes = _load_runtimes(state)
    runtimes[_plugin_key(plugin_id, version)] = record
    _dump_runtimes(state, runtimes)
    return record


def stop_runtime(state_dir: str | Path, plugin_id: str, version: str) -> dict[str, Any]:
    state = Path(state_dir).resolve()
    runtimes = _load_runtimes(state)
    record = runtimes.get(_plugin_key(plugin_id, version))
    if record is None:
        raise RuntimeHostError(f"runtime is not running: {plugin_id}@{version}")
    record = {**record, "status": "stopped", "stopped_at": datetime.now(UTC).isoformat(), "health": "stopped"}
    runtimes[_plugin_key(plugin_id, version)] = record
    _dump_runtimes(state, runtimes)
    return record


def runtime_health(state_dir: str | Path, plugin_id: str | None = None, version: str | None = None) -> dict[str, Any]:
    runtimes = _load_runtimes(Path(state_dir).resolve())
    if plugin_id and version:
        key = _plugin_key(plugin_id, version)
        record = runtimes.get(key)
        if record is None:
            raise RuntimeHostError(f"runtime is not registered: {key}")
        return {"status": "ok" if record.get("status") == "running" else "stopped", "runtime": record}
    return {"status": "ok", "runtimes": list(runtimes.values())}


def _stdio_adapters(plugin_id: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    adapters = []
    for entry in manifest.get("capabilities", {}).get("mcp", []) or []:
        if entry.get("transport") != "stdio":
            continue
        name = entry.get("name")
        if not name:
            continue
        adapters.append(
            {
                "name": name,
                "transport": "stdio",
                "command": entry.get("command"),
                "adapter_endpoint": f"http://127.0.0.1:8790/mcp/{plugin_id}/{name}",
                "status": "registered",
            }
        )
    return adapters


def _installed_entry(state: Path, plugin_id: str, version: str) -> dict[str, Any]:
    installed_path = state / "installed_plugins.json"
    if not installed_path.exists():
        raise RuntimeHostError("installed plugin state does not exist")
    import json

    with installed_path.open("r", encoding="utf-8") as file:
        installed = json.load(file)
    entry = installed.get("plugins", {}).get(_plugin_key(plugin_id, version))
    if entry is None:
        raise RuntimeHostError(f"plugin is not installed: {plugin_id}@{version}")
    return entry


def _load_runtimes(state: Path) -> dict[str, Any]:
    path = state / "runtime_host.json"
    if not path.exists():
        return {}
    import json

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def _dump_runtimes(state: Path, runtimes: dict[str, Any]) -> None:
    dump_json(state / "runtime_host.json", runtimes)


def _plugin_key(plugin_id: str, version: str) -> str:
    return f"{plugin_id}@{version}"
