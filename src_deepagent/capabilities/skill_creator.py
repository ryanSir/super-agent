"""Skill 创建器

在 src_deepagent 内独立实现，不依赖 src/ 命名空间。
支持两种模式：
- 最小化创建：仅提供名称和描述，自动生成模板脚本
- 完整创建：提供 script_content / doc_content，直接写入
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src_deepagent.capabilities.skills.registry import skill_registry
from src_deepagent.capabilities.skills.schema import SkillInfo, SkillMetadata
from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class SkillCreateRequest(BaseModel):
    """技能创建请求"""

    name: str = Field(description="技能名称（小写字母 + 连字符，如 my-skill）")
    description: str = Field(description="技能一句话描述")
    script_name: str = Field(default="main.py", description="主脚本文件名")
    script_content: Optional[str] = Field(default=None, description="脚本内容（可选，不提供则生成模板）")
    doc_content: Optional[str] = Field(default=None, description="附加文档内容（追加到 SKILL.md）")
    overwrite: bool = Field(default=False, description="是否覆盖已存在的技能目录")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(
                f"技能名称 '{v}' 不合法，必须符合 ^[a-z][a-z0-9-]*$（小写字母开头，只含小写字母、数字和连字符）"
            )
        return v


def create_skill(request: SkillCreateRequest) -> dict:
    """创建新技能包

    Args:
        request: 创建请求

    Returns:
        dict: WorkerResult 兼容格式，success=True 时 data 包含 SkillInfo 字段
    """
    skill_dir = Path(get_settings().skill_dir) / request.name

    # 冲突检测：先查 registry，再查文件系统
    existing = skill_registry.get(request.name)
    if existing or skill_dir.exists():
        if not request.overwrite:
            return {
                "success": False,
                "error": f"技能 '{request.name}' 已存在，如需覆盖请传 overwrite=true",
            }
        if skill_dir.exists():
            import shutil
            shutil.rmtree(skill_dir)
        logger.warning(f"[SkillCreator] 覆盖已存在技能 | name={request.name}")

    # 创建目录结构
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "references").mkdir(exist_ok=True)

    # 写入 SKILL.md
    skill_md_content = _build_skill_md(
        name=request.name,
        description=request.description,
        script_name=request.script_name,
        doc_content=request.doc_content,
    )
    (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

    # 写入脚本
    script_content = request.script_content or _generate_template_script(
        request.name, request.description
    )
    script_path = scripts_dir / request.script_name
    script_path.write_text(script_content, encoding="utf-8")
    script_path.chmod(0o755)

    # 注册到 registry
    info = SkillInfo(
        metadata=SkillMetadata(
            name=request.name,
            description=request.description,
            path=str(skill_dir),
        ),
        scripts=[request.script_name],
        references=[],
        doc_content=skill_md_content,
    )
    skill_registry.register(info)

    logger.info(
        f"[SkillCreator] 技能创建成功 | name={request.name} path={skill_dir} "
        f"script={request.script_name} overwrite={request.overwrite}"
    )

    return {
        "success": True,
        "message": f"技能 '{request.name}' 已创建并注册成功，无需再调用 search_skills 验证。",
        "data": {
            "name": info.metadata.name,
            "description": info.metadata.description,
            "path": info.metadata.path,
            "scripts": info.scripts,
            "references": info.references,
        },
    }


def _build_skill_md(name: str, description: str, script_name: str, doc_content: Optional[str]) -> str:
    """构建 SKILL.md 内容"""
    title = name.replace("-", " ").title()
    parts = [
        "---",
        f"name: {name}",
        f"description: {description}",
        "---",
        "",
        f"# {title}",
        "",
        description,
        "",
        "## 可用脚本",
        "",
        f"### {script_name}",
        "",
        "```bash",
        f"python ${{CLAUDE_SKILL_DIR}}/scripts/{script_name} [参数]",
        "```",
    ]
    if doc_content:
        parts.extend(["", doc_content])
    return "\n".join(parts) + "\n"


def _generate_template_script(name: str, description: str) -> str:
    """生成带 argparse 的 Python 模板脚本"""
    func_name = name.replace("-", "_")
    return f'''#!/usr/bin/env python3
"""
{description}

Skill: {name}
自动生成的模板脚本，请根据需要修改。

使用示例：
  python ${{CLAUDE_SKILL_DIR}}/scripts/main.py [参数]
"""

import sys
import json
import argparse


def {func_name}(input_text: str) -> dict:
    """执行 {name} 的核心逻辑

    Args:
        input_text: 输入文本

    Returns:
        结果字典
    """
    # TODO: 实现具体逻辑
    return {{
        "skill": "{name}",
        "input": input_text,
        "result": f"已处理: {{input_text}}",
        "status": "success",
    }}


def main():
    parser = argparse.ArgumentParser(description="{description}")
    parser.add_argument("input", nargs="?", default="", help="输入文本")
    args = parser.parse_args()

    result = {func_name}(args.input)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
'''
