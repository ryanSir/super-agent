"""ToolErrorHandling Middleware

捕获 tool 执行异常，转为错误消息返回给 Agent，防止整个请求失败。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from src.core.logging import get_logger
from src.middleware.base import AgentMiddleware

if TYPE_CHECKING:
    from src.middleware.context import MiddlewareContext

logger = get_logger(__name__)


class ToolErrorHandlingMiddleware(AgentMiddleware):
    """将 tool 异常转为错误消息，让 Agent 继续执行"""

    async def on_tool_error(
        self,
        context: MiddlewareContext,
        tool_name: str,
        error: Exception,
    ) -> Optional[str]:
        """捕获 tool 异常，返回格式化的错误消息"""
        detail = str(error).strip() or error.__class__.__name__
        if len(detail) > 500:
            detail = detail[:497] + "..."

        error_msg = (
            f"Error: Tool '{tool_name}' failed with "
            f"{error.__class__.__name__}: {detail}. "
            f"Continue with available context, or choose an alternative tool."
        )

        logger.warning(
            f"[ToolErrorHandling] tool 执行失败 | "
            f"session_id={context.session_id} tool={tool_name} "
            f"error_type={error.__class__.__name__} detail={detail[:100]}"
        )

        return error_msg
