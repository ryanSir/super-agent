"""记忆更新防抖队列

对同一用户的多次更新请求进行防抖合并。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _PendingUpdate:
    """待处理的更新"""
    session_id: str
    messages: List
    queued_at: datetime = field(default_factory=datetime.now)


class MemoryUpdateQueue:
    """防抖记忆更新队列

    在防抖窗口内的多次提交合并为一次 LLM 调用。

    Args:
        debounce_seconds: 防抖窗口（默认 5 秒）
    """

    def __init__(self, debounce_seconds: float = 5.0) -> None:
        self._debounce = debounce_seconds
        # user_id → 待处理更新列表
        self._pending: Dict[str, List[_PendingUpdate]] = {}
        # user_id → 防抖定时器 task
        self._timers: Dict[str, asyncio.Task] = {}

    def add(
        self,
        session_id: str,
        messages: list,
        user_id: str = "default",
    ) -> None:
        """提交一次记忆更新请求

        Args:
            session_id: 会话 ID
            messages: 过滤后的对话消息
            user_id: 用户 ID（默认 "default"）
        """
        if user_id not in self._pending:
            self._pending[user_id] = []

        self._pending[user_id].append(_PendingUpdate(
            session_id=session_id,
            messages=messages,
        ))

        # 重置防抖定时器
        if user_id in self._timers:
            self._timers[user_id].cancel()

        self._timers[user_id] = asyncio.get_event_loop().create_task(
            self._debounce_flush(user_id)
        )

    async def _debounce_flush(self, user_id: str) -> None:
        """防抖窗口结束后触发实际更新"""
        await asyncio.sleep(self._debounce)

        pending = self._pending.pop(user_id, [])
        self._timers.pop(user_id, None)

        if not pending:
            return

        # 合并所有待处理消息
        all_messages = []
        last_session_id = ""
        for update in pending:
            all_messages.extend(update.messages)
            last_session_id = update.session_id

        logger.info(
            f"[MemoryQueue] 防抖触发 | "
            f"user_id={user_id} merged={len(pending)} messages={len(all_messages)}"
        )

        # 异步执行更新
        try:
            from src.config.settings import get_settings
            from src.memory.updater import MemoryUpdater

            settings = get_settings()
            updater = MemoryUpdater(
                max_facts=settings.memory.max_facts,
                model_alias=settings.memory.update_model,
            )
            await updater.update(
                user_id=user_id,
                messages=all_messages,
                session_id=last_session_id,
            )
        except Exception as e:
            logger.error(f"[MemoryQueue] 更新失败 | user_id={user_id} error={e}")


# 全局单例
_queue: Optional[MemoryUpdateQueue] = None


def get_memory_queue() -> MemoryUpdateQueue:
    global _queue
    if _queue is None:
        from src.config.settings import get_settings
        settings = get_settings()
        _queue = MemoryUpdateQueue(
            debounce_seconds=settings.memory.debounce_seconds,
        )
    return _queue
