"""Sub-Agent 配置工厂

合并预置角色（researcher/analyst/writer）和自定义角色（agents/ 目录）。
所有 sub-agent 统一注入全量 base tools（去掉 plan_and_decompose）+ MCP toolsets + SkillsToolset。
角色差异化通过 instructions 控制，而非限制工具集。
"""

from __future__ import annotations

from typing import Any, Callable

from src_deepagent.config.settings import get_settings
from src_deepagent.core.logging import get_logger
from src_deepagent.llm.config import get_model
from src_deepagent.agents.roles import (
    ANALYSIS_INSTRUCTIONS,
    RESEARCH_INSTRUCTIONS,
    WRITING_INSTRUCTIONS,
)

logger = get_logger(__name__)


def create_sub_agent_configs(
    agent_tools: dict[str, list[Callable]],
    mcp_toolsets: list[Any] | None = None,
    custom_agents_dir: str = "agents",
) -> list[dict[str, Any]]:
    """创建 Sub-Agent 配置（预置 + 自定义合并）

    Args:
        agent_tools: 按职责分组的工具函数字典
        mcp_toolsets: MCP 外部工具 toolsets（与主 Agent 共享）
        custom_agents_dir: 自定义 Agent 目录路径

    Returns:
        SubAgentConfig 兼容的配置字典列表
    """
    # 合并所有组（排除 plan 组，sub-agent 不应自己规划 DAG）
    all_tools: list[Callable] = []
    for group, tools in agent_tools.items():
        if group != "plan":
            all_tools.extend(tools)

    settings = get_settings()

    # 预置角色
    builtin = _create_builtin_configs(all_tools, mcp_toolsets, settings.skill_dir)

    # 自定义角色
    custom = _load_custom_configs(all_tools, mcp_toolsets, settings.skill_dir, custom_agents_dir)

    configs = builtin + custom

    logger.info(
        f"Sub-Agent 配置创建完成 | "
        f"builtin={[c['name'] for c in builtin]} "
        f"custom={[c['name'] for c in custom]} "
        f"tools={len(all_tools)} mcp_toolsets={len(mcp_toolsets) if mcp_toolsets else 0}"
    )
    return configs


def _create_base_subagent_config(
    name: str,
    description: str,
    instructions: str,
    tools: list[Callable],
    mcp_toolsets: list[Any] | None,
    skill_dir: str,
) -> dict[str, Any]:
    """创建单个 sub-agent 的基础配置（所有角色共享）"""
    config: dict[str, Any] = {
        "name": name,
        "description": description,
        "instructions": instructions,
        "model": get_model("subagent"),
        "include_todo": True,
        "include_filesystem": False,
        "include_subagents": False,
        "include_skills": True,
        "skill_directories": [{"path": skill_dir, "recursive": True}],
        "web_search": False,
        "web_fetch": False,
        "context_manager": True,
        "context_manager_max_tokens": 100_000,
        "cost_tracking": True,
        "tools": tools,
    }
    if mcp_toolsets:
        config["toolsets"] = mcp_toolsets
    return config


def _create_builtin_configs(
    tools: list[Callable],
    mcp_toolsets: list[Any] | None,
    skill_dir: str,
) -> list[dict[str, Any]]:
    """创建三个预置角色配置"""
    return [
        _create_base_subagent_config(
            name="researcher",
            description="信息检索与综合分析专家",
            instructions=RESEARCH_INSTRUCTIONS,
            tools=tools,
            mcp_toolsets=mcp_toolsets,
            skill_dir=skill_dir,
        ),
        _create_base_subagent_config(
            name="analyst",
            description="数据分析与可视化专家",
            instructions=ANALYSIS_INSTRUCTIONS,
            tools=tools,
            mcp_toolsets=mcp_toolsets,
            skill_dir=skill_dir,
        ),
        _create_base_subagent_config(
            name="writer",
            description="报告与文档撰写专家",
            instructions=WRITING_INSTRUCTIONS,
            tools=tools,
            mcp_toolsets=mcp_toolsets,
            skill_dir=skill_dir,
        ),
    ]


def _load_custom_configs(
    tools: list[Callable],
    mcp_toolsets: list[Any] | None,
    skill_dir: str,
    agents_dir: str,
) -> list[dict[str, Any]]:
    """加载自定义 Agent 配置"""
    try:
        from src_deepagent.agents.custom.registry import custom_agent_registry

        if not custom_agent_registry._scanned:
            custom_agent_registry.scan(agents_dir)
        return custom_agent_registry.to_sub_agent_configs(tools, mcp_toolsets, skill_dir)
    except Exception as e:
        logger.warning(f"自定义 Agent 加载跳过 | error={e}")
        return []
