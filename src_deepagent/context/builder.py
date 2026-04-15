"""上下文系统 — System Prompt 构建器

从 templates/ 目录加载提示词模板，根据 ExecutionMode 动态组装。
提示词与代码分离，方便独立维护和调整。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# 模板缓存（启动时加载一次）
_cache: dict[str, str] = {}


def _load_template(name: str) -> str:
    """加载模板文件内容（带缓存）"""
    if name in _cache:
        return _cache[name]

    path = _TEMPLATES_DIR / f"{name}.md"
    if not path.exists():
        logger.warning(f"模板文件不存在 | name={name} path={path}")
        return ""

    content = path.read_text(encoding="utf-8").strip()
    _cache[name] = content
    return content


def reload_templates() -> None:
    """清除缓存，强制重新加载所有模板（热更新用）"""
    _cache.clear()
    logger.info("模板缓存已清除")


# ── 模式到模板文件的映射 ─────────────────────────────────

_MODE_TEMPLATES: dict[str, str] = {
    "direct": "mode_direct",
    "auto": "mode_auto",
    "plan_and_execute": "mode_plan_and_execute",
    "sub_agent": "mode_sub_agent",
}


def build_dynamic_instructions(
    skill_summary: str = "",
    memory_text: str = "",
    sub_agent_roles: list[dict[str, str]] | None = None,
    max_concurrent_subagents: int = 3,
    execution_mode: str = "auto",
    runtime_context: dict[str, str] | None = None,
) -> str:
    """构建主 Agent 的动态 system prompt

    从 templates/ 加载各模块模板，根据 execution_mode 动态组装。

    Args:
        skill_summary: Skill 注册表摘要
        memory_text: 用户记忆上下文
        sub_agent_roles: Sub-Agent 角色描述列表
        max_concurrent_subagents: Sub-Agent 最大并发数
        execution_mode: 执行模式（direct/auto/plan_and_execute/sub_agent）
        runtime_context: 运行时上下文（session_id/user_id/current_time 等）

    Returns:
        完整的 system prompt
    """
    sections: list[str] = []

    # 1. 角色定义
    sections.append(_load_template("role"))

    # 2. 运行时上下文（System Content）
    if runtime_context:
        ctx_template = _load_template("runtime_context")
        sections.append(ctx_template.format(
            session_id=runtime_context.get("session_id", ""),
            user_id=runtime_context.get("user_id", ""),
            current_time=runtime_context.get("current_time", ""),
            execution_mode=execution_mode,
            user_context=runtime_context.get("user_context", ""),
        ))

    # 3. 思考策略（DIRECT 模式不注入，避免模型输出 <thinking> 标签拖慢响应）
    # if execution_mode != "direct":
    sections.append(_load_template("thinking_style"))

    # 4. 澄清系统
    sections.append(_load_template("clarification"))

    # 4. 执行模式指导（根据 mode 加载对应模板）
    mode_template = _MODE_TEMPLATES.get(execution_mode, "mode_auto")
    sections.append(_load_template(mode_template))

    # 5. 工具使用规范
    sections.append(_load_template("tool_usage"))

    # 6. 技能系统（动态注入）
    if skill_summary:
        sections.append(
            f"<skill_system>\n"
            f"以下技能可通过 execute_skill 调用。先用 search_skills 查看详情，再执行。\n\n"
            f"{skill_summary}\n"
            f"</skill_system>"
        )

    # 7. Sub-Agent 编排指令（仅 auto/sub_agent 模式）
    if sub_agent_roles and execution_mode in ("auto", "sub_agent"):
        roles_text = "\n".join(
            f"  - {r['name']}: {r['description']}" for r in sub_agent_roles
        )
        mandatory = "你必须使用 Sub-Agent 完成任务。" if execution_mode == "sub_agent" else ""

        subagent_template = _load_template("subagent_system")
        sections.append(
            subagent_template.format(
                mandatory=mandatory,
                roles_text=roles_text,
                max_concurrent=max_concurrent_subagents,
            )
        )

    # 8. 用户记忆
    if memory_text:
        sections.append(f"<memory>\n{memory_text}\n</memory>")

    # 10. 回复风格
    sections.append(_load_template("response_style"))

    # 11. 关键提醒
    sections.append(_load_template("critical_reminders"))

    # 过滤空段落
    sections = [s for s in sections if s]

    return "\n\n".join(sections)
