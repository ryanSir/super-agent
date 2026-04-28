"""主 Agent 工厂

基于 pydantic-deepagents 的 create_deep_agent() 创建主 Orchestrator Agent。
接收 ExecutionPlan 和 SubAgentConfig，输出配置完整的 Agent + Deps。
"""

from __future__ import annotations

import warnings
from typing import Any

# 抑制 pydantic-ai WebSearch/WebFetch 可选依赖警告
warnings.filterwarnings("ignore", message=".*WebSearch local fallback.*")
warnings.filterwarnings("ignore", message=".*WebFetch local fallback.*")

from pydantic_deep.agent import create_deep_agent, create_default_deps
from pydantic_deep.deps import StateBackend

from src_deepagent.core.logging import get_logger
from src_deepagent.llm.registry import get_model_bundle
from src_deepagent.orchestrator.hooks import create_hooks
from src_deepagent.capabilities.event_publishing import EventPublishingCapability
from src_deepagent.context.builder import build_dynamic_instructions
from src_deepagent.orchestrator.reasoning_engine import ExecutionPlan

logger = get_logger(__name__)


def _schedule_mcp_tools_debug_log(mcp_toolsets: list[Any]) -> None:
    """Log MCP tool names from the sync agent factory without blocking creation."""
    if not mcp_toolsets:
        logger.info("MCP 工具列表 | toolsets=0 tools=[]")
        return

    async def _log() -> None:
        for index, toolset in enumerate(mcp_toolsets):
            label = getattr(toolset, "label", type(toolset).__name__)
            try:
                tools = await toolset.get_tools(None)
                logger.info(
                    f"MCP 工具列表 | "
                    f"index={index} label={label} count={len(tools)} names={list(tools.keys())}"
                )
            except Exception as e:
                logger.warning(
                    f"MCP 工具列表获取失败 | "
                    f"index={index} label={label} error={e}"
                )

    try:
        import asyncio

        asyncio.create_task(_log())
    except RuntimeError:
        logger.warning("MCP 工具列表获取跳过 | reason=no_running_event_loop")


def create_orchestrator_agent(
    plan: ExecutionPlan,
    sub_agent_configs: list[dict[str, Any]],
    session_id: str = "",
    trace_id: str = "",
    publish_fn: Any = None,
) -> tuple[Any, Any]:
    """创建主 Orchestrator Agent

    Args:
        plan: ReasoningEngine 输出的执行计划
        sub_agent_configs: Sub-Agent 声明式配置列表
        session_id: 会话 ID
        trace_id: 追踪 ID
        publish_fn: 事件发布函数

    Returns:
        (agent, deps) 元组
    """
    from src_deepagent.config.settings import get_settings

    settings = get_settings()
    role_descriptions = [
        {"name": c["name"], "description": c["description"]}
        for c in sub_agent_configs
    ]
    instructions = build_dynamic_instructions(
        skill_summary=plan.resources.prompt_ctx.skill_summary,
        sub_agent_roles=role_descriptions,
        max_concurrent_subagents=settings.max_concurrent_subagents,
        execution_mode=plan.mode.value,
    )

    # 构建 Hooks（pydantic-deep 框架格式）
    hooks = create_hooks()

    # 构建 Capabilities 列表
    capabilities = []

    # 事件发布 Capability
    hook_settings = settings.hooks
    if hook_settings.event_publishing_enabled and publish_fn:
        capabilities.append(EventPublishingCapability(
            publish_fn=publish_fn,
            session_id=session_id,
            trace_id=trace_id,
        ))

    # 安全 — ToolGuard 工具黑名单
    if hook_settings.blocked_tools:
        try:
            from pydantic_ai_shields import ToolGuard
            blocked = [t.strip() for t in hook_settings.blocked_tools.split(",") if t.strip()]
            if blocked:
                capabilities.append(ToolGuard(blocked=blocked))
                logger.info(f"ToolGuard 已启用 | blocked={blocked}")
        except ImportError:
            logger.warning("pydantic_ai_shields 未安装，ToolGuard 不可用")

    # 统一使用 orchestrator 角色绑定的模型
    bundle = get_model_bundle("orchestrator", plan.mode.value)

    # MCP toolsets（pydantic-ai MCPServer 实例）
    mcp_toolsets = plan.resources.mcp_toolsets
    _schedule_mcp_tools_debug_log(mcp_toolsets)

    # 创建主 Agent
    agent = create_deep_agent(
        model=bundle.model,
        instructions=instructions,
        hooks=hooks,
        capabilities=capabilities if capabilities else None,

        # deepagents 能力
        include_todo=True,
        include_subagents=True,
        include_filesystem=False,
        include_skills=True,
        include_memory=False,
        include_checkpoints=False,

        # Skill 目录配置
        skill_directories=[{"path": settings.skill_dir, "recursive": True}],

        # 禁用内置 web 工具（不兼容 OpenAIChatModel）
        web_search=False,
        web_fetch=False,

        # 禁用 create_deep_agent 内置 thinking，由 agent.iter() 的 model_settings 控制
        thinking=False,

        # 上下文管理
        context_manager=True,
        context_manager_max_tokens=200_000,

        # 成本追踪
        cost_tracking=True,

        # 工具（桥接工具 — 合并所有分组）
        tools=[t for group in plan.resources.agent_tools.values() for t in group],

        # MCP 外部工具（pydantic-ai toolsets）
        toolsets=mcp_toolsets if mcp_toolsets else None,

        # 关闭 patch_tool_calls，避免与 MCP toolset 错误处理冲突
        # （MCP 返回错误时框架已生成 retry-prompt，patch 会额外插入 tool-return 导致重复）
        patch_tool_calls=False,

        # Sub-Agent 配置
        subagents=sub_agent_configs,

        name="Orchestrator",
    )

    # 创建 Deps
    deps = create_default_deps(backend=StateBackend())
    if hasattr(deps, "metadata"):
        deps.metadata = {"session_id": session_id, "trace_id": trace_id}

    logger.info(
        f"主 Agent 创建完成 | mode={plan.mode.value} "
        f"sub_agents={[c['name'] for c in sub_agent_configs]} "
        f"tools={len(plan.resources.agent_tools)}"
    )
    return agent, deps
