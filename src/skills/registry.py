"""Skill 注册中心

扫描 skill/ 目录，解析 SKILL.md frontmatter，维护可用 skill 列表。
"""

# 标准库
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# 本地模块
from src.core.logging import get_logger
from src.skills.schema import SkillInfo, SkillMetadata

logger = get_logger(__name__)

# 默认 skill 根目录
DEFAULT_SKILL_DIR = Path(__file__).parent.parent.parent / "skill"


class SkillRegistry:
    """Skill 注册中心

    扫描 skill/ 目录，解析每个 skill 的 SKILL.md，
    维护全局可用 skill 列表供 Orchestrator 调用。
    """

    def __init__(self, skill_dir: Optional[Path] = None) -> None:
        self._skill_dir = skill_dir or DEFAULT_SKILL_DIR
        self._skills: Dict[str, SkillInfo] = {}

    @property
    def skill_dir(self) -> Path:
        return self._skill_dir

    def scan(self) -> int:
        """扫描 skill 目录，注册所有 skill

        Returns:
            注册的 skill 数量
        """
        self._skills.clear()

        if not self._skill_dir.exists():
            logger.warning(f"[SkillRegistry] skill 目录不存在 | path={self._skill_dir}")
            return 0

        for entry in sorted(self._skill_dir.iterdir()):
            if not entry.is_dir():
                continue

            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                info = self._parse_skill(entry, skill_md)
                self._skills[info.metadata.name] = info
                logger.info(
                    f"[SkillRegistry] 注册 skill | "
                    f"name={info.metadata.name} scripts={info.scripts}"
                )
            except Exception as e:
                logger.warning(
                    f"[SkillRegistry] 解析 skill 失败 | path={entry} error={e}"
                )

        logger.info(f"[SkillRegistry] 扫描完成 | total={len(self._skills)}")
        return len(self._skills)

    def get(self, name: str) -> Optional[SkillInfo]:
        """获取 skill 信息"""
        return self._skills.get(name)

    def list_skills(self) -> List[SkillInfo]:
        """列出所有已注册的 skill"""
        return list(self._skills.values())

    def list_names(self) -> List[str]:
        """列出所有 skill 名称"""
        return list(self._skills.keys())

    def get_skill_summary(self) -> str:
        """生成 skill 摘要（渐进式加载 - 阶段 1）

        仅返回名称 + 一句话描述的紧凑文本，用于注入 system prompt。
        Agent 需要完整定义时通过 search_skills 按需获取。
        """
        if not self._skills:
            return "当前没有可用的 Skill。"

        items = [
            f"{info.metadata.name} ({info.metadata.description})"
            for info in self._skills.values()
        ]
        return "Available skills: " + ", ".join(items)

    def search_skills(self, query: str) -> List[SkillInfo]:
        """按关键词检索匹配的 skill（渐进式加载 - 阶段 2）

        返回名称或描述中包含 query 的所有 Skill 的完整 SkillInfo。

        Args:
            query: 搜索关键词

        Returns:
            匹配的 SkillInfo 列表
        """
        query_lower = query.lower()
        results = []
        for info in self._skills.values():
            if (
                query_lower in info.metadata.name.lower()
                or query_lower in info.metadata.description.lower()
            ):
                results.append(info)
        return results

    def register(self, info: SkillInfo) -> None:
        """手动注册 skill（用于动态创建的 skill）"""
        self._skills[info.metadata.name] = info
        logger.info(f"[SkillRegistry] 手动注册 skill | name={info.metadata.name}")

    def _parse_skill(self, skill_dir: Path, skill_md: Path) -> SkillInfo:
        """解析单个 skill 目录"""
        content = skill_md.read_text(encoding="utf-8")
        metadata = self._parse_frontmatter(content, skill_dir)

        # 扫描 scripts/
        scripts_dir = skill_dir / "scripts"
        scripts = []
        if scripts_dir.exists():
            scripts = [
                f.name for f in sorted(scripts_dir.iterdir())
                if f.is_file() and f.suffix in (".py", ".sh", ".js", ".ts")
            ]

        # 扫描 references/
        refs_dir = skill_dir / "references"
        references = []
        if refs_dir.exists():
            references = [f.name for f in sorted(refs_dir.iterdir()) if f.is_file()]

        return SkillInfo(
            metadata=metadata,
            scripts=scripts,
            references=references,
            doc_content=content,
        )

    def _parse_frontmatter(self, content: str, skill_dir: Path) -> SkillMetadata:
        """解析 SKILL.md 的 YAML frontmatter"""
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            # 没有 frontmatter，用目录名作为 name
            return SkillMetadata(
                name=skill_dir.name,
                description="",
                path=str(skill_dir),
            )

        frontmatter = match.group(1)
        data = {}
        for line in frontmatter.strip().splitlines():
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                data[key.strip()] = value.strip()

        return SkillMetadata(
            name=data.get("name", skill_dir.name),
            description=data.get("description", ""),
            path=str(skill_dir),
        )


# 全局单例
skill_registry = SkillRegistry()
