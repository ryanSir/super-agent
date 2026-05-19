from pathlib import Path

from pydantic import BaseModel

from plugin_runtime_service.errors import CapabilityTypeError


class SkillContext(BaseModel):
    name: str
    description: str | None = None
    content: str
    path: str


def load_skill_context(plugin_dir: Path, name: str, path: str, description: str | None = None) -> SkillContext:
    skill_path = plugin_dir / path
    return SkillContext(
        name=name,
        description=description,
        content=skill_path.read_text(encoding="utf-8"),
        path=path,
    )


def execute_skill_context(_: SkillContext) -> None:
    raise CapabilityTypeError("Skill Context is not an executable runtime tool")
