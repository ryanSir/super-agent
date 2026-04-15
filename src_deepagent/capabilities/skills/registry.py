"""SkillRegistry — 精简版注册表

保留 register() / get() / list_names() 用于动态注册场景（create_skill 后立即生效）。
文件系统发现和三阶段加载已委托给 pydantic-deep 框架的 SkillsToolset。

Deprecated 方法（由 SkillsToolset 替代）：
- scan() → 框架 skill_directories 自动发现
- get_skill_summary() → 框架 SkillsToolset.get_instructions() 自动注入
- search_skills() → 框架 list_skills() 工具
- list_skills() → 框架 list_skills() 工具
"""

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import Any

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.capabilities.skills.schema import SkillInfo, SkillMetadata

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class SkillRegistry:
    """技能注册表 — 单例模式，三阶段渐进加载"""

    def __init__(self) -> None:
        self._skills: dict[str, SkillInfo] = {}
        self._scanned = False

    def scan(self, skill_dir: str | None = None) -> int:
        """扫描技能目录，解析 SKILL.md frontmatter

        .. deprecated:: 由框架 SkillsToolset skill_directories 自动发现替代

        Returns:
            发现的技能数量
        """
        warnings.warn(
            "SkillRegistry.scan() 已废弃，请使用框架 SkillsToolset skill_directories 自动发现",
            DeprecationWarning,
            stacklevel=2,
        )
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
        """列出所有技能

        .. deprecated:: 由框架 SkillsToolset list_skills() 工具替代
        """
        warnings.warn(
            "SkillRegistry.list_skills() 已废弃，请使用框架 SkillsToolset list_skills()",
            DeprecationWarning,
            stacklevel=2,
        )
        self._ensure_scanned()
        return list(self._skills.values())

    def search_skills(self, query: str) -> list[SkillInfo]:
        """按关键词搜索技能（名称和描述），支持多词分词匹配

        .. deprecated:: 由框架 SkillsToolset list_skills() 工具替代
        """
        warnings.warn(
            "SkillRegistry.search_skills() 已废弃，请使用框架 SkillsToolset list_skills()",
            DeprecationWarning,
            stacklevel=2,
        )
        self._ensure_scanned()
        # 按空格和连字符分词，任意一个 token 命中即返回
        tokens = [t.lower() for t in re.split(r"[\s\-_]+", query) if t]
        if not tokens:
            return list(self._skills.values())

        results = []
        for info in self._skills.values():
            haystack = (
                info.metadata.name.lower() + " "
                + info.metadata.description.lower() + " "
                + info.doc_content.lower()
            )
            if any(token in haystack for token in tokens):
                results.append(info)
        return results

    def get_skill_summary(self) -> str:
        """生成紧凑的技能摘要（注入 system prompt）

        .. deprecated:: 由框架 SkillsToolset.get_instructions() 自动注入替代
        """
        warnings.warn(
            "SkillRegistry.get_skill_summary() 已废弃，请使用框架 SkillsToolset.get_instructions()",
            DeprecationWarning,
            stacklevel=2,
        )
        self._ensure_scanned()
        if not self._skills:
            return "当前无可用技能。"

        lines = ["可用技能列表："]
        for info in self._skills.values():
            scripts = ", ".join(info.scripts) if info.scripts else "无脚本"
            lines.append(f"- {info.metadata.name}: {info.metadata.description} [{scripts}]")
        return "\n".join(lines)

    def register(self, info: SkillInfo) -> None:
        """手动注册技能（动态创建后立即生效）"""
        self._skills[info.metadata.name] = info
        logger.info(f"技能手动注册 | name={info.metadata.name}")

    def list_names(self) -> list[str]:
        """列出所有已注册技能名称"""
        self._ensure_scanned()
        return list(self._skills.keys())

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
        """解析 YAML frontmatter，支持多行折叠标量（>-、|）"""
        match = _FRONTMATTER_RE.match(content)
        name = skill_dir.name
        description = ""
        execution = "sandbox"

        if match:
            try:
                import yaml
                fm = yaml.safe_load(match.group(1)) or {}
                name = str(fm.get("name", skill_dir.name)).strip()
                description = str(fm.get("description", "")).strip()
                raw_execution = str(fm.get("execution", "sandbox")).strip().lower()
                if raw_execution in ("native", "sandbox"):
                    execution = raw_execution
                else:
                    logger.warning(
                        f"无效的 execution 值 '{raw_execution}'，回退为 sandbox | skill={name}"
                    )
            except Exception:
                # fallback：简单行匹配
                for line in match.group(1).splitlines():
                    line = line.strip()
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("execution:"):
                        raw_val = line.split(":", 1)[1].strip().strip("\"'").lower()
                        if raw_val in ("native", "sandbox"):
                            execution = raw_val

        return SkillMetadata(name=name, description=description, path=str(skill_dir), execution=execution)


# 全局单例
skill_registry = SkillRegistry()
