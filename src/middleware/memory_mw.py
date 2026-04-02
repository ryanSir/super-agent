"""Memory Middleware

Agent 执行后，过滤对话内容并异步提交到记忆更新队列。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from src.core.logging import get_logger
from src.middleware.base import AgentMiddleware

if TYPE_CHECKING:
    from src.middleware.context import MiddlewareContext
    from src.schemas.agent import OrchestratorOutput

logger = get_logger(__name__)


def _filter_messages_for_memory(messages: list) -> list:
    """过滤对话，仅保留用户输入和最终 Agent 回复

    过滤掉：
    - Tool 中间消息（tool call results）
    - 带 tool_calls 的 AI 消息（中间步骤）
    """
    filtered = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "")
            if role == "user":
                filtered.append(msg)
            elif role == "assistant" and not msg.get("tool_calls"):
                filtered.append(msg)
        elif hasattr(msg, "parts"):
            # PydanticAI 消息格式：检查是否包含 tool call
            has_tool_call = any(
                hasattr(part, "tool_name") for part in msg.parts
            )
            if not has_tool_call:
                filtered.append(msg)
    return filtered


class MemoryMiddleware(AgentMiddleware):
    """异步更新跨会话记忆

    在 after_agent 中将过滤后的对话提交到记忆更新队列，
    不阻塞主请求流程。
    """

    async def after_agent(
        self,
        context: MiddlewareContext,
        result: OrchestratorOutput,
    ) -> OrchestratorOutput:
        # 检查记忆系统是否启用
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            if not settings.memory.enabled:
                return result
        except Exception:
            return result

        if not context.messages:
            return result

        filtered = _filter_messages_for_memory(context.messages)

        # 需要至少有用户消息和 Agent 回复
        has_user = any(
            (isinstance(m, dict) and m.get("role") == "user")
            for m in filtered
        )
        has_assistant = any(
            (isinstance(m, dict) and m.get("role") == "assistant")
            or (hasattr(m, "parts") and not any(hasattr(p, "tool_name") for p in m.parts))
            for m in filtered
        )

        if not has_user or not has_assistant:
            return result

        # 异步提交到记忆更新队列（不阻塞）
        try:
            from src.memory.queue import get_memory_queue
            queue = get_memory_queue()
            queue.add(
                session_id=context.session_id,
                messages=filtered,
            )
            logger.info(
                f"[MemoryMiddleware] 对话已提交到记忆队列 | "
                f"session_id={context.session_id} messages={len(filtered)}"
            )
        except Exception as e:
            logger.warning(
                f"[MemoryMiddleware] 记忆队列提交失败 | "
                f"session_id={context.session_id} error={e}"
            )

        return result
