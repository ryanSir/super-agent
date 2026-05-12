from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from ..shared.errors import PluginPocError
from ..shared.io import dump_json, load_yaml
from .capability import build_capabilities, filter_capabilities, remove_plugin_capabilities


class PluginManagerError(PluginPocError):
    """Raised when plugin manager operations fail."""


def install_plugin(registry_dir: str | Path, state_dir: str | Path, plugin_id: str, version: str) -> dict:
    registry = Path(registry_dir).resolve()
    state = Path(state_dir).resolve()
    entry = _registry_entry(registry, plugin_id, version)

    install_dir = _install_dir(state, plugin_id, version)
    install_dir.mkdir(parents=True, exist_ok=True)
    source_dir = install_dir / "source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)

    package_path = registry / entry["package_path"]
    metadata_path = registry / entry["metadata_path"]
    manifest_path = registry / "packages" / plugin_id / version / "manifest.yaml"
    if not package_path.exists():
        raise PluginManagerError(f"missing package file: {package_path}")

    shutil.copy2(package_path, install_dir / "package.zip")
    shutil.copy2(metadata_path, install_dir / "metadata.json")
    shutil.copy2(manifest_path, install_dir / "manifest.yaml")
    with ZipFile(package_path) as archive:
        archive.extractall(source_dir)

    installed = _load_state(state, "installed_plugins.json", {"plugins": {}})
    installed["plugins"][_plugin_key(plugin_id, version)] = {
        "plugin_id": plugin_id,
        "version": version,
        "name": entry.get("name", ""),
        "description": entry.get("description", ""),
        "author": entry.get("author", ""),
        "checksum": entry.get("checksum"),
        "status": "installed",
        "install_dir": str(install_dir),
        "installed_at": datetime.now(UTC).isoformat(),
    }
    _dump_state(state, "installed_plugins.json", installed)
    return installed["plugins"][_plugin_key(plugin_id, version)]


def enable_plugin(state_dir: str | Path, plugin_id: str, version: str, workspace: str, agent: str) -> dict:
    state = Path(state_dir).resolve()
    installed_entry = _installed_entry(state, plugin_id, version)
    install_dir = Path(installed_entry["install_dir"])
    manifest = load_yaml(install_dir / "manifest.yaml")
    if not isinstance(manifest, dict):
        raise PluginManagerError(f"invalid installed manifest for {plugin_id}@{version}")

    enabled = _load_state(state, "enabled_plugins.json", {"bindings": []})
    binding = {
        "plugin_id": plugin_id,
        "version": version,
        "workspace": workspace,
        "agent": agent,
        "enabled_at": datetime.now(UTC).isoformat(),
    }
    enabled["bindings"] = [
        item
        for item in enabled["bindings"]
        if not _same_binding(item, plugin_id, version, workspace, agent)
    ]
    enabled["bindings"].append(binding)
    _dump_state(state, "enabled_plugins.json", enabled)

    index = _load_state(state, "capability_index.json", {"capabilities": []})
    index["capabilities"] = remove_plugin_capabilities(
        index["capabilities"],
        plugin_id,
        version,
        workspace,
        agent,
    )
    index["capabilities"].extend(build_capabilities(plugin_id, version, manifest, workspace, agent, install_dir))
    _dump_state(state, "capability_index.json", index)
    return binding


def disable_plugin(state_dir: str | Path, plugin_id: str, version: str, workspace: str, agent: str) -> dict:
    state = Path(state_dir).resolve()
    enabled = _load_state(state, "enabled_plugins.json", {"bindings": []})
    before = len(enabled["bindings"])
    enabled["bindings"] = [
        item
        for item in enabled["bindings"]
        if not _same_binding(item, plugin_id, version, workspace, agent)
    ]
    _dump_state(state, "enabled_plugins.json", enabled)

    index = _load_state(state, "capability_index.json", {"capabilities": []})
    index["capabilities"] = remove_plugin_capabilities(
        index["capabilities"],
        plugin_id,
        version,
        workspace,
        agent,
    )
    _dump_state(state, "capability_index.json", index)
    return {"removed": before - len(enabled["bindings"])}


def uninstall_plugin(state_dir: str | Path, plugin_id: str, version: str) -> dict:
    state = Path(state_dir).resolve()
    installed = _load_state(state, "installed_plugins.json", {"plugins": {}})
    key = _plugin_key(plugin_id, version)
    entry = installed["plugins"].pop(key, None)
    if entry is None:
        raise PluginManagerError(f"plugin is not installed: {plugin_id}@{version}")
    _dump_state(state, "installed_plugins.json", installed)

    enabled = _load_state(state, "enabled_plugins.json", {"bindings": []})
    enabled["bindings"] = [
        item
        for item in enabled["bindings"]
        if not (item.get("plugin_id") == plugin_id and item.get("version") == version)
    ]
    _dump_state(state, "enabled_plugins.json", enabled)

    index = _load_state(state, "capability_index.json", {"capabilities": []})
    index["capabilities"] = remove_plugin_capabilities(index["capabilities"], plugin_id, version)
    _dump_state(state, "capability_index.json", index)

    install_dir = Path(entry["install_dir"])
    if install_dir.exists():
        shutil.rmtree(install_dir)
    return {"uninstalled": key}


def list_installed(state_dir: str | Path) -> list[dict]:
    state = Path(state_dir).resolve()
    installed = _load_state(state, "installed_plugins.json", {"plugins": {}})
    return list(installed["plugins"].values())


def list_capabilities(state_dir: str | Path, workspace: str, agent: str) -> list[dict]:
    state = Path(state_dir).resolve()
    index = _load_state(state, "capability_index.json", {"capabilities": []})
    return filter_capabilities(index["capabilities"], workspace, agent)


def _registry_entry(registry: Path, plugin_id: str, version: str) -> dict:
    index_path = registry / "index.json"
    if not index_path.exists():
        raise PluginManagerError(f"missing registry index: {index_path}")
    with index_path.open("r", encoding="utf-8") as file:
        index = json.load(file)
    try:
        return index["plugins"][plugin_id][version]
    except KeyError as exc:
        raise PluginManagerError(f"plugin version not found in registry: {plugin_id}@{version}") from exc


def _installed_entry(state: Path, plugin_id: str, version: str) -> dict:
    installed = _load_state(state, "installed_plugins.json", {"plugins": {}})
    entry = installed["plugins"].get(_plugin_key(plugin_id, version))
    if entry is None:
        raise PluginManagerError(f"plugin is not installed: {plugin_id}@{version}")
    return entry


def _load_state(state: Path, filename: str, default: dict) -> dict:
    path = state / filename
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else default


def _dump_state(state: Path, filename: str, data: dict) -> None:
    dump_json(state / filename, data)


def _install_dir(state: Path, plugin_id: str, version: str) -> Path:
    return state / "installed" / plugin_id / version


def _plugin_key(plugin_id: str, version: str) -> str:
    return f"{plugin_id}@{version}"


def _same_binding(item: dict, plugin_id: str, version: str, workspace: str, agent: str) -> bool:
    return (
        item.get("plugin_id") == plugin_id
        and item.get("version") == version
        and item.get("workspace") == workspace
        and item.get("agent") == agent
    )
