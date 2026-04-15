"""Sub-Agent 配置工厂

合并预置角色（researcher/analyst/writer）和自定义角色（agents/ 目录）。
"""

from __future__ import annotations

from typing import Any, Callable

from src_deepagent.core.logging import get_logger
from src_deepagent.llm.config import get_model
from src_deepagent.agents.roles import (
    ANALYSIS_INSTRUCTIONS,
    RESEARCH_INSTRUCTIONS,
    WRITING_INSTRUCTIONS,
)

logger = get_logger(__name__)


def create_sub_agent_configs(
    agent_tools: list[Callable],
    custom_agents_dir: str = "agents",
) -> list[dict[str, Any]]:
    """创建 Sub-Agent 配置（预置 + 自定义合并）

    Args:
        agent_tools: 已创建的工具函数列表
        custom_agents_dir: 自定义 Agent 目录路径

    Returns:
        SubAgentConfig 兼容的配置字典列表
    """
    tool_map = {t.__name__: t for t in agent_tools}

    # 预置角色
    builtin = _create_builtin_configs(tool_map)

    # 自定义角色
    custom = _load_custom_configs(tool_map, custom_agents_dir)

    configs = builtin + custom

    logger.info(
        f"Sub-Agent 配置创建完成 | "
        f"builtin={[c['name'] for c in builtin]} "
        f"custom={[c['name'] for c in custom]} "
        f"agent_tools={len(agent_tools)}"
    )
    return configs


def _create_builtin_configs(tool_map: dict[str, Callable]) -> list[dict[str, Any]]:
    """创建三个预置角色配置"""
    return [
        {
            "name": "researcher",
            "description": "信息检索与综合分析专家",
            "instructions": RESEARCH_INSTRUCTIONS,
            "model": get_model("subagent"),
            "include_todo": True,
            "include_filesystem": False,
            "include_subagents": False,
            "include_skills": False,
            "web_search": False,
            "web_fetch": False,
            "context_manager": True,
            "context_manager_max_tokens": 100_000,
            "cost_tracking": True,
            "tools": _pick_tools(tool_map, [
                "execute_rag_search",
                "execute_api_call",
                "execute_skill",
                "search_skills",
                "create_skill",
                "execute_sandbox",
            ]),
        },
        {
            "name": "analyst",
            "description": "数据分析与可视化专家",
            "instructions": ANALYSIS_INSTRUCTIONS,
            "model": get_model("subagent"),
            "include_todo": True,
            "include_filesystem": False,
            "include_subagents": False,
            "include_skills": False,
            "web_search": False,
            "web_fetch": False,
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
            "model": get_model("subagent"),
            "include_todo": True,
            "include_filesystem": True,
            "include_subagents": False,
            "include_skills": False,
            "web_search": False,
            "web_fetch": False,
            "context_manager": True,
            "context_manager_max_tokens": 100_000,
            "cost_tracking": True,
            "tools": _pick_tools(tool_map, [
                "execute_skill",
                "create_skill",
                "execute_sandbox",
                "emit_chart",
            ]),
        },
    ]


def _load_custom_configs(
    tool_map: dict[str, Callable],
    agents_dir: str,
) -> list[dict[str, Any]]:
    """加载自定义 Agent 配置"""
    try:
        from src_deepagent.agents.custom.registry import custom_agent_registry

        if not custom_agent_registry._scanned:
            custom_agent_registry.scan(agents_dir)
        return custom_agent_registry.to_sub_agent_configs(tool_map)
    except Exception as e:
        logger.warning(f"自定义 Agent 加载跳过 | error={e}")
        return []


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
            logger.warning(f"工具未找到: {name}")
    return tools
