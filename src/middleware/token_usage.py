"""TokenUsage Middleware

Agent 执行后记录 token 用量到结构化日志和 Langfuse。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.logging import get_logger
from src.middleware.base import AgentMiddleware

if TYPE_CHECKING:
    from src.middleware.context import MiddlewareContext
    from src.schemas.agent import OrchestratorOutput

logger = get_logger(__name__)


class TokenUsageMiddleware(AgentMiddleware):
    """记录 LLM token 用量"""

    async def after_agent(
        self,
        context: MiddlewareContext,
        result: OrchestratorOutput,
    ) -> OrchestratorOutput:
        usage = context.token_usage
        if usage.total_tokens > 0:
            logger.info(
                f"[TokenUsage] LLM token usage | "
                f"session_id={context.session_id} "
                f"input={usage.input_tokens} output={usage.output_tokens} "
                f"total={usage.total_tokens}"
            )

            # 推送 middleware_event 到前端
            try:
                from src.streaming.stream_adapter import publish_event
                await publish_event(context.session_id, {
                    "event_type": "middleware_event",
                    "middleware_name": "token_usage",
                    "event_subtype": "usage_report",
                    "detail": {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "total_tokens": usage.total_tokens,
                    },
                })
            except Exception as e:
                logger.warning(f"[TokenUsage] 事件推送失败 | error={e}")

            # 记录到 Langfuse
            try:
                from src.monitoring.langfuse_tracer import observation_span
                async with observation_span(
                    name="token_usage",
                    trace_id=context.trace_id,
                    metadata={
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "total_tokens": usage.total_tokens,
                    },
                ):
                    pass
            except Exception:
                pass  # Langfuse 不可用时静默跳过

        return result
