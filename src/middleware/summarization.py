"""Summarization Middleware

检查对话历史 token 数，超过阈值时用 fast 模型压缩早期对话。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.logging import get_logger
from src.middleware.base import AgentMiddleware

if TYPE_CHECKING:
    from src.middleware.context import MiddlewareContext
    from src.schemas.agent import OrchestratorOutput

logger = get_logger(__name__)

# 粗略估算：1 token ≈ 4 字符（中英文混合场景偏保守）
CHARS_PER_TOKEN = 4
# 默认 context window 大小（Claude 系列）
DEFAULT_CONTEXT_WINDOW = 200_000


def _estimate_tokens(messages: list) -> int:
    """粗略估算对话历史的 token 数"""
    total_chars = 0
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content", "")
            total_chars += len(str(content))
        elif hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "content"):
                    total_chars += len(str(part.content))
        else:
            total_chars += len(str(msg))
    return total_chars // CHARS_PER_TOKEN


class SummarizationMiddleware(AgentMiddleware):
    """长对话摘要压缩

    Args:
        threshold_ratio: context window 占比阈值（默认 0.7）
        context_window: context window 大小（默认 200k）
        preserve_recent: 保留最近 N 条消息不压缩（默认 6）
    """

    def __init__(
        self,
        threshold_ratio: float = 0.7,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        preserve_recent: int = 6,
    ) -> None:
        self.threshold = int(context_window * threshold_ratio)
        self.preserve_recent = preserve_recent

    async def before_agent(self, context: MiddlewareContext) -> None:
        """检查 token 数，超阈值时压缩早期对话"""
        if not context.messages:
            return

        estimated_tokens = _estimate_tokens(context.messages)
        if estimated_tokens < self.threshold:
            return

        msg_count = len(context.messages)
        if msg_count <= self.preserve_recent:
            return

        # 分割：早期消息需要压缩，最近消息保留
        early_messages = context.messages[:-self.preserve_recent]
        recent_messages = context.messages[-self.preserve_recent:]

        logger.info(
            f"[Summarization] 触发摘要压缩 | "
            f"session_id={context.session_id} "
            f"estimated_tokens={estimated_tokens} threshold={self.threshold} "
            f"compressing={len(early_messages)} preserving={len(recent_messages)}"
        )

        try:
            summary = await self._summarize(early_messages)
            # 用摘要消息替换早期对话
            context.messages = [
                {"role": "system", "content": f"[对话历史摘要]\n{summary}"},
                *recent_messages,
            ]
            logger.info(
                f"[Summarization] 压缩完成 | "
                f"session_id={context.session_id} "
                f"before={msg_count} after={len(context.messages)}"
            )
        except Exception as e:
            logger.error(
                f"[Summarization] 压缩失败，保持原始对话 | "
                f"session_id={context.session_id} error={e}"
            )

    async def _summarize(self, messages: list) -> str:
        """用 fast 模型压缩对话历史"""
        from pydantic_ai import Agent
        from src.llm.config import get_model

        # 提取对话文本
        parts = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                parts.append(f"{role}: {content}")
            elif hasattr(msg, "parts"):
                for part in msg.parts:
                    if hasattr(part, "content"):
                        parts.append(str(part.content))

        conversation_text = "\n".join(parts)
        if len(conversation_text) > 8000:
            conversation_text = conversation_text[:8000]

        summarizer = Agent(
            model=get_model("fast"),
            output_type=str,
            instructions=(
                "你是一个对话摘要助手。将以下对话历史压缩为简洁的摘要，"
                "保留关键信息（用户意图、重要决策、工具执行结果）。"
                "摘要应该让后续对话能够理解上下文。使用中文。"
            ),
        )

        result = await summarizer.run(conversation_text)
        return result.output
