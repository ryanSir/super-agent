"""Skill 创建器

基于 Claude 官方 skill-creator 标准，创建符合规范的 skill 包。
支持两种模式：
1. 模板创建：调用官方 init_skill 生成标准模板
2. 完整创建：直接写入 SKILL.md + 脚本内容
"""

# 标准库
from pathlib import Path
from typing import Optional

# 本地模块
from src.core.logging import get_logger
from src.skills.init_skill import init_skill as official_init_skill
from src.skills.registry import skill_registry
from src.skills.schema import SkillCreateRequest, SkillInfo, SkillMetadata

logger = get_logger(__name__)


async def create_skill(request: SkillCreateRequest) -> SkillInfo:
    """创建新 skill

    如果提供了 script_content 或 doc_content，直接写入完整 skill。
    否则调用官方 init_skill 生成标准模板。

    Args:
        request: 创建请求

    Returns:
        SkillInfo: 创建的 skill 信息
    """
    skill_dir = skill_registry.skill_dir / request.name

    if skill_dir.exists():
        logger.warning(f"[SkillCreator] skill 已存在，覆盖 | name={request.name}")
        # 清理旧目录
        import shutil
        shutil.rmtree(skill_dir)

    has_custom_content = bool(request.script_content or request.doc_content)

    if has_custom_content:
        # 完整创建模式：直接写入用户提供的内容
        info = _create_full_skill(request, skill_dir)
    else:
        # 模板创建模式：调用官方 init_skill
        info = _create_template_skill(request, skill_dir)

    # 注册到 registry
    skill_registry.register(info)

    logger.info(
        f"[SkillCreator] skill 创建成功 | "
        f"name={request.name} path={skill_dir} scripts={info.scripts} "
        f"mode={'custom' if has_custom_content else 'template'}"
    )
    return info


def _create_template_skill(request: SkillCreateRequest, skill_dir: Path) -> SkillInfo:
    """使用官方 init_skill 创建模板 skill"""
    parent_dir = skill_dir.parent
    result = official_init_skill(request.name, str(parent_dir))

    if result is None:
        # init_skill 失败（目录已存在等），手动创建
        return _create_full_skill(request, skill_dir)

    # 读取生成的 SKILL.md 并更新 description
    skill_md_path = skill_dir / "SKILL.md"
    if skill_md_path.exists():
        content = skill_md_path.read_text(encoding="utf-8")
        # 替换 TODO description
        content = content.replace(
            "[TODO: Complete and informative explanation of what the skill does and when to use it. "
            "Include WHEN to use this skill - specific scenarios, file types, or tasks that trigger it.]",
            request.description,
        )
        skill_md_path.write_text(content, encoding="utf-8")

    # 扫描生成的文件
    scripts = _scan_dir(skill_dir / "scripts", (".py", ".sh", ".js", ".ts"))
    references = _scan_dir(skill_dir / "references")
    doc_content = skill_md_path.read_text(encoding="utf-8") if skill_md_path.exists() else ""

    return SkillInfo(
        metadata=SkillMetadata(
            name=request.name,
            description=request.description,
            path=str(skill_dir),
        ),
        scripts=scripts,
        references=references,
        doc_content=doc_content,
    )


def _create_full_skill(request: SkillCreateRequest, skill_dir: Path) -> SkillInfo:
    """直接创建完整 skill（用户提供了内容）"""
    # 创建目录结构
    scripts_dir = skill_dir / "scripts"
    refs_dir = skill_dir / "references"
    assets_dir = skill_dir / "assets"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 生成 SKILL.md
    title = request.name.replace("-", " ").title()
    skill_md_content = _build_skill_md(
        name=request.name,
        description=request.description,
        title=title,
        script_name=request.script_name,
        doc_content=request.doc_content,
    )
    (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

    # 写入脚本
    scripts = []
    script_content = request.script_content or _generate_template_script(
        request.name, request.description
    )
    script_path = scripts_dir / request.script_name
    script_path.write_text(script_content, encoding="utf-8")
    script_path.chmod(0o755)
    scripts.append(request.script_name)

    return SkillInfo(
        metadata=SkillMetadata(
            name=request.name,
            description=request.description,
            path=str(skill_dir),
        ),
        scripts=scripts,
        references=[],
        doc_content=skill_md_content,
    )


def _build_skill_md(
    name: str,
    description: str,
    title: str,
    script_name: str,
    doc_content: str,
) -> str:
    """构建 SKILL.md 内容"""
    parts = [
        f"---",
        f"name: {name}",
        f"description: {description}",
        f"---",
        f"",
        f"# {title}",
        f"",
        f"{description}",
        f"",
        f"## 可用脚本",
        f"",
        f"### {script_name}",
        f"",
        f"```bash",
        f"python ${{CLAUDE_SKILL_DIR}}/scripts/{script_name} [参数]",
        f"```",
    ]
    if doc_content:
        parts.extend(["", doc_content])

    return "\n".join(parts) + "\n"


def _generate_template_script(name: str, description: str) -> str:
    """生成模板脚本"""
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


def _scan_dir(dir_path: Path, extensions: tuple = None) -> list[str]:
    """扫描目录下的文件"""
    if not dir_path.exists():
        return []
    files = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file():
            if extensions is None or f.suffix.lower() in extensions:
                files.append(f.name)
    return files
