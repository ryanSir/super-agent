"""Middleware Pipeline

洋葱模型：before_agent 按列表正序执行，after_agent 按列表逆序执行。
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, List

from src.core.logging import get_logger
from src.middleware.base import AgentMiddleware
from src.middleware.context import MiddlewareContext
from src.monitoring.pipeline_events import pipeline_step
from src.schemas.agent import OrchestratorOutput

logger = get_logger(__name__)


class MiddlewarePipeline:
    """中间件管道

    Args:
        middlewares: 有序的 middleware 列表
    """

    def __init__(self, middlewares: List[AgentMiddleware]) -> None:
        self._middlewares = list(middlewares)

    async def execute(
        self,
        context: MiddlewareContext,
        agent_fn: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:
        """执行 middleware 管道

        before_agent 按正序执行，agent_fn 执行后，after_agent 按逆序执行。

        Args:
            context: 中间件上下文
            agent_fn: 被包裹的 Agent 执行函数

        Returns:
            经过 after_agent 处理后的结果
        """
        # before_agent: 正序
        async with pipeline_step("middleware.before", session_id=context.session_id):
            for mw in self._middlewares:
                logger.info(
                    f"[MiddlewarePipeline] before_agent | "
                    f"middleware={mw.__class__.__name__} session_id={context.session_id}"
                )
                await mw.before_agent(context)

        # 执行 Agent
        result = await agent_fn(context)

        # after_agent: 逆序
        async with pipeline_step("middleware.after", session_id=context.session_id):
            for mw in reversed(self._middlewares):
                logger.info(
                    f"[MiddlewarePipeline] after_agent | "
                    f"middleware={mw.__class__.__name__} session_id={context.session_id}"
                )
                result = await mw.after_agent(context, result)

        return result
