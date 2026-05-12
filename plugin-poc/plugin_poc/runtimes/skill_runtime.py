from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..management.manager import list_capabilities
from ..shared.errors import PluginPocError


class SkillRuntimeError(PluginPocError):
    """Raised when skill capability loading fails."""


def list_agent_skills(
    state_dir: str | Path,
    workspace: str,
    agent: str,
    include_content: bool = False,
) -> list[dict[str, Any]]:
    skills = []
    for capability in list_capabilities(state_dir, workspace, agent):
        if capability.get("type") != "skill":
            continue
        skill = load_skill_capability(capability)
        if not include_content:
            skill.pop("content", None)
        skills.append(skill)
    return skills


def render_skill_context(state_dir: str | Path, workspace: str, agent: str) -> str:
    skills = list_agent_skills(state_dir, workspace, agent, include_content=True)
    if not skills:
        return ""

    blocks = ["# Available Plugin Skills"]
    for skill in skills:
        blocks.extend(
            [
                "",
                f"## {skill['name']}",
                f"Plugin: {skill['plugin_id']}@{skill['version']}",
            ]
        )
        description = skill.get("description")
        if description:
            blocks.append(f"Description: {description}")
        blocks.extend(["", skill["content"].strip()])
    return "\n".join(blocks).strip() + "\n"


def load_skill_capability(capability: dict[str, Any]) -> dict[str, Any]:
    install_dir = capability.get("install_dir")
    source = capability.get("source")
    if not install_dir or not source:
        raise SkillRuntimeError("skill capability is missing install_dir or source")

    path = Path(install_dir) / "source" / source
    metadata, content = parse_skill_file(path)
    name = metadata.get("name") or capability.get("name") or path.parent.name

    return {
        "capability_id": capability["capability_id"],
        "plugin_id": capability["plugin_id"],
        "version": capability["version"],
        "name": name,
        "description": metadata.get("description") or capability.get("description", ""),
        "source": source,
        "content": content,
        "metadata": metadata,
    }


def parse_skill_file(path: str | Path) -> tuple[dict[str, Any], str]:
    skill_path = Path(path)
    if not skill_path.exists() or not skill_path.is_file():
        raise SkillRuntimeError(f"skill file does not exist: {skill_path}")

    raw = skill_path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        return {}, raw.strip()

    parts = raw.split("---\n", 2)
    if len(parts) < 3:
        return {}, raw.strip()

    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise SkillRuntimeError(f"invalid skill frontmatter: {skill_path}") from exc

    if not isinstance(metadata, dict):
        raise SkillRuntimeError(f"skill frontmatter must be an object: {skill_path}")
    return metadata, parts[2].strip()
