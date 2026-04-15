"""统一能力注册表

汇总所有工具来源（Base Tools + Skills + MCP），提供统一的资源获取接口。
替代 ReasoningEngine._resolve_resources() 中散落的各种 import。
"""

from __future__ import annotations

from typing import Any, Callable

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


class CapabilityRegistry:
    """统一能力注册表

    三类工具来源：
    - base_tools: 内置工具（封装 Workers/Skills/Memory 等）
    - skills: 可插拔业务技能（三阶段渐进加载）
    - mcp: 外部工具协议（pydantic-ai MCPServer toolsets）
    """

    def __init__(self, workers: dict[str, Any]) -> None:
        from src_deepagent.capabilities.base_tools import create_base_tools
        from src_deepagent.capabilities.mcp.client_manager import mcp_client_manager
        from src_deepagent.capabilities.skills.registry import skill_registry

        self._base_tools = create_base_tools(workers)
        self._skill_registry = skill_registry
        self._mcp_manager = mcp_client_manager

        logger.info(
            f"CapabilityRegistry 初始化完成 | "
            f"base_tools={len(self._base_tools)} "
            f"skills={len(self._skill_registry.list_skills())} "
            f"mcp_servers={self._mcp_manager.server_count}"
        )

    def get_agent_tools(self) -> list[Callable]:
        """返回所有 base tools（给 Agent 的工具函数）"""
        return self._base_tools

    def get_mcp_toolsets(self) -> list[Any]:
        """返回 MCP toolsets（传入 create_deep_agent(toolsets=...)）"""
        return self._mcp_manager.get_toolsets()

    def get_prompt_context(self) -> dict[str, Any]:
        """返回注入 System Prompt 的文本内容"""
        return {
            "skill_summary": self._skill_registry.get_skill_summary(),
        }
