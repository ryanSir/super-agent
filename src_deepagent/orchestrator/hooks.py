"""Hooks — 事件推送 / 循环检测 / 安全审计

替代自建中间件管道，通过 deepagents Hooks 机制实现。
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from typing import Any

from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


# ── 事件推送 Hook ────────────────────────────────────────


class EventPushHook:
    """工具调用事件推送到 Redis Stream → SSE → 前端"""

    def __init__(self, publish_fn: Any = None) -> None:
        self._publish = publish_fn

    async def __call__(self, event_type: str, data: dict[str, Any], ctx: Any) -> None:
        if not self._publish:
            return

        session_id = ""
        if hasattr(ctx, "deps") and hasattr(ctx.deps, "metadata"):
            session_id = ctx.deps.metadata.get("session_id", "")

        event = {
            "event_type": event_type,
            "tool_name": data.get("tool_name", ""),
            "timestamp": time.time(),
        }

        # 不推送完整 args/result 到前端（可能包含大量数据）
        if "tool_args" in data:
            args_str = str(data["tool_args"])
            event["tool_args_preview"] = args_str[:200]

        if "result" in data:
            result_str = str(data["result"])
            event["result_preview"] = result_str[:500]

        try:
            await self._publish(session_id, event)
        except Exception as e:
            logger.warning(f"事件推送失败 | session_id={session_id} error={e}")


# ── 循环检测 Hook ────────────────────────────────────────

_DEFAULT_WINDOW_SIZE = 20
_WARN_THRESHOLD = 3
_HARD_LIMIT = 5


class LoopDetectionHook:
    """循环检测：滑动窗口 + MD5 去重 + 警告 + 强制停止"""

    def __init__(
        self,
        window_size: int = _DEFAULT_WINDOW_SIZE,
        warn_threshold: int = _WARN_THRESHOLD,
        hard_limit: int = _HARD_LIMIT,
    ) -> None:
        self._window_size = window_size
        self._warn_threshold = warn_threshold
        self._hard_limit = hard_limit
        self._call_hashes: deque[str] = deque(maxlen=window_size)
        self._hash_counts: dict[str, int] = {}

    async def __call__(self, event_type: str, data: dict[str, Any], ctx: Any) -> None:
        if event_type != "tool_call":
            return

        tool_name = data.get("tool_name", "")
        tool_args = str(data.get("tool_args", ""))

        # 计算调用指纹
        fingerprint = hashlib.md5(
            f"{tool_name}:{tool_args}".encode()
        ).hexdigest()

        # 更新滑动窗口
        if len(self._call_hashes) >= self._window_size:
            evicted = self._call_hashes[0]
            self._hash_counts[evicted] = max(0, self._hash_counts.get(evicted, 0) - 1)
            if self._hash_counts[evicted] == 0:
                self._hash_counts.pop(evicted, None)

        self._call_hashes.append(fingerprint)
        self._hash_counts[fingerprint] = self._hash_counts.get(fingerprint, 0) + 1

        count = self._hash_counts[fingerprint]

        if count >= self._hard_limit:
            logger.error(
                f"循环检测: 强制停止 | tool={tool_name} count={count}/{self._hard_limit}"
            )
            raise LoopDetectedError(
                f"工具 '{tool_name}' 在滑动窗口内被调用 {count} 次，强制停止"
            )

        if count >= self._warn_threshold:
            logger.warning(
                f"循环检测: 警告 | tool={tool_name} count={count}/{self._hard_limit}"
            )

    def reset(self) -> None:
        """重置检测状态"""
        self._call_hashes.clear()
        self._hash_counts.clear()


class LoopDetectedError(Exception):
    """循环检测触发强制停止"""


# ── 安全审计 Hook ────────────────────────────────────────


class AuditLoggerHook:
    """安全审计日志：工具名/参数/耗时/结果"""

    def __init__(self) -> None:
        self._call_start_times: dict[str, float] = {}

    async def __call__(self, event_type: str, data: dict[str, Any], ctx: Any) -> None:
        tool_name = data.get("tool_name", "unknown")
        call_id = data.get("call_id", tool_name)

        if event_type == "tool_call":
            self._call_start_times[call_id] = time.monotonic()
            logger.info(
                f"[AUDIT] 工具调用开始 | tool={tool_name} "
                f"args={str(data.get('tool_args', ''))[:200]}"
            )

        elif event_type == "tool_result":
            start = self._call_start_times.pop(call_id, None)
            elapsed = f"{time.monotonic() - start:.2f}s" if start else "unknown"
            success = data.get("success", True)
            logger.info(
                f"[AUDIT] 工具调用完成 | tool={tool_name} "
                f"success={success} elapsed={elapsed} "
                f"result={str(data.get('result', ''))[:300]}"
            )


# ── 工厂函数 ─────────────────────────────────────────────


def create_hooks(publish_fn: Any = None) -> list[Any]:
    """创建所有 Hook 实例

    Args:
        publish_fn: 事件发布函数（async def publish(session_id, event)）

    Returns:
        Hook 实例列表
    """
    return [
        EventPushHook(publish_fn=publish_fn),
        LoopDetectionHook(),
        AuditLoggerHook(),
    ]
