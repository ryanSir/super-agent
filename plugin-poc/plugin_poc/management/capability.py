from __future__ import annotations

from pathlib import Path
from typing import Any

from ..shared.io import load_yaml


def build_capabilities(
    plugin_id: str,
    version: str,
    manifest: dict[str, Any],
    workspace: str,
    agent: str,
    install_dir: Path,
) -> list[dict[str, Any]]:
    capabilities = manifest.get("capabilities", {})
    result: list[dict[str, Any]] = []

    for entry in capabilities.get("tools", []) or []:
        tool_file = _load_child_yaml(install_dir, entry["path"])
        for tool in tool_file.get("tools", []) or []:
            name = tool.get("name")
            if name:
                result.append(
                    _capability(
                        plugin_id,
                        version,
                        workspace,
                        agent,
                        "tool",
                        name,
                        entry["path"],
                        tool.get("description", ""),
                        tool.get("input_schema"),
                        install_dir=str(install_dir),
                    )
                )

    for entry in capabilities.get("skills", []) or []:
        path = entry["path"]
        skill_metadata = _load_skill_metadata(install_dir, path)
        name = skill_metadata.get("name") or Path(path).parent.name
        result.append(
            _capability(
                plugin_id,
                version,
                workspace,
                agent,
                "skill",
                name,
                path,
                skill_metadata.get("description", ""),
                install_dir=str(install_dir),
            )
        )

    for entry in capabilities.get("openapi", []) or []:
        name = entry.get("name")
        if name:
            result.append(
                _capability(
                    plugin_id,
                    version,
                    workspace,
                    agent,
                    "openapi",
                    name,
                    entry["spec"],
                    install_dir=str(install_dir),
                )
            )

    for entry in capabilities.get("mcp", []) or []:
        name = entry.get("name")
        if name:
            result.append(
                _capability(
                    plugin_id,
                    version,
                    workspace,
                    agent,
                    "mcp",
                    name,
                    "",
                    transport=entry.get("transport"),
                    endpoint=entry.get("url") or entry.get("command"),
                    install_dir=str(install_dir),
                )
            )

    for entry in capabilities.get("data_sources", []) or []:
        source_file = _load_child_yaml(install_dir, entry["path"])
        name = source_file.get("id") or Path(entry["path"]).stem
        result.append(
            _capability(
                plugin_id,
                version,
                workspace,
                agent,
                "data_source",
                name,
                entry["path"],
                source_file.get("description", ""),
                install_dir=str(install_dir),
            )
        )

    return result


def filter_capabilities(capabilities: list[dict[str, Any]], workspace: str, agent: str) -> list[dict[str, Any]]:
    return [
        capability
        for capability in capabilities
        if capability.get("workspace") == workspace and capability.get("agent") == agent
    ]


def remove_plugin_capabilities(
    capabilities: list[dict[str, Any]],
    plugin_id: str,
    version: str,
    workspace: str | None = None,
    agent: str | None = None,
) -> list[dict[str, Any]]:
    filtered = []
    for capability in capabilities:
        same_plugin = capability.get("plugin_id") == plugin_id and capability.get("version") == version
        same_workspace = workspace is None or capability.get("workspace") == workspace
        same_agent = agent is None or capability.get("agent") == agent
        if same_plugin and same_workspace and same_agent:
            continue
        filtered.append(capability)
    return filtered


def _capability(
    plugin_id: str,
    version: str,
    workspace: str,
    agent: str,
    capability_type: str,
    name: str,
    source: str,
    description: str = "",
    input_schema: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    normalized_type = "datasource" if capability_type == "data_source" else capability_type
    capability = {
        "capability_id": f"{plugin_id}.{normalized_type}.{name}",
        "plugin_id": plugin_id,
        "version": version,
        "workspace": workspace,
        "agent": agent,
        "type": capability_type,
        "name": name,
        "source": source,
        "description": description,
    }
    if input_schema is not None:
        capability["input_schema"] = input_schema
    capability.update({key: value for key, value in extra.items() if value is not None})
    return capability


def _load_child_yaml(install_dir: Path, relative_path: str) -> dict[str, Any]:
    path = install_dir / "source" / relative_path
    data = load_yaml(path)
    return data if isinstance(data, dict) else {}


def _load_skill_metadata(install_dir: Path, relative_path: str) -> dict[str, Any]:
    path = install_dir / "source" / relative_path
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        return {}
    parts = raw.split("---\n", 2)
    if len(parts) < 3:
        return {}
    data = load_yaml_from_text(parts[1])
    return data if isinstance(data, dict) else {}


def load_yaml_from_text(raw: str) -> Any:
    import yaml

    return yaml.safe_load(raw) or {}
