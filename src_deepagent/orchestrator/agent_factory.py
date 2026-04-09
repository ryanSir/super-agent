"""主 Agent 工厂

基于 pydantic-deepagents 的 create_deep_agent() 创建主 Orchestrator Agent。
接收 ExecutionPlan 和 SubAgentConfig，输出配置完整的 Agent + Deps。
"""

from __future__ import annotations

from typing import Any

from src_deepagent.core.logging import get_logger
from src_deepagent.llm.config import get_model
from src_deepagent.orchestrator.hooks import create_hooks
from src_deepagent.orchestrator.prompts.system import build_dynamic_instructions
from src_deepagent.orchestrator.reasoning_engine import ExecutionPlan
from src_deepagent.schemas.agent import OrchestratorOutput

logger = get_logger(__name__)


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
    try:
        from pydantic_deep.agent import create_deep_agent, create_default_deps
        from pydantic_deep.deps import StateBackend
    except ImportError:
        logger.warning("pydantic-deep 未安装，使用 fallback 模式")
        return _create_fallback_agent(plan, session_id, trace_id)

    # 构建动态 system prompt
    from src_deepagent.config.settings import get_settings

    settings = get_settings()
    role_descriptions = [
        {"name": c["name"], "description": c["description"]}
        for c in sub_agent_configs
    ]
    instructions = build_dynamic_instructions(
        skill_summary=plan.resources.prompt_ctx.skill_summary,
        sub_agent_roles=role_descriptions,
        deferred_tool_names=plan.resources.prompt_ctx.deferred_tool_names,
        max_concurrent_subagents=settings.max_concurrent_subagents,
        execution_mode=plan.mode.value,
    )

    # 构建 Hooks（TODO: 适配 deepagents Hook 数据类格式）
    # hooks = create_hooks(publish_fn=publish_fn)

    # 创建主 Agent
    agent = create_deep_agent(
        model=get_model("planning"),
        instructions=instructions,
        output_type=OrchestratorOutput,

        # deepagents 能力
        include_todo=True,
        include_subagents=True,
        include_filesystem=False,
        include_skills=False,
        include_memory=False,
        include_checkpoints=False,

        # 禁用内置 web 工具（不兼容 OpenAIChatModel）
        web_search=False,
        web_fetch=False,

        # 上下文管理
        context_manager=True,
        context_manager_max_tokens=200_000,

        # 成本追踪
        cost_tracking=True,

        # 工具（桥接工具）
        tools=plan.resources.agent_tools,

        # Sub-Agent 配置
        subagents=sub_agent_configs,

        # MCP（已获取）
        toolsets=plan.resources.infra.mcp_toolsets or [],

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


def _create_fallback_agent(
    plan: ExecutionPlan,
    session_id: str,
    trace_id: str,
) -> tuple[Any, Any]:
    """Fallback: pydantic-deep 不可用时使用原生 PydanticAI"""
    from pydantic_ai import Agent

    agent = Agent(
        model=get_model("planning"),
        output_type=OrchestratorOutput,
        instructions="你是一个智能编排助手。pydantic-deep 未安装，功能受限。",
        name="Orchestrator-Fallback",
        retries=2,
    )

    # 注册桥接工具
    for tool_fn in plan.resources.agent_tools:
        agent.tool(tool_fn)

    logger.warning("使用 Fallback Agent（pydantic-deep 未安装）")
    return agent, {"session_id": session_id, "trace_id": trace_id}
