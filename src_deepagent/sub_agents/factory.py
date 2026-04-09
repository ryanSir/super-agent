"""Sub-Agent 配置工厂

基于 agent_tools 创建三个角色的 SubAgentConfig 声明式配置。
"""

from __future__ import annotations

from typing import Any, Callable

from src_deepagent.core.logging import get_logger
from src_deepagent.llm.config import get_model
from src_deepagent.sub_agents.prompts import (
    ANALYSIS_INSTRUCTIONS,
    RESEARCH_INSTRUCTIONS,
    WRITING_INSTRUCTIONS,
)

logger = get_logger(__name__)


def create_sub_agent_configs(
    agent_tools: list[Callable],
) -> list[dict[str, Any]]:
    """创建三个角色的 Sub-Agent 配置

    Args:
        agent_tools: 已创建的工具函数列表（从 ResolvedResources.agent_tools 传入）

    Returns:
        SubAgentConfig 兼容的配置字典列表
    """
    tool_map = {t.__name__: t for t in agent_tools}

    configs = [
        {
            "name": "researcher",
            "description": "信息检索与综合分析专家",
            "instructions": RESEARCH_INSTRUCTIONS,
            "model": get_model("execution"),
            "include_todo": True,
            "include_filesystem": False,
            "include_subagents": False,
            "include_skills": False,
            "context_manager": True,
            "context_manager_max_tokens": 100_000,
            "cost_tracking": True,
            "tools": _pick_tools(tool_map, [
                "execute_rag_search",
                "execute_api_call",
                "execute_skill",
                "search_skills",
                "execute_sandbox",
            ]),
        },
        {
            "name": "analyst",
            "description": "数据分析与可视化专家",
            "instructions": ANALYSIS_INSTRUCTIONS,
            "model": get_model("execution"),
            "include_todo": True,
            "include_filesystem": False,
            "include_subagents": False,
            "include_skills": False,
            "context_manager": True,
            "context_manager_max_tokens": 100_000,
            "cost_tracking": True,
            "tools": _pick_tools(tool_map, [
                "execute_db_query",
                "execute_rag_search",
                "execute_sandbox",
                "emit_chart",
            ]),
        },
        {
            "name": "writer",
            "description": "报告与文档撰写专家",
            "instructions": WRITING_INSTRUCTIONS,
            "model": get_model("execution"),
            "include_todo": True,
            "include_filesystem": True,
            "include_subagents": False,
            "include_skills": False,
            "context_manager": True,
            "context_manager_max_tokens": 100_000,
            "cost_tracking": True,
            "tools": _pick_tools(tool_map, [
                "execute_skill",
                "execute_sandbox",
                "emit_chart",
            ]),
        },
    ]

    logger.info(
        f"Sub-Agent 配置创建完成 | "
        f"roles={[c['name'] for c in configs]} "
        f"agent_tools={len(agent_tools)}"
    )
    return configs


def _pick_tools(
    tool_map: dict[str, Callable],
    names: list[str],
) -> list[Callable]:
    """从工具映射中选取指定工具"""
    tools: list[Callable] = []
    for name in names:
        tool = tool_map.get(name)
        if tool:
            tools.append(tool)
        else:
            logger.warning(f"桥接工具未找到: {name}")
    return tools
