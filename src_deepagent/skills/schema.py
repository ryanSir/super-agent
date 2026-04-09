"""Skill 数据模型"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    """Skill 元数据（从 SKILL.md frontmatter 解析）"""

    name: str = Field(description="技能名称（小写字母+连字符）")
    description: str = Field(default="", description="技能描述")
    path: str = Field(default="", description="技能目录路径")


class SkillInfo(BaseModel):
    """Skill 完整信息"""

    metadata: SkillMetadata
    scripts: list[str] = Field(default_factory=list, description="可用脚本列表")
    references: list[str] = Field(default_factory=list, description="参考文档列表")
    doc_content: str = Field(default="", description="SKILL.md 完整内容")
