"""SkillRegistry — 三阶段渐进加载

Stage 1: 摘要注入 system prompt（get_skill_summary）
Stage 2: 按需检索完整文档（search_skills）
Stage 3: 执行技能脚本（get + 外部调用）
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.skills.schema import SkillInfo, SkillMetadata

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class SkillRegistry:
    """技能注册表 — 单例模式，三阶段渐进加载"""

    def __init__(self) -> None:
        self._skills: dict[str, SkillInfo] = {}
        self._scanned = False

    def scan(self, skill_dir: str | None = None) -> int:
        """扫描技能目录，解析 SKILL.md frontmatter

        Returns:
            发现的技能数量
        """
        skill_dir = skill_dir or get_settings().skill_dir
        skill_path = Path(skill_dir)

        if not skill_path.exists():
            logger.warning(f"技能目录不存在 | path={skill_dir}")
            return 0

        count = 0
        for entry in skill_path.iterdir():
            if not entry.is_dir():
                continue
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                continue

            info = self._parse_skill(entry, skill_md)
            if info:
                self._skills[info.metadata.name] = info
                count += 1

        self._scanned = True
        logger.info(f"技能扫描完成 | count={count} dir={skill_dir}")
        return count

    def get(self, name: str) -> SkillInfo | None:
        """按名称获取技能"""
        self._ensure_scanned()
        return self._skills.get(name)

    def list_skills(self) -> list[SkillInfo]:
        """列出所有技能"""
        self._ensure_scanned()
        return list(self._skills.values())

    def search_skills(self, query: str) -> list[SkillInfo]:
        """按关键词搜索技能（名称和描述）"""
        self._ensure_scanned()
        query_lower = query.lower()
        return [
            info
            for info in self._skills.values()
            if query_lower in info.metadata.name.lower()
            or query_lower in info.metadata.description.lower()
            or query_lower in info.doc_content.lower()
        ]

    def get_skill_summary(self) -> str:
        """生成紧凑的技能摘要（注入 system prompt）"""
        self._ensure_scanned()
        if not self._skills:
            return "当前无可用技能。"

        lines = ["可用技能列表："]
        for info in self._skills.values():
            scripts = ", ".join(info.scripts) if info.scripts else "无脚本"
            lines.append(f"- {info.metadata.name}: {info.metadata.description} [{scripts}]")
        return "\n".join(lines)

    def _ensure_scanned(self) -> None:
        if not self._scanned:
            self.scan()

    def _parse_skill(self, skill_dir: Path, skill_md: Path) -> SkillInfo | None:
        """解析单个技能目录"""
        try:
            content = skill_md.read_text(encoding="utf-8")
            metadata = self._parse_frontmatter(content, skill_dir)

            # 发现脚本
            scripts_dir = skill_dir / "scripts"
            scripts: list[str] = []
            if scripts_dir.exists():
                scripts = [
                    f.name
                    for f in scripts_dir.iterdir()
                    if f.is_file() and f.suffix in (".py", ".sh", ".js", ".ts")
                ]

            # 发现参考文档
            refs_dir = skill_dir / "references"
            references: list[str] = []
            if refs_dir.exists():
                references = [f.name for f in refs_dir.iterdir() if f.is_file()]

            return SkillInfo(
                metadata=metadata,
                scripts=sorted(scripts),
                references=sorted(references),
                doc_content=content,
            )
        except Exception as e:
            logger.warning(f"技能解析失败 | dir={skill_dir} error={e}")
            return None

    def _parse_frontmatter(self, content: str, skill_dir: Path) -> SkillMetadata:
        """解析 YAML frontmatter"""
        match = _FRONTMATTER_RE.match(content)
        name = skill_dir.name
        description = ""

        if match:
            fm_text = match.group(1)
            for line in fm_text.splitlines():
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip("\"'")
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip("\"'")

        return SkillMetadata(name=name, description=description, path=str(skill_dir))


# 全局单例
skill_registry = SkillRegistry()
