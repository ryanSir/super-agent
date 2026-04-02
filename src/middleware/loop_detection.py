"""LoopDetection Middleware

检测重复 tool 调用，防止 Agent 陷入无限循环。
参考 deer-flow 的滑动窗口 + hash 方案。
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from src.core.logging import get_logger
from src.middleware.base import AgentMiddleware

if TYPE_CHECKING:
    from src.middleware.context import MiddlewareContext
    from src.schemas.agent import OrchestratorOutput

logger = get_logger(__name__)

_WARNING_MSG = (
    "[LOOP DETECTED] You are repeating the same tool calls. "
    "Stop calling tools and produce your final answer now. "
    "If you cannot complete the task, summarize what you accomplished so far."
)

_HARD_STOP_MSG = (
    "[FORCED STOP] Repeated tool calls exceeded the safety limit. "
    "Producing final answer with results collected so far."
)


def _hash_tool_calls(tool_calls: List[Dict[str, Any]]) -> str:
    """对 tool call 列表生成确定性 hash（name + args，顺序无关）"""
    normalized = sorted(
        [
            {
                "name": tc.get("name", ""),
                "args": tc.get("args", {}),
            }
            for tc in tool_calls
        ],
        key=lambda tc: (
            tc["name"],
            json.dumps(tc["args"], sort_keys=True, default=str),
        ),
    )
    blob = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.md5(blob.encode()).hexdigest()[:12]


class LoopDetectionMiddleware(AgentMiddleware):
    """检测并打断重复 tool 调用循环

    Args:
        warn_threshold: 相同 tool call 出现次数达到此值时注入警告（默认 3）
        hard_limit: 达到此值时强制终止 tool 调用（默认 5）
        window_size: 滑动窗口大小（默认 20）
    """

    def __init__(
        self,
        warn_threshold: int = 3,
        hard_limit: int = 5,
        window_size: int = 20,
    ) -> None:
        self.warn_threshold = warn_threshold
        self.hard_limit = hard_limit
        self.window_size = window_size
        # session_id → 最近 tool call hash 列表
        self._history: Dict[str, List[str]] = defaultdict(list)
        # session_id → 已警告过的 hash 集合
        self._warned: Dict[str, Set[str]] = defaultdict(set)

    async def after_agent(
        self,
        context: MiddlewareContext,
        result: OrchestratorOutput,
    ) -> OrchestratorOutput:
        """检查最近的 tool call 是否存在循环"""
        # 从对话历史中提取最后一轮的 tool calls
        tool_calls = self._extract_recent_tool_calls(context.messages)
        if not tool_calls:
            return result

        call_hash = _hash_tool_calls(tool_calls)
        sid = context.session_id

        history = self._history[sid]
        history.append(call_hash)
        if len(history) > self.window_size:
            history[:] = history[-self.window_size:]

        count = history.count(call_hash)
        tool_names = [tc.get("name", "?") for tc in tool_calls]

        if count >= self.hard_limit:
            logger.error(
                f"[LoopDetection] 强制终止 | "
                f"session_id={sid} hash={call_hash} count={count} tools={tool_names}"
            )
            # 推送事件
            await self._publish_event(sid, "hard_stop", tool_names)
            # 在 answer 中追加强制终止消息
            if result.answer:
                result.answer += f"\n\n{_HARD_STOP_MSG}"
            else:
                result.answer = _HARD_STOP_MSG
            return result

        if count >= self.warn_threshold:
            warned = self._warned[sid]
            if call_hash not in warned:
                warned.add(call_hash)
                logger.warning(
                    f"[LoopDetection] 检测到重复 | "
                    f"session_id={sid} hash={call_hash} count={count} tools={tool_names}"
                )
                await self._publish_event(sid, "warning", tool_names)
                # 注入警告到对话历史
                context.messages.append({
                    "role": "user",
                    "content": _WARNING_MSG,
                })

        return result

    def _extract_recent_tool_calls(self, messages: list) -> List[Dict[str, Any]]:
        """从对话历史中提取最近一轮的 tool calls"""
        tool_calls = []
        for msg in reversed(messages):
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    if hasattr(part, "tool_name") and hasattr(part, "args"):
                        tool_calls.append({
                            "name": part.tool_name,
                            "args": getattr(part, "args", {}),
                        })
                if tool_calls:
                    break
            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                for tc in msg.get("tool_calls", []):
                    tool_calls.append({
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    })
                if tool_calls:
                    break
        return tool_calls

    async def _publish_event(
        self, session_id: str, event_subtype: str, tool_names: list
    ) -> None:
        try:
            from src.streaming.stream_adapter import publish_event
            await publish_event(session_id, {
                "event_type": "middleware_event",
                "middleware_name": "loop_detection",
                "event_subtype": event_subtype,
                "detail": {"tools": tool_names},
            })
        except Exception as e:
            logger.warning(f"[LoopDetection] 事件推送失败 | error={e}")

    def reset(self, session_id: Optional[str] = None) -> None:
        """重置追踪状态"""
        if session_id:
            self._history.pop(session_id, None)
            self._warned.pop(session_id, None)
        else:
            self._history.clear()
            self._warned.clear()
