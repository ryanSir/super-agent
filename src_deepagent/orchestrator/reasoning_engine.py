"""推理引擎 — ReasoningEngine

资源获取 + 执行模式决策。
默认 AUTO 模式，让主 Agent 自主判断是否规划/委派；用户可显式指定模式。
"""

from __future__ import annotations

import asyncio
import enum
from dataclasses import dataclass
from typing import Any, Callable

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


# ── 枚举与数据类 ─────────────────────────────────────────


class ExecutionMode(str, enum.Enum):
    """执行模式"""

    DIRECT = "direct"
    AUTO = "auto"
    PLAN_AND_EXECUTE = "plan_and_execute"
    SUB_AGENT = "sub_agent"


@dataclass(frozen=True)
class InfraResources:
    """底层基础设施资源（被桥接工具依赖）"""

    workers: dict[str, Any]


@dataclass(frozen=True)
class PromptContext:
    """注入 System Prompt 的文本内容"""

    skill_summary: str


@dataclass(frozen=True)
class ResolvedResources:
    """一次获取的全部资源，整个请求生命周期内共享

    三层结构：
    - infra: 底层资源（Workers/MCP 连接），被 agent_tools 依赖
    - agent_tools: 给 LLM 的工具函数列表，基于 infra 构建
    - mcp_toolsets: MCP 外部工具 toolsets（传入 Agent）
    - prompt_ctx: 给 System Prompt 的文本内容
    """

    infra: InfraResources
    agent_tools: dict[str, list[Callable]]
    mcp_toolsets: list[Any]
    prompt_ctx: PromptContext


@dataclass(frozen=True)
class ExecutionPlan:
    """推理引擎输出"""

    mode: ExecutionMode
    prompt_prefix: str
    resources: ResolvedResources



# ── ReasoningEngine ──────────────────────────────────────


class ReasoningEngine:
    """推理引擎

    资源获取 + 执行模式决策。
    默认 AUTO，让主 Agent 自主判断是否规划/委派；用户可显式覆盖。
    """

    def __init__(self, workers: dict[str, Any]) -> None:
        self._workers = workers
        self._resources_cache: ResolvedResources | None = None
        self._refresh_task: asyncio.Task | None = None

    async def startup(self) -> None:
        """启动时预热：创建 MCP Server 实例 + 预热资源缓存 + 启动定期刷新任务"""
        # 先创建 MCP Server 实例
        await self._connect_mcp()
        # 再预热资源缓存
        await self._resolve_resources()

        from src_deepagent.config.settings import get_settings
        interval = get_settings().mcp.refresh_interval
        if interval > 0:
            self._refresh_task = asyncio.create_task(self._refresh_loop(interval))
            logger.info(f"[ReasoningEngine] MCP 定期刷新已启动 | interval={interval}s")

    async def shutdown(self) -> None:
        """关闭时取消刷新任务"""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("[ReasoningEngine] 刷新任务已停止")

    async def reload_mcp(self) -> int:
        """手动触发 MCP 刷新，清除资源缓存

        Returns:
            刷新后的 MCPServer 数量
        """
        from src_deepagent.capabilities.mcp.client_manager import mcp_client_manager
        server_count = mcp_client_manager.refresh()
        self._resources_cache = None
        logger.info(f"[ReasoningEngine] MCP 手动刷新完成 | servers={server_count}")
        return server_count

    async def _refresh_loop(self, interval: int) -> None:
        """定期刷新 MCP 工具列表"""
        while True:
            await asyncio.sleep(interval)
            try:
                tool_count = await self.reload_mcp()
                logger.info(f"[ReasoningEngine] MCP 定期刷新完成 | tools={tool_count}")
            except Exception as e:
                logger.error(f"[ReasoningEngine] MCP 定期刷新失败 | error={e}")

    # ── 公开接口 ──────────────────────────────────────────

    async def decide(self, query: str, mode: str = "auto") -> ExecutionPlan:
        """决策 + 资源获取

        Args:
            query: 用户自然语言请求
            mode: 用户指定的模式（auto/direct/plan_and_execute/sub_agent）

        Returns:
            ExecutionPlan 包含模式和已获取资源
        """
        execution_mode = self._resolve_mode(mode)
        resources = await self._resolve_resources()

        plan = ExecutionPlan(
            mode=execution_mode,
            prompt_prefix="",
            resources=resources,
        )

        logger.info(
            f"[ReasoningEngine] 决策完成 | mode={execution_mode.value} "
            f"query={query[:80]}"
        )
        return plan

    def invalidate_cache(self) -> None:
        """清除资源缓存（用于测试或资源变更后）"""
        self._resources_cache = None

    # ── 模式决策 ──────────────────────────────────────────

    def _resolve_mode(self, mode: str) -> ExecutionMode:
        """模式决策：用户显式指定 → 否则 AUTO（让主 Agent 自主判断）"""
        if mode != "auto":
            try:
                return ExecutionMode(mode)
            except ValueError:
                logger.warning(f"无效的执行模式: {mode}，回退到 auto")
        return ExecutionMode.AUTO

    # ── 资源获取 ──────────────────────────────────────────

    async def _resolve_resources(self) -> ResolvedResources:
        """获取工具资源（缓存复用，MCP 刷新后自动失效重建）"""
        if self._resources_cache is not None:
            return self._resources_cache

        from src_deepagent.capabilities.base_tools import create_base_tools

        agent_tools = create_base_tools(self._workers)

        from src_deepagent.capabilities.mcp.client_manager import mcp_client_manager

        mcp_toolsets = mcp_client_manager.get_toolsets()

        infra = InfraResources(workers=self._workers)
        prompt_ctx = PromptContext(skill_summary="")

        self._resources_cache = ResolvedResources(
            infra=infra,
            agent_tools=agent_tools,
            mcp_toolsets=mcp_toolsets,
            prompt_ctx=prompt_ctx,
        )

        total_tools = sum(len(v) for v in agent_tools.values())
        logger.info(
            f"[ReasoningEngine] 资源获取完成 | "
            f"workers={len(self._workers)} "
            f"agent_tools={total_tools} (groups={list(agent_tools.keys())}) "
            f"mcp_toolsets={len(mcp_toolsets)}"
        )
        return self._resources_cache

    async def _connect_mcp(self) -> None:
        """创建 MCP Server 实例（pydantic-ai toolsets）"""
        from src_deepagent.config.settings import get_settings
        from src_deepagent.capabilities.mcp.client_manager import (
            mcp_client_manager,
            parse_mcp_servers,
        )

        settings = get_settings()
        endpoints = parse_mcp_servers(
            servers_json=settings.mcp.servers_json,
            fallback_url=settings.mcp.server_url,
        )

        if not endpoints:
            return

        try:
            server_count = mcp_client_manager.setup(endpoints)
            logger.info(f"[ReasoningEngine] MCP 初始化完成 | servers={server_count}")
        except Exception as e:
            logger.error(f"[ReasoningEngine] MCP 初始化异常 | error={e}")
