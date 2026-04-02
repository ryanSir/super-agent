"""Orchestrator 系统 Prompt

从 system.md 加载提示词模板，保持代码与提示词分离。
"""

from pathlib import Path

_PROMPT_FILE = Path(__file__).parent / "system.md"
ORCHESTRATOR_SYSTEM_PROMPT = _PROMPT_FILE.read_text(encoding="utf-8")


def build_system_prompt(skill_summary: str = "", user_context: str = "") -> str:
    """构建完整的 system prompt

    Args:
        skill_summary: Skill 摘要文本（渐进式加载阶段 1）
        user_context: 用户记忆上下文（[User Context] 段落）

    Returns:
        完整的 system prompt
    """
    return ORCHESTRATOR_SYSTEM_PROMPT.format(
        skill_summary=skill_summary or "当前没有可用的 Skill。",
        user_context=user_context,
    )
