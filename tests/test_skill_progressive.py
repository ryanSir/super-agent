"""测试 Skill 渐进式加载"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.skills.registry import SkillRegistry
from src.skills.schema import SkillInfo, SkillMetadata


def _make_skill(name: str, description: str) -> SkillInfo:
    return SkillInfo(
        metadata=SkillMetadata(name=name, description=description, path=f"/skill/{name}"),
        scripts=["main.py"],
        references=[],
        doc_content=f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n详细文档内容...",
    )


def _make_registry() -> SkillRegistry:
    """创建预填充的 registry"""
    registry = SkillRegistry(skill_dir=Path("/nonexistent"))
    registry.register(_make_skill("baidu-search", "百度AI搜索"))
    registry.register(_make_skill("ai-ppt-generator", "AI PPT生成"))
    registry.register(_make_skill("paper-search", "论文语义检索"))
    return registry


class TestGetSkillSummary:
    def test_compact_format(self):
        """摘要仅包含名称和描述，格式紧凑"""
        registry = _make_registry()
        summary = registry.get_skill_summary()

        assert "Available skills:" in summary
        assert "baidu-search (百度AI搜索)" in summary
        assert "ai-ppt-generator (AI PPT生成)" in summary
        # 不应包含完整文档内容
        assert "详细文档内容" not in summary
        # 不应包含脚本信息
        assert "main.py" not in summary

    def test_empty_registry(self):
        """空 registry 返回提示文本"""
        registry = SkillRegistry(skill_dir=Path("/nonexistent"))
        summary = registry.get_skill_summary()
        assert "没有可用" in summary

    def test_token_efficiency(self):
        """摘要文本长度远小于全量注入"""
        registry = _make_registry()
        summary = registry.get_skill_summary()

        # 摘要应该很短
        assert len(summary) < 500

        # 全量注入（所有 doc_content）会更长
        full_content = "\n".join(s.doc_content for s in registry.list_skills())
        assert len(summary) < len(full_content)


class TestSearchSkills:
    def test_match_by_name(self):
        """按名称匹配"""
        registry = _make_registry()
        results = registry.search_skills("ppt")

        assert len(results) == 1
        assert results[0].metadata.name == "ai-ppt-generator"

    def test_match_by_description(self):
        """按描述匹配"""
        registry = _make_registry()
        results = registry.search_skills("论文")

        assert len(results) == 1
        assert results[0].metadata.name == "paper-search"

    def test_case_insensitive(self):
        """大小写不敏感"""
        registry = _make_registry()
        results = registry.search_skills("PPT")

        assert len(results) == 1

    def test_no_match_returns_empty(self):
        """无匹配返回空列表"""
        registry = _make_registry()
        results = registry.search_skills("nonexistent")

        assert results == []

    def test_returns_full_info(self):
        """返回完整 SkillInfo（含 doc_content）"""
        registry = _make_registry()
        results = registry.search_skills("baidu")

        assert len(results) == 1
        assert "详细文档内容" in results[0].doc_content

    def test_multiple_matches(self):
        """多个匹配"""
        registry = _make_registry()
        results = registry.search_skills("search")

        assert len(results) == 2
        names = {r.metadata.name for r in results}
        assert names == {"baidu-search", "paper-search"}

    def test_new_skill_appears_in_summary(self):
        """动态注册的 Skill 出现在摘要中"""
        registry = _make_registry()
        registry.register(_make_skill("new-skill", "新技能"))

        summary = registry.get_skill_summary()
        assert "new-skill (新技能)" in summary
