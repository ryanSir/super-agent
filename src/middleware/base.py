"""Agent Middleware 抽象基类

定义 before_agent / after_agent / on_tool_call / on_tool_error 四个钩子。
所有钩子为 async 方法，子类按需覆写。
"""

from __future__ import annotations

import asyncio
import inspect
from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from src.middleware.context import MiddlewareContext
    from src.schemas.agent import OrchestratorOutput


class AgentMiddleware(ABC):
    """Agent 级别中间件基类

    子类覆写需要的钩子即可，未覆写的钩子使用默认空实现。
    """

    async def before_agent(self, context: MiddlewareContext) -> None:
        """Agent 执行前钩子"""

    async def after_agent(
        self,
        context: MiddlewareContext,
        result: OrchestratorOutput,
    ) -> OrchestratorOutput:
        """Agent 执行后钩子，可修改并返回 result"""
        return result

    async def on_tool_call(
        self,
        context: MiddlewareContext,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Tool 调用拦截钩子，返回（可能修改过的）tool_args"""
        return tool_args

    async def on_tool_error(
        self,
        context: MiddlewareContext,
        tool_name: str,
        error: Exception,
    ) -> Optional[str]:
        """Tool 错误处理钩子，返回 fallback 内容或 None"""
        return None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """校验子类钩子方法必须是 async"""
        super().__init_subclass__(**kwargs)
        for name in ("before_agent", "after_agent", "on_tool_call", "on_tool_error"):
            method = getattr(cls, name, None)
            if method is not None and method is not getattr(AgentMiddleware, name):
                if not asyncio.iscoroutinefunction(method):
                    raise TypeError(
                        f"{cls.__name__}.{name} 必须是 async 方法"
                    )
