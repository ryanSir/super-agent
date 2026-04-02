"""Skill 数据模型"""

# 标准库
import enum
from typing import Any, Dict, List, Optional

# 第三方库
from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    """Skill 元数据 — 从 SKILL.md frontmatter 解析"""
    name: str
    description: str
    path: str = ""  # skill 目录绝对路径


class SkillInfo(BaseModel):
    """Skill 完整信息"""
    metadata: SkillMetadata
    scripts: List[str] = Field(default_factory=list)  # 可用脚本列表
    references: List[str] = Field(default_factory=list)  # 参考资料列表
    doc_content: str = ""  # SKILL.md 完整内容


class SkillExecuteRequest(BaseModel):
    """Skill 执行请求"""
    skill_name: str
    script_name: str = ""  # 不指定则用第一个脚本
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=60, ge=5, le=600)


class SkillExecuteResult(BaseModel):
    """Skill 执行结果"""
    skill_name: str
    script_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    output_data: Optional[Any] = None  # 解析后的 JSON 输出


class SkillCreateRequest(BaseModel):
    """Skill 创建请求"""
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str
    script_content: str = ""  # 可选，不传则生成模板
    script_name: str = "main.py"
    doc_content: str = ""
