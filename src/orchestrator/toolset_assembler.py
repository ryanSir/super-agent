"""工具集装配器

根据执行模式动态组装 Agent 可用的工具子集。
参考 Semantic Kernel 的 FunctionChoiceBehavior 设计。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic_ai import RunContext

from src.core.logging import get_logger
from src.orchestrator.intent_router import ExecutionMode

logger = get_logger(__name__)

# direct 模式下需要过滤的工具（规划相关）
_DIRECT_TOOL_BLACKLIST = frozenset([
    "plan_and_decompose",
    "list_available_skills",
    "create_new_skill",
])

# plan_and_execute 模式的 prompt 前缀
_PLAN_EXECUTE_PREFIX = (
    "[执行模式: plan_and_execute] "
    "这是一个复杂的多步骤任务，请先调用 plan_and_decompose 进行任务规划，"
    "然后按照 DAG 拓扑顺序逐步执行各子任务。\n\n"
)


@dataclass
class AssembleResult:
    """工具集装配结果

    Args:
        tool_filter: 工具名称黑名单（这些工具将从 Agent 可用列表中移除）
        prompt_prefix: 注入到 query 前的文本
        agent_override: 可选的替代 Agent 实例（用于 direct 模式备选方案）
    """
    tool_filter: Optional[List[str]] = None
    prompt_prefix: str = ""
    agent_override: Optional[Any] = None


class ToolSetAssembler:
    """工具集装配器

    根据 ExecutionMode 返回该模式下 Agent 可用的工具配置。
    """

    def __init__(self) -> None:
        # direct 模式的 Agent 实例（lazy 初始化）
        self._direct_agent: Optional[Any] = None

    def assemble(self, mode: ExecutionMode) -> AssembleResult:
        """根据执行模式装配工具集

        Args:
            mode: 执行模式

        Returns:
            AssembleResult 包含工具过滤和 prompt 配置
        """
        if mode == ExecutionMode.DIRECT:
            result = AssembleResult(
                tool_filter=list(_DIRECT_TOOL_BLACKLIST),
                prompt_prefix="",
                agent_override=self._get_direct_agent(),
            )
            logger.info(
                f"[ToolSetAssembler] 装配完成 | mode=direct "
                f"filtered={_DIRECT_TOOL_BLACKLIST}"
            )
            return result

        if mode == ExecutionMode.PLAN_AND_EXECUTE:
            result = AssembleResult(
                tool_filter=None,
                prompt_prefix=_PLAN_EXECUTE_PREFIX,
            )
            logger.info("[ToolSetAssembler] 装配完成 | mode=plan_and_execute prompt_prefix=yes")
            return result

        # AUTO: 全量工具，无约束
        logger.info("[ToolSetAssembler] 装配完成 | mode=auto full_toolset")
        return AssembleResult()

    def _get_direct_agent(self) -> Any:
        """获取 direct 模式专用 Agent（lazy 初始化）

        排除 plan_and_decompose / list_available_skills / create_new_skill 工具，
        防止 Agent 进行不必要的规划。
        """
        if self._direct_agent is not None:
            return self._direct_agent

        try:
            from pydantic_ai import Agent
            from pydantic_ai.models.instrumented import InstrumentationSettings

            from src.llm.config import get_model
            from src.orchestrator.prompts.system import build_system_prompt
            from src.schemas.agent import OrchestratorOutput

            # 导入依赖类型
            from src.orchestrator.orchestrator_agent import OrchestratorDeps

            # 动态构建 system prompt
            from src.skills.registry import skill_registry
            skill_summary = skill_registry.get_skill_summary()

            direct_agent = Agent(
                model=get_model("planning"),
                output_type=OrchestratorOutput,
                deps_type=OrchestratorDeps,
                instructions=build_system_prompt(skill_summary=skill_summary),
                name="Orchestrator-Direct",
                retries=3,
                instrument=InstrumentationSettings(version=1),
            )

            # 注册 direct 模式需要的工具（排除规划相关工具）
            self._register_direct_tools(direct_agent)

            self._direct_agent = direct_agent
            logger.info("[ToolSetAssembler] direct Agent 初始化完成")
            return self._direct_agent
        except Exception as e:
            logger.warning(f"[ToolSetAssembler] direct Agent 初始化失败，返回 None | error={e}")
            return None

    def _register_direct_tools(self, agent: Any) -> None:
        """为 direct Agent 注册工具（排除规划相关）"""
        import uuid
        from typing import Any as TypAny, Dict, List, Optional

        from src.orchestrator.orchestrator_agent import (
            OrchestratorDeps,
            _push_event,
        )
        from src.schemas.agent import WorkerResult

        # PydanticAI 的 @agent.tool 用 get_type_hints() 解析注解，
        # 它只从 module globals 查找类型。需要把 OrchestratorDeps 注入模块全局。
        import src.orchestrator.toolset_assembler as _self_module
        _self_module.OrchestratorDeps = OrchestratorDeps

        @agent.tool
        async def execute_native_worker(
            ctx: RunContext[OrchestratorDeps],
            task_id: str,
            task_type: str,
            description: str,
            input_data: Dict[str, TypAny],
        ) -> Dict[str, TypAny]:
            """执行可信子任务（Python 原生 Worker）"""
            from src.orchestrator.orchestrator_agent import execute_native_worker as _orig
            return await _orig(ctx, task_id, task_type, description, input_data)

        @agent.tool
        async def execute_sandbox_task(
            ctx: RunContext[OrchestratorDeps],
            task_id: str,
            instruction: str,
            context_files: Optional[Dict[str, str]] = None,
        ) -> Dict[str, TypAny]:
            """执行沙箱高危任务（E2B 隔离环境）"""
            from src.orchestrator.orchestrator_agent import execute_sandbox_task as _orig
            return await _orig(ctx, task_id, instruction, context_files)

        @agent.tool
        async def execute_skill(
            ctx: RunContext[OrchestratorDeps],
            skill_name: str,
            params: Dict[str, TypAny],
        ) -> Dict[str, TypAny]:
            """执行已注册的 Skill"""
            from src.orchestrator.orchestrator_agent import execute_skill as _orig
            return await _orig(ctx, skill_name, params)

        @agent.tool
        async def search_skills(
            ctx: RunContext[OrchestratorDeps],
            query: str,
        ) -> Dict[str, TypAny]:
            """按关键词检索匹配的 Skill"""
            from src.orchestrator.orchestrator_agent import search_skills as _orig
            return await _orig(ctx, query)

        @agent.tool
        async def recall_memory(
            ctx: RunContext[OrchestratorDeps],
            user_id: str,
        ) -> Dict[str, TypAny]:
            """检索用户历史记忆"""
            from src.orchestrator.orchestrator_agent import recall_memory as _orig
            return await _orig(ctx, user_id)

        @agent.tool
        async def emit_chart(
            ctx: RunContext[OrchestratorDeps],
            title: str,
            chart_type: str,
            x_axis: List[str],
            series_data: TypAny,
        ) -> Dict[str, TypAny]:
            """渲染数据图表到前端"""
            from src.orchestrator.orchestrator_agent import emit_chart as _orig
            return await _orig(ctx, title, chart_type, x_axis, series_data)

        @agent.tool
        async def emit_widget(
            ctx: RunContext[OrchestratorDeps],
            ui_component: str,
            props: Dict[str, TypAny],
        ) -> Dict[str, TypAny]:
            """渲染任意前端组件"""
            from src.orchestrator.orchestrator_agent import emit_widget as _orig
            return await _orig(ctx, ui_component, props)


# 全局单例
toolset_assembler = ToolSetAssembler()
